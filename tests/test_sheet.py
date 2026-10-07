import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.font import GLYPH_H, draw_text, text_width
from pixelrows.image import Image
from pixelrows.palette import as_rgb
from pixelrows.sheet import (
    CELL_GAP,
    DIM,
    INK,
    LABEL_GAP,
    LARGE_SCALE,
    MARGIN,
    MAX_WIDTH,
    PAGE,
    PLATE,
    PLATE_GAP,
    contact_sheet,
)
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

RED = "#ff0000"
GREEN = "#00ff00"
BLUE = "#0000ff"
WHITE = "#ffffff"

PALETTE = {"r": RED, "g": GREEN, "b": BLUE}

# One letter a pixel, so a page can be read as rows of text.
LETTERS = {PAGE: "_", PLATE: "p", INK: "i", DIM: "d", RED: "r", GREEN: "g", BLUE: "b", WHITE: "w"}

# Wider than it is tall, with an empty cell beside each painted one.
TILE = ["rg.", "..b"]


def pixel(colour):
    """A colour as the solid pixel it makes."""
    return (*as_rgb(colour), 255)


def rows(image):
    """The image as rows of letters, '?' for a pixel that has none."""
    letters = {pixel(colour): letter for colour, letter in LETTERS.items()}
    return [
        "".join(letters.get(image.get(x, y), "?") for x in range(image.width))
        for y in range(image.height)
    ]


def runs(image, y, colour):
    """Every unbroken stretch of `colour` along row `y`, as (first x, length)."""
    wanted = pixel(colour)
    found = []
    start = None
    for x in range(image.width + 1):
        if x < image.width and image.get(x, y) == wanted:
            if start is None:
                start = x
        elif start is not None:
            found.append((start, x - start))
            start = None
    return found


def cut(image, x, y, width, height):
    """The part of the image that starts at (x, y), as an image of its own."""
    part = Image(width, height)
    part.blit(image, -x, -y)
    return part


def written(text, colour, scale, width):
    """A band of page, `width` wide and one label line tall, with `text` drawn from its left end."""
    band = Image(width, GLYPH_H * scale, PAGE)
    draw_text(band, text, 0, 0, colour, scale)
    return band


def set_of(*sprites, palette=PALETTE):
    """A set that holds the sprites in the order given."""
    spriteset = SpriteSet(palette)
    for sprite in sprites:
        spriteset.add(sprite)
    return spriteset


def one_tile():
    """A set of one sprite, 'tile', 3 wide and 2 tall."""
    return set_of(Sprite("tile", TILE))


def dots(chars):
    """A set of sprites of one cell each, named d0, d1 and so on, one for each character."""
    return set_of(*(Sprite(f"d{index}", [ch]) for index, ch in enumerate(chars)))


def bars(count, width):
    """A set of `count` sprites, each one row of `width` red cells."""
    return set_of(*(Sprite(f"bar{index}", ["r" * width]) for index in range(count)))


class LayoutNumbersTest(unittest.TestCase):
    def test_the_four_colours(self):
        self.assertEqual((PAGE, PLATE, INK, DIM), ("#1e1e24", "#4a4a55", "#d8d8e0", "#8a8a96"))

    def test_margin_gaps_and_widest_page(self):
        self.assertEqual((MARGIN, CELL_GAP, PLATE_GAP, MAX_WIDTH), (8, 8, 4, 1600))

    def test_label_gap_is_four_at_label_scale_one_and_six_at_two(self):
        self.assertEqual(LABEL_GAP, {1: 4, 2: 6})

    def test_labels_are_large_from_a_scale_of_four(self):
        self.assertEqual(LARGE_SCALE, 4)


