import contextlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pixelrows.cli import main
from pixelrows.render import render_sprite
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
DARK = (0x1A, 0x1A, 0x22, 255)
GREEN = (0x58, 0xA8, 0x4C, 255)
CLEAR = (0, 0, 0, 0)

#: Three cells by two. Only its top-left cell is dark, so a flip shows.
HOOK = ["o..", "ogg"]


def hook_set():
    """The hook, and a second one with a green of its own."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("hook", HOOK))
    spriteset.add(Sprite("pale", HOOK, {"g": "#7cc86a"}))
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


class RenderCommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = str(self.folder / "hook.json")
        self.out = str(self.folder / "hook.png")
        hook_set().save(self.path)

    def test_writes_the_sprite_at_scale_8_and_returns_0(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out])
        self.assertEqual((code, err), (0, ""))
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (24, 16))
        spriteset = hook_set()
        expected = render_sprite(spriteset.sprite("hook"), spriteset.palette_for("hook"), 8)
        self.assertEqual(Path(self.out).read_bytes(), expected.to_png())

    def test_prints_the_path_and_the_size_of_the_picture(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out])
        data = json.loads(out)
        self.assertEqual(data, {"wrote": self.out, "width": 24, "height": 16})
        self.assertEqual(list(data), ["wrote", "width", "height"])
        self.assertEqual(out, json.dumps(data, indent=2) + "\n")

    def test_the_path_is_printed_as_it_was_given(self):
        given = f"{self.folder}/hook.png"
        data = json.loads(run_main(["render", self.path, "hook", "--out", given])[1])
        self.assertEqual(data["wrote"], given)
        self.assertEqual(Png(self.out).width, 24)

    def test_every_cell_is_a_block_of_its_colour(self):
        run_main(["render", self.path, "hook", "--out", self.out])
        picture = Png(self.out)
        for x, y in ((0, 0), (7, 7), (0, 8), (7, 15)):
            self.assertEqual(picture.at(x, y), DARK, (x, y))
        for x, y in ((8, 8), (23, 15)):
            self.assertEqual(picture.at(x, y), GREEN, (x, y))

    def test_without_a_background_the_empty_cells_are_transparent(self):
        run_main(["render", self.path, "hook", "--out", self.out])
        picture = Png(self.out)
        for x, y in ((8, 0), (23, 0), (23, 7)):
            self.assertEqual(picture.at(x, y), CLEAR, (x, y))

    def test_background_fills_the_empty_cells(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out, "--background", "#102030"])
        self.assertEqual((code, err), (0, ""))
        picture = Png(self.out)
        for x, y in ((8, 0), (23, 0), (23, 7)):
            self.assertEqual(picture.at(x, y), (0x10, 0x20, 0x30, 255), (x, y))
        self.assertEqual(picture.at(0, 0), DARK)

    def test_scale_sets_the_pixels_to_the_cell(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out, "--scale", "3"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out), {"wrote": self.out, "width": 9, "height": 6})
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (9, 6))
        self.assertEqual(picture.at(2, 2), DARK)
        self.assertEqual(picture.at(3, 2), CLEAR)
        self.assertEqual(picture.at(3, 3), GREEN)

    def test_scale_1_is_one_pixel_to_the_cell(self):
        run_main(["render", self.path, "hook", "--out", self.out, "--scale", "1"])
        picture = Png(self.out)
        self.assertEqual((picture.width, picture.height), (3, 2))
        self.assertEqual([picture.at(x, 0) for x in range(3)], [DARK, CLEAR, CLEAR])
        self.assertEqual([picture.at(x, 1) for x in range(3)], [DARK, GREEN, GREEN])

    def test_flip_turns_the_sprite_left_to_right(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out, "--scale", "1", "--flip"])
        self.assertEqual((code, err), (0, ""))
        picture = Png(self.out)
        self.assertEqual([picture.at(x, 0) for x in range(3)], [CLEAR, CLEAR, DARK])
        self.assertEqual([picture.at(x, 1) for x in range(3)], [GREEN, GREEN, DARK])

    def test_the_sprite_is_read_against_its_own_palette_laid_over_the_set_s(self):
        run_main(["render", self.path, "pale", "--out", self.out, "--scale", "1"])
        picture = Png(self.out)
        self.assertEqual(picture.at(0, 0), DARK)
        self.assertEqual(picture.at(1, 1), (0x7C, 0xC8, 0x6A, 255))

    def test_folders_on_the_way_to_the_picture_are_made(self):
        out = str(self.folder / "art" / "big" / "hook.png")
        code, out_text, err = run_main(["render", self.path, "hook", "--out", out])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(Png(out).width, 24)

    def test_an_unknown_sprite_is_an_error_and_nothing_is_written(self):
        code, out, err = run_main(["render", self.path, "boot", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: no sprite named 'boot'\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_missing_file_is_an_error(self):
        path = str(self.folder / "none.json")
        code, out, err = run_main(["render", path, "hook", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no such file: {path}\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_background_that_is_not_a_colour_is_an_error(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out, "--background", "red"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: not a colour: 'red'"), err)
        self.assertFalse(Path(self.out).exists())

    def test_a_scale_below_1_is_an_error(self):
        code, out, err = run_main(["render", self.path, "hook", "--out", self.out, "--scale", "0"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: scale must be a whole number of 1 or more"), err)
        self.assertFalse(Path(self.out).exists())

    def test_a_sprite_with_a_character_the_palette_lacks_is_an_error(self):
        spriteset = hook_set()
        spriteset.add(Sprite("odd", ["oq"]))
        spriteset.save(self.path)
        code, out, err = run_main(["render", self.path, "odd", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("sprite 'odd'", err)
        self.assertFalse(Path(self.out).exists())

    def test_without_out_it_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["render", self.path, "hook"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--out", err.getvalue())

    def test_a_scale_that_is_not_a_whole_number_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["render", self.path, "hook", "--out", self.out, "--scale", "1.5"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--scale", err.getvalue())
        self.assertFalse(Path(self.out).exists())


if __name__ == "__main__":
    unittest.main()
