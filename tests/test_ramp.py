import dataclasses
import math
import unittest

from pixelrows.colour import in_gamut, oklch_to_hex, to_oklch
from pixelrows.errors import PixelRowsError
from pixelrows.palette import parse_hex
from pixelrows.ramp import Step, even_lightness, ramp


class EvenLightnessTest(unittest.TestCase):
    def test_default_ends(self):
        values = even_lightness(5)
        self.assertEqual(len(values), 5)
        self.assertEqual(values[0], 0.30)
        self.assertEqual(values[-1], 0.82)

    def test_given_ends(self):
        for steps in (2, 3, 4, 7, 10):
            with self.subTest(steps=steps):
                values = even_lightness(steps, 0.2, 0.9)
                self.assertEqual(len(values), steps)
                self.assertEqual(values[0], 0.2)
                self.assertEqual(values[-1], 0.9)

    def test_spacing_is_even(self):
        for got, want in zip(even_lightness(5), (0.30, 0.43, 0.56, 0.69, 0.82)):
            self.assertAlmostEqual(got, want, places=12)
        values = even_lightness(8, 0.1, 0.95)
        gaps = [b - a for a, b in zip(values, values[1:])]
        for gap in gaps:
            self.assertAlmostEqual(gap, (0.95 - 0.1) / 7, places=12)

    def test_two_steps_are_the_two_ends(self):
        self.assertEqual(even_lightness(2), [0.30, 0.82])

    def test_one_step_is_the_midpoint(self):
        self.assertEqual(len(even_lightness(1)), 1)
        self.assertAlmostEqual(even_lightness(1)[0], 0.56, places=12)
        self.assertAlmostEqual(even_lightness(1, 0.2, 0.9)[0], 0.55, places=12)

    def test_steps_below_1_is_an_error(self):
        for bad in (0, -1, -5):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    even_lightness(bad)
                self.assertIn("steps", str(caught.exception))

    def test_steps_must_be_a_whole_number(self):
        for bad in (2.5, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    even_lightness(bad)


class StepTest(unittest.TestCase):
    def setUp(self):
        self.step = Step(lightness=0.55, chroma=0.1, hue=255.0, hex="#4773ab", asked_chroma=0.1, clipped=False)

    def test_to_dict_keys(self):
        self.assertEqual(
            list(self.step.to_dict()),
            ["lightness", "chroma", "hue", "hex", "asked_chroma", "clipped"],
        )

    def test_to_dict_values(self):
        self.assertEqual(self.step.to_dict(), {
            "lightness": 0.55,
            "chroma": 0.1,
            "hue": 255.0,
            "hex": "#4773ab",
            "asked_chroma": 0.1,
            "clipped": False,
        })

    def test_cannot_be_changed(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.step.chroma = 0.2

    def test_to_dict_rounds_lightness_and_both_chromas_to_4_places(self):
        step = Step(
            lightness=0.42999999999999994,
            chroma=0.07887072372436524,
            hue=39.75,
            hex="#6b3a21",
            asked_chroma=0.08399999999999999,
            clipped=True,
        )
        self.assertEqual(step.to_dict(), {
            "lightness": 0.43,
            "chroma": 0.0789,
            "hue": 39.75,
            "hex": "#6b3a21",
            "asked_chroma": 0.084,
            "clipped": True,
        })

    def test_to_dict_rounds_the_hue_to_2_places(self):
        rounded = ((264.00000000000006, 264.0), (33.333333333333336, 33.33), (12.345678, 12.35), (0.004, 0.0))
        for hue, printed in rounded:
            with self.subTest(hue=hue):
                step = dataclasses.replace(self.step, hue=hue)
                self.assertEqual(step.to_dict()["hue"], printed)

    def test_to_dict_keeps_a_hue_that_rounds_up_to_360_below_360(self):
        step = dataclasses.replace(self.step, hue=359.999)
        self.assertEqual(step.to_dict()["hue"], 0.0)
        self.assertEqual(dataclasses.replace(self.step, hue=359.99).to_dict()["hue"], 359.99)

    def test_to_dict_leaves_the_fields_exact(self):
        step = Step(
            lightness=0.42999999999999994,
            chroma=0.07887072372436524,
            hue=264.00000000000006,
            hex="#394c75",
            asked_chroma=0.08399999999999999,
            clipped=True,
        )
        step.to_dict()
        self.assertEqual(step.lightness, 0.42999999999999994)
        self.assertEqual(step.chroma, 0.07887072372436524)
        self.assertEqual(step.hue, 264.00000000000006)
        self.assertEqual(step.asked_chroma, 0.08399999999999999)

    def test_to_dict_of_a_ramp_has_no_number_longer_than_its_places(self):
        for step in ramp(30, 0.12, even_lightness(4, 0.25, 0.9), hue_shift=6.4, taper=0.3):
            data = step.to_dict()
            for key, places in (("lightness", 4), ("chroma", 4), ("asked_chroma", 4), ("hue", 2)):
                with self.subTest(key=key, value=data[key]):
                    self.assertEqual(data[key], round(getattr(step, key), places))
                    self.assertLessEqual(len(repr(data[key]).partition(".")[2]), places)


class WorkedRampTest(unittest.TestCase):
    LIGHTNESS = [0.30, 0.42, 0.55, 0.68, 0.82]

    def setUp(self):
        self.steps = ramp(255, 0.10, self.LIGHTNESS, hue_shift=9, taper=0.55)

    def test_one_step_a_lightness_in_order(self):
        self.assertEqual([step.lightness for step in self.steps], self.LIGHTNESS)

    def test_hues(self):
        for step, want in zip(self.steps, (273, 264, 255, 246, 237)):
            self.assertAlmostEqual(step.hue, want, places=9)

    def test_asked_chromas(self):
        for step, want in zip(self.steps, (0.045, 0.0725, 0.10, 0.0725, 0.045)):
            self.assertAlmostEqual(step.asked_chroma, want, places=12)

    def test_nothing_is_clipped(self):
        for step in self.steps:
            self.assertFalse(step.clipped)
            self.assertEqual(step.chroma, step.asked_chroma)

    def test_hex_values(self):
        listed = ("#262c44", "#394c75", "#4773ab", "#739dc3", "#aac9de")
        for step, want in zip(self.steps, listed):
            with self.subTest(want=want):
                for got_channel, want_channel in zip(parse_hex(step.hex), parse_hex(want)):
                    self.assertLessEqual(abs(got_channel - want_channel), 1)

    def test_each_hex_is_its_step_in_oklch(self):
        for step in self.steps:
            self.assertEqual(step.hex, oklch_to_hex(step.lightness, step.chroma, step.hue))

    def test_goes_from_dark_to_light(self):
        measured = [to_oklch(step.hex)[0] for step in self.steps]
        self.assertEqual(measured, sorted(measured))
        for got, want in zip(measured, self.LIGHTNESS):
            self.assertAlmostEqual(got, want, delta=0.01)


class RampTest(unittest.TestCase):
    def test_lightness_defaults_to_five_even_steps(self):
        steps = ramp(140, 0.08)
        self.assertEqual([step.lightness for step in steps], even_lightness(5))

    def test_steps_come_back_in_the_order_of_lightness(self):
        steps = ramp(140, 0.05, [0.8, 0.3, 0.5])
        self.assertEqual([step.lightness for step in steps], [0.8, 0.3, 0.5])

    def test_no_shift_and_no_taper_keeps_hue_and_chroma(self):
        for step in ramp(140, 0.05, [0.4, 0.5, 0.6, 0.7]):
            self.assertEqual(step.hue, 140)
            self.assertEqual(step.asked_chroma, 0.05)

    def test_hue_shift_turns_dark_and_light_steps_opposite_ways(self):
        steps = ramp(100, 0.05, [0.4, 0.5, 0.6, 0.7], hue_shift=10)
        for step, want in zip(steps, (115, 105, 95, 85)):
            self.assertAlmostEqual(step.hue, want, places=9)

    def test_hue_below_0_wraps(self):
        steps = ramp(5, 0.05, [0.3, 0.5, 0.7], hue_shift=10)
        for step, want in zip(steps, (15, 5, 355)):
            self.assertAlmostEqual(step.hue, want, places=9)

    def test_hue_above_360_wraps(self):
        steps = ramp(355, 0.05, [0.3, 0.5, 0.7], hue_shift=10)
        for step, want in zip(steps, (5, 355, 345)):
            self.assertAlmostEqual(step.hue, want, places=9)

    def test_hue_is_always_from_0_up_to_360(self):
        for hue in (-725, -360, -1e-20, 0, 359.999, 360, 725):
            for shift in (-200, -45, 0, 45, 200):
                with self.subTest(hue=hue, shift=shift):
                    for step in ramp(hue, 0.02, [0.3, 0.4, 0.5, 0.6, 0.7], hue_shift=shift):
                        self.assertTrue(0 <= step.hue < 360)

    def test_a_wrapped_hue_gives_the_same_colour(self):
        self.assertEqual(
            [step.hex for step in ramp(5, 0.05, [0.3, 0.5, 0.7], hue_shift=10)],
            [step.hex for step in ramp(365, 0.05, [0.3, 0.5, 0.7], hue_shift=10)],
        )

    def test_taper_is_the_share_of_chroma_lost_at_the_ends(self):
        steps = ramp(255, 0.08, [0.3, 0.45, 0.6, 0.75, 0.9], taper=0.5)
        for step, want in zip(steps, (0.04, 0.06, 0.08, 0.06, 0.04)):
            self.assertAlmostEqual(step.asked_chroma, want, places=12)

    def test_full_taper_leaves_the_ends_grey(self):
        steps = ramp(255, 0.08, [0.3, 0.6, 0.9], taper=1)
        self.assertAlmostEqual(steps[0].asked_chroma, 0.0, places=12)
        self.assertAlmostEqual(steps[1].asked_chroma, 0.08, places=12)
        self.assertAlmostEqual(steps[2].asked_chroma, 0.0, places=12)
        first = parse_hex(steps[0].hex)
        self.assertEqual(first[0], first[1])
        self.assertEqual(first[1], first[2])

    def test_an_even_count_has_no_step_at_full_chroma(self):
        steps = ramp(255, 0.09, [0.3, 0.5, 0.7, 0.9], taper=0.6)
        for step, want in zip(steps, (0.036, 0.072, 0.072, 0.036)):
            self.assertAlmostEqual(step.asked_chroma, want, places=12)

    def test_one_step(self):
        steps = ramp(200, 0.08, [0.5], hue_shift=30, taper=1.0)
        self.assertEqual(len(steps), 1)
        step = steps[0]
        self.assertEqual(step.lightness, 0.5)
        self.assertEqual(step.hue, 200)
        self.assertEqual(step.asked_chroma, 0.08)
        self.assertEqual(step.chroma, 0.08)
        self.assertFalse(step.clipped)
        self.assertEqual(step.hex, oklch_to_hex(0.5, 0.08, 200))

    def test_more_chroma_than_srgb_has_comes_back_clipped_and_in_gamut(self):
        steps = ramp(30, 0.30, [0.9])
        self.assertEqual(len(steps), 1)
        step = steps[0]
        self.assertTrue(step.clipped)
        self.assertEqual(step.asked_chroma, 0.30)
        self.assertLess(step.chroma, 0.30)
        self.assertGreater(step.chroma, 0.0)
        self.assertFalse(in_gamut(0.9, 0.30, 30))
        self.assertTrue(in_gamut(step.lightness, step.chroma, step.hue))
        self.assertEqual(step.hex, oklch_to_hex(0.9, 0.30, 30))

    def test_only_the_steps_that_need_it_are_clipped(self):
        steps = ramp(30, 0.12, [0.2, 0.6, 0.97])
        self.assertEqual([step.clipped for step in steps], [True, False, True])
        for step in steps:
            self.assertTrue(in_gamut(step.lightness, step.chroma, step.hue))
            self.assertEqual(step.clipped, step.chroma < step.asked_chroma)

    def test_lightness_0_and_1_are_black_and_white(self):
        steps = ramp(120, 0.1, [0, 1])
        self.assertEqual([step.hex for step in steps], ["#000000", "#ffffff"])
        self.assertEqual([step.chroma for step in steps], [0.0, 0.0])
        self.assertEqual([step.clipped for step in steps], [True, True])

    def test_no_chroma_is_a_grey_ramp(self):
        for step in ramp(77, 0, [0.2, 0.5, 0.8]):
            r, g, b = parse_hex(step.hex)
            self.assertEqual(r, g)
            self.assertEqual(g, b)
            self.assertFalse(step.clipped)


class RampErrorTest(unittest.TestCase):
    def test_no_lightness_values(self):
        for empty in ([], ()):
            with self.subTest(empty=empty):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(255, 0.1, empty)
                self.assertIn("no lightness", str(caught.exception))

    def test_a_lightness_outside_0_1(self):
        for bad, where in (([0.3, 1.2, 0.8], "lightness 1"), ([-0.1, 0.5], "lightness 0"), ([0.2, 0.5, 1.0001], "lightness 2")):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(255, 0.1, bad)
                self.assertIn(where, str(caught.exception))

    def test_a_negative_chroma(self):
        with self.assertRaises(PixelRowsError) as caught:
            ramp(255, -0.01)
        self.assertIn("chroma", str(caught.exception))

    def test_a_taper_outside_0_1(self):
        for bad in (-0.1, 1.1):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(255, 0.1, taper=bad)
                self.assertIn("taper", str(caught.exception))

    def test_the_ends_of_each_range_are_allowed(self):
        self.assertEqual(len(ramp(255, 0, [0, 1], taper=0)), 2)
        self.assertEqual(len(ramp(255, 0.1, [0.0, 1.0], taper=1)), 2)

    def test_a_chroma_above_1(self):
        for bad in (1.0001, 2, 1e200):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(30, bad)
                self.assertEqual(str(caught.exception), f"ramp: chroma is {bad!r}, it cannot be above 1")

    def test_a_chroma_of_1_is_allowed_and_comes_back_clipped(self):
        (step,) = ramp(30, 1, [0.5])
        self.assertEqual(step.asked_chroma, 1.0)
        self.assertTrue(step.clipped)
        self.assertTrue(in_gamut(step.lightness, step.chroma, step.hue))

    def test_a_hue_a_chroma_a_hue_shift_or_a_taper_that_is_not_a_finite_number(self):
        refused = (float("nan"), float("inf"), float("-inf"), 10 ** 400, "0.1", None, True, False, [0.1])
        for name in ("hue", "chroma", "hue_shift", "taper"):
            for bad in refused:
                with self.subTest(argument=name, bad=bad):
                    arguments = {"hue": 255, "chroma": 0.1, "hue_shift": 0.0, "taper": 0.0, name: bad}
                    with self.assertRaises(PixelRowsError) as caught:
                        ramp(**arguments)
                    self.assertEqual(str(caught.exception), f"ramp: {name} is {bad!r}, not a finite number")

    def test_a_lightness_value_that_is_not_a_finite_number(self):
        for bad in (float("nan"), float("inf"), float("-inf"), 10 ** 400, "0.5", None, True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(255, 0.1, [0.3, bad, 0.8])
                self.assertEqual(str(caught.exception), f"ramp: lightness 1 is {bad!r}, not a finite number")

    def test_a_lightness_that_is_not_a_list_or_a_tuple(self):
        for bad in (0.5, 1, "0.5", {0.5}, {0.3: 0.8}, range(1), iter([0.3, 0.8])):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError) as caught:
                    ramp(255, 0.1, bad)
                self.assertEqual(str(caught.exception), f"ramp: lightness is {bad!r}, not a list or a tuple")

    def test_a_lightness_may_be_a_list_or_a_tuple(self):
        self.assertEqual(ramp(255, 0.1, (0.3, 0.55, 0.8)), ramp(255, 0.1, [0.3, 0.55, 0.8]))

    def test_whole_numbers_are_taken_as_numbers(self):
        steps = ramp(255, 0, [0, 1], hue_shift=9, taper=1)
        self.assertEqual([step.hex for step in steps], ["#000000", "#ffffff"])
        self.assertEqual([step.lightness for step in steps], [0.0, 1.0])

    def test_a_hue_of_any_finite_size_is_wrapped(self):
        for hue in (-1e300, -725, 725, 1e300, 10 ** 300):
            with self.subTest(hue=hue):
                for step in ramp(hue, 0.05, [0.3, 0.5, 0.7], hue_shift=1e6):
                    self.assertTrue(0 <= step.hue < 360)

    def test_a_hue_and_a_hue_shift_too_large_to_work_out(self):
        with self.assertRaises(PixelRowsError) as caught:
            ramp(1e308, 0.1, hue_shift=1e308)
        self.assertEqual(
            str(caught.exception), "ramp: hue 1e+308 turned by hue_shift 1e+308 is too large to work out"
        )

    def test_arguments_are_refused_with_a_value_error_and_no_other(self):
        calls = (
            lambda: ramp(float("nan"), 0.1),
            lambda: ramp(30, 1e200),
            lambda: ramp(255, 0.1, 0.5),
            lambda: ramp(255, 0.1, ["0.5"]),
            lambda: ramp(255, 0.1, taper="1"),
        )
        for index, call in enumerate(calls):
            with self.subTest(call=index):
                with self.assertRaises(ValueError) as caught:
                    call()
                self.assertIsInstance(caught.exception, PixelRowsError)

    def test_no_step_has_a_number_that_is_not_finite(self):
        for hue, shift in ((-1e300, 1e300), (1e300, 0), (0, -1e306), (359.999, 1e-300)):
            for step in ramp(hue, 1, [0, 0.001, 0.5, 0.999, 1], hue_shift=shift, taper=1):
                with self.subTest(hue=hue, shift=shift, lightness=step.lightness):
                    for value in (step.lightness, step.chroma, step.hue, step.asked_chroma):
                        self.assertTrue(math.isfinite(value))


if __name__ == "__main__":
    unittest.main()
