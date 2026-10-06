import unittest

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
                self.assertEqual(bytes(image.data), before)

    def test_colour_that_is_not_a_colour(self):
        image = Image(2, 2)
        for bad in ("red", "#12", (0, 0, 300), None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    image.set(0, 0, bad)


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
                self.assertEqual(image.data, bytearray(4 * 3 * 4))

    def test_no_width_or_no_height_draws_nothing(self):
        image = Image(4, 3)
        for w, h in ((0, 2), (2, 0), (-1, 2), (2, -1), (0, 0)):
            with self.subTest(w=w, h=h):
                image.fill(1, 1, w, h, RED)
                self.assertEqual(image.data, bytearray(4 * 3 * 4))


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