class SheetSizeTest(unittest.TestCase):
    def test_gives_an_image(self):
        self.assertIsInstance(contact_sheet(one_tile()), Image)

    def test_size_of_one_sprite_without_labels(self):
        # At scale 8 the plate of a 3 by 2 sprite is (3 + 2) * 8 by (2 + 2) * 8.
        image = contact_sheet(one_tile(), labels=False)
        self.assertEqual((image.width, image.height), (MARGIN + 40 + MARGIN, MARGIN + 32 + MARGIN))

    def test_size_of_one_sprite_with_labels(self):
        # The labels are at scale 2. 'tile' is 4 glyphs, (4 * 6 - 1) * 2 = 46 wide, wider than
        # the plate of 40 and than '3X2'. Each of the two lines is 7 * 2 tall under its gap.
        image = contact_sheet(one_tile())
        self.assertEqual(image.width, MARGIN + 46 + MARGIN)
        self.assertEqual(image.height, MARGIN + 32 + (LABEL_GAP[2] + 14) * 2 + MARGIN)

    def test_size_with_two_scales_in_the_cell(self):
        # A plate of 5 by 4 and one of 40 by 32, side by side.
        image = contact_sheet(one_tile(), scales=(1, 8), labels=False)
        self.assertEqual(image.width, MARGIN + 5 + PLATE_GAP + 40 + MARGIN)
        self.assertEqual(image.height, MARGIN + 32 + MARGIN)

    def test_size_of_three_sprites_in_two_columns(self):
        # At scales 1 and 4 the plates are, wide by tall:
        #   ab    2 by 3:  4 by 5  and 16 by 20, 4 + 16 and the gap across
        #   tile  3 by 2:  5 by 4  and 20 by 16, 5 + 20 and the gap across
        #   dot   1 by 1:  3 by 3  and 12 by 12, 3 + 12 and the gap across
        # The tallest plate is 20. The labels are at scale 2 and the widest is
        # 'tile', 46, wider than any pair of plates, so every cell is 46 wide
        # and 20 + (gap + 14) * 2 tall. Three cells in two columns make two rows.
        spriteset = set_of(Sprite("ab", ["r.", "rg", ".g"]), Sprite("tile", TILE), Sprite("dot", ["b"]))
        image = contact_sheet(spriteset, scales=(1, 4), columns=2)
        cell_height = 20 + (LABEL_GAP[2] + 14) * 2
        self.assertEqual(image.width, MARGIN + 46 + CELL_GAP + 46 + MARGIN)
        self.assertEqual(image.height, MARGIN + cell_height + CELL_GAP + cell_height + MARGIN)


