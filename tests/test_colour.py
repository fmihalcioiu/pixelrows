import itertools
import math
import unittest

from pixelrows.colour import (
    difference,
    lightness,
    oklab_to_linear,
    oklab_to_srgb,
    oklch_to_oklab,
    srgb_to_oklab,
    to_oklch,
)
from pixelrows.errors import PixelRowsError

GRID = tuple(itertools.product((0, 51, 102, 153, 204, 255), repeat=3))


class SrgbToOklabTest(unittest.TestCase):
    def assertLab(self, rgb, expected):
        for got, want in zip(srgb_to_oklab(rgb), expected):
            self.assertAlmostEqual(got, want, delta=5e-4)

    def test_white(self):
        self.assertLab((255, 255, 255), (1, 0, 0))

    def test_black(self):
        self.assertLab((0, 0, 0), (0, 0, 0))

    def test_red(self):
        self.assertLab((255, 0, 0), (0.62796, 0.22486, 0.12585))

    def test_green(self):
        self.assertLab((0, 255, 0), (0.86644, -0.23389, 0.17950))

    def test_blue(self):
        self.assertLab((0, 0, 255), (0.45201, -0.03246, -0.31153))

    def test_rejects_what_is_not_a_colour(self):
        for bad in ((256, 0, 0), (0, -1, 0), (1, 2)):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    srgb_to_oklab(bad)


class OklabToSrgbTest(unittest.TestCase):
    def test_grid_survives_the_round_trip_exactly(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                self.assertEqual(oklab_to_srgb(srgb_to_oklab(rgb)), rgb)

    def test_channels_are_clamped_to_0_255(self):
        for lab in ((0.5, 0.4, 0.0), (0.5, -0.4, 0.0), (0.5, 0.0, 0.4), (0.5, 0.0, -0.4), (1.5, 0, 0), (-0.5, 0, 0)):
            with self.subTest(lab=lab):
                rgb = oklab_to_srgb(lab)
                self.assertEqual(len(rgb), 3)
                for channel in rgb:
                    self.assertIsInstance(channel, int)
                    self.assertTrue(0 <= channel <= 255)

    def test_past_white_is_white_and_below_black_is_black(self):
        self.assertEqual(oklab_to_srgb((1.5, 0, 0)), (255, 255, 255))
        self.assertEqual(oklab_to_srgb((-0.5, 0, 0)), (0, 0, 0))


class OklabToLinearTest(unittest.TestCase):
    def test_white_and_black(self):
        for got in oklab_to_linear(srgb_to_oklab((255, 255, 255))):
            self.assertAlmostEqual(got, 1.0, places=5)
        self.assertEqual(oklab_to_linear((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0))

    def test_mid_grey_is_the_linear_value_of_its_channel(self):
        linear = ((128 / 255 + 0.055) / 1.055) ** 2.4
        for got in oklab_to_linear(srgb_to_oklab((128, 128, 128))):
            self.assertAlmostEqual(got, linear, places=5)

    def test_falls_outside_0_1_for_a_colour_srgb_lacks(self):
        linear = oklab_to_linear(oklch_to_oklab(0.5, 0.4, 0))
        self.assertTrue(min(linear) < 0 or max(linear) > 1)


class ToOklchTest(unittest.TestCase):
    def test_takes_either_form(self):
        self.assertEqual(to_oklch("#4773ab"), to_oklch((0x47, 0x73, 0xAB)))

    def test_lightness_and_chroma_are_those_of_oklab(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                l, a, b = srgb_to_oklab(rgb)
                got_l, got_c, _ = to_oklch(rgb)
                self.assertEqual(got_l, l)
                self.assertAlmostEqual(got_c, math.hypot(a, b), places=12)

    def test_hue_is_from_0_up_to_360(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                self.assertTrue(0 <= to_oklch(rgb)[2] < 360)

    def test_hue_below_the_a_axis_is_above_180(self):
        # Blue has a negative b, so atan2 gives a negative angle that must wrap.
        self.assertAlmostEqual(to_oklch("#0000ff")[2], 264.05, delta=0.05)
        self.assertAlmostEqual(to_oklch("#ff00ff")[2], 328.36, delta=0.05)

    def test_known_hues(self):
        self.assertAlmostEqual(to_oklch("#ff0000")[2], 29.23, delta=0.05)
        self.assertAlmostEqual(to_oklch("#00ff00")[2], 142.50, delta=0.05)

    def test_a_grey_has_hue_0(self):
        for value in (0, 1, 51, 128, 204, 255):
            with self.subTest(value=value):
                _, c, h = to_oklch((value, value, value))
                self.assertLess(c, 1e-7)
                self.assertEqual(h, 0.0)

    def test_goes_back_through_oklch_to_oklab(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                self.assertEqual(oklab_to_srgb(oklch_to_oklab(*to_oklch(rgb))), rgb)


class OklchToOklabTest(unittest.TestCase):
    def assertLab(self, got, expected):
        for g, e in zip(got, expected):
            self.assertAlmostEqual(g, e, places=12)

    def test_quarter_turns(self):
        self.assertLab(oklch_to_oklab(0.5, 0.1, 0), (0.5, 0.1, 0.0))
        self.assertLab(oklch_to_oklab(0.5, 0.1, 90), (0.5, 0.0, 0.1))
        self.assertLab(oklch_to_oklab(0.5, 0.1, 180), (0.5, -0.1, 0.0))
        self.assertLab(oklch_to_oklab(0.5, 0.1, 270), (0.5, 0.0, -0.1))

    def test_no_chroma_is_on_the_grey_axis(self):
        self.assertLab(oklch_to_oklab(0.7, 0.0, 123), (0.7, 0.0, 0.0))


class LightnessTest(unittest.TestCase):
    def test_black_is_0_and_white_is_1(self):
        self.assertEqual(lightness("#000000"), 0.0)
        self.assertAlmostEqual(lightness("#ffffff"), 1.0, delta=5e-4)

    def test_is_the_l_of_oklab(self):
        self.assertEqual(lightness("#ff0000"), srgb_to_oklab((255, 0, 0))[0])
        self.assertAlmostEqual(lightness((0, 255, 0)), 0.86644, delta=5e-4)

    def test_rises_with_a_grey(self):
        values = [lightness((v, v, v)) for v in range(0, 256, 15)]
        self.assertEqual(values, sorted(values))
        self.assertEqual(len(set(values)), len(values))


class DifferenceTest(unittest.TestCase):
    def test_a_colour_and_itself(self):
        self.assertEqual(difference("#4773ab", (0x47, 0x73, 0xAB)), 0.0)

    def test_black_to_white_is_1(self):
        self.assertAlmostEqual(difference("#000000", "#ffffff"), 1.0, delta=5e-4)

    def test_is_the_same_both_ways(self):
        self.assertEqual(difference("#ff0000", "#0000ff"), difference("#0000ff", "#ff0000"))

    def test_is_the_distance_in_oklab(self):
        a, b = srgb_to_oklab((255, 0, 0)), srgb_to_oklab((0, 255, 0))
        expected = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        self.assertAlmostEqual(difference("#ff0000", "#00ff00"), expected, places=12)

    def test_near_colours_are_closer_than_far_ones(self):
        self.assertLess(difference("#4773ab", "#4874ac"), difference("#4773ab", "#739dc3"))


if __name__ == "__main__":
    unittest.main()
