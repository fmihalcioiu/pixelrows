"""Pages for looking sprites over: each one drawn on a plate, with its labels in the label font."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from .errors import PixelRowsError
from .font import GLYPH_H, draw_text, text_width
from .image import Image
from .palette import RGB, as_rgb
from .render import draw_sprite
from .sprite import Sprite
from .spriteset import SpriteSet

PAGE = "#1e1e24"     # the page
PLATE = "#4a4a55"    # behind each sprite, unless a background is given
INK = "#d8d8e0"      # labels
DIM = "#8a8a96"      # second-line labels

#: Between the edge of the page and the cells.
MARGIN = 8

#: Between one cell and the next.
CELL_GAP = 8

#: Between one plate and the next in a cell.
PLATE_GAP = 4

#: The widest a page is made when the number of columns is not given.
MAX_WIDTH = 1600

#: The label font is drawn at scale 2 when the largest scale of the sprites is this or more, else at 1.
LARGE_SCALE = 4

#: Between a plate and a label line and between one label line and the next, by the scale of the label font.
LABEL_GAP = {1: 4, 2: 6}

#: A label line: its text and its colour.
_Line = tuple[str, str]


def contact_sheet(spriteset: SpriteSet, names: Sequence[str] | None = None,
                  scales: Sequence[int] = (8,), background: str | RGB = PLATE,
                  columns: int | None = None, labels: bool = True) -> Image:
    """
    A page of cells, one for each sprite in `names`, in that order, or for every sprite of the set.

    In a cell the sprite is drawn once for each of `scales`, left to right.
    Each drawing is on a plate of `background` that is one scaled pixel larger
    than the sprite on every side, and the plates stand on one line. With
    `labels`, the sprite's name and its size are under them. Every cell is the
    size of the largest.

    `columns` is how many cells go in a row, and never more than there are
    cells. When it is None the page takes as many as keep it at most 1600
    wide. PixelRowsError if a name is not a sprite of the set, or if there is
    nothing to show.
    """
    sprites = _chosen(spriteset, names)
    scales = _checked_scales(scales)
    plate = as_rgb(background)
    if columns is not None:
        _whole("columns", columns)
    label_scale = _label_scale(max(scales))
    cells = [
        (sprite, [(sprite.name, INK), (f"{sprite.width}X{sprite.height}", DIM)] if labels else [])
        for sprite in sprites
    ]
    plates_height = max(_plate_size(sprite, max(scales))[1] for sprite in sprites)
    cell_width = max(
        max(
            sum(_plate_size(sprite, scale)[0] for scale in scales) + PLATE_GAP * (len(scales) - 1),
            _lines_width(lines, label_scale),
        )
        for sprite, lines in cells
    )
    cell_height = plates_height + (_lines_height(2, label_scale) if labels else 0)
    if columns is None:
        columns = max(1, (MAX_WIDTH - 2 * MARGIN + CELL_GAP) // (cell_width + CELL_GAP))
    columns = min(columns, len(cells))
    page = Image(_span(columns, cell_width), _span(-(-len(cells) // columns), cell_height), PAGE)
    for index, (sprite, lines) in enumerate(cells):
        left = MARGIN + index % columns * (cell_width + CELL_GAP)
        foot = MARGIN + index // columns * (cell_height + CELL_GAP) + plates_height
        x = left
        for scale in scales:
            width, height = _plate_size(sprite, scale)
            _draw_plate(page, spriteset, sprite, x, foot - height, scale, plate)
            x += width + PLATE_GAP
        _draw_lines(page, lines, left, foot, label_scale)
    return page


def _chosen(spriteset: SpriteSet, names: Sequence[str] | None) -> list[Sprite]:
    """The sprites to show: those named, in that order, or every sprite of the set in its order."""
    if names is None:
        sprites = list(spriteset.sprites.values())
    elif isinstance(names, str) or not isinstance(names, Iterable):
        raise PixelRowsError(f"names must be a list of sprite names, got {names!r}")
    else:
        sprites = [spriteset.sprite(name) for name in names]
    if not sprites:
        raise PixelRowsError("nothing to show")
    return sprites


def _checked_scales(scales: Sequence[int]) -> tuple[int, ...]:
    """`scales` as a tuple, if it holds one or more whole numbers of 1 or more."""
    if isinstance(scales, str) or not isinstance(scales, Iterable):
        raise PixelRowsError(f"scales must be a list of whole numbers, got {scales!r}")
    scales = tuple(scales)
    if not scales:
        raise PixelRowsError("scales must hold at least one scale")
    for scale in scales:
        _whole("scale", scale)
    return scales


def _whole(what: str, value: int) -> int:
    """`value` if it is a whole number of 1 or more."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PixelRowsError(f"{what} must be a whole number of 1 or more, got {value!r}")
    return value


def _label_scale(largest: int) -> int:
    """The scale of the label font on a page whose largest sprite scale is `largest`."""
    return 2 if largest >= LARGE_SCALE else 1


def _span(count: int, size: int) -> int:
    """How long a side of the page is that holds `count` cells of `size`: the margins, the cells and the gaps."""
    return 2 * MARGIN + count * size + (count - 1) * CELL_GAP


def _plate_size(sprite: Sprite, scale: int) -> tuple[int, int]:
    """The width and height of a sprite's plate: one scaled pixel larger than the sprite on every side."""
    return (sprite.width + 2) * scale, (sprite.height + 2) * scale


def _draw_plate(image: Image, spriteset: SpriteSet, sprite: Sprite, x: int, y: int, scale: int,
                colour: RGB) -> None:
    """Draws a plate of `colour` with its top-left corner at (x, y), and the sprite on it."""
    width, height = _plate_size(sprite, scale)
    image.fill(x, y, width, height, colour)
    draw_sprite(image, sprite, spriteset.palette_for(sprite), x + scale, y + scale, scale)


def _lines_width(lines: Sequence[_Line], scale: int) -> int:
    """How wide the widest of the label lines is drawn."""
    return max((text_width(text, scale) for text, _ in lines), default=0)


def _lines_height(count: int, scale: int) -> int:
    """How much height `count` label lines take, each with the gap that sets it off."""
    return count * (LABEL_GAP[scale] + GLYPH_H * scale)


def _draw_lines(image: Image, lines: Sequence[_Line], x: int, y: int, scale: int) -> None:
    """Draws label lines one under the other from (x, y), a gap above each."""
    for text, colour in lines:
        y += LABEL_GAP[scale]
        draw_text(image, text, x, y, colour, scale)
        y += GLYPH_H * scale
