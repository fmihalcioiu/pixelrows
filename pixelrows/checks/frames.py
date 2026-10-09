"""Rules that hold the frames of a clip against each other."""
from __future__ import annotations

from ..errors import PixelRowsError
from ..sprite import Sprite
from ..spriteset import Anim, SpriteSet
from . import Finding, Options


def check(spriteset: SpriteSet, options: Options) -> list[Finding]:
    """
    The findings of every anim, in the set's order.

    An anim of one frame is skipped. So is one with a frame missing or with
    frames of different sizes, which `SpriteSet.problems` reports.
    """
    found: list[Finding] = []
    for anim in spriteset.anims.values():
        if len(anim.frames) < 2:
            continue
        try:
            frames = spriteset.frames_of(anim)
        except PixelRowsError:
            continue
        found.extend(_frame_pixels(anim, frames, options))
        found.extend(_feet_drift(anim, frames, options))
    return found


def _frame_pixels(anim: Anim, frames: list[Sprite], options: Options) -> list[Finding]:
    """One finding for each frame whose painted count is too far from the clip's mean."""
    counts = [frame.painted() for frame in frames]
    mean = sum(counts) / len(counts)
    found: list[Finding] = []
    for index, (name, count) in enumerate(zip(anim.frames, counts)):
        if abs(count - mean) > options.frame_slack * mean:
            message = f"frame {index} ({name!r}) has {count} painted pixels, the clip's mean is {mean:.1f}"
            found.append(Finding("frame_pixels", anim.name, message))
    return found


def _feet_drift(anim: Anim, frames: list[Sprite], options: Options) -> list[Finding]:
    """One finding when the lowest painted row moves too far across the frames that have anything painted."""
    feet = [box[1] + box[3] - 1 for box in (frame.bbox() for frame in frames) if box is not None]
    if not feet:
        return []
    top, bottom = min(feet), max(feet)
    if bottom - top <= options.feet_slack:
        return []
    message = f"the lowest painted row moves {bottom - top} rows across the clip (rows {top} to {bottom})"
    return [Finding("feet_drift", anim.name, message)]
