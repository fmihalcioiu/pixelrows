"""A sprite set: one palette, the sprites read against it and the anims that play them, kept as a JSON file."""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .errors import PixelRowsError
from .palette import RGB, Palette
from .sprite import Sprite

_TOP_KEYS = ("palette", "sprites", "anims")
_SPRITE_KEYS = ("rows", "palette")
_ANIM_KEYS = ("frames", "fps")

#: The byte order mark some editors write at the start of a UTF-8 file. It is not part of the JSON.
_BYTE_ORDER_MARK = "\ufeff"


@dataclass(frozen=True)
class Anim:
    """A clip: the names of its sprites in play order, and how many of them show each second."""

    name: str
    frames: tuple[str, ...]
    fps: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise PixelRowsError(f"an anim's name is a non-empty string, got {self.name!r}")
        where = f"anim {self.name!r}"
        frames = self.frames
        if isinstance(frames, str):
            raise PixelRowsError(f"{where}: frames are a list of sprite names, got one string {frames!r}")
        try:
            frames = tuple(frames)
        except TypeError:
            raise PixelRowsError(f"{where}: frames are a list of sprite names, got {frames!r}") from None
        if not frames:
            raise PixelRowsError(f"{where}: there are no frames")
        for index, frame in enumerate(frames):
            if not isinstance(frame, str):
                raise PixelRowsError(f"{where}: frame {index} is not a string, got {frame!r}")
        if not _is_number(self.fps) or not self.fps > 0:
            raise PixelRowsError(f"{where}: fps is a number above 0, got {self.fps!r}")
        object.__setattr__(self, "frames", frames)

    @property
    def duration(self) -> float:
        """How long one pass of the clip takes, in seconds."""
        return len(self.frames) / self.fps


class SpriteSet:
    """
    One palette, the sprites read against it and the anims that play them.

    It is what a set file holds. A set may be half drawn: an anim may name a
    sprite that is not there yet, and `problems` says so.
    """

    def __init__(self, palette: Palette | Mapping[str, str | RGB | None] | None = None):
        if palette is None:
            self.palette = Palette()
        elif isinstance(palette, Palette):
            self.palette = Palette(palette.to_dict())
        elif isinstance(palette, Mapping):
            self.palette = Palette(palette)
        else:
            raise PixelRowsError(f"a set's palette is a Palette or a mapping, got {palette!r}")
        self.sprites: dict[str, Sprite] = {}
        self.anims: dict[str, Anim] = {}

    def add(self, sprite: Sprite) -> Sprite:
        """Puts a sprite in the set and returns it. It takes the place of one with the same name."""
        if not isinstance(sprite, Sprite):
            raise PixelRowsError(f"only a Sprite can be added to a set, got {sprite!r}")
        self.sprites[sprite.name] = sprite
        return sprite

    def add_anim(self, name: str, frames: Iterable[str], fps: float) -> Anim:
        """Makes an anim, puts it in the set and returns it. It takes the place of one with the same name."""
        anim = Anim(name, frames, fps)
        self.anims[anim.name] = anim
        return anim

    def sprite(self, name: str) -> Sprite:
        """The sprite of that name. PixelRowsError if there is none."""
        try:
            return self.sprites[name]
        except (KeyError, TypeError):
            raise PixelRowsError(f"no sprite named {name!r}") from None

    def anim(self, name: str) -> Anim:
        """The anim of that name. PixelRowsError if there is none."""
        try:
            return self.anims[name]
        except (KeyError, TypeError):
            raise PixelRowsError(f"no anim named {name!r}") from None

    def palette_for(self, sprite: Sprite | str) -> Palette:
        """The palette to read a sprite against: the set's, with the sprite's own entries laid over it."""
        if not isinstance(sprite, Sprite):
            sprite = self.sprite(sprite)
        return self.palette.merged(sprite.palette)

    def frames_of(self, anim: Anim | str) -> list[Sprite]:
        """An anim's sprites in play order. PixelRowsError if one is missing or they differ in size."""
        if not isinstance(anim, Anim):
            anim = self.anim(anim)
        wrong = self._anim_problems(anim)
        if wrong:
            raise PixelRowsError(wrong[0])
        return [self.sprites[frame] for frame in anim.frames]

    def problems(self) -> list[str]:
        """Everything that stops the set from being drawn or played, one line each. Empty when there is nothing."""
        found: list[str] = []
        for sprite in self.sprites.values():
            palette = self.palette_for(sprite)
            for ch in sprite.chars_used():
                if ch not in palette:
                    found.append(f"sprite {sprite.name!r} uses {ch!r}, which is not in the palette")
        for anim in self.anims.values():
            found.extend(self._anim_problems(anim))
        return found

    def _anim_problems(self, anim: Anim) -> list[str]:
        """One anim's lines: its frames that name no sprite, then its frames that differ in size from the first."""
        missing: list[str] = []
        uneven: list[str] = []
        first: Sprite | None = None
        for frame in anim.frames:
            sprite = self.sprites.get(frame)
            if sprite is None:
                missing.append(f"anim {anim.name!r} names {frame!r}, which is not a sprite")
            elif first is None:
                first = sprite
            elif (sprite.width, sprite.height) != (first.width, first.height):
                uneven.append(
                    f"anim {anim.name!r}: frame {frame!r} is {sprite.width}x{sprite.height}, "
                    f"the first frame is {first.width}x{first.height}"
                )
        return missing + uneven

    def to_dict(self) -> dict:
        """The set as plain data, in the shape of a set file."""
        sprites: dict[str, dict] = {}
        for name, sprite in self.sprites.items():
            entry: dict = {"rows": list(sprite.rows)}
            own = sprite.palette
            if own is not None:
                entry["palette"] = own.to_dict()
            sprites[name] = entry
        anims: dict[str, dict] = {}
        for name, anim in self.anims.items():
            fps = anim.fps
            if isinstance(fps, float) and fps.is_integer():
                fps = int(fps)
            anims[name] = {"frames": list(anim.frames), "fps": fps}
        return {"palette": self.palette.to_dict(), "sprites": sprites, "anims": anims}

    @classmethod
    def from_dict(cls, data: Mapping) -> SpriteSet:
        """A set from plain data in the shape of a set file. PixelRowsError says which key is wrong."""
        if not isinstance(data, Mapping):
            raise PixelRowsError("a set must be an object with 'palette', 'sprites' and 'anims'")
        _no_unknown_keys(data, _TOP_KEYS, "at the top")
        result = cls(_object_at(data, "palette"))
        for name, entry in _object_at(data, "sprites").items():
            result.add(_sprite_from(name, entry))
        for name, entry in _object_at(data, "anims").items():
            where = f"anims.{name}"
            if not isinstance(entry, Mapping):
                raise PixelRowsError(f"{where} must be an object")
            _no_unknown_keys(entry, _ANIM_KEYS, f"in {where}")
            for key in _ANIM_KEYS:
                if key not in entry:
                    raise PixelRowsError(f"{where}.{key} is missing")
            if not _is_list_of_strings(entry["frames"]):
                raise PixelRowsError(f"{where}.frames must be a list of strings")
            if not _is_number(entry["fps"]):
                raise PixelRowsError(f"{where}.fps must be a number")
            result.add_anim(name, entry["frames"], entry["fps"])
        return result

    @classmethod
    def load(cls, path: str | PathLike[str]) -> SpriteSet:
        """Reads a set file. PixelRowsError if it is not JSON or not a set, OSError if it cannot be read."""
        raw = Path(path).read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PixelRowsError(f"{path}: not UTF-8 at byte {error.start}") from None
        try:
            data = json.loads(text.removeprefix(_BYTE_ORDER_MARK))
        except json.JSONDecodeError as error:
            raise PixelRowsError(
                f"{path}: not JSON at line {error.lineno}, column {error.colno}: {error.msg}"
            ) from None
        return cls.from_dict(data)

    def save(self, path: str | PathLike[str]) -> None:
        """Writes the set file, one row of a sprite to a line. Parent folders are made if they are missing."""
        text = json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SpriteSet)
            and self.palette == other.palette
            and list(self.sprites.items()) == list(other.sprites.items())
            and list(self.anims.items()) == list(other.anims.items())
        )


