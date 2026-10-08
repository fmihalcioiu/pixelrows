"""Checks: rules that read a sprite set and say what looks wrong in it."""
from __future__ import annotations

import pkgutil
from dataclasses import dataclass
from importlib import import_module

from ..spriteset import SpriteSet


@dataclass(frozen=True)
class Finding:
    """One thing a rule found."""

    rule: str  # the rule's name, such as 'lone_pixel'
    target: str  # the sprite's name
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
    """What the rules go by."""

    outline: str | None = None  # the outline character; without one, outline_gap is skipped
    lone_allow: frozenset[str] = frozenset()  # characters a lone pixel may be: eyes, glints
    max_colours: int | None = None  # colours a sprite may use; None works it out from its size
    pixels_per_colour: int = 6  # painted pixels that allow a sprite one colour, when its size sets the count


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
