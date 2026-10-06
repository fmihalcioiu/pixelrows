"""Colours by character: the table a sprite's rows are read against."""
from __future__ import annotations

from collections.abc import Iterator, Mapping

from .errors import PixelRowsError

RGB = tuple[int, int, int]

#: The one character that is never painted. It has no entry in a palette.
TRANSPARENT = "."

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def parse_hex(text: str) -> RGB:
    """'#rrggbb' or '#rgb' as (r, g, b)."""
    if not isinstance(text, str) or not text.startswith("#"):
        raise PixelRowsError(f"not a colour: {text!r} (expected '#rrggbb')")
    digits = text[1:]
    if len(digits) == 3:
        digits = "".join(d * 2 for d in digits)
    if len(digits) != 6 or not set(digits) <= _HEX_DIGITS:
        raise PixelRowsError(f"not a colour: {text!r} (expected '#rrggbb')")
    n = int(digits, 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def to_hex(rgb: RGB) -> str:
    """(r, g, b) as '#rrggbb', in lower case."""
    try:
        r, g, b = (int(v) for v in rgb)
    except (TypeError, ValueError):
        raise PixelRowsError(f"not a colour: {rgb!r} (expected three numbers)") from None
    if not all(0 <= v <= 255 for v in (r, g, b)):
        raise PixelRowsError(f"not a colour: {rgb!r} (each number is 0 to 255)")
    return f"#{r:02x}{g:02x}{b:02x}"


class Palette:
    """
    Characters and the colours they stand for.

    A key is one character. '.' is transparent in every palette: it is always
    known, it has no colour, and it cannot be given one.
    """

    def __init__(self, colours: Mapping[str, str | RGB | None] | None = None):
        self._hex: dict[str, str] = {}
        for ch, colour in (colours or {}).items():
            self.set(ch, colour)

    def set(self, ch: str, colour: str | RGB | None) -> None:
        """Gives `ch` a colour, or changes the one it has."""
        if not isinstance(ch, str) or len(ch) != 1:
            raise PixelRowsError(f"a palette key is one character, got {ch!r}")
        if ch == TRANSPARENT:
            if colour is None:
                return
            raise PixelRowsError("'.' is transparent and cannot be given a colour")
        if ch.isspace():
            raise PixelRowsError("a space cannot be a palette key")
        if colour is None:
            raise PixelRowsError(f"{ch!r} has no colour; only '.' is transparent")
        self._hex[ch] = to_hex(parse_hex(colour) if isinstance(colour, str) else colour)

    def hex(self, ch: str) -> str | None:
        """The colour of `ch` as '#rrggbb', or None for '.'. KeyError if `ch` is not in the palette."""
        if ch == TRANSPARENT:
            return None
        return self._hex[ch]

    def rgb(self, ch: str) -> RGB | None:
        """The colour of `ch` as (r, g, b), or None for '.'. KeyError if `ch` is not in the palette."""
        colour = self.hex(ch)
        return None if colour is None else parse_hex(colour)

    def __getitem__(self, ch: str) -> RGB | None:
        return self.rgb(ch)

    def __contains__(self, ch: object) -> bool:
        return ch == TRANSPARENT or ch in self._hex

    def chars(self) -> list[str]:
        """Every character with a colour, in the order they were given."""
        return list(self._hex)

    def __iter__(self) -> Iterator[str]:
        return iter(self._hex)

    def __len__(self) -> int:
        return len(self._hex)

    def to_dict(self) -> dict[str, str]:
        """Character to '#rrggbb', in order. What a set file stores."""
        return dict(self._hex)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Palette) and self._hex == other._hex

    def __repr__(self) -> str:
        return f"Palette({self._hex!r})"