def _is_number(value: object) -> bool:
    """True for an int or a float that is not a bool, an infinity or a NaN."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not isinstance(value, float) or math.isfinite(value)


def _is_list_of_strings(value: object) -> bool:
    """True for a list or a tuple whose every item is a string."""
    return isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value)


def _no_unknown_keys(entry: Mapping, known: tuple[str, ...], where: str) -> None:
    """PixelRowsError naming the first key of `entry` that is not one of `known`."""
    for key in entry:
        if key not in known:
            expected = ", ".join(repr(k) for k in known)
            raise PixelRowsError(f"unknown key {key!r} {where} (the keys are {expected})")


def _object_at(data: Mapping, key: str) -> Mapping:
    """One of the three top-level objects of a set file, empty when the key is missing."""
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise PixelRowsError(f"{key} must be an object")
    return value


def _sprite_from(name: str, entry: object) -> Sprite:
    """A sprite from its entry in a set file: an object with "rows", or the list of rows alone."""
    where = f"sprites.{name}"
    if isinstance(entry, (list, tuple)):
        if not _is_list_of_strings(entry):
            raise PixelRowsError(f"{where} must be an object or a list of strings")
        return Sprite(name, entry)
    if not isinstance(entry, Mapping):
        raise PixelRowsError(f"{where} must be an object or a list of strings")
    _no_unknown_keys(entry, _SPRITE_KEYS, f"in {where}")
    if "rows" not in entry:
        raise PixelRowsError(f"{where}.rows is missing")
    if not _is_list_of_strings(entry["rows"]):
        raise PixelRowsError(f"{where}.rows must be a list of strings")
    own = entry.get("palette", {})
    if not isinstance(own, Mapping):
        raise PixelRowsError(f"{where}.palette must be an object")
    return Sprite(name, entry["rows"], own)
