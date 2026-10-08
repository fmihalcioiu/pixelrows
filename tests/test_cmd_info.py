import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pixelrows.cli import main
from pixelrows.info import set_info
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]


def blob_set():
    """Two frames of a blob, a hat, and the clip that plays the blob."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1, {"g": "#7cc86a"}))
    spriteset.add(Sprite("hat", [".oo.", "oooo"]))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    return spriteset


def half_drawn_set():
    """The blob set with a character no palette has, and a clip with a missing frame."""
    spriteset = blob_set()
    spriteset.add(Sprite("odd", ["oq"]))
    spriteset.add_anim("walk", ["blob_0", "blob_9"], 8)
    return spriteset


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class InfoCommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = str(self.folder / "blob.json")
        blob_set().save(self.path)

    def test_prints_the_info_of_the_set_and_returns_0(self):
        code, out, err = run_main(["info", self.path])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out), set_info(blob_set()))

    def test_the_output_is_one_json_document_indented_by_2(self):
        code, out, err = run_main(["info", self.path])
        self.assertEqual(out, json.dumps(set_info(blob_set()), indent=2) + "\n")

    def test_the_output_has_the_keys_of_set_info(self):
        data = json.loads(run_main(["info", self.path])[1])
        self.assertEqual(list(data), ["palette", "sprites", "anims", "problems"])
        self.assertEqual([sprite["name"] for sprite in data["sprites"]], ["blob_0", "blob_1", "hat"])
        self.assertEqual([anim["name"] for anim in data["anims"]], ["blob_idle"])
        self.assertEqual(data["problems"], [])

    def test_with_names_only_those_sprites_and_anims_are_listed(self):
        whole = set_info(blob_set())
        code, out, err = run_main(["info", self.path, "blob_1", "blob_idle"])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(list(data), ["palette", "sprites", "anims", "problems"])
        self.assertEqual(data["sprites"], [whole["sprites"][1]])
        self.assertEqual(data["anims"], whole["anims"])
        self.assertEqual(data["palette"], whole["palette"])

    def test_a_sprite_named_alone_leaves_no_anims(self):
        data = json.loads(run_main(["info", self.path, "hat"])[1])
        self.assertEqual([sprite["name"] for sprite in data["sprites"]], ["hat"])
        self.assertEqual(data["anims"], [])

    def test_an_anim_named_alone_leaves_no_sprites(self):
        data = json.loads(run_main(["info", self.path, "blob_idle"])[1])
        self.assertEqual(data["sprites"], [])
        self.assertEqual([anim["name"] for anim in data["anims"]], ["blob_idle"])

    def test_named_sprites_stay_in_the_order_of_the_set(self):
        data = json.loads(run_main(["info", self.path, "hat", "blob_0"])[1])
        self.assertEqual([sprite["name"] for sprite in data["sprites"]], ["blob_0", "hat"])

    def test_a_name_that_is_a_sprite_and_an_anim_lists_both(self):
        spriteset = blob_set()
        spriteset.add_anim("hat", ["hat"], 1)
        spriteset.save(self.path)
        data = json.loads(run_main(["info", self.path, "hat"])[1])
        self.assertEqual([sprite["name"] for sprite in data["sprites"]], ["hat"])
        self.assertEqual([anim["name"] for anim in data["anims"]], ["hat"])

    def test_a_name_that_is_neither_is_an_error(self):
        code, out, err = run_main(["info", self.path, "blob_0", "boot"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: no sprite or anim named 'boot'\n")

    def test_a_half_drawn_set_is_printed_with_its_problems_and_the_code_is_0(self):
        half_drawn_set().save(self.path)
        code, out, err = run_main(["info", self.path])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data, set_info(half_drawn_set()))
        self.assertEqual(data["problems"], [
            "sprite 'odd' uses 'q', which is not in the palette",
            "anim 'walk' names 'blob_9', which is not a sprite",
        ])

    def test_with_names_the_problems_of_the_whole_set_are_still_listed(self):
        half_drawn_set().save(self.path)
        data = json.loads(run_main(["info", self.path, "hat"])[1])
        self.assertEqual(data["problems"], set_info(half_drawn_set())["problems"])

    def test_a_missing_file_is_an_error(self):
        path = str(self.folder / "none.json")
        code, out, err = run_main(["info", path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no such file: {path}\n")

    def test_no_file_at_all_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as left:
                main(["info"])
        self.assertEqual(left.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
