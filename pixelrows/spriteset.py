"""A sprite set: one palette and the sprites read against it, kept as a JSON file."""
from __future__ import annotations

import json
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

from .errors import PixelRowsError
from .palette import RGB, Palette
from .sprite import Sprite

_TOP_KEYS = ("palette", "sprites")
_SPRITE_KEYS = ("rows", "palette")


class SpriteSet:
    """
    One palette and the sprites read against it.

    It is what a set file holds.
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

    def add(self, sprite: Sprite) -> Sprite:
        """Puts a sprite in the set and returns it. It takes the place of one with the same name."""
        if not isinstance(sprite, Sprite):
            raise PixelRowsError(f"only a Sprite can be added to a set, got {sprite!r}")
        self.sprites[sprite.name] = sprite
        return sprite

    def sprite(self, name: str) -> Sprite:
        """The sprite of that name. PixelRowsError if there is none."""
        try:
            return self.sprites[name]
        except (KeyError, TypeError):
            raise PixelRowsError(f"no sprite named {name!r}") from None

    def palette_for(self, sprite: Sprite | str) -> Palette:
        """The palette to read a sprite against: the set's, with the sprite's own entries laid over it."""
        if not isinstance(sprite, Sprite):
            sprite = self.sprite(sprite)
        return self.palette.merged(sprite.palette)

    def to_dict(self) -> dict:
        """The set as plain data, in the shape of a set file."""
        sprites: dict[str, dict] = {}
        for name, sprite in self.sprites.items():
            entry: dict = {"rows": list(sprite.rows)}
            own = sprite.palette
            if own is not None:
                entry["palette"] = own.to_dict()
            sprites[name] = entry
        return {"palette": self.palette.to_dict(), "sprites": sprites}

    @classmethod
    def from_dict(cls, data: Mapping) -> SpriteSet:
        """A set from plain data in the shape of a set file. PixelRowsError says which key is wrong."""
        if not isinstance(data, Mapping):
            raise PixelRowsError("a set must be an object with 'palette' and 'sprites'")
        _no_unknown_keys(data, _TOP_KEYS, "at the top")
        result = cls(_object_at(data, "palette"))
        for name, entry in _object_at(data, "sprites").items():
            result.add(_sprite_from(name, entry))
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
            data = json.loads(text)
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
        )


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
    """One of the two top-level objects of a set file, empty when the key is missing."""
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
