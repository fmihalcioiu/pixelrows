import contextlib
import io
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pixelrows.anim import gif_bytes
from pixelrows.cli import main
from pixelrows.sheet import anim_strip
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
DARK = (0x1A, 0x1A, 0x22, 255)
PAGE = (0x1E, 0x1E, 0x24, 255)
PLATE = (0x4A, 0x4A, 0x55, 255)
INK = (0xD8, 0xD8, 0xE0, 255)
DIM = (0x8A, 0x8A, 0x96, 255)

#: Six cells by four.
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]


def blob_set():
    """Two frames of a blob, and three clips that play them: of two frames, of three and of one."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1, {"g": "#7cc86a"}))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    spriteset.add_anim("blink", ["blob_0", "blob_1", "blob_0"], 7.5)
    spriteset.add_anim("still", ["blob_0"], 1)
    return spriteset


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def gif_start(path):
    """The start of a GIF file: its width, its height, and whether its first frame has a transparent colour."""
    data = Path(path).read_bytes()
    if data[:6] != b"GIF89a":
        raise AssertionError(f"{path} does not start as a GIF")
    width, height, packed = struct.unpack("<HHB", data[6:11])
    at = 13 + 3 * 2 ** ((packed & 7) + 1)
    if data[at:at + 3] == b"\x21\xff\x0b":
        at += 19
    if data[at:at + 3] != b"\x21\xf9\x04":
        raise AssertionError(f"{path} has no graphic control extension before its first frame")
    return width, height, bool(data[at + 3] & 1)


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


class AnimCommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = str(self.folder / "blob.json")
        self.out = str(self.folder / "clips")
        self.gif = Path(self.out, "blob_idle.gif")
        self.strip = Path(self.out, "blob_idle_strip.png")
        blob_set().save(self.path)

    def anim(self, name, *extra):
        """Runs the command on that anim with `extra` after it. The run must go well. What it printed, as data."""
        code, out, err = run_main(["anim", self.path, name, "--out", self.out, *extra])
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def test_writes_the_gif_and_the_strip_into_the_folder_and_returns_0(self):
        code, out, err = run_main(["anim", self.path, "blob_idle", "--out", self.out])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(sorted(path.name for path in Path(self.out).iterdir()),
                         ["blob_idle.gif", "blob_idle_strip.png"])

    def test_prints_the_two_paths_and_the_timing_of_the_clip(self):
        code, out, err = run_main(["anim", self.path, "blob_idle", "--out", self.out])
        data = json.loads(out)
        self.assertEqual(data, {
            "gif": os.path.join(self.out, "blob_idle.gif"),
            "strip": os.path.join(self.out, "blob_idle_strip.png"),
            "frames": ["blob_0", "blob_1"],
            "fps": 3,
            "seconds": 0.6667,
        })
        self.assertEqual(list(data), ["gif", "strip", "frames", "fps", "seconds"])
        self.assertEqual(out, json.dumps(data, indent=2) + "\n")

    def test_the_paths_start_with_the_folder_as_it_was_given(self):
        given = f"{self.folder}/clips"
        code, out, err = run_main(["anim", self.path, "blob_idle", "--out", given])
        data = json.loads(out)
        self.assertEqual(data["gif"], os.path.join(given, "blob_idle.gif"))
        self.assertEqual(data["strip"], os.path.join(given, "blob_idle_strip.png"))
        self.assertTrue(data["gif"].startswith(given))
        self.assertTrue(Path(data["gif"]).exists())
        self.assertTrue(Path(data["strip"]).exists())

    def test_the_timing_is_that_of_the_clip(self):
        data = self.anim("blink")
        self.assertEqual(data["frames"], ["blob_0", "blob_1", "blob_0"])
        self.assertEqual(data["fps"], 7.5)
        self.assertEqual(data["seconds"], 0.4)
        self.assertEqual(data["gif"], os.path.join(self.out, "blink.gif"))
        self.assertEqual(data["strip"], os.path.join(self.out, "blink_strip.png"))

    def test_the_gif_is_at_scale_8_and_transparent(self):
        self.anim("blob_idle")
        self.assertEqual(gif_start(self.gif), (48, 32, True))
        self.assertEqual(self.gif.read_bytes(), gif_bytes(blob_set(), "blob_idle", 8))

    def test_the_strip_is_at_scale_8_on_plates_with_labels(self):
        self.anim("blob_idle")
        page = anim_strip(blob_set(), "blob_idle")
        self.assertEqual(self.strip.read_bytes(), page.to_png())
        picture = Png(self.strip)
        self.assertEqual((picture.width, picture.height), (page.width, page.height))
        self.assertTrue({PAGE, PLATE, INK, DIM} <= picture.colours())

    def test_the_strip_has_one_plate_a_frame_with_the_frame_on_it(self):
        # Two plates of 64 by 48, 8 apart, inside a margin of 8.
        self.anim("blob_idle", "--no-labels")
        picture = Png(self.strip)
        self.assertEqual((picture.width, picture.height), (8 + 64 + 8 + 64 + 8, 8 + 48 + 8))
        self.assertEqual(picture.at(0, 0), PAGE)
        self.assertEqual(picture.at(8, 8), PLATE)
        self.assertEqual(picture.at(8 + 8 + 2 * 8, 8 + 8), DARK)
        self.assertEqual(picture.at(72, 8), PAGE)
        self.assertEqual(picture.at(80, 8), PLATE)
        self.assertEqual(picture.at(80 + 8 + 2 * 8, 8 + 8), PLATE)
        self.assertEqual(picture.at(80 + 8 + 8, 8 + 8 + 8), DARK)

    def test_scale_sets_the_pixels_to_the_cell_in_both(self):
        self.anim("blob_idle", "--scale", "2")
        self.assertEqual(gif_start(self.gif), (12, 8, True))
        self.assertEqual(self.gif.read_bytes(), gif_bytes(blob_set(), "blob_idle", 2))
        self.assertEqual(self.strip.read_bytes(), anim_strip(blob_set(), "blob_idle", 2).to_png())
        self.anim("blob_idle", "--scale", "2", "--no-labels")
        picture = Png(self.strip)
        self.assertEqual((picture.width, picture.height), (8 + 16 + 8 + 16 + 8, 8 + 12 + 8))

    def test_background_goes_behind_the_gif_and_on_the_plates_of_the_strip(self):
        self.anim("blob_idle", "--background", "#102030")
        self.assertEqual(gif_start(self.gif), (48, 32, False))
        self.assertEqual(self.gif.read_bytes(), gif_bytes(blob_set(), "blob_idle", 8, "#102030"))
        self.assertEqual(self.strip.read_bytes(), anim_strip(blob_set(), "blob_idle", 8, "#102030").to_png())
        self.anim("blob_idle", "--background", "#102030", "--no-labels")
        picture = Png(self.strip)
        self.assertEqual(picture.at(8, 8), (0x10, 0x20, 0x30, 255))
        self.assertEqual(picture.at(0, 0), PAGE)
        self.assertNotIn(PLATE, picture.colours())

    def test_no_labels_takes_the_text_off_the_strip_and_leaves_the_gif_as_it_is(self):
        self.anim("blob_idle", "--no-labels")
        self.assertEqual(self.strip.read_bytes(), anim_strip(blob_set(), "blob_idle", labels=False).to_png())
        colours = Png(self.strip).colours()
        self.assertNotIn(INK, colours)
        self.assertNotIn(DIM, colours)
        self.assertEqual(self.gif.read_bytes(), gif_bytes(blob_set(), "blob_idle", 8))

    def test_every_option_together(self):
        self.anim("blink", "--scale", "3", "--background", "#203040", "--no-labels")
        gif = Path(self.out, "blink.gif")
        strip = Path(self.out, "blink_strip.png")
        self.assertEqual(gif_start(gif), (18, 12, False))
        self.assertEqual(gif.read_bytes(), gif_bytes(blob_set(), "blink", 3, "#203040"))
        self.assertEqual(strip.read_bytes(), anim_strip(blob_set(), "blink", 3, "#203040", False).to_png())

    def test_a_clip_of_one_frame_is_written_too(self):
        data = self.anim("still", "--no-labels")
        self.assertEqual((data["frames"], data["fps"], data["seconds"]), (["blob_0"], 1, 1.0))
        self.assertEqual(gif_start(Path(self.out, "still.gif")), (48, 32, True))
        picture = Png(Path(self.out, "still_strip.png"))
        self.assertEqual((picture.width, picture.height), (8 + 64 + 8, 8 + 48 + 8))

    def test_folders_on_the_way_are_made(self):
        out = str(self.folder / "art" / "clips" / "blob")
        code, text, err = run_main(["anim", self.path, "blob_idle", "--out", out])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(gif_start(Path(out, "blob_idle.gif"))[:2], (48, 32))
        self.assertTrue(Path(out, "blob_idle_strip.png").exists())

    def test_an_unknown_anim_is_an_error_and_nothing_is_written(self):
        for name in ("run", "blob_0"):
            with self.subTest(name=name):
                code, out, err = run_main(["anim", self.path, name, "--out", self.out])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertEqual(err, f"error: no anim named {name!r}\n")
                self.assertFalse(Path(self.out).exists())

    def test_a_clip_that_cannot_play_is_an_error_and_nothing_is_written(self):
        spriteset = blob_set()
        spriteset.add_anim("walk", ["blob_0", "blob_9"], 8)
        spriteset.save(self.path)
        code, out, err = run_main(["anim", self.path, "walk", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: anim 'walk' names 'blob_9', which is not a sprite\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_missing_file_is_an_error(self):
        path = str(self.folder / "none.json")
        code, out, err = run_main(["anim", path, "blob_idle", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no such file: {path}\n")
        self.assertFalse(Path(self.out).exists())

    def test_a_background_that_is_not_a_colour_is_an_error_and_nothing_is_written(self):
        code, out, err = run_main(["anim", self.path, "blob_idle", "--out", self.out, "--background", "grey"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: not a colour: 'grey'"), err)
        self.assertFalse(Path(self.out).exists())

    def test_a_scale_below_1_is_an_error_and_nothing_is_written(self):
        code, out, err = run_main(["anim", self.path, "blob_idle", "--out", self.out, "--scale", "0"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: scale must be a whole number of 1 or more"), err)
        self.assertFalse(Path(self.out).exists())

    def test_without_out_it_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["anim", self.path, "blob_idle"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--out", err.getvalue())

    def test_without_a_name_it_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["anim", self.path, "--out", self.out])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("NAME", err.getvalue())


if __name__ == "__main__":
    unittest.main()
