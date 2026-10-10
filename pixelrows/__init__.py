"""Pixel art as rows of text."""

from .canvas import Canvas
from .errors import PixelRowsError
from .image import Image
from .palette import Palette
from .render import render_sprite
from .sprite import Sprite
from .spriteset import Anim, SpriteSet

__version__ = "0.1.0"

__all__ = [
    "Anim",
    "Canvas",
    "Image",
    "Palette",
    "PixelRowsError",
    "Sprite",
    "SpriteSet",
    "render_sprite",
]
