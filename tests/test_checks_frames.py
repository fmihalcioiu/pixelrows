import unittest

from pixelrows import checks
from pixelrows.checks import Finding, Options, frames
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

#: Frames named for how many cells they have painted. Each has its lowest painted cell on row 4.
BODY_24 = ["oooo.", "ooooo", "ooooo", "ooooo", "ooooo"]
BODY_23 = [".ooo.", "ooooo", "ooooo", "ooooo", "ooooo"]
BODY_17 = [".ooo.", ".ooo.", ".ooo.", ".ooo.", "ooooo"]
BODY_16 = [".ooo.", ".ooo.", ".ooo.", ".ooo.", "oooo."]
BODY_11 = [".....", ".....", ".ooo.", ".ooo.", "ooooo"]

#: Frames named for the row of their lowest painted cell. Each has six cells painted.
FEET_1 = ["ooo..", "ooo..", ".....", ".....", "....."]
FEET_2 = [".....", "ooo..", "ooo..", ".....", "....."]
FEET_3 = [".....", ".....", "ooo..", "ooo..", "....."]
FEET_4 = [".....", ".....", ".....", "ooo..", "ooo.."]

BLANK = [".....", ".....", ".....", ".....", "....."]


def add_clip(spriteset, name, *rows_of_frames):
    """Adds a sprite for each frame, named name_0, name_1 and so on, and an anim of that name playing them."""
    names = [f"{name}_{index}" for index in range(len(rows_of_frames))]
    for sprite_name, rows in zip(names, rows_of_frames):
        spriteset.add(Sprite(sprite_name, rows))
    spriteset.add_anim(name, names, 8)
    return spriteset


def clip(name, *rows_of_frames):
    """A set holding one such clip and nothing else."""
    return add_clip(SpriteSet(), name, *rows_of_frames)


def found(rule, spriteset, **options):
    """What one rule of the module finds in the set, on those options."""
    return [finding for finding in frames.check(spriteset, Options(**options)) if finding.rule == rule]


class FramePixelsTest(unittest.TestCase):
    def test_a_frame_too_far_from_the_mean_of_the_clip_is_flagged(self):
        hop = clip("hop", BODY_23, BODY_23, BODY_17, BODY_23)
        self.assertEqual(
            found("frame_pixels", hop),
            [Finding("frame_pixels", "hop", "frame 2 ('hop_2') has 17 painted pixels, the clip's mean is 21.5")],
        )

    def test_frames_near_the_mean_are_not_flagged(self):
        hop = clip("hop", BODY_24, BODY_23, BODY_24, BODY_23)
        self.assertEqual(found("frame_pixels", hop), [])

    def test_a_frame_exactly_at_the_slack_is_not_flagged(self):
        puff = clip("puff", BODY_23, BODY_17)
        self.assertEqual(found("frame_pixels", puff), [])

    def test_a_frame_one_pixel_past_the_slack_is_flagged(self):
        puff = clip("puff", BODY_24, BODY_16)
        self.assertEqual(
            found("frame_pixels", puff),
            [
                Finding("frame_pixels", "puff", "frame 0 ('puff_0') has 24 painted pixels, the clip's mean is 20.0"),
                Finding("frame_pixels", "puff", "frame 1 ('puff_1') has 16 painted pixels, the clip's mean is 20.0"),
            ],
        )

    def test_frame_slack_sets_how_far_a_frame_may_be(self):
        self.assertEqual(len(found("frame_pixels", clip("puff", BODY_23, BODY_17), frame_slack=0.125)), 2)
        self.assertEqual(found("frame_pixels", clip("puff", BODY_24, BODY_16), frame_slack=0.25), [])

    def test_each_place_in_the_clip_is_a_frame_named_by_its_sprite(self):
        spriteset = SpriteSet()
        spriteset.add(Sprite("open", BODY_24))
        spriteset.add(Sprite("shut", BODY_11))
        spriteset.add_anim("blink", ["open", "shut", "open"], 8)
        self.assertEqual(
            found("frame_pixels", spriteset),
            [
                Finding("frame_pixels", "blink", "frame 0 ('open') has 24 painted pixels, the clip's mean is 19.7"),
                Finding("frame_pixels", "blink", "frame 1 ('shut') has 11 painted pixels, the clip's mean is 19.7"),
                Finding("frame_pixels", "blink", "frame 2 ('open') has 24 painted pixels, the clip's mean is 19.7"),
            ],
        )

    def test_an_empty_frame_has_no_painted_pixels(self):
        pop = clip("pop", BODY_24, BODY_24, BODY_24, BLANK)
        self.assertEqual(
            found("frame_pixels", pop),
            [
                Finding("frame_pixels", "pop", "frame 0 ('pop_0') has 24 painted pixels, the clip's mean is 18.0"),
                Finding("frame_pixels", "pop", "frame 1 ('pop_1') has 24 painted pixels, the clip's mean is 18.0"),
                Finding("frame_pixels", "pop", "frame 2 ('pop_2') has 24 painted pixels, the clip's mean is 18.0"),
                Finding("frame_pixels", "pop", "frame 3 ('pop_3') has 0 painted pixels, the clip's mean is 18.0"),
            ],
        )

    def test_a_clip_with_nothing_painted_is_not_flagged(self):
        self.assertEqual(found("frame_pixels", clip("gap", BLANK, BLANK)), [])


