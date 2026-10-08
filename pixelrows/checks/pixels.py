"""Rules that look at one sprite's cells."""
from __future__ import annotations

import math

from ..sprite import Sprite
from ..spriteset import SpriteSet
from . import Finding, Options

_AROUND = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def check(spriteset: SpriteSet, options: Options) -> list[Finding]:
    """The findings of every sprite, in the set's order."""
    found: list[Finding] = []
    for sprite in spriteset.sprites.values():
        found.extend(_lone_pixel(sprite, options))
        found.extend(_colour_count(sprite, options))
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


def _colour_count(sprite: Sprite, options: Options) -> list[Finding]:
    """One finding when the sprite uses more characters than it may."""
    used = len(sprite.chars_used())
    painted = sprite.painted()
    allowed = options.max_colours
    if allowed is None:
        allowed = max(3, math.ceil(painted / options.pixels_per_colour))
    if used <= allowed:
        return []
    message = f"uses {used} colours, {allowed} allowed for {painted} painted pixels"
    return [Finding("colour_count", sprite.name, message)]
