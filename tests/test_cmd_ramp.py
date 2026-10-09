import contextlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pixelrows.cli import main
from pixelrows.palette import parse_hex
from pixelrows.ramp import even_lightness, ramp

#: The ramp most tests ask for.
BLUE = ["ramp", "--hue", "255", "--chroma", "0.1"]


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def printed(argv):
    """What a run that went well printed, as data."""
    code, out, err = run_main(argv)
    if (code, err) != (0, ""):
        raise AssertionError(f"main({argv!r}) returned {code} and said {err!r}")
    return json.loads(out)


def as_data(steps):
    """Steps of a ramp as the command prints them."""
    return [step.to_dict() for step in steps]


class Png:
    """A PNG file this package wrote, read back: the size from its IHDR, the pixels from its IDAT."""

    def __init__(self, path):
        data = Path(path).read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise AssertionError(f"{path} does not start as a PNG")
        self.width, self.height = struct.unpack(">II", data[16:24])
        (length,) = struct.unpack(">I", data[33:37])
        if data[37:41] != b"IDAT":
            raise AssertionError(f"{path} has no IDAT after its IHDR")
        self.stride = self.width * 4 + 1
        self.rows = zlib.decompress(data[41:41 + length])

    def at(self, x, y):
        """The pixel at (x, y) as (r, g, b, a)."""
        start = y * self.stride + 1 + x * 4
        return tuple(self.rows[start:start + 4])


class RampStepsTest(unittest.TestCase):
    def test_prints_five_steps_from_dark_to_light_and_returns_0(self):
        code, out, err = run_main(BLUE)
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(list(data), ["steps"])
        self.assertEqual(data["steps"], as_data(ramp(255, 0.1, even_lightness(5))))
        self.assertEqual(len(data["steps"]), 5)
        self.assertEqual(out, json.dumps(data, indent=2) + "\n")

    def test_the_default_ends_are_those_of_even_lightness(self):
        steps = printed(BLUE)["steps"]
        self.assertEqual([step["lightness"] for step in steps], even_lightness(5))
        self.assertEqual(steps[0]["lightness"], 0.30)
        self.assertEqual(steps[-1]["lightness"], 0.82)

    def test_a_step_is_printed_with_every_key_of_a_step(self):
        step = printed(BLUE)["steps"][2]
        self.assertEqual(list(step), ["lightness", "chroma", "hue", "hex", "asked_chroma", "clipped"])
        self.assertEqual(step["hue"], 255)
        self.assertEqual(step["asked_chroma"], 0.1)
        self.assertIs(step["clipped"], False)
        self.assertEqual(parse_hex(step["hex"]), parse_hex(ramp(255, 0.1)[2].hex))

    def test_steps_sets_how_many_there_are(self):
        for count in (1, 2, 3, 8):
            with self.subTest(steps=count):
                steps = printed(BLUE + ["--steps", str(count)])["steps"]
                self.assertEqual(steps, as_data(ramp(255, 0.1, even_lightness(count))))
                self.assertEqual(len(steps), count)

    def test_darkest_and_lightest_set_the_two_ends(self):
        steps = printed(BLUE + ["--darkest", "0.2", "--lightest", "0.9", "--steps", "3"])["steps"]
        self.assertEqual([step["lightness"] for step in steps], even_lightness(3, 0.2, 0.9))
        self.assertEqual(steps[0]["lightness"], 0.2)
        self.assertEqual(steps[-1]["lightness"], 0.9)

    def test_hue_shift_turns_the_hue_from_step_to_step(self):
        steps = printed(BLUE + ["--hue-shift", "9"])["steps"]
        self.assertEqual([step["hue"] for step in steps], [273, 264, 255, 246, 237])

    def test_a_hue_shift_below_0_turns_it_the_other_way(self):
        steps = printed(BLUE + ["--hue-shift", "-9"])["steps"]
        self.assertEqual([step["hue"] for step in steps], [237, 246, 255, 264, 273])

    def test_taper_takes_chroma_from_the_two_ends(self):
        steps = printed(BLUE + ["--taper", "0.55"])["steps"]
        for step, asked in zip(steps, (0.045, 0.0725, 0.10, 0.0725, 0.045)):
            self.assertAlmostEqual(step["asked_chroma"], asked, places=12)

    def test_every_option_is_handed_to_the_ramp(self):
        argv = ["ramp", "--hue", "30", "--chroma", "0.12", "--steps", "4", "--darkest", "0.25",
                "--lightest", "0.9", "--hue-shift", "6.5", "--taper", "0.3"]
        expected = ramp(30, 0.12, even_lightness(4, 0.25, 0.9), hue_shift=6.5, taper=0.3)
        self.assertEqual(printed(argv), {"steps": as_data(expected)})

    def test_a_step_with_more_chroma_than_srgb_has_is_printed_as_clipped(self):
        argv = ["ramp", "--hue", "30", "--chroma", "0.30", "--steps", "1", "--darkest", "0.9", "--lightest", "0.9"]
        (step,) = printed(argv)["steps"]
        self.assertIs(step["clipped"], True)
        self.assertEqual(step["asked_chroma"], 0.30)
        self.assertLess(step["chroma"], 0.30)


