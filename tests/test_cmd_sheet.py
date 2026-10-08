import contextlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pixelrows.cli import main
from pixelrows.sheet import contact_sheet
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
DARK = (0x1A, 0x1A, 0x22, 255)
GREEN = (0x58, 0xA8, 0x4C, 255)
PAGE = (0x1E, 0x1E, 0x24, 255)
PLATE = (0x4A, 0x4A, 0x55, 255)
INK = (0xD8, 0xD8, 0xE0, 255)
DIM = (0x8A, 0x8A, 0x96, 255)

#: Three cells by two.
HOOK = ["o..", "ogg"]

#: Four cells by one.
BAR = ["gggg"]


def hook_set():
    """A hook, a second one with a green of its own, and a bar."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("hook", HOOK))
    spriteset.add(Sprite("pale", HOOK, {"g": "#7cc86a"}))
    spriteset.add(Sprite("bar", BAR))
    return spriteset


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


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

    def colours(self):
        """Every distinct pixel of the picture."""
        return {self.at(x, y) for y in range(self.height) for x in range(self.width)}


class SheetCommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = str(self.folder / "hook.json")
        self.out = str(self.folder / "sheet.png")
        hook_set().save(self.path)

    def sheet(self, *extra):
        """Runs the command on the set with `extra` after the file. The run must go well. What it printed, as data."""
        code, out, err = run_main(["sheet", self.path, *extra, "--out", self.out])
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def assert_wrote(self, page):
        """Holds that the file written is `page`, pixel for pixel."""
        self.assertEqual(Path(self.out).read_bytes(), page.to_png())

    def test_writes_every_sprite_at_scale_8_with_labels_and_returns_0(self):
        code, out, err = run_main(["sheet", self.path, "--out", self.out])
        self.assertEqual((code, err), (0, ""))
        page = contact_sheet(hook_set())
        self.assert_wrote(page)
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (page.width, page.height))
        self.assertIn(INK, picture.colours())
        self.assertIn(DIM, picture.colours())

    def test_prints_the_path_the_size_of_the_page_and_the_sprites_on_it(self):
        code, out, err = run_main(["sheet", self.path, "--out", self.out])
        data = json.loads(out)
        page = contact_sheet(hook_set())
        self.assertEqual(data, {
            "wrote": self.out,
            "width": page.width,
            "height": page.height,
            "sprites": ["hook", "pale", "bar"],
        })
        self.assertEqual(list(data), ["wrote", "width", "height", "sprites"])
        self.assertEqual(out, json.dumps(data, indent=2) + "\n")

    def test_the_path_is_printed_as_it_was_given(self):
        given = f"{self.folder}/sheet.png"
        code, out, err = run_main(["sheet", self.path, "--out", given])
        self.assertEqual(json.loads(out)["wrote"], given)
        self.assertTrue(Path(self.out).exists())

    def test_the_page_the_plate_and_the_sprite_are_where_a_sheet_puts_them(self):
        # One row of three cells, each 48 wide (the bar's plate) and 32 high (a hook's plate).
        data = self.sheet("--no-labels")
        self.assertEqual((data["width"], data["height"]), (8 + 48 + 8 + 48 + 8 + 48 + 8, 8 + 32 + 8))
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (176, 48))
        self.assertEqual(picture.at(0, 0), PAGE)
        self.assertEqual(picture.at(8, 8), PLATE)
        self.assertEqual(picture.at(16, 16), DARK)
        self.assertEqual(picture.at(24, 24), GREEN)

    def test_names_choose_the_sprites_and_their_order(self):
        data = self.sheet("pale", "hook")
        self.assertEqual(data["sprites"], ["pale", "hook"])
        self.assert_wrote(contact_sheet(hook_set(), ["pale", "hook"]))

    def test_one_name_is_a_page_of_one_cell(self):
        data = self.sheet("hook", "--no-labels")
        self.assertEqual(data, {"wrote": self.out, "width": 8 + 40 + 8, "height": 8 + 32 + 8, "sprites": ["hook"]})
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (56, 48))

    def test_scale_sets_the_pixels_to_the_cell(self):
        data = self.sheet("hook", "--no-labels", "--scale", "2")
        self.assertEqual((data["width"], data["height"]), (8 + 10 + 8, 8 + 8 + 8))
        self.assert_wrote(contact_sheet(hook_set(), ["hook"], scales=[2], labels=False))
        picture = Png(self.out)
        self.assertEqual(picture.at(8, 8), PLATE)
        self.assertEqual(picture.at(10, 10), DARK)

    def test_a_list_of_scales_draws_each_sprite_once_for_each(self):
        # A plate of 5 by 4, a gap of 4, a plate of 40 by 32.
        data = self.sheet("hook", "--no-labels", "--scale", "1,8")
        self.assertEqual((data["width"], data["height"]), (8 + 5 + 4 + 40 + 8, 8 + 32 + 8))
        self.assert_wrote(contact_sheet(hook_set(), ["hook"], scales=[1, 8], labels=False))
        self.sheet("--scale", "1,8")
        self.assert_wrote(contact_sheet(hook_set(), scales=[1, 8]))

    def test_background_is_the_colour_of_the_plates(self):
        self.sheet("--background", "#102030", "--no-labels")
        picture = Png(self.out)
        self.assertEqual(picture.at(8, 8), (0x10, 0x20, 0x30, 255))
        self.assertEqual(picture.at(0, 0), PAGE)
        self.assertNotIn(PLATE, picture.colours())
        self.sheet("--background", "#102030")
        self.assert_wrote(contact_sheet(hook_set(), background="#102030"))

    def test_columns_sets_how_many_sprites_go_in_a_row(self):
        data = self.sheet("--no-labels", "--columns", "1")
        self.assertEqual((data["width"], data["height"]), (8 + 48 + 8, 8 + 32 + 8 + 32 + 8 + 32 + 8))
        self.assert_wrote(contact_sheet(hook_set(), columns=1, labels=False))
        data = self.sheet("--no-labels", "--columns", "2")
        self.assertEqual((data["width"], data["height"]), (8 + 48 + 8 + 48 + 8, 8 + 32 + 8 + 32 + 8))
        self.sheet("--columns", "2")
        self.assert_wrote(contact_sheet(hook_set(), columns=2))

    def test_no_labels_leaves_the_names_and_sizes_out(self):
        with_labels = self.sheet()
        without = self.sheet("--no-labels")
        self.assertLess(without["height"], with_labels["height"])
        self.assert_wrote(contact_sheet(hook_set(), labels=False))
        colours = Png(self.out).colours()
        self.assertNotIn(INK, colours)
        self.assertNotIn(DIM, colours)

    def test_every_option_together(self):
        data = self.sheet("bar", "pale", "--scale", "2,4", "--background", "#203040", "--columns", "1",
                          "--no-labels")
        self.assertEqual(data["sprites"], ["bar", "pale"])
        self.assert_wrote(contact_sheet(hook_set(), ["bar", "pale"], [2, 4], "#203040", 1, False))

    def test_folders_on_the_way_to_the_page_are_made(self):
        out = str(self.folder / "art" / "sheets" / "all.png")
        code, text, err = run_main(["sheet", self.path, "--out", out])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(Png(out).width, json.loads(text)["width"])

    def test_an_unknown_sprite_is_an_error_and_nothing_is_written(self):
        code, out, err = run_main(["sheet", self.path, "hook", "boot", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: no sprite named 'boot'\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_set_without_sprites_is_an_error(self):
        SpriteSet(PALETTE).save(self.path)
        code, out, err = run_main(["sheet", self.path, "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: nothing to show\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_missing_file_is_an_error(self):
        path = str(self.folder / "none.json")
        code, out, err = run_main(["sheet", path, "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no such file: {path}\n")

    def test_a_background_that_is_not_a_colour_is_an_error(self):
        code, out, err = run_main(["sheet", self.path, "--out", self.out, "--background", "grey"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: not a colour: 'grey'"), err)
        self.assertFalse(Path(self.out).exists())

    def test_columns_below_1_is_an_error(self):
        code, out, err = run_main(["sheet", self.path, "--out", self.out, "--columns", "0"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: columns must be a whole number of 1 or more"), err)
        self.assertFalse(Path(self.out).exists())

    def test_a_scale_that_is_not_a_list_of_whole_numbers_exits_with_2(self):
        for scale in ("0", "1,x", "1.5", "8,"):
            with self.subTest(scale=scale):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as left:
                        main(["sheet", self.path, "--out", self.out, "--scale", scale])
                self.assertEqual(left.exception.code, 2)
                self.assertIn("--scale", err.getvalue())
                self.assertFalse(Path(self.out).exists())

    def test_without_out_it_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["sheet", self.path])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--out", err.getvalue())


if __name__ == "__main__":
    unittest.main()