class SheetPlateTest(unittest.TestCase):
    def test_whole_page_at_scale_one(self):
        edge = "_" * MARGIN
        blank = "_" * (MARGIN + 5 + MARGIN)
        self.assertEqual(
            rows(contact_sheet(one_tile(), scales=(1,), labels=False)),
            [blank] * MARGIN
            + [edge + "ppppp" + edge, edge + "prgpp" + edge, edge + "pppbp" + edge, edge + "ppppp" + edge]
            + [blank] * MARGIN,
        )

    def test_page_colour_at_the_corners_of_the_page(self):
        for labels in (True, False):
            image = contact_sheet(one_tile(), labels=labels)
            for x in (0, image.width - 1):
                for y in (0, image.height - 1):
                    with self.subTest(labels=labels, x=x, y=y):
                        self.assertEqual(image.get(x, y), pixel(PAGE))

    def test_plate_colour_at_the_corners_of_the_plate(self):
        image = contact_sheet(one_tile())
        for x in (MARGIN, MARGIN + 39):
            for y in (MARGIN, MARGIN + 31):
                with self.subTest(x=x, y=y):
                    self.assertEqual(image.get(x, y), pixel(PLATE))

    def test_page_colour_just_outside_the_plate(self):
        image = contact_sheet(one_tile())
        for x, y in ((MARGIN - 1, MARGIN), (MARGIN, MARGIN - 1), (MARGIN + 40, MARGIN), (MARGIN, MARGIN + 32)):
            with self.subTest(x=x, y=y):
                self.assertEqual(image.get(x, y), pixel(PAGE))

    def test_plate_is_one_scaled_pixel_larger_than_the_sprite_on_every_side(self):
        spriteset = set_of(Sprite("block", ["rr", "rr"]))
        for scale in (1, 3, 8):
            with self.subTest(scale=scale):
                image = contact_sheet(spriteset, scales=(scale,), labels=False)
                plate = cut(image, MARGIN, MARGIN, 4 * scale, 4 * scale)
                self.assertEqual(
                    rows(plate),
                    ["p" * 4 * scale] * scale
                    + ["p" * scale + "r" * 2 * scale + "p" * scale] * 2 * scale
                    + ["p" * 4 * scale] * scale,
                )

    def test_painted_pixel_is_at_its_place_and_colour_at_scale_one(self):
        # The small plate stands at the foot of the cell, which is as tall as the large one.
        image = contact_sheet(one_tile(), scales=(1, 8), labels=False)
        left, top = MARGIN + 1, MARGIN + 32 - 4 + 1
        self.assertEqual(image.get(left, top), pixel(RED))
        self.assertEqual(image.get(left + 1, top), pixel(GREEN))
        self.assertEqual(image.get(left + 2, top + 1), pixel(BLUE))

    def test_painted_pixel_is_a_block_at_its_place_and_colour_at_scale_eight(self):
        image = contact_sheet(one_tile(), scales=(1, 8), labels=False)
        left, top = MARGIN + 5 + PLATE_GAP + 8, MARGIN + 8
        for cell_x, cell_y, colour in ((0, 0, RED), (1, 0, GREEN), (2, 1, BLUE)):
            for x in (left + cell_x * 8, left + cell_x * 8 + 7):
                for y in (top + cell_y * 8, top + cell_y * 8 + 7):
                    with self.subTest(x=x, y=y):
                        self.assertEqual(image.get(x, y), pixel(colour))

    def test_empty_cell_of_the_sprite_shows_the_plate(self):
        image = contact_sheet(one_tile(), labels=False)
        left, top = MARGIN + 8, MARGIN + 8
        for cell_x, cell_y in ((2, 0), (0, 1), (1, 1)):
            with self.subTest(cell_x=cell_x, cell_y=cell_y):
                self.assertEqual(image.get(left + cell_x * 8, top + cell_y * 8), pixel(PLATE))
                self.assertEqual(image.get(left + cell_x * 8 + 7, top + cell_y * 8 + 7), pixel(PLATE))

    def test_two_scales_stand_on_one_line(self):
        image = contact_sheet(one_tile(), scales=(1, 8), labels=False)
        foot = MARGIN + 32
        small, large = MARGIN, MARGIN + 5 + PLATE_GAP
        self.assertEqual(runs(image, foot - 1, PLATE), [(small, 5), (large, 40)])
        self.assertEqual(runs(image, foot, PLATE), [])
        # The small plate is 4 tall: above it the row holds the large one alone.
        self.assertEqual(runs(image, foot - 4, PLATE)[0], (small, 5))
        self.assertEqual(runs(image, foot - 5, PLATE)[0][0], large)

    def test_two_scales_are_four_apart(self):
        image = contact_sheet(one_tile(), scales=(1, 8), labels=False)
        gap = cut(image, MARGIN + 5, 0, PLATE_GAP, image.height)
        self.assertEqual(gap, Image(PLATE_GAP, image.height, PAGE))
        self.assertEqual(image.get(MARGIN + 5 + PLATE_GAP, MARGIN), pixel(PLATE))

    def test_scales_are_drawn_left_to_right_in_the_order_given(self):
        image = contact_sheet(one_tile(), scales=(8, 1), labels=False)
        self.assertEqual(runs(image, MARGIN + 31, PLATE), [(MARGIN, 40), (MARGIN + 40 + PLATE_GAP, 5)])

    def test_three_scales_in_one_cell(self):
        image = contact_sheet(one_tile(), scales=(1, 2, 3), labels=False)
        self.assertEqual(image.width, MARGIN + 5 + PLATE_GAP + 10 + PLATE_GAP + 15 + MARGIN)
        self.assertEqual(
            runs(image, MARGIN + 11, PLATE),
            [(MARGIN, 5), (MARGIN + 5 + PLATE_GAP, 10), (MARGIN + 5 + PLATE_GAP + 10 + PLATE_GAP, 15)],
        )

    def test_background_is_the_colour_of_the_plate(self):
        for background in (WHITE, (255, 255, 255)):
            with self.subTest(background=background):
                image = contact_sheet(one_tile(), background=background, labels=False)
                self.assertEqual(image.get(MARGIN, MARGIN), pixel(WHITE))
                self.assertNotIn(pixel(PLATE), image.colours())

    def test_background_leaves_the_page_as_it_is(self):
        image = contact_sheet(one_tile(), background=WHITE)
        self.assertEqual(image.get(0, 0), pixel(PAGE))

    def test_own_palette_entry_of_a_sprite_shows(self):
        spriteset = set_of(Sprite("plain", ["rg"]), Sprite("own", ["rg"], {"g": WHITE}))
        image = contact_sheet(spriteset, scales=(1,), labels=False)
        second = MARGIN + 4 + CELL_GAP
        self.assertEqual(image.get(MARGIN + 2, MARGIN + 1), pixel(GREEN))
        self.assertEqual(image.get(second + 1, MARGIN + 1), pixel(RED))
        self.assertEqual(image.get(second + 2, MARGIN + 1), pixel(WHITE))

    def test_character_the_palette_lacks_raises_naming_the_sprite(self):
        spriteset = set_of(Sprite("tile", TILE), Sprite("odd", ["rx"]))
        with self.assertRaises(PixelRowsError) as caught:
            contact_sheet(spriteset)
        self.assertEqual(str(caught.exception), "sprite 'odd': the palette has no colour for 'x'")


