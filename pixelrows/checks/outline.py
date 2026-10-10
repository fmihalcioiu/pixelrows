"""A rule for sprites drawn with an outline."""
from __future__ import annotations

from ..palette import TRANSPARENT
from ..sprite import Sprite
from ..spriteset import SpriteSet
from . import Finding, Options

_BESIDE = ((0, -1), (-1, 0), (1, 0), (0, 1))


def check(spriteset: SpriteSet, options: Options) -> list[Finding]:
    """The findings of every sprite, in the set's order."""
    found: list[Finding] = []
    for sprite in spriteset.sprites.values():
        found.extend(_outline_gap(sprite, options))
    return found


def _outline_gap(sprite: Sprite, options: Options) -> list[Finding]:
    """
    One finding when edge cells of an outlined sprite are not the outline character.

    An edge cell is a painted cell with an empty cell or the sprite's border
    above, below, left or right of it. A sprite that does not use the outline
    character is not an outlined sprite, and is skipped.
    """
    outline = options.outline
    if outline is None or outline not in sprite.chars_used():
        return []
    edge = [
        (x, y, ch)
        for x, y, ch in sprite.cells()
        if any(sprite.at(x + dx, y + dy) == TRANSPARENT for dx, dy in _BESIDE)
    ]
    gaps = tuple((x, y) for x, y, ch in edge if ch != outline)
    if not gaps:
        return []
    verb = "is" if len(gaps) == 1 else "are"
    message = f"{len(gaps)} of {len(edge)} edge pixels {verb} not the outline {outline!r}"
    return [Finding("outline_gap", sprite.name, message, gaps)]
