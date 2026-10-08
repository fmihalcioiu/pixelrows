"""Rules that look at one sprite's cells."""
from __future__ import annotations

from ..sprite import Sprite
from ..spriteset import SpriteSet
from . import Finding, Options

_AROUND = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def check(spriteset: SpriteSet, options: Options) -> list[Finding]:
    """The findings of every sprite, in the set's order."""
    found: list[Finding] = []
    for sprite in spriteset.sprites.values():
        found.extend(_lone_pixel(sprite, options))
    return found


def _lone_pixel(sprite: Sprite, options: Options) -> list[Finding]:
    """One finding when painted cells have no cell of their own character among the eight around them."""
    lone = tuple(
        (x, y)
        for x, y, ch in sprite.cells()
        if ch not in options.lone_allow and all(sprite.at(x + dx, y + dy) != ch for dx, dy in _AROUND)
    )
    if not lone:
        return []
    message = "1 lone pixel" if len(lone) == 1 else f"{len(lone)} lone pixels"
    return [Finding("lone_pixel", sprite.name, message, lone)]