class FeetDriftTest(unittest.TestCase):
    def test_a_lowest_painted_row_that_moves_past_the_slack_is_flagged(self):
        hop = clip("hop", FEET_4, FEET_1, FEET_4)
        self.assertEqual(
            found("feet_drift", hop),
            [Finding("feet_drift", "hop", "the lowest painted row moves 3 rows across the clip (rows 1 to 4)")],
        )

    def test_a_move_exactly_at_the_slack_is_not_flagged(self):
        self.assertEqual(found("feet_drift", clip("bob", FEET_4, FEET_3)), [])

    def test_a_move_one_row_past_the_slack_is_flagged(self):
        bob = clip("bob", FEET_4, FEET_2)
        self.assertEqual(
            found("feet_drift", bob),
            [Finding("feet_drift", "bob", "the lowest painted row moves 2 rows across the clip (rows 2 to 4)")],
        )

    def test_only_the_two_rows_furthest_apart_count(self):
        climb = clip("climb", FEET_3, FEET_4, FEET_2, FEET_3)
        self.assertEqual(
            found("feet_drift", climb),
            [Finding("feet_drift", "climb", "the lowest painted row moves 2 rows across the clip (rows 2 to 4)")],
        )

    def test_feet_slack_sets_how_far_the_row_may_move(self):
        self.assertEqual(found("feet_drift", clip("hop", FEET_4, FEET_1), feet_slack=3), [])
        self.assertEqual(len(found("feet_drift", clip("hop", FEET_4, FEET_1), feet_slack=2)), 1)

    def test_it_is_the_lowest_painted_row_that_counts_not_the_highest(self):
        self.assertEqual(found("feet_drift", clip("duck", BODY_23, FEET_4)), [])

    def test_an_empty_frame_is_not_counted(self):
        self.assertEqual(found("feet_drift", clip("flash", FEET_4, BLANK, FEET_4)), [])
        self.assertEqual(found("feet_drift", clip("flash", BLANK, FEET_3, FEET_4)), [])
        flash = clip("flash", FEET_1, BLANK, FEET_4)
        self.assertEqual(
            found("feet_drift", flash),
            [Finding("feet_drift", "flash", "the lowest painted row moves 3 rows across the clip (rows 1 to 4)")],
        )

    def test_a_clip_with_nothing_painted_is_not_flagged(self):
        self.assertEqual(found("feet_drift", clip("gap", BLANK, BLANK)), [])


class ClipsTest(unittest.TestCase):
    def test_a_clip_with_a_missing_frame_is_skipped(self):
        spriteset = clip("hop", FEET_1, BODY_23)
        self.assertEqual(len(frames.check(spriteset, Options())), 3)
        spriteset.add_anim("hop", ["hop_0", "hop_1", "hop_2"], 8)
        self.assertEqual(frames.check(spriteset, Options()), [])

    def test_a_clip_with_frames_of_different_sizes_is_skipped(self):
        spriteset = clip("hop", FEET_1, ["ooooo", "ooooo", "ooooo"])
        self.assertEqual(frames.check(spriteset, Options()), [])

    def test_a_clip_of_one_frame_is_skipped(self):
        # With a slack below zero, every frame of a clip that is looked at is flagged.
        strict = Options(frame_slack=-1.0, feet_slack=-1)
        spriteset = SpriteSet()
        spriteset.add(Sprite("still", FEET_4))
        spriteset.add_anim("wait", ["still", "still"], 8)
        self.assertEqual(len(frames.check(spriteset, strict)), 3)
        spriteset.add_anim("wait", ["still"], 8)
        self.assertEqual(frames.check(spriteset, strict), [])

    def test_findings_come_anim_by_anim_with_the_frames_first(self):
        spriteset = clip("hop", FEET_1, BODY_23)
        spriteset.add_anim("torn", ["hop_0", "hop_1", "hop_2"], 8)
        add_clip(spriteset, "bob", FEET_4, FEET_2)
        self.assertEqual(
            frames.check(spriteset, Options()),
            [
                Finding("frame_pixels", "hop", "frame 0 ('hop_0') has 6 painted pixels, the clip's mean is 14.5"),
                Finding("frame_pixels", "hop", "frame 1 ('hop_1') has 23 painted pixels, the clip's mean is 14.5"),
                Finding("feet_drift", "hop", "the lowest painted row moves 3 rows across the clip (rows 1 to 4)"),
                Finding("feet_drift", "bob", "the lowest painted row moves 2 rows across the clip (rows 2 to 4)"),
            ],
        )

    def test_a_set_with_no_anims_has_no_findings(self):
        spriteset = SpriteSet()
        spriteset.add(Sprite("still", FEET_4))
        self.assertEqual(frames.check(spriteset, Options()), [])


class RunTest(unittest.TestCase):
    def test_run_finds_the_rules_and_hands_them_the_options(self):
        spriteset = clip("hop", FEET_1, BODY_23)
        uneven = Finding("frame_pixels", "hop", "frame 0 ('hop_0') has 6 painted pixels, the clip's mean is 14.5")
        drift = Finding("feet_drift", "hop", "the lowest painted row moves 3 rows across the clip (rows 1 to 4)")
        self.assertIn(uneven, checks.run(spriteset))
        self.assertIn(drift, checks.run(spriteset))
        self.assertNotIn(uneven, checks.run(spriteset, Options(frame_slack=1.0)))
        self.assertNotIn(drift, checks.run(spriteset, Options(feet_slack=3)))


if __name__ == "__main__":
    unittest.main()
