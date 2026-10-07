"""A canvas: something to paint on in code, which becomes a sprite."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .errors import PixelRowsError
from .palette import RGB, TRANSPARENT, Palette
from .sprite import Sprite

# The cells around a cell as (dx, dy): the four beside it, and the four at its corners.
_SIDES = ((0, -1), (-1, 0), (1, 0), (0, 1))
_CORNERS = ((-1, -1), (1, -1), (-1, 1), (1, 1))


def _whole(what: str, value: int) -> int:
    """`value` if it is a whole number of 1 or more."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PixelRowsError(f"{what} must be a whole number of 1 or more, got {value!r}")
    return value


def _one_character(ch: str) -> str:
    """`ch` if it is one character that is not whitespace."""
    if not isinstance(ch, str) or len(ch) != 1 or ch.isspace():
        raise PixelRowsError(f"ch is one character that is not whitespace, got {ch!r}")
    return ch


def _sprite_rows(what: str, rows: Iterable[str]) -> tuple[str, ...]:
    """`rows` as a tuple, held to the rules of a sprite's rows. The error names `what` in place of a sprite."""
    try:
        return Sprite(what, rows).rows
    except PixelRowsError as error:
        raise PixelRowsError(str(error).replace(f"sprite {what!r}", what, 1)) from None


class Canvas:
    """
    Something to paint on in code, which becomes a sprite.

    It is rows of characters, one for each pixel, and it starts all '.'. Every
    drawing method changes the canvas and returns it, so calls chain. Whatever
    falls outside the canvas is dropped without an error. `ch` is one character
    that is not whitespace; '.' is allowed and erases.
    """

    def __init__(self, width: int, height: int):
        _whole("canvas width", width)
        _whole("canvas height", height)
        self._grid = [[TRANSPARENT] * width for _ in range(height)]

    @classmethod
    def from_rows(cls, rows: Iterable[str]) -> Canvas:
        """A canvas holding `rows`, which keep the rules of a sprite's rows."""
        rows = _sprite_rows("canvas", rows)
        canvas = cls(len(rows[0]), len(rows))
        canvas._grid = [list(row) for row in rows]
        return canvas

    @classmethod
    def from_sprite(cls, sprite: Sprite) -> Canvas:
        """A canvas holding a copy of the sprite's rows. The sprite's name and palette are left behind."""
        if not isinstance(sprite, Sprite):
            raise PixelRowsError(f"from_sprite takes a Sprite, got {type(sprite).__name__}")
        return cls.from_rows(sprite.rows)

    @property
    def width(self) -> int:
        """How many pixels wide."""
        return len(self._grid[0])

    @property
    def height(self) -> int:
        """How many pixels tall."""
        return len(self._grid)

    def get(self, x: int, y: int) -> str:
        """The character at (x, y), or '.' anywhere outside the canvas."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self._grid[y][x]
        return TRANSPARENT

    def _put(self, x: int, y: int, ch: str) -> None:
        """Gives one cell a character. Outside the canvas it does nothing."""
        if 0 <= y < self.height and 0 <= x < self.width:
            self._grid[y][x] = ch

    def px(self, x: int, y: int, ch: str) -> Canvas:
        """Paints the one cell at (x, y)."""
        self._put(x, y, _one_character(ch))
        return self

    def rect(self, x: int, y: int, w: int, h: int, ch: str) -> Canvas:
        """Fills a box `w` wide and `h` tall, top-left corner at (x, y). A size of 0 or less draws nothing."""
        ch = _one_character(ch)
        for cy in range(max(y, 0), min(y + h, self.height)):
            for cx in range(max(x, 0), min(x + w, self.width)):
                self._grid[cy][cx] = ch
        return self

    def line(self, x0: int, y0: int, x1: int, y1: int, ch: str) -> Canvas:
        """
        Draws Bresenham's line from (x0, y0) to (x1, y1), both ends included.

        The cells are the same whichever end is given first.
        """
        ch = _one_character(ch)
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0, x1, y1 = y0, x0, y1, x1
        if x0 > x1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        step = 1 if y0 < y1 else -1
        error = 2 * dy - dx
        y = y0
        for x in range(x0, x1 + 1):
            if steep:
                self._put(y, x, ch)
            else:
                self._put(x, y, ch)
            if error > 0:
                y += step
                error -= 2 * dx
            error += 2 * dy
        return self

    def stamp(self, x: int, y: int, rows: Iterable[str] | Sprite | Canvas, flip: bool = False) -> Canvas:
        """
        Lays rows of characters down with their top-left corner at (x, y).

        A '.' in them keeps what is underneath. `rows` is a list of strings, a sprite or
        another canvas. A list of strings keeps the rules of a sprite's rows. `flip` lays
        the rows down turned left to right.
        """
        if isinstance(rows, Canvas):
            rows = rows.rows()
        elif isinstance(rows, Sprite):
            rows = rows.rows
        else:
            rows = _sprite_rows("stamp", rows)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(reversed(row) if flip else row):
                if ch != TRANSPARENT:
                    self._put(x + dx, y + dy, ch)
        return self

    def mirror(self) -> Canvas:
        """Copies the left half over the right half, mirrored. With an odd width the middle column stays."""
        for row in self._grid:
            for x in range(self.width // 2):
                row[-1 - x] = row[x]
        return self

    def outline(self, ch: str, grow: bool = False, diagonal: bool = False) -> Canvas:
        """
        Gives `ch` to every empty cell that has a painted cell above, below, left or right of it.

        `diagonal` counts the four diagonals as well. It is decided from the canvas as it was
        before the call, so the outline is one cell thick. `grow` first adds one empty cell on
        every side: the canvas gets 2 wider and 2 taller and the art moves by (1, 1), so no
        part of the outline is lost.
        """
        ch = _one_character(ch)
        if grow:
            blank = [TRANSPARENT] * (self.width + 2)
            self._grid = [blank[:], *([TRANSPARENT, *row, TRANSPARENT] for row in self._grid), blank[:]]
        before = Canvas.from_rows(self.rows())
        around = _SIDES + _CORNERS if diagonal else _SIDES
        for y in range(self.height):
            for x in range(self.width):
                if before.get(x, y) != TRANSPARENT:
                    continue
                if any(before.get(x + dx, y + dy) != TRANSPARENT for dx, dy in around):
                    self._grid[y][x] = ch
        return self

    def rows(self) -> list[str]:
        """The rows as strings, top to bottom."""
        return ["".join(row) for row in self._grid]

    def to_sprite(self, name: str, palette: Palette | Mapping[str, str | RGB | None] | None = None) -> Sprite:
        """A sprite of the canvas as it is now, with `name` and `palette` as `Sprite` takes them."""
        return Sprite(name, self.rows(), palette)
