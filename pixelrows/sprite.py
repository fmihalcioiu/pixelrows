"""A sprite: rows of characters, one character for each pixel."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator

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

    def cells(self) -> Iterator[tuple[int, int, str]]:
        """Every painted cell as (x, y, character), row by row."""
        for y, row in enumerate(self._rows):
            for x, ch in enumerate(row):
                if ch != TRANSPARENT:
                    yield x, y, ch

    def painted(self) -> int:
        """How many cells are painted."""
        return sum(len(row) - row.count(TRANSPARENT) for row in self._rows)

    def chars_used(self) -> dict[str, int]:
        """The painted characters and how many cells each has, in order of first appearance."""
        counts: dict[str, int] = {}
        for _, _, ch in self.cells():
            counts[ch] = counts.get(ch, 0) + 1
        return counts

    def bbox(self) -> tuple[int, int, int, int] | None:
        """(x, y, width, height) of the smallest box holding every painted cell, or None if nothing is painted."""
        xs: list[int] = []
        ys: list[int] = []
        for x, y, _ in self.cells():
            xs.append(x)
            ys.append(y)
        if not xs:
            return None
        return min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1

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