class SheetLabelTest(unittest.TestCase):
    def test_name_is_under_the_plate_in_ink(self):
        image = contact_sheet(one_tile())
        top = MARGIN + 32 + LABEL_GAP[2]
        self.assertEqual(cut(image, MARGIN, top, 46, 14), written("TILE", INK, 2, 46))

    def test_size_is_under_the_name_in_dim(self):
        image = contact_sheet(one_tile())
        top = MARGIN + 32 + LABEL_GAP[2] + 14 + LABEL_GAP[2]
        self.assertEqual(cut(image, MARGIN, top, 46, 14), written("3X2", DIM, 2, 46))

    def test_gaps_above_the_label_lines_are_page(self):
        image = contact_sheet(one_tile())
        gap = LABEL_GAP[2]
        for top in (MARGIN + 32, MARGIN + 32 + gap + 14):
            with self.subTest(top=top):
                self.assertEqual(cut(image, 0, top, image.width, gap), Image(image.width, gap, PAGE))

    def test_labels_start_at_the_left_of_the_cell(self):
        # 'L' has ink down its whole left side, so the label's first column is the cell's.
        image = contact_sheet(set_of(Sprite("L", ["r"])), scales=(1,))
        top = MARGIN + 3 + LABEL_GAP[1]
        self.assertEqual([image.get(MARGIN, top + y) for y in range(GLYPH_H)], [pixel(INK)] * GLYPH_H)
        self.assertEqual(image.get(MARGIN - 1, top), pixel(PAGE))

    def test_no_ink_or_dim_pixel_without_labels(self):
        for scales in ((1,), (8,), (1, 8)):
            with self.subTest(scales=scales):
                colours = contact_sheet(one_tile(), scales=scales, labels=False).colours()
                self.assertNotIn(pixel(INK), colours)
                self.assertNotIn(pixel(DIM), colours)

    def test_ink_and_dim_pixels_with_labels(self):
        colours = contact_sheet(one_tile()).colours()
        self.assertIn(pixel(INK), colours)
        self.assertIn(pixel(DIM), colours)

    def test_page_without_labels_is_the_page_with_them_less_the_label_lines(self):
        with_labels = contact_sheet(set_of(Sprite("t", TILE)))
        without = contact_sheet(set_of(Sprite("t", TILE)), labels=False)
        self.assertEqual(with_labels.width, without.width)
        self.assertEqual(with_labels.height, without.height + (LABEL_GAP[2] + 14) * 2)

    def test_label_font_is_at_scale_one_below_a_largest_scale_of_four(self):
        # 'tile' is (4 * 6 - 1) * 1 = 23 wide, wider than the plate of 15.
        image = contact_sheet(one_tile(), scales=(LARGE_SCALE - 1,))
        self.assertEqual(image.width, MARGIN + 23 + MARGIN)
        self.assertEqual(image.height, MARGIN + 12 + (LABEL_GAP[1] + 7) * 2 + MARGIN)
        top = MARGIN + 12 + LABEL_GAP[1]
        self.assertEqual(cut(image, MARGIN, top, 23, 7), written("TILE", INK, 1, 23))
        self.assertEqual(cut(image, MARGIN, top + 7 + LABEL_GAP[1], 23, 7), written("3X2", DIM, 1, 23))

    def test_label_font_is_at_scale_two_from_a_largest_scale_of_four(self):
        image = contact_sheet(one_tile(), scales=(LARGE_SCALE,))
        self.assertEqual(image.width, MARGIN + 46 + MARGIN)
        self.assertEqual(image.height, MARGIN + 16 + (LABEL_GAP[2] + 14) * 2 + MARGIN)
        top = MARGIN + 16 + LABEL_GAP[2]
        self.assertEqual(cut(image, MARGIN, top, 46, 14), written("TILE", INK, 2, 46))
        self.assertEqual(cut(image, MARGIN, top + 14 + LABEL_GAP[2], 46, 14), written("3X2", DIM, 2, 46))

    def test_label_scale_goes_by_the_largest_scale_wherever_it_stands(self):
        heights = {
            (1, 3): 12 + (LABEL_GAP[1] + 7) * 2,
            (3, 1): 12 + (LABEL_GAP[1] + 7) * 2,
            (1, 4): 16 + (LABEL_GAP[2] + 14) * 2,
            (4, 1): 16 + (LABEL_GAP[2] + 14) * 2,
        }
        for scales, cell_height in heights.items():
            with self.subTest(scales=scales):
                image = contact_sheet(one_tile(), scales=scales)
                self.assertEqual(image.height, MARGIN + cell_height + MARGIN)

    def test_long_name_widens_every_cell(self):
        # The plates are 24 wide. The long name is 16 glyphs at scale 2: (16 * 6 - 1) * 2 = 190.
        spriteset = set_of(Sprite("a", ["r"]), Sprite("a_very_long_name", ["g"]), Sprite("b", ["b"]))
        image = contact_sheet(spriteset)
        self.assertEqual(text_width("a_very_long_name", 2), 190)
        self.assertEqual(image.width, MARGIN + 190 + CELL_GAP + 190 + CELL_GAP + 190 + MARGIN)
        self.assertEqual(
            runs(image, MARGIN, PLATE),
            [(MARGIN, 24), (MARGIN + 190 + CELL_GAP, 24), (MARGIN + (190 + CELL_GAP) * 2, 24)],
        )

    def test_long_name_is_drawn_whole(self):
        spriteset = set_of(Sprite("a", ["r"]), Sprite("a_very_long_name", ["g"]))
        image = contact_sheet(spriteset)
        left, top = MARGIN + 190 + CELL_GAP, MARGIN + 24 + LABEL_GAP[2]
        self.assertEqual(cut(image, left, top, 190, 14), written("A_VERY_LONG_NAME", INK, 2, 190))

    def test_plates_and_labels_are_level_across_a_row(self):
        # At scale 2 the plates are 6 wide, 10 tall for 'tall' and 6 tall for 'short'.
        # The labels are at scale 1 and 'short' is the widest thing in a cell: 29.
        spriteset = set_of(Sprite("tall", ["r", "r", "r"]), Sprite("short", ["g"]))
        image = contact_sheet(spriteset, scales=(2,))
        second = MARGIN + 29 + CELL_GAP
        foot = MARGIN + 10
        self.assertEqual(runs(image, MARGIN, PLATE), [(MARGIN, 6)])
        self.assertEqual(runs(image, foot - 6, PLATE)[-1], (second, 6))
        self.assertEqual(image.get(second, foot - 7), pixel(PAGE))
        self.assertEqual(image.get(second, foot - 1), pixel(PLATE))
        self.assertEqual(image.get(second, foot), pixel(PAGE))
        top = foot + LABEL_GAP[1]
        self.assertEqual(cut(image, MARGIN, top, 29, 7), written("TALL", INK, 1, 29))
        self.assertEqual(cut(image, second, top, 29, 7), written("SHORT", INK, 1, 29))
        self.assertEqual(cut(image, MARGIN, top + 7 + LABEL_GAP[1], 29, 7), written("1X3", DIM, 1, 29))
        self.assertEqual(cut(image, second, top + 7 + LABEL_GAP[1], 29, 7), written("1X1", DIM, 1, 29))


