import itertools
import math
import unittest

from pixelrows.colour import (
    difference,
    fit_chroma,
    in_gamut,
    lightness,
    oklab_to_linear,
    oklab_to_srgb,
    oklch_to_hex,
    oklch_to_oklab,
    srgb_to_oklab,
    to_oklch,
)
from pixelrows.errors import PixelRowsError
from pixelrows.palette import to_hex

GRID = tuple(itertools.product((0, 51, 102, 153, 204, 255), repeat=3))
CORNERS = tuple(itertools.product((0, 255), repeat=3))

# Lightness, chroma and hue values the gamut tests run over.
LIGHTNESSES = (0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
CHROMAS = (0.0, 0.02, 0.08, 0.15, 0.25, 0.4)
HUES = tuple(range(0, 360, 20))

# What is not a finite number.
NOT_FINITE = (float("nan"), float("inf"), float("-inf"), 10 ** 400, "0.5", None, True, False)


def excursion(l, c, h):
    """How far the worst linear channel of this colour falls outside 0..1."""
    return max(max(-v, v - 1, 0.0) for v in oklab_to_linear(oklch_to_oklab(l, c, h)))


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

    def test_numbers_too_large_to_work_out_are_refused(self):
        with self.assertRaises(PixelRowsError) as caught:
            oklab_to_linear((1e200, 0.0, 0.0))
        self.assertEqual(str(caught.exception), "OKLab (1e+200, 0.0, 0.0) is too large to work out as sRGB")
        with self.assertRaises(PixelRowsError) as caught:
            oklab_to_srgb([0.5, -1e150, 0.0])
        self.assertEqual(str(caught.exception), "OKLab (0.5, -1e+150, 0.0) is too large to work out as sRGB")


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

    def test_a_lightness_a_chroma_or_a_hue_that_is_not_a_finite_number_is_refused(self):
        for index, name in enumerate(("lightness", "chroma", "hue")):
            for bad in NOT_FINITE:
                with self.subTest(argument=name, bad=bad):
                    arguments = [0.5, 0.1, 30]
                    arguments[index] = bad
                    with self.assertRaises(PixelRowsError) as caught:
                        oklch_to_oklab(*arguments)
                    self.assertEqual(str(caught.exception), f"{name} must be a finite number, got {bad!r}")

    def test_any_finite_number_is_taken(self):
        self.assertLab(oklch_to_oklab(1, 0, 0), (1.0, 0.0, 0.0))
        self.assertLab(oklch_to_oklab(-0.5, 0.1, 720), (-0.5, 0.1, 0.0))
        self.assertLab(oklch_to_oklab(1.5, 0.1, -90), (1.5, 0.0, -0.1))
        self.assertEqual(oklch_to_oklab(1e300, 0.0, 1e300)[0], 1e300)


class InGamutTest(unittest.TestCase):
    def test_all_eight_corners_of_the_cube_are_in(self):
        for rgb in CORNERS:
            with self.subTest(rgb=rgb):
                self.assertTrue(in_gamut(*to_oklch(rgb)))

    def test_every_grid_colour_is_in(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                self.assertTrue(in_gamut(*to_oklch(rgb)))

    def chroma_with_excursion(self, l, h, target):
        """The chroma at which the worst linear channel is `target` outside 0..1."""
        low, high = 0.0, 0.4
        for _ in range(50):
            mid = (low + high) / 2
            if excursion(l, mid, h) <= target:
                low = mid
            else:
                high = mid
        return low

    def test_the_tolerance_is_the_smallest_that_holds_the_corners(self):
        worst = max(excursion(*to_oklch(rgb)) for rgb in CORNERS)
        smallest = next(t for t in (1e-6, 1e-5, 1e-4) if worst <= t)
        self.assertEqual(smallest, 1e-6)
        # A channel half that far out is let through, one twice that far out is not.
        for l, h in ((0.6, 30), (0.5, 140), (0.4, 265), (0.85, 100)):
            with self.subTest(l=l, h=h):
                self.assertTrue(in_gamut(l, self.chroma_with_excursion(l, h, smallest / 2), h))
                self.assertFalse(in_gamut(l, self.chroma_with_excursion(l, h, smallest * 2), h))

    def test_too_much_chroma_is_out(self):
        for h in HUES:
            with self.subTest(h=h):
                self.assertFalse(in_gamut(0.5, 0.4, h))

    def test_lighter_than_white_and_darker_than_black_are_out(self):
        self.assertFalse(in_gamut(1.1, 0.0, 0))
        self.assertFalse(in_gamut(-0.1, 0.0, 0))

    def test_greys_are_in(self):
        for l in (0.0, 0.25, 0.5, 0.75, 1.0):
            with self.subTest(l=l):
                self.assertTrue(in_gamut(l, 0.0, 0))

    def test_what_is_not_a_finite_number_is_refused(self):
        for index, name in enumerate(("lightness", "chroma", "hue")):
            for bad in NOT_FINITE:
                with self.subTest(argument=name, bad=bad):
                    arguments = [0.5, 0.1, 30]
                    arguments[index] = bad
                    with self.assertRaises(PixelRowsError) as caught:
                        in_gamut(*arguments)
                    self.assertEqual(str(caught.exception), f"{name} must be a finite number, got {bad!r}")

    def test_numbers_too_large_to_work_out_are_refused(self):
        for l, c in ((0.5, 1e200), (0.5, 1e103), (1e200, 0.0), (-1e200, 0.0)):
            with self.subTest(l=l, c=c):
                with self.assertRaises(PixelRowsError) as caught:
                    in_gamut(l, c, 30)
                self.assertIn("is too large to work out as sRGB", str(caught.exception))

    def test_a_large_number_that_can_be_worked_out_is_only_out(self):
        self.assertFalse(in_gamut(0.5, 1e100, 30))
        self.assertFalse(in_gamut(1e100, 0.0, 30))
        self.assertTrue(in_gamut(0.5, 0.05, 1e300))


class FitChromaTest(unittest.TestCase):
    def test_never_returns_a_chroma_out_of_gamut(self):
        for l, c, h in itertools.product(LIGHTNESSES, CHROMAS, HUES):
            with self.subTest(l=l, c=c, h=h):
                fitted = fit_chroma(l, c, h)
                self.assertTrue(in_gamut(l, fitted, h))
                self.assertTrue(0 <= fitted <= c)

    def test_returns_the_chroma_itself_when_it_is_in_gamut(self):
        for l, c, h in itertools.product(LIGHTNESSES, CHROMAS, HUES):
            if in_gamut(l, c, h):
                with self.subTest(l=l, c=c, h=h):
                    self.assertEqual(fit_chroma(l, c, h), c)

    def test_comes_down_to_the_edge_of_the_gamut(self):
        found = 0
        for l, c, h in itertools.product(LIGHTNESSES, CHROMAS, HUES):
            if in_gamut(l, c, h):
                continue
            found += 1
            with self.subTest(l=l, c=c, h=h):
                fitted = fit_chroma(l, c, h)
                self.assertLess(fitted, c)
                self.assertFalse(in_gamut(l, fitted + 1e-6, h))
        self.assertGreater(found, 0)

    def test_lightness_at_or_below_0_gives_0(self):
        self.assertEqual(fit_chroma(0.0, 0.1, 40), 0.0)
        self.assertEqual(fit_chroma(-0.2, 0.1, 40), 0.0)

    def test_lightness_at_or_above_1_gives_0(self):
        self.assertEqual(fit_chroma(1.0, 0.1, 40), 0.0)
        self.assertEqual(fit_chroma(1.3, 0.1, 40), 0.0)

    def test_no_chroma_asked_gives_0(self):
        self.assertEqual(fit_chroma(0.5, 0.0, 40), 0.0)

    def test_a_colour_keeps_its_own_chroma(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                l, c, h = to_oklch(rgb)
                if 0 < l < 1:
                    self.assertEqual(fit_chroma(l, c, h), c)

    def test_what_cannot_be_worked_out_is_refused(self):
        nan, inf = float("nan"), float("inf")
        refused = ((nan, 0.1, 30), (0.5, nan, 30), (0.5, inf, 30), (0.5, 1e200, 30), (0.5, 0.1, nan), (0.5, 0.1, inf))
        for l, c, h in refused:
            with self.subTest(l=l, c=c, h=h):
                with self.assertRaises(PixelRowsError):
                    fit_chroma(l, c, h)


class OklchToHexTest(unittest.TestCase):
    def test_a_colours_own_oklch_gives_the_colour_back(self):
        for rgb in GRID:
            with self.subTest(rgb=rgb):
                self.assertEqual(oklch_to_hex(*to_oklch(rgb)), to_hex(rgb))

    def test_other_colours_come_back_too(self):
        for colour in ("#262c44", "#394c75", "#4773ab", "#739dc3", "#aac9de", "#1a1a22", "#e8b087", "#010101"):
            with self.subTest(colour=colour):
                self.assertEqual(oklch_to_hex(*to_oklch(colour)), colour)

    def test_chroma_is_fitted_first(self):
        l, c, h = 0.9, 0.30, 30
        self.assertFalse(in_gamut(l, c, h))
        fitted = fit_chroma(l, c, h)
        self.assertEqual(oklch_to_hex(l, c, h), to_hex(oklab_to_srgb(oklch_to_oklab(l, fitted, h))))
        # The fitted colour keeps the lightness and hue that were asked for.
        got_l, _, got_h = to_oklch(oklch_to_hex(l, c, h))
        self.assertAlmostEqual(got_l, l, delta=0.01)
        self.assertAlmostEqual(got_h, h, delta=3)

    def test_the_ends_of_lightness_are_black_and_white(self):
        self.assertEqual(oklch_to_hex(0.0, 0.2, 100), "#000000")
        self.assertEqual(oklch_to_hex(1.0, 0.2, 100), "#ffffff")

    def test_is_lower_case_hex(self):
        text = oklch_to_hex(0.7, 0.1, 50)
        self.assertRegex(text, r"^#[0-9a-f]{6}$")

    def test_what_cannot_be_worked_out_is_refused(self):
        nan, inf = float("nan"), float("inf")
        refused = (
            (nan, 0.1, 30), (inf, 0.1, 30), (-inf, 0.1, 30), (1e200, 0.1, 30), (-1e200, 0.1, 30),
            (0.5, nan, 30), (0.5, inf, 30), (0.5, 1e200, 30),
            (0.5, 0.1, nan), (0.5, 0.1, inf), (0.0, 0.1, nan), (1.0, 0.1, inf),
        )
        for l, c, h in refused:
            with self.subTest(l=l, c=c, h=h):
                with self.assertRaises(PixelRowsError):
                    oklch_to_hex(l, c, h)

    def test_a_hue_of_any_finite_size_is_an_angle(self):
        self.assertEqual(oklch_to_hex(0.6, 0.1, 30 + 360 * 5), oklch_to_hex(0.6, 0.1, 30))
        self.assertRegex(oklch_to_hex(0.6, 0.1, 1e300), r"^#[0-9a-f]{6}$")


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
