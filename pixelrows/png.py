"""PNG files from raw RGBA pixels, written with the standard library alone."""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

from .errors import PixelRowsError

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, body: bytes) -> bytes:
    """One chunk: the body's length, the four-letter kind, the body, and the CRC of kind and body."""
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def encode_png(width: int, height: int, rgba: bytes | bytearray) -> bytes:
    """
    The bytes of a PNG file for `width` by `height` pixels.

    `rgba` holds four bytes a pixel (red, green, blue, alpha), row by row from
    the top. The file is 8 bits a channel, not interlaced, with one IDAT chunk.
    """
    for name, value in (("width", width), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise PixelRowsError(f"png: {name} must be a whole number of 1 or more, got {value!r}")
    if not isinstance(rgba, (bytes, bytearray)):
        raise PixelRowsError(f"png: the pixels must be bytes or a bytearray, got {type(rgba).__name__}")
    if len(rgba) != width * height * 4:
        raise PixelRowsError(
            f"png: {width}x{height} needs {width * height * 4} bytes of RGBA, got {len(rgba)}"
        )
    stride = width * 4
    # Every row is stored as it is, behind a filter byte of 0.
    rows = b"".join(b"\x00" + rgba[start:start + stride] for start in range(0, len(rgba), stride))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows, 9))
        + _chunk(b"IEND", b"")
    )


def write_png(path: str | os.PathLike[str], width: int, height: int, rgba: bytes | bytearray) -> None:
    """Writes the pixels to `path` as a PNG file. Folders on the way that do not exist are made."""
    data = encode_png(width, height, rgba)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
