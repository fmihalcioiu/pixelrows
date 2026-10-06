import math
import unittest
from fractions import Fraction

from pixelrows.errors import PixelRowsError
from pixelrows.image import Image

CLEAR = (0, 0, 0, 0)

BLACK = "#000000"
WHITE = "#ffffff"
RED = "#ff0000"
GREEN = "#00ff00"
BLUE = "#0000ff"

# One letter a pixel, so a small image can be written and read as rows of text.
LETTERS = {
    ".": CLEAR,
    "k": (0, 0, 0, 255),
    "w": (255, 255, 255, 255),
    "r": (255, 0, 0, 255),
    "g": (0, 255, 0, 255),
    "b": (0, 0, 255, 255),
    "y": (255, 255, 0, 255),
}
NAMES = {rgba: letter for letter, rgba in LETTERS.items()}


def put(image, x, y, rgba):
    """Writes one pixel straight into the image's bytes."""
    at = (y * image.width + x) * 4
    image.data[at:at + 4] = bytes(rgba)


def at(image, x, y):
    """Reads one pixel straight from the image's bytes."""
    start = (y * image.width + x) * 4
    return tuple(image.data[start:start + 4])


def drawn(*lines):
    """An image from rows of letters."""
    image = Image(len(lines[0]), len(lines))
    for y, line in enumerate(lines):
        for x, letter in enumerate(line):
            put(image, x, y, LETTERS[letter])
    return image


def rows(image):
    """The image as rows of letters, '?' for a pixel that has none."""
    return [
        "".join(NAMES.get(at(image, x, y), "?") for x in range(image.width))
        for y in range(image.height)
    ]


def strip(pixels):
    """An image one pixel high holding the given (r, g, b, a) values."""
    image = Image(len(pixels), 1)
    for x, rgba in enumerate(pixels):
        put(image, x, 0, rgba)
    return image


def source_over(top, under):
    """
    `top` laid over `under`, both (r, g, b, a), by the source-over rule.

    Worked out in exact fractions with alpha from 0 to 1, then each channel
    rounded to the nearest whole number.
    """
    top_alpha = Fraction(top[3], 255)
    under_alpha = Fraction(under[3], 255)
    alpha = top_alpha + under_alpha * (1 - top_alpha)
    if top_alpha == 0:
        return tuple(under)
    half = Fraction(1, 2)
    channels = [
        math.floor((t * top_alpha + u * under_alpha * (1 - top_alpha)) / alpha + half)
        for t, u in zip(top[:3], under[:3])
    ]
    return (*channels, math.floor(alpha * 255 + half))


SPREAD_COLOURS = [(255, 255, 255), (0, 0, 0), (200, 10, 255), (1, 2, 3)]
SPREAD_ALPHAS = [1, 2, 64, 127, 128, 200, 254]
SPREAD_UNDER = [
    CLEAR,
    (0, 0, 0, 255),
    (255, 255, 255, 255),
    (50, 250, 0, 255),
    (50, 250, 0, 1),
    (255, 0, 128, 128),
    (13, 77, 201, 254),
]


