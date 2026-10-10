import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.palette import TRANSPARENT, Palette, as_rgb, parse_hex, to_hex

#: What is not three whole numbers in a list or a tuple, one of each kind.
NOT_NUMBERS = (
    [1.9, 2.0, 3.5],
    ["1", "2", "3"],
    [True, False, True],
    {1: 0, 2: 0, 3: 0},
    {1, 2, 3},
    (1, 2),
    [1, 2, 3, 4],
    (float("inf"), 0, 0),
    [0, float("nan"), 0],
)


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

    def test_takes_a_list_or_a_tuple_of_whole_numbers(self):
        self.assertEqual(to_hex([255, 160, 0]), "#ffa000")
        self.assertEqual(to_hex((255, 160, 0)), "#ffa000")
        self.assertEqual(to_hex([0, 0, 0]), "#000000")
        self.assertEqual(to_hex((255, 255, 255)), "#ffffff")

    def assert_refused(self, *colours):
        for bad in colours:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    to_hex(bad)
                self.assertEqual(
                    str(caught.exception),
                    f"not a colour: {bad!r} (expected a list or a tuple of three whole numbers)",
                )

    def test_floats_are_refused(self):
        self.assert_refused([1.9, 2.0, 3.5], (1.0, 2.0, 3.0), [1, 2, 3.0], (0.5, 2, 3))

    def test_digit_strings_in_a_list_are_refused(self):
        self.assert_refused(["1", "2", "3"], [1, "2", 3], ("ff", "a0", "00"))

    def test_bools_are_refused(self):
        self.assert_refused([True, False, True], (1, 2, True), [False, 0, 0])

    def test_a_dict_is_refused(self):
        self.assert_refused({1: 0, 2: 0, 3: 0}, {"r": 1, "g": 2, "b": 3})

    def test_a_set_is_refused(self):
        self.assert_refused({1, 2, 3}, frozenset((1, 2, 3)))

    def test_a_string_is_refused(self):
        self.assert_refused("123", "abc", "#102030")

    def test_two_or_four_numbers_are_refused(self):
        self.assert_refused((1, 2), [1, 2], (1, 2, 3, 4), [1, 2, 3, 255], [7], ())

    def test_infinity_and_nan_are_refused(self):
        self.assert_refused([float("inf"), 0, 0], (0, float("-inf"), 0), [0, 0, float("nan")])

    def test_what_is_not_a_list_or_a_tuple_is_refused(self):
        self.assert_refused(None, 7, 1.5, True, range(3), b"\x01\x02\x03", iter([1, 2, 3]))

    def test_a_float_a_digit_string_and_a_bool_together_are_refused(self):
        self.assert_refused([1.9, "2", True])

    def test_number_out_of_range_says_the_range(self):
        for bad in ((256, 0, 0), [0, -1, 0], (0, 0, 1000)):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    to_hex(bad)
                self.assertEqual(str(caught.exception), f"not a colour: {bad!r} (each number is 0 to 255)")


class AsRgbTest(unittest.TestCase):
    def test_takes_either_form(self):
        self.assertEqual(as_rgb("#102030"), (16, 32, 48))
        self.assertEqual(as_rgb((16, 32, 48)), (16, 32, 48))

    def test_takes_a_list_or_a_tuple_of_whole_numbers(self):
        self.assertEqual(as_rgb([16, 32, 48]), (16, 32, 48))
        self.assertEqual(as_rgb((0, 255, 7)), (0, 255, 7))
        self.assertIsInstance(as_rgb([16, 32, 48]), tuple)

    def test_what_is_not_whole_numbers_is_refused(self):
        for bad in NOT_NUMBERS:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    as_rgb(bad)
                self.assertEqual(
                    str(caught.exception),
                    f"not a colour: {bad!r} (expected a list or a tuple of three whole numbers)",
                )

    def test_a_string_that_is_not_a_hex_colour_is_refused(self):
        for bad in ("123", "abc", "1,2,3", "(1, 2, 3)"):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    as_rgb(bad)
                self.assertEqual(str(caught.exception), f"not a colour: {bad!r} (expected '#rrggbb')")

    def test_numbers_out_of_range_are_refused(self):
        for bad in ((256, 0, 0), [0, -1, 0]):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    as_rgb(bad)


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

    def test_merged_lays_the_other_over(self):
        merged = self.palette.merged({"s": "#ffffff", "x": "#ff0000"})
        self.assertEqual(merged.to_dict(), {"o": "#1a1a22", "s": "#ffffff", "x": "#ff0000"})
        self.assertEqual(self.palette.hex("s"), "#e8b087")

    def test_merged_takes_a_palette_or_nothing(self):
        self.assertEqual(self.palette.merged(Palette({"x": "#ff0000"})).chars(), ["o", "s", "x"])
        self.assertEqual(self.palette.merged(None), self.palette)

    def test_to_dict_keeps_order_and_round_trips(self):
        self.assertEqual(list(self.palette.to_dict()), ["o", "s"])
        self.assertEqual(Palette(self.palette.to_dict()), self.palette)

    def test_set_changes_a_colour(self):
        self.palette.set("o", "#000")
        self.assertEqual(self.palette.hex("o"), "#000000")

    def test_colour_may_be_a_list_or_a_tuple_of_whole_numbers(self):
        palette = Palette({"a": [16, 32, 48], "b": (16, 32, 48)})
        self.assertEqual(palette.to_dict(), {"a": "#102030", "b": "#102030"})
        palette.set("a", [0, 0, 255])
        self.assertEqual(palette.rgb("a"), (0, 0, 255))

    def test_colour_that_is_not_whole_numbers_is_refused(self):
        for bad in NOT_NUMBERS:
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    Palette({"o": bad})
                self.assertEqual(
                    str(caught.exception),
                    f"not a colour: {bad!r} (expected a list or a tuple of three whole numbers)",
                )
                with self.assertRaises(PixelRowsError):
                    self.palette.set("o", bad)
                with self.assertRaises(PixelRowsError):
                    self.palette.merged({"o": bad})
        self.assertEqual(self.palette.hex("o"), "#1a1a22")


if __name__ == "__main__":
    unittest.main()
