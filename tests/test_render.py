import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.image import Image
from pixelrows.palette import Palette
from pixelrows.render import draw_sprite, render_sprite
from pixelrows.sprite import Sprite

RED = "#ff0000"
GREEN = "#00ff00"
BLUE = "#0000ff"
WHITE = "#ffffff"

CLEAR = (0, 0, 0, 0)

# One letter a pixel, so an image can be read as rows of text.
LETTERS = {
    CLEAR: ".",
    (255, 0, 0, 255): "r",
    (0, 255, 0, 255): "g",
    (0, 0, 255, 255): "b",
    (255, 255, 255, 255): "w",
}

PALETTE = Palette({"r": RED, "g": GREEN, "b": BLUE})

# Wider than it is tall, and not the same turned left to right or top to bottom.
TILE = Sprite("tile", ["rg.", "..b"])


def rows(image):
    """The image as rows of letters, '?' for a pixel that has none."""
    return [
        "".join(LETTERS.get(image.get(x, y), "?") for x in range(image.width))
        for y in range(image.height)
    ]


def put(image, x, y, rgba):
    """Writes one pixel straight into the image's bytes."""
    at = (y * image.width + x) * 4
    image.data[at:at + 4] = bytes(rgba)


class RenderSpriteTest(unittest.TestCase):
    def test_gives_an_image(self):
        self.assertIsInstance(render_sprite(TILE, PALETTE), Image)

    def test_image_is_the_size_of_the_sprite_at_scale_one(self):
        image = render_sprite(TILE, PALETTE)
        self.assertEqual((image.width, image.height), (3, 2))

    def test_image_is_width_and_height_times_scale(self):
        for scale in (2, 3, 8):
            with self.subTest(scale=scale):
                image = render_sprite(TILE, PALETTE, scale)
                self.assertEqual((image.width, image.height), (3 * scale, 2 * scale))

    def test_painted_cell_is_one_pixel_of_its_colour_at_scale_one(self):
        self.assertEqual(rows(render_sprite(TILE, PALETTE)), ["rg.", "..b"])

    def test_painted_cell_is_a_block_of_its_colour_at_scale_three(self):
        self.assertEqual(
            rows(render_sprite(TILE, PALETTE, 3)),
            ["rrrggg..."] * 3 + ["......bbb"] * 3,
        )

    def test_colour_is_the_one_in_the_palette_and_solid(self):
        image = render_sprite(Sprite("dot", ["o"]), Palette({"o": "#102030"}), 2)
        self.assertEqual(image.data, bytearray([16, 32, 48, 255] * 4))

    def test_empty_cell_is_transparent_without_a_background(self):
        image = render_sprite(TILE, PALETTE, 3)
        for cell_x, cell_y in ((2, 0), (0, 1), (1, 1)):
            for y in range(cell_y * 3, cell_y * 3 + 3):
                for x in range(cell_x * 3, cell_x * 3 + 3):
                    with self.subTest(x=x, y=y):
                        self.assertEqual(image.get(x, y), CLEAR)

    def test_empty_cell_keeps_the_background(self):
        self.assertEqual(rows(render_sprite(TILE, PALETTE, background=WHITE)), ["rgw", "wwb"])
        self.assertEqual(
            rows(render_sprite(TILE, PALETTE, 3, WHITE)),
            ["rrrgggwww"] * 3 + ["wwwwwwbbb"] * 3,
        )

    def test_background_as_numbers(self):
        self.assertEqual(rows(render_sprite(TILE, PALETTE, 1, (255, 255, 255))), ["rgw", "wwb"])

    def test_sprite_with_nothing_painted_is_all_background(self):
        blank = Sprite("blank", ["..", ".."])
        self.assertEqual(render_sprite(blank, Palette(), 2), Image(4, 4))
        self.assertEqual(render_sprite(blank, Palette(), 2, WHITE), Image(4, 4, WHITE))

    def test_scaled_render_is_the_plain_render_scaled(self):
        for scale in (1, 2, 3, 5):
            for background in (None, WHITE):
                with self.subTest(scale=scale, background=background):
                    self.assertEqual(
                        render_sprite(TILE, PALETTE, scale, background),
                        render_sprite(TILE, PALETTE, 1, background).scaled(scale),
                    )

    def test_flip_draws_the_sprite_left_to_right(self):
        self.assertEqual(rows(render_sprite(TILE, PALETTE, flip=True)), [".gr", "b.."])

    def test_flip_at_scale_three(self):
        self.assertEqual(
            rows(render_sprite(TILE, PALETTE, 3, flip=True)),
            ["...gggrrr"] * 3 + ["bbb......"] * 3,
        )

    def test_flip_keeps_the_background(self):
        self.assertEqual(rows(render_sprite(TILE, PALETTE, 1, WHITE, True)), ["wgr", "bww"])

    def test_flip_is_the_flipped_sprite_drawn_plain(self):
        for scale in (1, 2, 3):
            with self.subTest(scale=scale):
                self.assertEqual(
                    render_sprite(TILE, PALETTE, scale, flip=True),
                    render_sprite(TILE.flipped(), PALETTE, scale),
                )

    def test_not_flipped_unless_asked(self):
        self.assertEqual(render_sprite(TILE, PALETTE, flip=False), render_sprite(TILE, PALETTE))