class NewImageTest(unittest.TestCase):
    def test_keeps_its_size(self):
        image = Image(3, 2)
        self.assertEqual((image.width, image.height), (3, 2))

    def test_default_is_fully_transparent(self):
        image = Image(3, 2)
        self.assertIsInstance(image.data, bytearray)
        self.assertEqual(image.data, bytearray(3 * 2 * 4))
        for y in range(2):
            for x in range(3):
                self.assertEqual(image.get(x, y), CLEAR)

    def test_background_as_hex_is_opaque_everywhere(self):
        image = Image(3, 2, "#102030")
        self.assertEqual(image.data, bytearray([16, 32, 48, 255] * 6))

    def test_background_as_numbers(self):
        image = Image(2, 2, (1, 2, 3))
        self.assertEqual(image.data, bytearray([1, 2, 3, 255] * 4))

    def test_data_is_rgba_row_by_row(self):
        image = Image(3, 2)
        image.set(1, 0, (10, 20, 30))
        image.set(0, 1, (40, 50, 60))
        self.assertEqual(image.data[4:8], bytearray([10, 20, 30, 255]))
        self.assertEqual(image.data[12:16], bytearray([40, 50, 60, 255]))
        self.assertEqual(sum(image.data), 10 + 20 + 30 + 255 + 40 + 50 + 60 + 255)

    def test_size_must_be_a_whole_number_of_one_or_more(self):
        for bad in (0, -1, 1.5, 2.0, "3", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    Image(bad, 4)
                with self.assertRaises(PixelRowsError):
                    Image(4, bad)

    def test_size_error_says_which_side(self):
        with self.assertRaisesRegex(PixelRowsError, "width"):
            Image(0, 4)
        with self.assertRaisesRegex(PixelRowsError, "height"):
            Image(4, 0)

    def test_background_that_is_not_a_colour(self):
        for bad in ("red", "#12345", (256, 0, 0), (1, 2)):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    Image(2, 2, bad)


class GetTest(unittest.TestCase):
    def test_gives_red_green_blue_alpha(self):
        image = Image(2, 2)
        put(image, 1, 1, (9, 8, 7, 6))
        self.assertEqual(image.get(1, 1), (9, 8, 7, 6))
        self.assertIsInstance(image.get(1, 1), tuple)

    def test_outside_raises_index_error(self):
        image = Image(3, 2, WHITE)
        for x, y in ((-1, 0), (0, -1), (3, 0), (0, 2), (3, 2), (-1, -1), (100, 100)):
            with self.subTest(x=x, y=y):
                with self.assertRaises(IndexError):
                    image.get(x, y)

    def test_every_corner_is_inside(self):
        image = Image(3, 2, WHITE)
        for x, y in ((0, 0), (2, 0), (0, 1), (2, 1)):
            self.assertEqual(image.get(x, y), (255, 255, 255, 255))


class SetTest(unittest.TestCase):
    def test_replaces_the_pixel(self):
        image = Image(2, 2, WHITE)
        image.set(1, 0, RED)
        self.assertEqual(rows(image), ["wr", "ww"])

    def test_takes_hex_or_numbers(self):
        image = Image(2, 1)
        image.set(0, 0, "#0a141e")
        image.set(1, 0, (10, 20, 30))
        self.assertEqual(image.get(0, 0), (10, 20, 30, 255))
        self.assertEqual(image.get(1, 0), (10, 20, 30, 255))

    def test_outside_is_ignored(self):
        image = Image(3, 2, WHITE)
        before = bytes(image.data)
        for x, y in ((-1, 0), (0, -1), (3, 0), (0, 2), (3, 2), (-5, -5), (100, 1)):
            with self.subTest(x=x, y=y):
                image.set(x, y, RED)
                image.set(x, y, RED, 128)
                self.assertEqual(bytes(image.data), before)

    def test_alpha_zero_does_nothing(self):
        image = strip([CLEAR, (0, 0, 0, 255), (5, 6, 7, 8)])
        before = bytes(image.data)
        for x in range(3):
            image.set(x, 0, WHITE, 0)
        self.assertEqual(bytes(image.data), before)

    def test_alpha_255_replaces_a_partly_transparent_pixel(self):
        image = strip([(5, 6, 7, 8)])
        image.set(0, 0, (100, 110, 120), 255)
        self.assertEqual(image.get(0, 0), (100, 110, 120, 255))

    def test_colour_that_is_not_a_colour(self):
        image = Image(2, 2)
        for bad in ("red", "#12", (0, 0, 300), None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    image.set(0, 0, bad)

    def test_alpha_must_be_a_whole_number_from_0_to_255(self):
        image = Image(2, 2)
        for bad in (-1, 256, 0.5, "255", None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    image.set(0, 0, WHITE, bad)
        self.assertEqual(image.data, bytearray(16))


class AlphaRuleTest(unittest.TestCase):
    def test_half_white_over_opaque_black_is_mid_grey_and_opaque(self):
        image = Image(2, 1, BLACK)
        image.set(0, 0, WHITE, 128)
        image.set(1, 0, WHITE, 127)
        # 255 * 128 / 255 = 128 and 255 * 127 / 255 = 127; the alpha stays 255.
        self.assertEqual(image.get(0, 0), (128, 128, 128, 255))
        self.assertEqual(image.get(1, 0), (127, 127, 127, 255))

    def test_half_transparent_over_transparent_keeps_its_colour_and_its_alpha(self):
        image = Image(1, 1)
        image.set(0, 0, RED, 128)
        self.assertEqual(image.get(0, 0), (255, 0, 0, 128))

    def test_half_white_over_half_black(self):
        image = Image(1, 1)
        image.set(0, 0, BLACK, 128)
        self.assertEqual(image.get(0, 0), (0, 0, 0, 128))
        image.set(0, 0, WHITE, 128)
        # Alpha: 128 + 128 * 127 / 255 = 191.75, so 192.
        # White's share: 128 / 191.75 = 0.6675, times 255 is 170.2, so 170.
        self.assertEqual(image.get(0, 0), (170, 170, 170, 192))

    def test_channels_round_to_the_nearest_and_not_down(self):
        image = Image(1, 1, (50, 250, 0))
        image.set(0, 0, (200, 10, 255), 100)
        # Red: (200 * 100 + 50 * 155) / 255 = 108.82, so 109.
        # Green: (10 * 100 + 250 * 155) / 255 = 155.88, so 156.
        # Blue: (255 * 100 + 0 * 155) / 255 = 100.
        self.assertEqual(image.get(0, 0), (109, 156, 100, 255))

    def test_the_alpha_of_the_result_is_rounded_too(self):
        image = Image(1, 1)
        image.set(0, 0, BLACK, 100)
        image.set(0, 0, WHITE, 100)
        # Alpha: 100 + 100 * 155 / 255 = 160.78, so 161.
        # White's share: 100 / 160.78 = 0.62195, times 255 is 158.6, so 159.
        self.assertEqual(image.get(0, 0), (159, 159, 159, 161))

    def test_the_colour_under_a_transparent_pixel_does_not_show(self):
        image = strip([(255, 255, 255, 0)])
        image.set(0, 0, BLACK, 128)
        self.assertEqual(image.get(0, 0), (0, 0, 0, 128))

    def test_set_holds_source_over_for_a_spread_of_values(self):
        for colour in SPREAD_COLOURS:
            for alpha in SPREAD_ALPHAS:
                image = strip(SPREAD_UNDER)
                for x, under in enumerate(SPREAD_UNDER):
                    image.set(x, 0, colour, alpha)
                    self.assertEqual(
                        image.get(x, 0), source_over((*colour, alpha), under),
                        f"{colour} at alpha {alpha} over {under}",
                    )

    def test_fill_holds_source_over_for_a_spread_of_values(self):
        for colour in SPREAD_COLOURS:
            for alpha in SPREAD_ALPHAS:
                image = strip(SPREAD_UNDER)
                image.fill(0, 0, len(SPREAD_UNDER), 1, colour, alpha)
                for x, under in enumerate(SPREAD_UNDER):
                    self.assertEqual(
                        image.get(x, 0), source_over((*colour, alpha), under),
                        f"{colour} at alpha {alpha} over {under}",
                    )

    def test_blit_holds_source_over_for_a_spread_of_values(self):
        for colour in SPREAD_COLOURS:
            for alpha in SPREAD_ALPHAS + [0, 255]:
                image = strip(SPREAD_UNDER)
                image.blit(strip([(*colour, alpha)] * len(SPREAD_UNDER)), 0, 0)
                for x, under in enumerate(SPREAD_UNDER):
                    self.assertEqual(
                        image.get(x, 0), source_over((*colour, alpha), under),
                        f"{colour} at alpha {alpha} over {under}",
                    )


class FillTest(unittest.TestCase):
    def test_fills_a_rectangle(self):
        image = Image(4, 3)
        image.fill(1, 1, 2, 1, RED)
        self.assertEqual(rows(image), ["....", ".rr.", "...."])

    def test_fills_the_whole_image(self):
        image = Image(4, 3, WHITE)
        image.fill(0, 0, 4, 3, (0, 0, 255))
        self.assertEqual(rows(image), ["bbbb", "bbbb", "bbbb"])

    def test_replaces_what_is_there(self):
        image = drawn("rg", "b.")
        image.fill(0, 0, 2, 2, BLACK)
        self.assertEqual(rows(image), ["kk", "kk"])

    def test_clips_at_the_top_left(self):
        image = Image(4, 3)
        image.fill(-1, -1, 2, 2, RED)
        self.assertEqual(rows(image), ["r...", "....", "...."])

    def test_clips_at_the_bottom_right(self):
        image = Image(4, 3)
        image.fill(3, 2, 5, 5, GREEN)
        self.assertEqual(rows(image), ["....", "....", "...g"])

    def test_clips_at_the_left_and_right(self):
        image = Image(4, 3)
        image.fill(-5, 1, 100, 1, BLUE)
        self.assertEqual(rows(image), ["....", "bbbb", "...."])

    def test_clips_at_the_top_and_bottom(self):
        image = Image(4, 3)
        image.fill(1, -5, 1, 100, BLUE)
        self.assertEqual(rows(image), [".b..", ".b..", ".b.."])

    def test_larger_than_the_image_fills_it_all(self):
        image = Image(4, 3)
        image.fill(-10, -10, 100, 100, WHITE)
        self.assertEqual(rows(image), ["wwww", "wwww", "wwww"])

    def test_wholly_outside_does_nothing(self):
        image = Image(4, 3)
        for x, y in ((-2, 0), (4, 0), (0, -2), (0, 3), (50, 50)):
            with self.subTest(x=x, y=y):
                image.fill(x, y, 2, 2, RED)
                image.fill(x, y, 2, 2, RED, 128)
                self.assertEqual(image.data, bytearray(4 * 3 * 4))

    def test_no_width_or_no_height_draws_nothing(self):
        image = Image(4, 3)
        for w, h in ((0, 2), (2, 0), (-1, 2), (2, -1), (0, 0)):
            with self.subTest(w=w, h=h):
                image.fill(1, 1, w, h, RED)
                image.fill(1, 1, w, h, RED, 128)
                self.assertEqual(image.data, bytearray(4 * 3 * 4))

    def test_alpha_zero_does_nothing(self):
        image = drawn("rg", "b.")
        image.fill(0, 0, 2, 2, WHITE, 0)
        self.assertEqual(rows(image), ["rg", "b."])

    def test_alpha_between_lays_over_each_pixel_by_the_rule(self):
        image = drawn("k.w")
        image.fill(0, 0, 3, 1, WHITE, 128)
        self.assertEqual(image.get(0, 0), (128, 128, 128, 255))
        self.assertEqual(image.get(1, 0), (255, 255, 255, 128))
        self.assertEqual(image.get(2, 0), (255, 255, 255, 255))

    def test_alpha_between_leaves_the_rest_alone(self):
        image = drawn("kkk", "kkk", "kkk")
        image.fill(1, 1, 1, 1, WHITE, 128)
        self.assertEqual(rows(image), ["kkk", "k?k", "kkk"])
        self.assertEqual(image.get(1, 1), (128, 128, 128, 255))

    def test_bad_colour_and_bad_alpha(self):
        image = Image(2, 2)
        with self.assertRaises(PixelRowsError):
            image.fill(0, 0, 2, 2, "not a colour")
        for bad in (-1, 256, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    image.fill(0, 0, 2, 2, WHITE, bad)
        self.assertEqual(image.data, bytearray(16))


class BlitTest(unittest.TestCase):
    def setUp(self):
        self.base = drawn("kkk", "kkk", "kkk")
        self.stamp = drawn("rg", "by")

    def test_lands_with_its_top_left_corner_at_x_y(self):
        self.base.blit(self.stamp, 1, 1)
        self.assertEqual(rows(self.base), ["kkk", "krg", "kby"])

    def test_opaque_pixels_replace_what_is_there(self):
        base = drawn("wwww", "wwww")
        base.blit(drawn("rgby"), 0, 1)
        self.assertEqual(rows(base), ["wwww", "rgby"])

    def test_transparent_source_pixels_keep_what_is_underneath(self):
        base = drawn("kkk", "kkk")
        base.blit(drawn("r.g", ".w."), 0, 0)
        self.assertEqual(rows(base), ["rkg", "kwk"])

    def test_transparent_over_transparent_stays_transparent(self):
        base = Image(3, 1)
        base.blit(drawn("r.g"), 0, 0)
        self.assertEqual(rows(base), ["r.g"])

    def test_a_wholly_transparent_source_changes_nothing(self):
        self.base.blit(Image(2, 2), 0, 0)
        self.assertEqual(rows(self.base), ["kkk", "kkk", "kkk"])

    def test_the_colour_of_a_transparent_source_pixel_does_not_leak(self):
        self.base.blit(strip([(255, 255, 255, 0)]), 1, 1)
        self.assertEqual(rows(self.base), ["kkk", "kkk", "kkk"])

    def test_partly_transparent_pixels_are_laid_over_by_the_rule(self):
        base = drawn("k.")
        base.blit(strip([(255, 255, 255, 128), (255, 255, 255, 128)]), 0, 0)
        self.assertEqual(base.get(0, 0), (128, 128, 128, 255))
        self.assertEqual(base.get(1, 0), (255, 255, 255, 128))

    def test_clips_at_the_left(self):
        self.base.blit(self.stamp, -1, 0)
        self.assertEqual(rows(self.base), ["gkk", "ykk", "kkk"])

    def test_clips_at_the_top(self):
        self.base.blit(self.stamp, 0, -1)
        self.assertEqual(rows(self.base), ["byk", "kkk", "kkk"])

    def test_clips_at_the_right(self):
        self.base.blit(self.stamp, 2, 0)
        self.assertEqual(rows(self.base), ["kkr", "kkb", "kkk"])

    def test_clips_at_the_bottom(self):
        self.base.blit(self.stamp, 0, 2)
        self.assertEqual(rows(self.base), ["kkk", "kkk", "rgk"])

    def test_clips_at_each_corner(self):
        cases = {
            (-1, -1): ["ykk", "kkk", "kkk"],
            (2, -1): ["kkb", "kkk", "kkk"],
            (-1, 2): ["kkk", "kkk", "gkk"],
            (2, 2): ["kkk", "kkk", "kkr"],
        }
        for (x, y), expected in cases.items():
            with self.subTest(x=x, y=y):
                base = drawn("kkk", "kkk", "kkk")
                base.blit(self.stamp, x, y)
                self.assertEqual(rows(base), expected)

    def test_clips_on_all_four_sides_at_once(self):
        base = drawn("kk", "kk")
        base.blit(drawn("rgby", "gbyr", "byrg", "yrgb"), -1, -1)
        self.assertEqual(rows(base), ["by", "yr"])

    def test_clips_partly_transparent_pixels_too(self):
        stamp = strip([(255, 255, 255, 128)] * 4)
        for x in (-3, -1, 1, 2):
            with self.subTest(x=x):
                base = drawn("kkk")
                base.blit(stamp, x, 0)
                expected = ["?" if x <= i < x + 4 else "k" for i in range(3)]
                self.assertEqual(rows(base), ["".join(expected)])

    def test_wholly_outside_does_nothing(self):
        for x, y in ((-2, 0), (3, 0), (0, -2), (0, 3), (-9, -9), (9, 9)):
            with self.subTest(x=x, y=y):
                self.base.blit(self.stamp, x, y)
                self.assertEqual(rows(self.base), ["kkk", "kkk", "kkk"])

    def test_does_what_set_does_pixel_by_pixel(self):
        stamp = Image(3, 3)
        values = [
            (255, 0, 0, 255), (0, 255, 0, 128), CLEAR,
            (9, 9, 9, 1), (0, 0, 255, 255), (200, 100, 50, 254),
            CLEAR, (255, 255, 255, 77), (1, 2, 3, 255),
        ]
        for i, rgba in enumerate(values):
            put(stamp, i % 3, i // 3, rgba)
        lines = ("rg.kw", "w.kgr", "..b..", "kkwww")
        for x, y in ((0, 0), (1, 1), (2, 1), (-1, -2), (3, 2), (4, 3), (-2, 3)):
            with self.subTest(x=x, y=y):
                blitted = drawn(*lines)
                blitted.blit(stamp, x, y)
                by_set = drawn(*lines)
                for sy in range(3):
                    for sx in range(3):
                        r, g, b, a = at(stamp, sx, sy)
                        by_set.set(x + sx, y + sy, (r, g, b), a)
                self.assertEqual(blitted.data, by_set.data)

    def test_leaves_the_source_as_it_is(self):
        before = bytes(self.stamp.data)
        self.base.blit(self.stamp, 1, 1)
        self.base.blit(self.stamp, -1, -1)
        self.assertEqual(bytes(self.stamp.data), before)

    def test_onto_itself_reads_the_image_as_it_was(self):
        image = drawn("rg.", "...", "...")
        image.blit(image, 1, 1)
        self.assertEqual(rows(image), ["rg.", ".rg", "..."])

    def test_takes_only_an_image(self):
        for bad in (None, bytearray(16), ["rg", "by"]):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    self.base.blit(bad, 0, 0)


class CopyTest(unittest.TestCase):
    def test_a_copy_is_equal(self):
        image = drawn("rg", "b.")
        twin = image.copy()
        self.assertIsNot(twin, image)
        self.assertEqual(twin, image)
        self.assertEqual((twin.width, twin.height), (2, 2))

    def test_drawing_on_the_copy_leaves_the_image(self):
        image = drawn("rg", "b.")
        twin = image.copy()
        twin.set(0, 0, WHITE)
        twin.fill(1, 0, 1, 2, BLACK)
        self.assertEqual(rows(image), ["rg", "b."])
        self.assertEqual(rows(twin), ["wk", "bk"])

    def test_drawing_on_the_image_leaves_the_copy(self):
        image = drawn("rg", "b.")
        twin = image.copy()
        image.fill(0, 0, 2, 2, WHITE)
        self.assertEqual(rows(twin), ["rg", "b."])

    def test_the_bytes_are_not_shared(self):
        image = Image(2, 2, RED)
        self.assertIsNot(image.copy().data, image.data)


class EqualityTest(unittest.TestCase):
    def test_same_size_and_same_pixels_are_equal(self):
        self.assertEqual(drawn("rg", "b."), drawn("rg", "b."))
        self.assertEqual(Image(3, 2), Image(3, 2))
        self.assertEqual(Image(3, 2, "#ff0000"), Image(3, 2, (255, 0, 0)))

    def test_one_different_pixel_is_not_equal(self):
        self.assertNotEqual(drawn("rg", "b."), drawn("rg", "bk"))

    def test_a_different_alpha_is_not_equal(self):
        self.assertNotEqual(strip([(1, 2, 3, 255)]), strip([(1, 2, 3, 254)]))

    def test_same_bytes_in_another_shape_are_not_equal(self):
        self.assertEqual(Image(2, 3).data, Image(3, 2).data)
        self.assertNotEqual(Image(2, 3), Image(3, 2))
        self.assertNotEqual(Image(1, 4), Image(4, 1))

    def test_not_equal_to_what_is_not_an_image(self):
        image = Image(1, 1)
        for other in (None, bytearray(4), bytes(4), [CLEAR], "image"):
            with self.subTest(other=other):
                self.assertNotEqual(image, other)


if __name__ == "__main__":
    unittest.main()
