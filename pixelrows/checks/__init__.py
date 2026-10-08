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
    points: tuple[tuple[int, int], ...] = ()  # the cells it is about, as (x, y)

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

    lone_allow: frozenset[str] = frozenset()  # characters a lone pixel may be: eyes, glints


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