class DrawSpriteTest(unittest.TestCase):
    def test_gives_nothing_back(self):
        self.assertIsNone(draw_sprite(Image(3, 2), TILE, PALETTE))

    def test_draws_at_the_top_left_unless_told(self):
        image = Image(5, 3)
        draw_sprite(image, TILE, PALETTE)
        self.assertEqual(rows(image), ["rg...", "..b..", "....."])

    def test_draws_at_an_offset_on_a_larger_image(self):
        image = Image(7, 5, WHITE)
        draw_sprite(image, TILE, PALETTE, 2, 1)
        self.assertEqual(rows(image), ["wwwwwww", "wwrgwww", "wwwwbww", "wwwwwww", "wwwwwww"])

    def test_offset_is_counted_in_pixels_of_the_image_whatever_the_scale(self):
        image = Image(8, 6)
        draw_sprite(image, TILE, PALETTE, 1, 1, 2)
        self.assertEqual(
            rows(image),
            ["........", ".rrgg...", ".rrgg...", ".....bb.", ".....bb.", "........"],
        )

    def test_block_at_scale_three_at_an_offset(self):
        image = Image(12, 8, WHITE)
        draw_sprite(image, TILE, PALETTE, 2, 1, 3)
        self.assertEqual(
            rows(image),
            ["wwwwwwwwwwww"] + ["wwrrrgggwwww"] * 3 + ["wwwwwwwwbbbw"] * 3 + ["wwwwwwwwwwww"],
        )

    def test_empty_cell_leaves_what_is_underneath(self):
        image = Image(3, 2, BLUE)
        put(image, 2, 0, (9, 8, 7, 6))
        put(image, 0, 1, CLEAR)
        draw_sprite(image, TILE, PALETTE)
        self.assertEqual(image.get(2, 0), (9, 8, 7, 6))
        self.assertEqual(image.get(0, 1), CLEAR)
        self.assertEqual(image.get(1, 1), (0, 0, 255, 255))

    def test_painted_cell_replaces_what_is_underneath(self):
        image = Image(3, 2, BLUE)
        put(image, 0, 0, (9, 8, 7, 6))
        put(image, 1, 0, CLEAR)
        draw_sprite(image, TILE, PALETTE)
        self.assertEqual(image.get(0, 0), (255, 0, 0, 255))
        self.assertEqual(image.get(1, 0), (0, 255, 0, 255))
        self.assertEqual(image.get(2, 1), (0, 0, 255, 255))

    def test_a_second_sprite_is_laid_over_the_first(self):
        image = Image(4, 2)
        draw_sprite(image, TILE, PALETTE)
        draw_sprite(image, Sprite("bar", ["b.b"]), PALETTE, 1, 0)
        self.assertEqual(rows(image), ["rb.b", "..b."])

    def test_flip_at_an_offset_stays_in_the_same_box(self):
        image = Image(7, 5, WHITE)
        draw_sprite(image, TILE, PALETTE, 2, 1, flip=True)
        self.assertEqual(rows(image), ["wwwwwww", "wwwgrww", "wwbwwww", "wwwwwww", "wwwwwww"])

    def test_flip_at_scale_at_an_offset(self):
        image = Image(8, 6)
        draw_sprite(image, TILE, PALETTE, 1, 1, 2, True)
        self.assertEqual(
            rows(image),
            ["........", "...ggrr.", "...ggrr.", ".bb.....", ".bb.....", "........"],
        )

    def test_partly_off_each_edge_draws_the_part_that_fits(self):
        cases = {
            "left": (-1, 0, ["g..", ".b."]),
            "right": (1, 0, [".rg", "..."]),
            "top": (0, -1, ["..b", "..."]),
            "bottom": (0, 1, ["...", "rg."]),
        }
        for edge, (x, y, expected) in cases.items():
            with self.subTest(edge=edge):
                image = Image(3, 2)
                draw_sprite(image, TILE, PALETTE, x, y)
                self.assertEqual(rows(image), expected)

    def test_block_partly_off_each_edge_is_cut(self):
        cases = {
            "left": (-1, 0, ["rgg...", "rgg...", "...bb.", "...bb."]),
            "right": (1, 0, [".rrgg.", ".rrgg.", ".....b", ".....b"]),
            "top": (0, -1, ["rrgg..", "....bb", "....bb", "......"]),
            "bottom": (0, 1, ["......", "rrgg..", "rrgg..", "....bb"]),
            "corner": (-1, -1, ["rgg...", "...bb.", "...bb.", "......"]),
        }
        for edge, (x, y, expected) in cases.items():
            with self.subTest(edge=edge):
                image = Image(6, 4)
                draw_sprite(image, TILE, PALETTE, x, y, 2)
                self.assertEqual(rows(image), expected)

    def test_flipped_and_partly_off_an_edge(self):
        image = Image(3, 2)
        draw_sprite(image, TILE, PALETTE, -1, 0, flip=True)
        self.assertEqual(rows(image), ["gr.", "..."])

    def test_wholly_outside_draws_nothing(self):
        for x, y in ((7, 0), (-3, 0), (0, 5), (0, -2), (100, 100), (-100, -100)):
            with self.subTest(x=x, y=y):
                image = Image(7, 5, WHITE)
                draw_sprite(image, TILE, PALETTE, x, y)
                self.assertEqual(image, Image(7, 5, WHITE))

    def test_larger_than_the_image_draws_the_part_that_fits(self):
        image = Image(4, 3)
        draw_sprite(image, TILE, PALETTE, -4, -2, 4)
        self.assertEqual(rows(image), ["gggg", "gggg", "...."])

    def test_any_offset_is_the_render_laid_there(self):
        under = Image(7, 5, WHITE)
        put(under, 3, 2, (9, 8, 7, 6))
        put(under, 0, 0, CLEAR)
        for scale in (1, 2, 3):
            for flip in (False, True):
                stamp = render_sprite(TILE, PALETTE, scale, flip=flip)
                for y in range(-stamp.height - 1, under.height + 2):
                    for x in range(-stamp.width - 1, under.width + 2):
                        with self.subTest(scale=scale, flip=flip, x=x, y=y):
                            expected = under.copy()
                            expected.blit(stamp, x, y)
                            image = under.copy()
                            draw_sprite(image, TILE, PALETTE, x, y, scale, flip)
                            self.assertEqual(image.data, expected.data)


