"""Plain numbers about what is drawn, as data that goes straight to json.dumps."""
from __future__ import annotations

from .palette import Palette
from .sprite import Sprite
from .spriteset import Anim, SpriteSet


def sprite_info(sprite: Sprite, palette: Palette) -> dict:
    """One sprite: its size, how much of it is painted and where, and its colours in order of first appearance."""
    bbox = sprite.bbox()
    return {
        "name": sprite.name,
        "width": sprite.width,
        "height": sprite.height,
        "painted": sprite.painted(),
        "bbox": None if bbox is None else list(bbox),
        "colours": [
            {"char": ch, "hex": palette.hex(ch) if ch in palette else None, "count": count}
            for ch, count in sprite.chars_used().items()
        ],
    }


def anim_info(spriteset: SpriteSet, anim: Anim | str) -> dict:
    """One clip: its frames, its speed and length, the size its frames share and how much of each is painted."""
    if not isinstance(anim, Anim):
        anim = spriteset.anim(anim)
    sprites = [spriteset.sprites.get(frame) for frame in anim.frames]
    return {
        "name": anim.name,
        "frames": list(anim.frames),
        "fps": anim.fps,
        "seconds": round(anim.duration, 4),
        "size": _shared_size(sprites),
        "painted": [None if sprite is None else sprite.painted() for sprite in sprites],
    }


def set_info(spriteset: SpriteSet) -> dict:
    """A whole set: its palette, every sprite and every anim in the set's order, and what `problems` finds."""
    return {
        "palette": spriteset.palette.to_dict(),
        "sprites": [sprite_info(sprite, spriteset.palette_for(sprite)) for sprite in spriteset.sprites.values()],
        "anims": [anim_info(spriteset, anim) for anim in spriteset.anims.values()],
        "problems": spriteset.problems(),
    }


def _shared_size(sprites: list[Sprite | None]) -> list[int] | None:
    """[width, height] when every frame is there and they are all one size, otherwise None."""
    if any(sprite is None for sprite in sprites):
        return None
    sizes = {(sprite.width, sprite.height) for sprite in sprites}
    return list(sizes.pop()) if len(sizes) == 1 else None
