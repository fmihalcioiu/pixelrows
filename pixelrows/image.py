"""A grid of RGBA pixels to draw on."""
from __future__ import annotations

from .errors import PixelRowsError
from .palette import RGB, as_rgb

RGBA = tuple[int, int, int, int]


def _whole(what: str, value: int) -> int:
    """`value` if it is a whole number of 1 or more."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PixelRowsError(f"{what} must be a whole number of 1 or more, got {value!r}")
    return value


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

    def set(self, x: int, y: int, colour: str | RGB) -> None:
        """Lays one pixel of `colour` over (x, y). Outside the image it does nothing."""
        r, g, b = as_rgb(colour)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        at = (y * self.width + x) * 4
        data = self.data
        data[at:at + 4] = bytes((r, g, b, 255))

    def fill(self, x: int, y: int, w: int, h: int, colour: str | RGB) -> None:
        """Lays a `w` by `h` rectangle of `colour` with its top-left corner at (x, y), clipped to the image."""
        r, g, b = as_rgb(colour)
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + w, self.width), min(y + h, self.height)
        if left >= right or top >= bottom:
            return
        data = self.data
        for row_y in range(top, bottom):
            for col_x in range(left, right):
                at = (row_y * self.width + col_x) * 4
                data[at:at + 4] = bytes((r, g, b, 255))

    def copy(self) -> Image:
        """A new image with the same pixels. Drawing on one leaves the other as it is."""
        return Image._of(self.width, self.height, bytearray(self.data))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Image)
            and self.width == other.width
            and self.height == other.height
            and self.data == other.data
        )