class SheetCellsTest(unittest.TestCase):
    # A sprite of one cell at scale 8 is on a plate of 24 by 24, the sprite's block 8 in from its corner.

    def cell_colours(self, image, count, columns):
        """The pixel in the middle of each of the first `count` cells, read row by row."""
        step = 24 + CELL_GAP
        return [
            image.get(MARGIN + index % columns * step + 12, MARGIN + index // columns * step + 12)
            for index in range(count)
        ]

    def test_every_sprite_of_the_set_in_its_order(self):
        image = contact_sheet(dots("rgb"), labels=False)
        self.assertEqual(image.width, MARGIN + 24 * 3 + CELL_GAP * 2 + MARGIN)
        self.assertEqual(self.cell_colours(image, 3, 3), [pixel(RED), pixel(GREEN), pixel(BLUE)])

    def test_names_choose_the_sprites_and_their_order(self):
        image = contact_sheet(dots("rgb"), names=["d2", "d0"], labels=False)
        self.assertEqual(image.width, MARGIN + 24 * 2 + CELL_GAP + MARGIN)
        self.assertEqual(self.cell_colours(image, 2, 2), [pixel(BLUE), pixel(RED)])
        self.assertNotIn(pixel(GREEN), image.colours())

    def test_names_as_a_tuple(self):
        image = contact_sheet(dots("rgb"), names=("d1",), labels=False)
        self.assertEqual(self.cell_colours(image, 1, 1), [pixel(GREEN)])

    def test_chosen_name_is_the_one_on_the_label(self):
        image = contact_sheet(dots("rgb"), names=["d2"])
        top = MARGIN + 24 + LABEL_GAP[2]
        self.assertEqual(cut(image, MARGIN, top, 24, 14), written("D2", INK, 2, 24))

    def test_name_given_twice_has_two_cells(self):
        image = contact_sheet(dots("rgb"), names=["d1", "d1"], labels=False)
        self.assertEqual(self.cell_colours(image, 2, 2), [pixel(GREEN), pixel(GREEN)])

    def test_only_the_chosen_sprites_set_the_size_of_a_cell(self):
        spriteset = set_of(Sprite("dot", ["r"]), Sprite("wide", ["gggggggg"]))
        image = contact_sheet(spriteset, names=["dot"], labels=False)
        self.assertEqual((image.width, image.height), (MARGIN + 24 + MARGIN, MARGIN + 24 + MARGIN))

    def test_missing_name_raises_through_the_set(self):
        with self.assertRaises(PixelRowsError) as caught:
            contact_sheet(dots("rgb"), names=["d0", "d9"])
        self.assertEqual(str(caught.exception), "no sprite named 'd9'")

    def test_names_as_one_string_raises(self):
        with self.assertRaises(PixelRowsError):
            contact_sheet(dots("rgb"), names="d0")

    def test_empty_set_raises_nothing_to_show(self):
        with self.assertRaises(PixelRowsError) as caught:
            contact_sheet(SpriteSet(PALETTE))
        self.assertEqual(str(caught.exception), "nothing to show")

    def test_no_names_raises_nothing_to_show(self):
        for names in ([], ()):
            with self.subTest(names=names):
                with self.assertRaises(PixelRowsError) as caught:
                    contact_sheet(dots("rgb"), names=names)
                self.assertEqual(str(caught.exception), "nothing to show")

    def test_columns_given_wraps_the_cells(self):
        image = contact_sheet(dots("rgbrg"), columns=2, labels=False)
        self.assertEqual(image.width, MARGIN + 24 * 2 + CELL_GAP + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 * 3 + CELL_GAP * 2 + MARGIN)
        self.assertEqual(
            self.cell_colours(image, 5, 2),
            [pixel(RED), pixel(GREEN), pixel(BLUE), pixel(RED), pixel(GREEN)],
        )

    def test_cells_fill_each_row_from_the_left(self):
        image = contact_sheet(dots("rgbrg"), columns=3, labels=False)
        second_row = MARGIN + 24 + CELL_GAP
        self.assertEqual(
            runs(image, MARGIN, PLATE),
            [(MARGIN, 24), (MARGIN + 24 + CELL_GAP, 24), (MARGIN + (24 + CELL_GAP) * 2, 24)],
        )
        self.assertEqual(runs(image, second_row, PLATE), [(MARGIN, 24), (MARGIN + 24 + CELL_GAP, 24)])
        last = cut(image, MARGIN + (24 + CELL_GAP) * 2, second_row, 24, 24)
        self.assertEqual(last, Image(24, 24, PAGE))

    def test_rows_of_cells_are_eight_apart(self):
        image = contact_sheet(dots("rgb"), columns=1, labels=False)
        self.assertEqual(
            cut(image, 0, MARGIN + 24, image.width, CELL_GAP),
            Image(image.width, CELL_GAP, PAGE),
        )
        self.assertEqual(image.get(MARGIN, MARGIN + 24 + CELL_GAP), pixel(PLATE))

    def test_one_column(self):
        image = contact_sheet(dots("rgb"), columns=1, labels=False)
        self.assertEqual(image.width, MARGIN + 24 + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 * 3 + CELL_GAP * 2 + MARGIN)

    def test_more_columns_than_cells_makes_the_page_no_wider(self):
        self.assertEqual(
            contact_sheet(dots("rgb"), columns=10, labels=False),
            contact_sheet(dots("rgb"), columns=3, labels=False),
        )

    def test_columns_none_puts_few_cells_in_one_row(self):
        image = contact_sheet(dots("rgb"), labels=False)
        self.assertEqual(image.width, MARGIN + 24 * 3 + CELL_GAP * 2 + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 + MARGIN)

    def test_columns_none_wraps_at_1600(self):
        # A sprite of 8 by 1 at scale 8 is on a plate of 80 by 24. Eighteen columns are
        # 8 + 18 * 80 + 17 * 8 + 8 = 1592 wide, and nineteen would be 1680.
        image = contact_sheet(bars(20, 8), labels=False)
        self.assertEqual(image.width, MARGIN + 18 * 80 + 17 * CELL_GAP + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 + CELL_GAP + 24 + MARGIN)
        self.assertLessEqual(image.width, MAX_WIDTH)
        self.assertGreater(image.width + CELL_GAP + 80, MAX_WIDTH)
        self.assertEqual(len(runs(image, MARGIN, PLATE)), 18)
        self.assertEqual(len(runs(image, MARGIN + 24 + CELL_GAP, PLATE)), 2)

    def test_columns_none_keeps_a_page_of_exactly_1600(self):
        # A plate of 191 by 3: eight columns are 8 + 8 * 191 + 7 * 8 + 8 = 1600 wide.
        image = contact_sheet(bars(9, 189), scales=(1,), labels=False)
        self.assertEqual(image.width, MARGIN + 8 * 191 + 7 * CELL_GAP + MARGIN)
        self.assertEqual(image.width, MAX_WIDTH)
        self.assertEqual(image.height, MARGIN + 3 + CELL_GAP + 3 + MARGIN)

    def test_columns_none_takes_one_column_fewer_when_the_page_would_be_1601_or_more(self):
        # A plate of 192 by 3: eight columns would be 1608 wide, so there are seven.
        image = contact_sheet(bars(9, 190), scales=(1,), labels=False)
        self.assertEqual(image.width, MARGIN + 7 * 192 + 6 * CELL_GAP + MARGIN)
        self.assertEqual(image.height, MARGIN + 3 + CELL_GAP + 3 + MARGIN)

    def test_columns_none_takes_at_least_one_column(self):
        # A plate of (200 + 2) * 8 = 1616 is wider than the widest page.
        image = contact_sheet(bars(2, 200), labels=False)
        self.assertEqual(image.width, MARGIN + 1616 + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 + CELL_GAP + 24 + MARGIN)

    def test_columns_given_may_pass_1600(self):
        image = contact_sheet(bars(20, 8), columns=20, labels=False)
        self.assertEqual(image.width, MARGIN + 20 * 80 + 19 * CELL_GAP + MARGIN)
        self.assertEqual(image.height, MARGIN + 24 + MARGIN)

    def test_columns_below_one_or_not_a_whole_number_raises(self):
        for bad in (0, -1, 1.5, 2.0, True, "2"):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    contact_sheet(dots("rgb"), columns=bad)

    def test_columns_error_says_what_was_given(self):
        with self.assertRaises(PixelRowsError) as caught:
            contact_sheet(dots("rgb"), columns=0)
        self.assertEqual(str(caught.exception), "columns must be a whole number of 1 or more, got 0")


class SheetScalesTest(unittest.TestCase):
    def test_scales_as_a_list(self):
        self.assertEqual(
            contact_sheet(one_tile(), scales=[1, 8]),
            contact_sheet(one_tile(), scales=(1, 8)),
        )

    def test_default_scale_is_eight(self):
        self.assertEqual(contact_sheet(one_tile()), contact_sheet(one_tile(), scales=(8,)))

    def test_scale_below_one_or_not_a_whole_number_raises(self):
        for bad in ((0,), (8, -1), (1.5,), (2.0,), (True,), ("8",), (None,)):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    contact_sheet(one_tile(), scales=bad)

    def test_scale_error_says_what_was_given(self):
        with self.assertRaises(PixelRowsError) as caught:
            contact_sheet(one_tile(), scales=(8, 0))
        self.assertEqual(str(caught.exception), "scale must be a whole number of 1 or more, got 0")

    def test_no_scales_raises(self):
        for bad in ((), []):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    contact_sheet(one_tile(), scales=bad)

    def test_scales_that_are_not_a_list_raise(self):
        for bad in (8, "8", None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    contact_sheet(one_tile(), scales=bad)

    def test_background_that_is_not_a_colour_raises(self):
        for bad in ("red", "#12", (1, 2), (0, 0, 256), None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    contact_sheet(one_tile(), background=bad)

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            contact_sheet(SpriteSet(PALETTE))


if __name__ == "__main__":
    unittest.main()
