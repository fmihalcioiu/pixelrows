"""An anim as pictures: one image a frame, the time each frame shows, and the clip as a GIF file."""
from __future__ import annotations

import os
import struct
from pathlib import Path

from .errors import PixelRowsError
from .gif import encode_gif
from .image import RGBA, Image
from .palette import RGB
from .render import render_sprite
from .spriteset import FPS_MAX, FPS_MIN, Anim, SpriteSet

#: The most colours a GIF's table holds.
_MAX_COLOURS = 256

#: The shortest time a frame is given, in hundredths of a second.
_SHORTEST = 2


def frame_images(spriteset: SpriteSet, anim: Anim | str, scale: int = 1,
                 background: str | RGB | None = None) -> list[Image]:
    """
    One image for each frame of `anim`, in play order, `scale` pixels to the cell.

    Each frame is read against the set's palette with its own entries laid over
    it, on `background` or on nothing. PixelRowsError if the clip cannot play:
    a frame names no sprite, or the frames differ in size.
    """
    return [
        render_sprite(frame, spriteset.palette_for(frame), scale, background)
        for frame in spriteset.frames_of(anim)
    ]


def delays(fps: float, count: int) -> list[int]:
    """
    The time each of `count` frames shows at `fps`, in hundredths of a second.

    Each time is the gap between where the frame starts and where it ends,
    both rounded, so the clip as a whole runs at `fps` however the single
    frames round. No time is below 2.
    """
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not FPS_MIN <= fps <= FPS_MAX:
        raise PixelRowsError(f"fps must be from {FPS_MIN} to {FPS_MAX}, got {fps!r}")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise PixelRowsError(f"count must be a whole number of 1 or more, got {count!r}")
    return [
        max(_SHORTEST, round((i + 1) * 100 / fps) - round(i * 100 / fps))
        for i in range(count)
    ]


def gif_bytes(spriteset: SpriteSet, anim: Anim | str, scale: int = 1,
              background: str | RGB | None = None, loop: int = 0) -> bytes:
    """
    The bytes of a GIF file that plays `anim` at its own speed.

    The colour table is the colours of the frames in order of first
    appearance. Without a background the first entry is the transparent
    colour, and every pixel with nothing painted on it shows what is behind
    the picture. `loop` is how often the clip repeats, 0 for ever.
    PixelRowsError if the frames have more colours than a GIF holds.
    """
    if not isinstance(anim, Anim):
        anim = spriteset.anim(anim)
    images = frame_images(spriteset, anim, scale, background)
    see_through = background is None
    # Black stands in the table for the transparent colour, which is never shown.
    table: list[RGB] = [(0, 0, 0)] if see_through else []
    index_of: dict[RGBA, int] = {}
    for name, image in zip(anim.frames, images):
        for colour in image.colours():
            if colour in index_of:
                continue
            red, green, blue, alpha = colour
            if alpha == 255:
                index_of[colour] = len(table)
                table.append((red, green, blue))
            elif alpha == 0 and see_through:
                index_of[colour] = 0
            else:
                raise PixelRowsError(
                    f"anim {anim.name!r}: frame {name!r} has a pixel of alpha {alpha}, "
                    "a GIF holds alpha 255 and, without a background, alpha 0"
                )
    if len(table) > _MAX_COLOURS:
        counted = ", the transparent one counted" if see_through else ""
        raise PixelRowsError(
            f"anim {anim.name!r} needs {len(table)} colours{counted}, a GIF holds {_MAX_COLOURS} at most"
        )
    frames = [
        bytes(index_of[pixel] for pixel in struct.iter_unpack("4B", image.data))
        for image in images
    ]
    first = images[0]
    return encode_gif(first.width, first.height, frames, table, delays(anim.fps, len(images)), loop,
                      0 if see_through else None)


def save_gif(path: str | os.PathLike[str], spriteset: SpriteSet, anim: Anim | str, scale: int = 1,
             background: str | RGB | None = None, loop: int = 0) -> None:
    """Writes `anim` to `path` as a GIF file. Folders on the way that do not exist are made."""
    data = gif_bytes(spriteset, anim, scale, background, loop)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