class PaletteReadTest(unittest.TestCase):
    def test_own_entries_are_used_when_the_merged_palette_is_passed(self):
        sprite = Sprite("hat", ["rgo"], {"g": BLUE, "o": WHITE})
        merged = PALETTE.merged(sprite.palette)
        self.assertEqual(rows(render_sprite(sprite, merged)), ["rbw"])
        image = Image(3, 1)
        draw_sprite(image, sprite, merged)
        self.assertEqual(rows(image), ["rbw"])

    def test_only_the_palette_passed_is_read(self):
        sprite = Sprite("hat", ["rg"], {"g": BLUE})
        self.assertEqual(rows(render_sprite(sprite, PALETTE)), ["rg"])
        with self.assertRaises(PixelRowsError):
            render_sprite(Sprite("hat", ["ro"], {"o": WHITE}), PALETTE)

    def test_error_names_the_sprite_and_the_missing_character(self):
        with self.assertRaises(PixelRowsError) as caught:
            draw_sprite(Image(3, 1), Sprite("hat", ["rxg"]), PALETTE)
        self.assertEqual(str(caught.exception), "sprite 'hat': the palette has no colour for 'x'")

    def test_error_names_every_missing_character_once_in_order_of_appearance(self):
        sprite = Sprite("hat", ["rzx", "xgy", "z.b"])
        with self.assertRaises(PixelRowsError) as caught:
            draw_sprite(Image(3, 3), sprite, PALETTE)
        self.assertEqual(
            str(caught.exception),
            "sprite 'hat': the palette has no colour for 'z', 'x', 'y'",
        )

    def test_render_sprite_names_them_too(self):
        with self.assertRaises(PixelRowsError) as caught:
            render_sprite(Sprite("boot", ["xr", "gy"]), PALETTE, 2, WHITE, True)
        self.assertEqual(str(caught.exception), "sprite 'boot': the palette has no colour for 'x', 'y'")

    def test_empty_palette_lacks_every_painted_character(self):
        with self.assertRaises(PixelRowsError) as caught:
            render_sprite(TILE, Palette())
        self.assertEqual(
            str(caught.exception),
            "sprite 'tile': the palette has no colour for 'r', 'g', 'b'",
        )

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            render_sprite(Sprite("hat", ["x"]), PALETTE)

    def test_nothing_is_drawn_when_a_character_is_missing(self):
        image = Image(4, 3, WHITE)
        put(image, 1, 1, (9, 8, 7, 6))
        before = image.copy()
        sprite = Sprite("hat", ["rgb", "bgr", "rgx"])
        for scale in (1, 2):
            for flip in (False, True):
                with self.subTest(scale=scale, flip=flip):
                    with self.assertRaises(PixelRowsError):
                        draw_sprite(image, sprite, PALETTE, 0, 0, scale, flip)
                    self.assertEqual(image.data, before.data)

    def test_missing_character_is_refused_even_where_it_would_fall_outside(self):
        image = Image(2, 1, WHITE)
        with self.assertRaises(PixelRowsError):
            draw_sprite(image, Sprite("hat", ["rgx"]), PALETTE)
        with self.assertRaises(PixelRowsError):
            draw_sprite(image, Sprite("hat", ["rgx"]), PALETTE, 50, 50)
        self.assertEqual(image, Image(2, 1, WHITE))