class RampPaletteTest(unittest.TestCase):
    def test_without_chars_there_is_no_palette(self):
        self.assertNotIn("palette", printed(BLUE))

    def test_chars_adds_a_palette_of_one_character_a_step(self):
        data = printed(BLUE + ["--chars", "12345"])
        self.assertEqual(list(data), ["steps", "palette"])
        self.assertEqual(data["steps"], as_data(ramp(255, 0.1, even_lightness(5))))
        self.assertEqual(list(data["palette"].items()), [
            (ch, step["hex"]) for ch, step in zip("12345", data["steps"])
        ])

    def test_chars_follow_the_count_of_steps(self):
        data = printed(BLUE + ["--steps", "2", "--chars", "dl"])
        self.assertEqual(data["palette"], {"d": data["steps"][0]["hex"], "l": data["steps"][1]["hex"]})

    def test_a_count_of_chars_that_differs_from_the_steps_is_an_error(self):
        for chars in ("", "abc", "abcdef"):
            with self.subTest(chars=chars):
                code, out, err = run_main(BLUE + ["--chars", chars])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertEqual(
                    err, f"error: --chars has {len(chars)} characters for 5 steps, it takes one a step\n"
                )

    def test_a_character_given_twice_is_an_error(self):
        code, out, err = run_main(BLUE + ["--chars", "abcda"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: --chars has a character twice in 'abcda'"), err)

    def test_a_character_no_palette_can_hold_is_an_error(self):
        for chars in ("ab.de", "ab de"):
            with self.subTest(chars=chars):
                code, out, err = run_main(BLUE + ["--chars", chars])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("error: "), err)


class RampSwatchTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.out = str(self.folder / "blue.png")

    def test_without_out_nothing_is_written(self):
        printed(BLUE)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_out_writes_one_32_by_32_square_a_step(self):
        data = printed(BLUE + ["--out", self.out])
        swatch = Png(self.out)
        self.assertEqual((swatch.width, swatch.height), (160, 32))
        for index, step in enumerate(data["steps"]):
            colour = (*parse_hex(step["hex"]), 255)
            left = index * 32
            for x, y in ((left, 0), (left + 31, 0), (left + 16, 16), (left, 31), (left + 31, 31)):
                self.assertEqual(swatch.at(x, y), colour, (index, x, y))

    def test_the_squares_run_dark_to_light_from_the_left(self):
        printed(BLUE + ["--out", self.out])
        swatch = Png(self.out)
        sums = [sum(swatch.at(index * 32 + 16, 16)[:3]) for index in range(5)]
        self.assertEqual(sums, sorted(sums))
        self.assertEqual(len(set(sums)), 5)

    def test_the_swatch_is_as_wide_as_its_steps(self):
        for count in (1, 3, 7):
            with self.subTest(steps=count):
                printed(BLUE + ["--steps", str(count), "--out", self.out])
                swatch = Png(self.out)
                self.assertEqual((swatch.width, swatch.height), (32 * count, 32))

    def test_out_leaves_what_is_printed_as_it_is(self):
        self.assertEqual(printed(BLUE + ["--out", self.out]), printed(BLUE))
        with_chars = BLUE + ["--chars", "abcde"]
        self.assertEqual(printed(with_chars + ["--out", self.out]), printed(with_chars))

    def test_folders_on_the_way_to_the_swatch_are_made(self):
        out = str(self.folder / "art" / "ramps" / "blue.png")
        printed(BLUE + ["--out", out])
        self.assertEqual(Png(out).width, 160)

    def test_no_swatch_is_written_when_the_chars_are_wrong(self):
        code, out, err = run_main(BLUE + ["--chars", "abc", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertFalse(Path(self.out).exists())


class RampErrorsTest(unittest.TestCase):
    def test_what_the_ramp_refuses_is_an_error(self):
        cases = {
            "steps": ["--steps", "0"],
            "taper": ["--taper", "2"],
            "lightness": ["--lightest", "1.5"],
        }
        for word, extra in cases.items():
            with self.subTest(extra=extra):
                code, out, err = run_main(BLUE + extra)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("error: "), err)
                self.assertIn(word, err)

    def test_a_chroma_below_0_is_an_error(self):
        code, out, err = run_main(["ramp", "--hue", "255", "--chroma", "-0.1"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: ramp: chroma is -0.1, it cannot be negative\n")

    def test_without_a_hue_or_a_chroma_it_exits_with_2(self):
        for argv, missing in ((["ramp", "--chroma", "0.1"], "--hue"), (["ramp", "--hue", "255"], "--chroma")):
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as left:
                        main(argv)
                self.assertEqual(left.exception.code, 2)
                self.assertIn(missing, err.getvalue())

    def test_a_hue_that_is_not_a_number_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["ramp", "--hue", "blue", "--chroma", "0.1"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--hue", err.getvalue())


if __name__ == "__main__":
    unittest.main()
