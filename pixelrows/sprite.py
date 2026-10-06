"""A sprite: rows of characters, one character for each pixel."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .errors import PixelRowsError

TRANSPARENT = "."


class Sprite:
    """
    A named picture written as rows of characters, one character for each pixel.

    '.' is an empty pixel and every other character is a painted one. A sprite
    is not changed after it is made.
    """

    __slots__ = ("_name", "_rows")

    def __init__(self, name: str, rows: Iterable[str]):
        if not isinstance(name, str) or not name:
            raise PixelRowsError(f"a sprite's name is a non-empty string, got {name!r}")
        self._name = name
        self._rows = _checked_rows(name, rows)

    @property
    def name(self) -> str:
        """What the sprite is called."""
        return self._name

    @property
    def rows(self) -> tuple[str, ...]:
        """The rows, top to bottom."""
        return self._rows

    @property
    def width(self) -> int:
        """How many pixels wide."""
        return len(self._rows[0])

    @property
    def height(self) -> int:
        """How many pixels tall."""
        return len(self._rows)

    def at(self, x: int, y: int) -> str:
        """The character at (x, y), or '.' anywhere outside the sprite."""
        if 0 <= y < len(self._rows) and 0 <= x < len(self._rows[0]):
            return self._rows[y][x]
        return TRANSPARENT

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Sprite)
            and self._name == other._name
            and self._rows == other._rows
        )

    def __repr__(self) -> str:
        return f"Sprite({self._name!r}, {self.width}x{self.height})"


def _checked_rows(name: str, rows: Iterable[str]) -> tuple[str, ...]:
    """The rows as a tuple. PixelRowsError naming the sprite and the row if they break a rule."""
    where = f"sprite {name!r}"
    if isinstance(rows, str):
        raise PixelRowsError(f"{where}: rows are a list of strings, got one string {rows!r}")
    try:
        rows = tuple(rows)
    except TypeError:
        raise PixelRowsError(f"{where}: rows are a list of strings, got {rows!r}") from None
    if not rows:
        raise PixelRowsError(f"{where}: there are no rows")
    for y, row in enumerate(rows):
        if not isinstance(row, str):
            raise PixelRowsError(f"{where}: row {y} is not a string, got {row!r}")
        if not row:
            raise PixelRowsError(f"{where}: row {y} is empty")
        for x, ch in enumerate(row):
            if ch.isspace():
                raise PixelRowsError(f"{where}: row {y} has whitespace at column {x}")
    usual = Counter(len(row) for row in rows).most_common(1)[0][0]
    for y, row in enumerate(rows):
        if len(row) != usual:
            raise PixelRowsError(f"{where}: row {y} is {len(row)} wide, the others are {usual}")
    return rows
