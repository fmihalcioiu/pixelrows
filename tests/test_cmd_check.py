import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pixelrows import checks
from pixelrows.checks import Options
from pixelrows.cli import main
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c", "e": "#f0f0f0"}

#: Two frames of a blob that no rule finds anything in.
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]

#: One 'e' with no 'e' beside it.
EYE = ["ooo", "oeo", "ooo"]

#: An outline of 'o' with one 'g' on the right edge.
OPEN = ["ooo", "ogg", "ooo"]


def clean_set():
    """The blob and the clip that plays it: no problems, and nothing for a rule to find."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    return spriteset


def eye_set():
    """The clean set with a sprite that has one lone pixel."""
    spriteset = clean_set()
    spriteset.add(Sprite("eye", EYE))
    return spriteset


def open_set():
    """The clean set with a sprite whose outline has one gap."""
    spriteset = clean_set()
    spriteset.add(Sprite("open", OPEN))
    return spriteset


def hop_set():
    """The clean set with a clip whose lowest painted row moves two rows."""
    spriteset = clean_set()
    spriteset.add(Sprite("hop_0", ["oo", "oo", "..", ".."]))
    spriteset.add(Sprite("hop_1", ["..", "..", "oo", "oo"]))
    spriteset.add_anim("hop", ["hop_0", "hop_1"], 6)
    return spriteset


def half_drawn_set():
    """The clean set with a clip that names a sprite that is not there."""
    spriteset = clean_set()
    spriteset.add_anim("walk", ["blob_0", "blob_9"], 8)
    return spriteset


def as_data(findings):
    """Findings as the command prints them."""
    return [finding.to_dict() for finding in findings]


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CheckCommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = str(self.folder / "set.json")

    def check(self, spriteset, *extra):
        """Saves the set and runs the command on it with `extra`. The code, and what it printed as data."""
        spriteset.save(self.path)
        code, out, err = run_main(["check", self.path, *extra])
        self.assertEqual(err, "")
        return code, json.loads(out)

    def test_a_set_with_nothing_wrong_prints_two_empty_lists_and_returns_0(self):
        clean_set().save(self.path)
        code, out, err = run_main(["check", self.path])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data, {"problems": [], "findings": []})
        self.assertEqual(list(data), ["problems", "findings"])
        self.assertEqual(out, json.dumps(data, indent=2) + "\n")

    def test_a_finding_is_printed_with_every_key_and_the_code_is_1(self):
        code, data = self.check(eye_set())
        self.assertEqual(code, 1)
        self.assertEqual(data, {
            "problems": [],
            "findings": [{"rule": "lone_pixel", "target": "eye", "message": "1 lone pixel", "points": [[1, 1]]}],
        })
        self.assertEqual(list(data["findings"][0]), ["rule", "target", "message", "points"])

    def test_the_findings_are_those_of_the_rules_on_their_default_options(self):
        code, data = self.check(eye_set())
        self.assertEqual(data["findings"], as_data(checks.run(eye_set())))

    def test_a_problem_alone_makes_the_code_1(self):
        code, data = self.check(half_drawn_set())
        self.assertEqual(code, 1)
        self.assertEqual(data, {
            "problems": ["anim 'walk' names 'blob_9', which is not a sprite"],
            "findings": [],
        })

    def test_problems_and_findings_are_printed_side_by_side(self):
        spriteset = half_drawn_set()
        spriteset.add(Sprite("eye", EYE))
        spriteset.add(Sprite("odd", ["oq", "oq"]))
        code, data = self.check(spriteset)
        self.assertEqual(code, 1)
        self.assertEqual(data["problems"], spriteset.problems())
        self.assertEqual(len(data["problems"]), 2)
        self.assertEqual(data["findings"], as_data(checks.run(spriteset)))
        self.assertEqual([finding["target"] for finding in data["findings"]], ["eye"])

    def test_the_rules_for_clips_run_too(self):
        code, data = self.check(hop_set())
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], [{
            "rule": "feet_drift",
            "target": "hop",
            "message": "the lowest painted row moves 2 rows across the clip (rows 1 to 3)",
            "points": [],
        }])

    def test_allow_lone_names_the_characters_a_lone_pixel_may_be(self):
        code, data = self.check(eye_set(), "--allow-lone", "e")
        self.assertEqual((code, data), (0, {"problems": [], "findings": []}))
        code, data = self.check(eye_set(), "--allow-lone", "xe")
        self.assertEqual((code, data), (0, {"problems": [], "findings": []}))

    def test_allow_lone_of_other_characters_leaves_the_finding(self):
        code, data = self.check(eye_set(), "--allow-lone", "xg")
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], as_data(checks.run(eye_set(), Options(lone_allow=frozenset("xg")))))
        self.assertEqual([finding["rule"] for finding in data["findings"]], ["lone_pixel"])

    def test_without_outline_no_outline_is_checked(self):
        code, data = self.check(open_set())
        self.assertEqual((code, data), (0, {"problems": [], "findings": []}))

    def test_outline_names_the_outline_character(self):
        code, data = self.check(open_set(), "--outline", "o")
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], [{
            "rule": "outline_gap",
            "target": "open",
            "message": "1 of 8 edge pixels are not the outline 'o'",
            "points": [[2, 1]],
        }])
        self.assertEqual(data["findings"], as_data(checks.run(open_set(), Options(outline="o"))))

    def test_without_max_colours_the_count_comes_from_the_size_of_the_sprite(self):
        spriteset = clean_set()
        spriteset.add(Sprite("stripes", ["ogeq"]))
        spriteset.palette.set("q", "#804020")
        code, data = self.check(spriteset)
        self.assertEqual(code, 1)
        self.assertIn(
            {"rule": "colour_count", "target": "stripes",
             "message": "uses 4 colours, 3 allowed for 4 painted pixels", "points": []},
            data["findings"],
        )

    def test_max_colours_sets_how_many_colours_a_sprite_may_use(self):
        code, data = self.check(clean_set(), "--max-colours", "1")
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], [
            {"rule": "colour_count", "target": "blob_0",
             "message": "uses 2 colours, 1 allowed for 18 painted pixels", "points": []},
            {"rule": "colour_count", "target": "blob_1",
             "message": "uses 2 colours, 1 allowed for 16 painted pixels", "points": []},
        ])
        code, data = self.check(clean_set(), "--max-colours", "2")
        self.assertEqual((code, data["findings"]), (0, []))

    def test_every_option_is_handed_to_the_rules(self):
        spriteset = eye_set()
        spriteset.add(Sprite("open", OPEN))
        options = Options(outline="o", lone_allow=frozenset("e"), max_colours=1)
        code, data = self.check(spriteset, "--outline", "o", "--allow-lone", "e", "--max-colours", "1")
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], as_data(checks.run(spriteset, options)))
        self.assertEqual(
            sorted({finding["rule"] for finding in data["findings"]}), ["colour_count", "outline_gap"]
        )

    def test_a_missing_file_is_an_error(self):
        path = str(self.folder / "none.json")
        code, out, err = run_main(["check", path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no such file: {path}\n")

    def test_a_file_that_is_not_a_set_is_an_error(self):
        Path(self.path).write_text('{"sprites": {"hat": {"rows": ["oo", "o"]}}}', encoding="utf-8")
        code, out, err = run_main(["check", self.path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: sprite 'hat'"), err)

    def test_an_outline_that_is_not_one_character_is_an_error(self):
        clean_set().save(self.path)
        for outline in ("og", ""):
            with self.subTest(outline=outline):
                code, out, err = run_main(["check", self.path, "--outline", outline])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertEqual(err, f"error: --outline takes one character, got {outline!r}\n")

    def test_a_max_colours_that_is_not_a_whole_number_exits_with_2(self):
        clean_set().save(self.path)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["check", self.path, "--max-colours", "few"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("--max-colours", err.getvalue())

    def test_no_file_at_all_exits_with_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as left:
                main(["check"])
        self.assertEqual(left.exception.code, 2)
        self.assertIn("FILE", err.getvalue())


if __name__ == "__main__":
    unittest.main()
