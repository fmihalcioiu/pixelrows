import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.palette import TRANSPARENT, Palette, as_rgb, parse_hex, to_hex


class ParseHexTest(unittest.TestCase):
    def test_six_digits(self):
        self.assertEqual(parse_hex("#1a2b3c"), (0x1A, 0x2B, 0x3C))

    def test_upper_case(self):
        self.assertEqual(parse_hex("#FFA000"), (255, 160, 0))

    def test_three_digits_are_doubled(self):
        self.assertEqual(parse_hex("#f80"), (255, 136, 0))

    def test_rejects_what_is_not_a_colour(self):
        for bad in ("1a2b3c", "#1a2b3", "#1a2b3cd", "#gggggg", "", "#", None, 7):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    parse_hex(bad)


class ToHexTest(unittest.TestCase):
    def test_lower_case_and_padded(self):
        self.assertEqual(to_hex((255, 160, 0)), "#ffa000")
        self.assertEqual(to_hex((0, 1, 2)), "#000102")

    def test_rejects_numbers_out_of_range(self):
        for bad in ((256, 0, 0), (0, -1, 0), (1, 2), "abc"):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    to_hex(bad)

    def test_round_trip(self):
        self.assertEqual(to_hex(parse_hex("#4773ab")), "#4773ab")


class AsRgbTest(unittest.TestCase):
    def test_takes_either_form(self):
        self.assertEqual(as_rgb("#102030"), (16, 32, 48))
        self.assertEqual(as_rgb((16, 32, 48)), (16, 32, 48))


class PaletteTest(unittest.TestCase):
    def setUp(self):
        self.palette = Palette({"o": "#1A1A22", "s": (232, 176, 135)})

    def test_colours_come_back_both_ways(self):
        self.assertEqual(self.palette.hex("o"), "#1a1a22")
        self.assertEqual(self.palette.rgb("o"), (26, 26, 34))
        self.assertEqual(self.palette["s"], (232, 176, 135))
        self.assertEqual(self.palette.hex("s"), "#e8b087")

    def test_dot_is_always_known_and_has_no_colour(self):
        self.assertIn(TRANSPARENT, self.palette)
        self.assertIn(TRANSPARENT, Palette())
        self.assertIsNone(self.palette.hex("."))
        self.assertIsNone(self.palette["."])

    def test_dot_is_not_counted(self):
        self.assertEqual(self.palette.chars(), ["o", "s"])
        self.assertEqual(list(self.palette), ["o", "s"])
        self.assertEqual(len(self.palette), 2)

    def test_dot_may_be_listed_as_none_and_is_dropped(self):
        palette = Palette({".": None, "o": "#000000"})
        self.assertEqual(palette.to_dict(), {"o": "#000000"})

    def test_dot_cannot_be_given_a_colour(self):
        with self.assertRaises(PixelRowsError):
            Palette({".": "#ffffff"})

    def test_unknown_character(self):
        self.assertNotIn("q", self.palette)
        with self.assertRaises(KeyError):
            self.palette.hex("q")
        with self.assertRaises(KeyError):
            self.palette["q"]

    def test_bad_keys(self):
        for bad in ("ab", "", " ", "\t", 1):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    Palette({bad: "#000000"})

    def test_only_dot_may_be_none(self):
        with self.assertRaises(PixelRowsError):
            Palette({"o": None})

    def test_to_dict_keeps_order_and_round_trips(self):
        self.assertEqual(list(self.palette.to_dict()), ["o", "s"])
        self.assertEqual(Palette(self.palette.to_dict()), self.palette)

    def test_set_changes_a_colour(self):
        self.palette.set("o", "#000")
        self.assertEqual(self.palette.hex("o"), "#000000")


if __name__ == "__main__":
    unittest.main()