class ScaleTest(unittest.TestCase):
    BAD = (0, -1, -3, 1.5, 2.0, True, False, "2", None)

    def test_draw_sprite_refuses_a_scale_below_one_or_not_a_whole_number(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    draw_sprite(Image(6, 4), TILE, PALETTE, 0, 0, bad)

    def test_render_sprite_refuses_a_scale_below_one_or_not_a_whole_number(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    render_sprite(TILE, PALETTE, bad)

    def test_error_says_what_was_given(self):
        with self.assertRaises(PixelRowsError) as caught:
            draw_sprite(Image(6, 4), TILE, PALETTE, scale=0)
        self.assertEqual(str(caught.exception), "scale must be a whole number of 1 or more, got 0")
        with self.assertRaises(PixelRowsError) as caught:
            render_sprite(TILE, PALETTE, scale=True)
        self.assertEqual(str(caught.exception), "scale must be a whole number of 1 or more, got True")

    def test_nothing_is_drawn_when_the_scale_is_refused(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                image = Image(6, 4, WHITE)
                with self.assertRaises(PixelRowsError):
                    draw_sprite(image, TILE, PALETTE, 1, 1, bad)
                self.assertEqual(image, Image(6, 4, WHITE))

    def test_scale_is_checked_when_nothing_is_painted(self):
        blank = Sprite("blank", ["..", ".."])
        for bad in self.BAD:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    draw_sprite(Image(2, 2), blank, Palette(), 0, 0, bad)
                with self.assertRaises(PixelRowsError):
                    render_sprite(blank, Palette(), bad)


if __name__ == "__main__":
    unittest.main()
