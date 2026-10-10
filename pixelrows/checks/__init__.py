"""Checks: rules that read a sprite set and say what looks wrong in it."""
from __future__ import annotations

import math
import pkgutil
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module

from ..errors import PixelRowsError
from ..palette import TRANSPARENT
from ..spriteset import SpriteSet


@dataclass(frozen=True)
class Finding:
    """One thing a rule found."""

    rule: str  # the rule's name, such as 'lone_pixel'
    target: str  # the sprite's name, or the anim's
    message: str
    points: tuple[tuple[int, int], ...] = ()  # the cells it is about, as (x, y), when it is about cells

    def to_dict(self) -> dict:
        """The finding as plain data, each point a list of x and y."""
        return {
            "rule": self.rule,
            "target": self.target,
            "message": self.message,
            "points": [[x, y] for x, y in self.points],
        }


@dataclass(frozen=True)
class Options:
    """
    What the rules go by.

    `lone_allow` is given as a string or any iterable of single characters, and
    is kept as a frozenset. PixelRowsError naming the option when one is given
    a value it cannot have.
    """

    outline: str | None = None  # the outline character; without one, outline_gap is skipped
    lone_allow: frozenset[str] = frozenset()  # characters a lone pixel may be: eyes, glints
    max_colours: int | None = None  # colours a sprite may use; None works it out from its size
    pixels_per_colour: int = 6  # painted pixels that allow a sprite one colour, when its size sets the count
    frame_slack: float = 0.15  # how far from its clip's mean a frame's painted count may be, as a share of the mean
    feet_slack: int = 1  # how many rows the lowest painted row may move across a clip

    def __post_init__(self) -> None:
        """Holds every option to what it may be, and keeps `lone_allow` as a frozenset."""
        outline = self.outline
        if outline is not None and not (
            isinstance(outline, str) and len(outline) == 1 and not outline.isspace() and outline != TRANSPARENT
        ):
            raise PixelRowsError(f"outline must be one character that is not whitespace and not '.', got {outline!r}")
        object.__setattr__(self, "lone_allow", _characters("lone_allow", self.lone_allow))
        if self.max_colours is not None:
            _whole("max_colours", self.max_colours, 1)
        _whole("pixels_per_colour", self.pixels_per_colour, 1)
        slack = self.frame_slack
        if isinstance(slack, bool) or not isinstance(slack, (int, float)) or not _is_finite(slack) or slack < 0:
            raise PixelRowsError(f"frame_slack must be a finite number of 0 or more, got {slack!r}")
        _whole("feet_slack", self.feet_slack, 0)


def _characters(what: str, value: str | Iterable[str]) -> frozenset[str]:
    """The single characters of `value`, which is a string or an iterable of them, as a frozenset."""
    try:
        characters = frozenset(value)
    except TypeError:
        characters = None
    if characters is None or not all(isinstance(ch, str) and len(ch) == 1 for ch in characters):
        raise PixelRowsError(f"{what} must be a string or an iterable of single characters, got {value!r}")
    return characters


def _whole(what: str, value: int, least: int) -> int:
    """`value` if it is a whole number of `least` or more: an int, and not a bool."""
    if not isinstance(value, int) or isinstance(value, bool) or value < least:
        raise PixelRowsError(f"{what} must be a whole number of {least} or more, got {value!r}")
    return value


def _is_finite(value: int | float) -> bool:
    """Whether a number is finite as a float. A whole number too large to be a float is not."""
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def run(spriteset: SpriteSet, options: Options | None = None) -> list[Finding]:
    """
    The findings of every rule, on the default options when none are given.

    Every other module of this package is a rule module: it has a `check` that
    takes the set and the options. They are called in the order of their names.
    """
    if options is None:
        options = Options()
    found: list[Finding] = []
    for name in sorted(module.name for module in pkgutil.iter_modules(__path__)):
        found.extend(import_module(f"{__name__}.{name}").check(spriteset, options))
    return found
