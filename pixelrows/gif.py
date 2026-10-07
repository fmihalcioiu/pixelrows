"""GIF89a files from frames of palette indices, written with the standard library alone."""
from __future__ import annotations

import os
import struct
from collections.abc import Sequence
from pathlib import Path

from .errors import PixelRowsError
from .palette import RGB, as_rgb

_MAX_COLOURS = 256
_MAX_U16 = 65535

#: A code is never wider than 12 bits, so a code table never holds more than 4096 entries.
_MAX_CODE_BITS = 12
_MAX_CODES = 1 << _MAX_CODE_BITS

#: The most bytes one data sub-block holds.
_BLOCK = 255


def _is_whole(value: object, low: int, high: int) -> bool:
    """True for an int from `low` to `high`. A bool is not a number here."""
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _table_bits(colours: int) -> int:
    """The bits that index a colour table holding `colours` entries: 1 for up to 2, 8 for up to 256."""
    return max(1, (colours - 1).bit_length())


def _lzw(indices: bytes | bytearray, min_code_size: int) -> bytes:
    """The LZW code stream for one frame's indices, codes packed lowest bit first."""
    clear = 1 << min_code_size
    end = clear + 1
    first_free = clear + 2
    first_size = min_code_size + 1

    out = bytearray()
    buffer = 0  # the bits not yet written out, the oldest lowest
    held = 0    # how many bits the buffer holds
    code_size = first_size

    def put(code: int) -> None:
        nonlocal buffer, held
        buffer |= code << held
        held += code_size
        while held >= 8:
            out.append(buffer & 255)
            buffer >>= 8
            held -= 8

    put(clear)
    # (the code of a string, the index after it) to the code of the longer string.
    table: dict[tuple[int, int], int] = {}
    next_code = first_free
    pixels = iter(indices)
    prefix = next(pixels)
    for index in pixels:
        code = table.get((prefix, index))
        if code is not None:
            prefix = code
            continue
        put(prefix)
        table[(prefix, index)] = next_code
        next_code += 1
        if next_code == _MAX_CODES:
            # The table is full. The clear code goes out at the current size, then all starts over.
            put(clear)
            table = {}
            next_code = first_free
            code_size = first_size
        elif next_code > 1 << code_size:
            # The code just handed out does not fit the current size, so codes are one bit wider
            # from here. The table is cleared before this can pass 12 bits.
            code_size += 1
        prefix = index
    put(prefix)
    if next_code == 1 << code_size:
        # A decoder makes a table entry after this code too, and reads the end code one bit wider.
        code_size += 1
    put(end)
    if held:
        out.append(buffer)
    return bytes(out)


def _sub_blocks(data: bytes) -> bytes:
    """`data` cut into sub-blocks of at most 255 bytes, each behind its length, with the empty block that ends them."""
    out = bytearray()
    for start in range(0, len(data), _BLOCK):
        block = data[start:start + _BLOCK]
        out.append(len(block))
        out += block
    out.append(0)
    return bytes(out)


def encode_gif(width: int, height: int, frames: Sequence[bytes], palette: Sequence[RGB],
               delays: Sequence[int], loop: int = 0, transparent: int | None = None) -> bytes:
    """
    The bytes of a GIF89a file that shows `frames` one after the other.

    Each frame is `width * height` bytes, one index into `palette` a pixel, row
    by row from the top. `delays` has one time a frame, in hundredths of a
    second. `loop` is how often the clip repeats, 0 for ever; it is stored only
    when there is more than one frame. `transparent` is the index that shows
    what is behind the picture, if any does.
    """
    for name, value in (("width", width), ("height", height)):
        if not _is_whole(value, 1, _MAX_U16):
            raise PixelRowsError(f"gif: {name} must be a whole number from 1 to {_MAX_U16}, got {value!r}")
    frames = list(frames)
    palette = list(palette)
    delays = list(delays)
    if not frames:
        raise PixelRowsError("gif: there are no frames")
    if not palette:
        raise PixelRowsError("gif: the palette is empty")
    if len(palette) > _MAX_COLOURS:
        raise PixelRowsError(f"gif: the palette has {len(palette)} colours, a GIF holds {_MAX_COLOURS} at most")
    colours: list[RGB] = []
    for i, colour in enumerate(palette):
        try:
            colours.append(as_rgb(colour))
        except PixelRowsError as error:
            raise PixelRowsError(f"gif: palette entry {i}: {error}") from None
    if len(delays) != len(frames):
        raise PixelRowsError(f"gif: there are {len(frames)} frames and {len(delays)} delays")
    for i, delay in enumerate(delays):
        if not _is_whole(delay, 0, _MAX_U16):
            raise PixelRowsError(f"gif: delay {i} must be a whole number from 0 to {_MAX_U16}, got {delay!r}")
    if not _is_whole(loop, 0, _MAX_U16):
        raise PixelRowsError(f"gif: loop must be a whole number from 0 to {_MAX_U16}, got {loop!r}")
    if transparent is not None and not _is_whole(transparent, 0, len(colours) - 1):
        raise PixelRowsError(
            f"gif: transparent must be an index from 0 to {len(colours) - 1}, got {transparent!r}"
        )
    size = width * height
    for i, frame in enumerate(frames):
        if not isinstance(frame, (bytes, bytearray)):
            raise PixelRowsError(f"gif: frame {i} must be bytes or a bytearray, got {type(frame).__name__}")
        if len(frame) != size:
            raise PixelRowsError(f"gif: frame {i} is {len(frame)} bytes, {width}x{height} needs {size}")
        if max(frame) >= len(colours):
            at = next(n for n, index in enumerate(frame) if index >= len(colours))
            raise PixelRowsError(
                f"gif: frame {i} has index {frame[at]} at ({at % width}, {at // width}), "
                f"the palette has {len(colours)} colours"
            )

    bits = _table_bits(len(colours))
    # The background is the transparent index when there is one, so that a frame
    # restored to background is cleared to nothing.
    background = 0 if transparent is None else transparent
    out = bytearray(b"GIF89a")
    # Logical screen: a global table follows; colour resolution and table size are both `bits`.
    out += struct.pack("<HHBBB", width, height, 0x80 | ((bits - 1) << 4) | (bits - 1), background, 0)
    # The table is black wherever the palette does not reach.
    out += b"".join(bytes(colour) for colour in colours).ljust(3 << bits, b"\x00")
    if len(frames) > 1:
        out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01" + struct.pack("<H", loop) + b"\x00"
    if transparent is None:
        control, see_through = 1 << 2, 0        # disposal 1: leave the frame in place
    else:
        control, see_through = (2 << 2) | 1, transparent    # disposal 2: restore to background
    min_code_size = max(2, bits)
    for frame, delay in zip(frames, delays):
        out += b"\x21\xf9\x04" + struct.pack("<BHB", control, delay, see_through) + b"\x00"
        out += b"\x2c" + struct.pack("<HHHHB", 0, 0, width, height, 0)
        out.append(min_code_size)
        out += _sub_blocks(_lzw(frame, min_code_size))
    out += b"\x3b"
    return bytes(out)


def write_gif(path: str | os.PathLike[str], width: int, height: int, frames: Sequence[bytes],
              palette: Sequence[RGB], delays: Sequence[int], loop: int = 0,
              transparent: int | None = None) -> None:
    """Writes the frames to `path` as a GIF file. Folders on the way that do not exist are made."""
    data = encode_gif(width, height, frames, palette, delays, loop, transparent)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
