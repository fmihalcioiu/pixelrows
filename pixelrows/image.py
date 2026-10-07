"""A grid of RGBA pixels to draw on and save as a PNG."""
from __future__ import annotations

import os
import re
import struct

from . import png
from .errors import PixelRowsError
from .palette import RGB, as_rgb

RGBA = tuple[int, int, int, int]

# In a row's alpha bytes: a run of opaque pixels, or one pixel that is partly transparent.
_PAINTED = re.compile(rb"\xff+|[\x01-\xfe]")


def _whole(what: str, value: int) -> int:
    """`value` if it is a whole number of 1 or more."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PixelRowsError(f"{what} must be a whole number of 1 or more, got {value!r}")
    return value


def _alpha(value: int) -> int:
    """`value` if it is a whole number from 0 to 255."""
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255:
        raise PixelRowsError(f"alpha must be a whole number from 0 to 255, got {value!r}")
    return value


def _over(sr: int, sg: int, sb: int, sa: int, dr: int, dg: int, db: int, da: int) -> RGBA:
    """
    One pixel laid over another (source-over), every channel rounded to the nearest whole number.

    The first four numbers are the pixel on top, the last four the one underneath.
    """
    if sa == 255:
        return sr, sg, sb, 255
    if sa == 0:
        return dr, dg, db, da
    under = da * (255 - sa)
    total = sa * 255 + under
    top = sa * 255
    return (
        (2 * (sr * top + dr * under) + total) // (2 * total),
        (2 * (sg * top + dg * under) + total) // (2 * total),
        (2 * (sb * top + db * under) + total) // (2 * total),
        (2 * total + 255) // 510,
    )


class Image:
    """
    Pixels in a bytearray, four bytes each (red, green, blue, alpha), row by row from the top.

    Colours are given as '#rrggbb' or (r, g, b). An alpha of 255 is solid and 0 is nothing.
    """

    def __init__(self, width: int, height: int, background: str | RGB | None = None):
        self.width = _whole("image width", width)
        self.height = _whole("image height", height)
        if background is None:
            self.data = bytearray(width * height * 4)
        else:
            self.data = bytearray(bytes((*as_rgb(background), 255)) * (width * height))

    @classmethod
    def _of(cls, width: int, height: int, data: bytearray) -> Image:
        """An image around pixels that are already laid out."""
        image = cls.__new__(cls)
        image.width = width
        image.height = height
        image.data = data
        return image

    def get(self, x: int, y: int) -> RGBA:
        """The pixel at (x, y) as (r, g, b, a). IndexError outside the image."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"({x}, {y}) is outside the {self.width}x{self.height} image")
        at = (y * self.width + x) * 4
        data = self.data
        return data[at], data[at + 1], data[at + 2], data[at + 3]

    def set(self, x: int, y: int, colour: str | RGB, alpha: int = 255) -> None:
        """Lays one pixel of `colour` over (x, y). Outside the image it does nothing."""
        r, g, b = as_rgb(colour)
        alpha = _alpha(alpha)
        if alpha == 0 or not (0 <= x < self.width and 0 <= y < self.height):
            return
        at = (y * self.width + x) * 4
        data = self.data
        data[at:at + 4] = bytes(_over(r, g, b, alpha, data[at], data[at + 1], data[at + 2], data[at + 3]))

    def fill(self, x: int, y: int, w: int, h: int, colour: str | RGB, alpha: int = 255) -> None:
        """Lays a `w` by `h` rectangle of `colour` with its top-left corner at (x, y), clipped to the image."""
        r, g, b = as_rgb(colour)
        alpha = _alpha(alpha)
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + w, self.width), min(y + h, self.height)
        if alpha == 0 or left >= right or top >= bottom:
            return
        data = self.data
        stride = self.width * 4
        span = (right - left) * 4
        first = top * stride + left * 4
        starts = range(first, first + (bottom - top) * stride, stride)
        if alpha == 255:
            row = bytes((r, g, b, 255)) * (right - left)
            for start in starts:
                data[start:start + span] = row
            return
        # A pixel value that came up before is not worked out again, and neither
        # is a row that reads the same as the one above it.
        known: dict[bytes, bytes] = {}
        before = laid = b""
        for start in starts:
            row = bytes(data[start:start + span])
            if row != before:
                before = row
                parts = []
                for at in range(0, span, 4):
                    pixel = row[at:at + 4]
                    mixed = known.get(pixel)
                    if mixed is None:
                        mixed = known[pixel] = bytes(_over(r, g, b, alpha, *pixel))
                    parts.append(mixed)
                laid = b"".join(parts)
            data[start:start + span] = laid

    def blit(self, other: Image, x: int, y: int) -> None:
        """Lays `other` over this image with its top-left corner at (x, y), clipped to this image."""
        if not isinstance(other, Image):
            raise PixelRowsError(f"blit takes an Image, got {type(other).__name__}")
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + other.width, self.width), min(y + other.height, self.height)
        if left >= right or top >= bottom:
            return
        # An image laid over itself is read as it was before the call.
        source = bytes(other.data) if other is self else other.data
        data = self.data
        span = (right - left) * 4
        for row_y in range(top, bottom):
            src = ((row_y - y) * other.width + (left - x)) * 4
            dst = (row_y * self.width + left) * 4
            row = bytes(source[src:src + span])
            # Opaque runs are copied whole, partly transparent pixels are laid
            # over one at a time, and fully transparent ones are passed by.
            for run in _PAINTED.finditer(row[3::4]):
                lo, hi = run.start() * 4, run.end() * 4
                if row[lo + 3] == 255:
                    data[dst + lo:dst + hi] = row[lo:hi]
                else:
                    data[dst + lo:dst + hi] = bytes(_over(*row[lo:hi], *data[dst + lo:dst + hi]))

    def scaled(self, factor: int) -> Image:
        """A new image `factor` times the size: every pixel becomes a `factor` by `factor` block."""
        _whole("scale factor", factor)
        if factor == 1:
            return self.copy()
        data = bytes(self.data)
        stride = self.width * 4
        out = bytearray()
        for start in range(0, len(data), stride):
            row = data[start:start + stride]
            wide = b"".join(row[at:at + 4] * factor for at in range(0, stride, 4))
            out += wide * factor
        return Image._of(self.width * factor, self.height * factor, out)

    def copy(self) -> Image:
        """A new image with the same pixels. Drawing on one leaves the other as it is."""
        return Image._of(self.width, self.height, bytearray(self.data))

    def colours(self) -> list[RGBA]:
        """Every distinct pixel value as (r, g, b, a), in order of first appearance, row by row."""
        return list(dict.fromkeys(struct.iter_unpack("4B", self.data)))

    def to_png(self) -> bytes:
        """The image as the bytes of a PNG file."""
        return png.encode_png(self.width, self.height, self.data)

    def save(self, path: str | os.PathLike[str]) -> None:
        """Writes the image to `path` as a PNG file. Folders on the way that do not exist are made."""
        png.write_png(path, self.width, self.height, self.data)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Image)
            and self.width == other.width
            and self.height == other.height
            and self.data == other.data
        )
