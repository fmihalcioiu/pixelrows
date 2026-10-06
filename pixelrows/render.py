"""Drawing a sprite on an image: a block of colour for each painted cell."""
from __future__ import annotations

from .errors import PixelRowsError
from .image import Image
from .palette import RGB, Palette
from .sprite import Sprite


def draw_sprite(
    image: Image,
    sprite: Sprite,
    palette: Palette,
    x: int = 0,
    y: int = 0,
    scale: int = 1,
    flip: bool = False,
) -> None:
    """
    Draws `sprite` on `image` with its top-left corner at (x, y).

    Each painted cell becomes a `scale` by `scale` block of its colour in
    `palette`, and a '.' leaves what is underneath. `flip` draws the sprite
    turned left to right. What falls outside the image is dropped.

    `palette` is the full palette to read against. PixelRowsError if it lacks
    a character the sprite uses, raised before anything is drawn.
    """
    _checked_scale(scale)
    colours = _colours(sprite, palette)
    last = sprite.width - 1
    for cell_x, cell_y, ch in sprite.cells():
        if flip:
            cell_x = last - cell_x
        image.fill(x + cell_x * scale, y + cell_y * scale, scale, scale, colours[ch])


def render_sprite(
    sprite: Sprite,
    palette: Palette,
    scale: int = 1,
    background: str | RGB | None = None,
    flip: bool = False,
) -> Image:
    """
    A new image of `sprite`, `scale` pixels to the cell.

    The image is `background` all over, or transparent when there is none,
    with the sprite drawn on it as `draw_sprite` draws it.
    """
    _checked_scale(scale)
    image = Image(sprite.width * scale, sprite.height * scale, background)
    draw_sprite(image, sprite, palette, 0, 0, scale, flip)
    return image


def _checked_scale(scale: int) -> int:
    """`scale` if it is a whole number of 1 or more."""
    if not isinstance(scale, int) or isinstance(scale, bool) or scale < 1:
        raise PixelRowsError(f"scale must be a whole number of 1 or more, got {scale!r}")
    return scale


def _colours(sprite: Sprite, palette: Palette) -> dict[str, str]:
    """
    The colour of every character the sprite uses, as '#rrggbb'.

    PixelRowsError naming the sprite and every character the palette lacks.
    """
    used = sprite.chars_used()
    missing = [ch for ch in used if ch not in palette]
    if missing:
        listed = ", ".join(repr(ch) for ch in missing)
        raise PixelRowsError(f"sprite {sprite.name!r}: the palette has no colour for {listed}")
    return {ch: palette.hex(ch) for ch in used}
