import json
import tempfile
import unittest
from pathlib import Path

from pixelrows.errors import PixelRowsError
from pixelrows.palette import Palette
from pixelrows.sprite import Sprite
from pixelrows.spriteset import Anim, SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]

#: The set file of the design, as data.
FILE = {
    "palette": {"o": "#1a1a22", "g": "#58a84c"},
    "sprites": {
        "blob_0": {"rows": ["..oo..", ".oggo.", "oggggo", "oooooo"]},
        "blob_1": {"rows": ["......", ".oooo.", "oggggo", "oooooo"], "palette": {"g": "#7cc86a"}},
    },
    "anims": {
        "blob_idle": {"frames": ["blob_0", "blob_1"], "fps": 3},
    },
}


def blob_set():
    """The same set as FILE, built in code."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1, {"g": "#7cc86a"}))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    return spriteset


def block(name, width, height):
    """A sprite of that size, every cell 'o'."""
    return Sprite(name, ["o" * width] * height)


class AnimTest(unittest.TestCase):
    def assert_refused(self, message, *args):
        with self.assertRaises(PixelRowsError) as caught:
            Anim(*args)
        self.assertEqual(str(caught.exception), message)

    def test_fields_are_kept(self):
        anim = Anim("walk", ("a_0", "a_1"), 10)
        self.assertEqual(anim.name, "walk")
        self.assertEqual(anim.frames, ("a_0", "a_1"))
        self.assertEqual(anim.fps, 10)

    def test_frames_given_as_a_list_become_a_tuple(self):
        anim = Anim("walk", ["a_0", "a_1"], 10)
        self.assertEqual(anim.frames, ("a_0", "a_1"))
        self.assertIsInstance(anim.frames, tuple)

    def test_a_frame_may_play_more_than_once(self):
        self.assertEqual(Anim("walk", ["a_0", "a_1", "a_0"], 10).frames, ("a_0", "a_1", "a_0"))

    def test_duration_is_frames_over_fps_in_seconds(self):
        self.assertAlmostEqual(Anim("walk", ["a", "b", "c", "d"], 10).duration, 0.4)
        self.assertEqual(Anim("idle", ["a", "b"], 3).duration, 2 / 3)
        self.assertEqual(Anim("slow", ["a"], 0.5).duration, 2.0)

    def test_fps_may_be_an_int_or_a_float(self):
        self.assertEqual(Anim("walk", ["a"], 12).fps, 12)
        self.assertEqual(Anim("walk", ["a"], 7.5).fps, 7.5)

    def test_cannot_be_changed(self):
        anim = Anim("walk", ["a_0"], 10)
        for field, value in (("name", "run"), ("frames", ("b",)), ("fps", 5)):
            with self.subTest(field=field):
                with self.assertRaises(AttributeError):
                    setattr(anim, field, value)

    def test_equal_when_name_frames_and_fps_match(self):
        self.assertEqual(Anim("walk", ["a", "b"], 10), Anim("walk", ("a", "b"), 10.0))
        self.assertEqual(hash(Anim("walk", ["a", "b"], 10)), hash(Anim("walk", ("a", "b"), 10.0)))
        self.assertNotEqual(Anim("walk", ["a", "b"], 10), Anim("run", ["a", "b"], 10))
        self.assertNotEqual(Anim("walk", ["a", "b"], 10), Anim("walk", ["b", "a"], 10))
        self.assertNotEqual(Anim("walk", ["a", "b"], 10), Anim("walk", ["a", "b"], 12))

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            Anim("walk", [], 10)

    def test_name_must_be_a_non_empty_string(self):
        self.assert_refused("an anim's name is a non-empty string, got ''", "", ["a"], 10)
        self.assert_refused("an anim's name is a non-empty string, got None", None, ["a"], 10)

    def test_at_least_one_frame(self):
        self.assert_refused("anim 'walk': there are no frames", "walk", [], 10)
        self.assert_refused("anim 'walk': there are no frames", "walk", (), 10)

    def test_every_frame_is_a_string(self):
        self.assert_refused("anim 'walk': frame 1 is not a string, got 2", "walk", ["a", 2], 10)
        self.assert_refused("anim 'walk': frame 0 is not a string, got None", "walk", [None], 10)

    def test_frames_must_be_a_list_not_one_string(self):
        self.assert_refused("anim 'walk': frames are a list of sprite names, got one string 'a_0'", "walk", "a_0", 10)

    def test_frames_that_cannot_be_read_as_a_list(self):
        self.assert_refused("anim 'walk': frames are a list of sprite names, got 4", "walk", 4, 10)

    def test_fps_must_be_above_zero(self):
        self.assert_refused("anim 'walk': fps is a number above 0, got 0", "walk", ["a"], 0)
        self.assert_refused("anim 'walk': fps is a number above 0, got 0.0", "walk", ["a"], 0.0)
        self.assert_refused("anim 'walk': fps is a number above 0, got -2", "walk", ["a"], -2)

    def test_fps_must_be_a_number(self):
        self.assert_refused("anim 'walk': fps is a number above 0, got '10'", "walk", ["a"], "10")
        self.assert_refused("anim 'walk': fps is a number above 0, got None", "walk", ["a"], None)

    def test_a_bool_is_not_an_fps(self):
        self.assert_refused("anim 'walk': fps is a number above 0, got True", "walk", ["a"], True)
        self.assert_refused("anim 'walk': fps is a number above 0, got False", "walk", ["a"], False)

    def test_fps_must_be_finite(self):
        self.assert_refused("anim 'walk': fps is a number above 0, got inf", "walk", ["a"], float("inf"))
        self.assert_refused("anim 'walk': fps is a number above 0, got nan", "walk", ["a"], float("nan"))


class SpriteSetMakingTest(unittest.TestCase):
    def test_starts_empty(self):
        spriteset = SpriteSet()
        self.assertEqual(spriteset.palette, Palette())
        self.assertEqual(spriteset.sprites, {})
        self.assertEqual(spriteset.anims, {})

    def test_mapping_becomes_a_palette(self):
        spriteset = SpriteSet({"o": "#1A1A22"})
        self.assertIsInstance(spriteset.palette, Palette)
        self.assertEqual(spriteset.palette.to_dict(), {"o": "#1a1a22"})

    def test_palette_it_was_made_from_can_change_without_it(self):
        palette = Palette(PALETTE)
        spriteset = SpriteSet(palette)
        self.assertEqual(spriteset.palette, palette)
        palette.set("x", "#ffffff")
        self.assertNotIn("x", spriteset.palette)

    def test_palette_of_a_wrong_kind(self):
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet(["o"])
        self.assertEqual(str(caught.exception), "a set's palette is a Palette or a mapping, got ['o']")

    def test_palette_errors_pass_through(self):
        with self.assertRaises(PixelRowsError):
            SpriteSet({"o": "black"})


class AddTest(unittest.TestCase):
    def test_add_returns_the_sprite_and_keeps_it_by_name(self):
        spriteset = SpriteSet()
        sprite = Sprite("a", ["o"])
        self.assertIs(spriteset.add(sprite), sprite)
        self.assertIs(spriteset.sprites["a"], sprite)

    def test_sprites_stay_in_the_order_added(self):
        spriteset = SpriteSet()
        for name in ("zed", "bee", "ay", "em"):
            spriteset.add(Sprite(name, ["o"]))
        self.assertEqual(list(spriteset.sprites), ["zed", "bee", "ay", "em"])

    def test_add_replaces_one_of_the_same_name(self):
        spriteset = SpriteSet()
        spriteset.add(Sprite("a", ["o"]))
        spriteset.add(Sprite("b", ["o"]))
        newer = spriteset.add(Sprite("a", ["oo", "oo"]))
        self.assertEqual(len(spriteset.sprites), 2)
        self.assertIs(spriteset.sprites["a"], newer)
        self.assertEqual(spriteset.sprite("a").rows, ("oo", "oo"))
        self.assertEqual(list(spriteset.sprites), ["a", "b"])

    def test_add_takes_only_a_sprite(self):
        spriteset = SpriteSet()
        with self.assertRaises(PixelRowsError) as caught:
            spriteset.add(["oo", "oo"])
        self.assertEqual(str(caught.exception), "only a Sprite can be added to a set, got ['oo', 'oo']")
        self.assertEqual(spriteset.sprites, {})

    def test_add_anim_returns_the_anim_and_keeps_it_by_name(self):
        spriteset = SpriteSet()
        anim = spriteset.add_anim("walk", ["a_0", "a_1"], 10)
        self.assertEqual(anim, Anim("walk", ("a_0", "a_1"), 10))
        self.assertIsInstance(anim.frames, tuple)
        self.assertIs(spriteset.anims["walk"], anim)

    def test_anims_stay_in_the_order_added(self):
        spriteset = SpriteSet()
        for name in ("walk", "idle", "attack"):
            spriteset.add_anim(name, ["a"], 10)
        self.assertEqual(list(spriteset.anims), ["walk", "idle", "attack"])

    def test_add_anim_replaces_one_of_the_same_name(self):
        spriteset = SpriteSet()
        spriteset.add_anim("walk", ["a_0", "a_1"], 10)
        spriteset.add_anim("idle", ["a_0"], 2)
        newer = spriteset.add_anim("walk", ["a_2"], 6)
        self.assertEqual(len(spriteset.anims), 2)
        self.assertIs(spriteset.anims["walk"], newer)
        self.assertEqual(spriteset.anim("walk").frames, ("a_2",))
        self.assertEqual(spriteset.anim("walk").fps, 6)
        self.assertEqual(list(spriteset.anims), ["walk", "idle"])

    def test_add_anim_may_name_sprites_that_are_not_drawn_yet(self):
        spriteset = SpriteSet()
        spriteset.add_anim("walk", ["a_0"], 10)
        self.assertEqual(spriteset.sprites, {})
        self.assertEqual(spriteset.anim("walk").frames, ("a_0",))

    def test_add_anim_holds_the_rules_of_an_anim(self):
        spriteset = SpriteSet()
        for frames, fps in (([], 10), (["a"], 0), (["a"], True), ([1], 10)):
            with self.subTest(frames=frames, fps=fps):
                with self.assertRaises(PixelRowsError):
                    spriteset.add_anim("walk", frames, fps)
        self.assertEqual(spriteset.anims, {})


class LookUpTest(unittest.TestCase):
    def setUp(self):
        self.spriteset = blob_set()

    def test_sprite_by_name(self):
        self.assertEqual(self.spriteset.sprite("blob_0"), Sprite("blob_0", BLOB_0))

    def test_no_sprite_of_that_name(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.sprite("x")
        self.assertEqual(str(caught.exception), "no sprite named 'x'")

    def test_an_anim_is_not_a_sprite(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.sprite("blob_idle")
        self.assertEqual(str(caught.exception), "no sprite named 'blob_idle'")

    def test_anim_by_name(self):
        self.assertEqual(self.spriteset.anim("blob_idle"), Anim("blob_idle", ("blob_0", "blob_1"), 3))

    def test_no_anim_of_that_name(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.anim("x")
        self.assertEqual(str(caught.exception), "no anim named 'x'")

    def test_a_sprite_is_not_an_anim(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.anim("blob_0")
        self.assertEqual(str(caught.exception), "no anim named 'blob_0'")


class PaletteForTest(unittest.TestCase):
    def setUp(self):
        self.spriteset = blob_set()

    def test_sprite_with_no_palette_of_its_own_gets_the_sets(self):
        palette = self.spriteset.palette_for(self.spriteset.sprite("blob_0"))
        self.assertEqual(palette.to_dict(), {"o": "#1a1a22", "g": "#58a84c"})

    def test_sprites_own_entries_are_laid_over_the_sets(self):
        palette = self.spriteset.palette_for(self.spriteset.sprite("blob_1"))
        self.assertEqual(palette.to_dict(), {"o": "#1a1a22", "g": "#7cc86a"})

    def test_sprites_own_new_character_is_added(self):
        sprite = self.spriteset.add(Sprite("eye", ["ow"], {"w": "#ffffff"}))
        palette = self.spriteset.palette_for(sprite)
        self.assertEqual(palette.to_dict(), {"o": "#1a1a22", "g": "#58a84c", "w": "#ffffff"})

    def test_takes_a_name(self):
        self.assertEqual(self.spriteset.palette_for("blob_1").hex("g"), "#7cc86a")
        self.assertEqual(self.spriteset.palette_for("blob_0").hex("g"), "#58a84c")

    def test_name_of_no_sprite(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.palette_for("x")
        self.assertEqual(str(caught.exception), "no sprite named 'x'")

    def test_takes_a_sprite_that_is_not_in_the_set(self):
        palette = self.spriteset.palette_for(Sprite("loose", ["r"], {"r": "#ff0000"}))
        self.assertEqual(palette.to_dict(), {"o": "#1a1a22", "g": "#58a84c", "r": "#ff0000"})

    def test_sets_palette_is_left_as_it_was(self):
        palette = self.spriteset.palette_for("blob_1")
        palette.set("o", "#ffffff")
        self.assertIsNot(palette, self.spriteset.palette)
        self.assertEqual(self.spriteset.palette.to_dict(), PALETTE)
        self.assertEqual(self.spriteset.palette_for("blob_0").to_dict(), PALETTE)


class FramesOfTest(unittest.TestCase):
    def setUp(self):
        self.spriteset = SpriteSet({"o": "#000000"})
        self.a_0 = self.spriteset.add(block("a_0", 12, 16))
        self.a_1 = self.spriteset.add(block("a_1", 12, 16))
        self.a_2 = self.spriteset.add(block("a_2", 12, 17))

    def test_sprites_come_back_in_play_order(self):
        self.spriteset.add_anim("walk", ["a_1", "a_0", "a_1"], 10)
        frames = self.spriteset.frames_of("walk")
        self.assertEqual(len(frames), 3)
        self.assertIs(frames[0], self.a_1)
        self.assertIs(frames[1], self.a_0)
        self.assertIs(frames[2], self.a_1)

    def test_takes_an_anim_or_its_name(self):
        anim = self.spriteset.add_anim("walk", ["a_0", "a_1"], 10)
        self.assertEqual(self.spriteset.frames_of(anim), self.spriteset.frames_of("walk"))
        self.assertEqual(self.spriteset.frames_of(Anim("loose", ["a_1"], 4)), [self.a_1])

    def test_name_of_no_anim(self):
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.frames_of("x")
        self.assertEqual(str(caught.exception), "no anim named 'x'")

    def test_frame_naming_a_missing_sprite(self):
        self.spriteset.add_anim("walk", ["a_0", "a_9", "a_1"], 10)
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.frames_of("walk")
        self.assertEqual(str(caught.exception), "anim 'walk' names 'a_9', which is not a sprite")

    def test_frames_that_differ_in_size(self):
        self.spriteset.add_anim("walk", ["a_0", "a_1", "a_2"], 10)
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.frames_of("walk")
        self.assertEqual(str(caught.exception), "anim 'walk': frame 'a_2' is 12x17, the first frame is 12x16")

    def test_frames_that_differ_in_width(self):
        self.spriteset.add(block("wide", 13, 16))
        self.spriteset.add_anim("walk", ["a_0", "wide"], 10)
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.frames_of("walk")
        self.assertEqual(str(caught.exception), "anim 'walk': frame 'wide' is 13x16, the first frame is 12x16")

    def test_missing_sprite_is_said_before_a_size(self):
        self.spriteset.add_anim("walk", ["a_0", "a_2", "a_9"], 10)
        with self.assertRaises(PixelRowsError) as caught:
            self.spriteset.frames_of("walk")
        self.assertEqual(str(caught.exception), "anim 'walk' names 'a_9', which is not a sprite")

    def test_one_frame_plays(self):
        self.spriteset.add_anim("still", ["a_2"], 1)
        self.assertEqual(self.spriteset.frames_of("still"), [self.a_2])


class ToDictTest(unittest.TestCase):
    def test_shape_is_the_set_file(self):
        self.assertEqual(blob_set().to_dict(), FILE)

    def test_all_three_keys_are_always_there_in_order(self):
        self.assertEqual(SpriteSet().to_dict(), {"palette": {}, "sprites": {}, "anims": {}})
        self.assertEqual(list(SpriteSet().to_dict()), ["palette", "sprites", "anims"])
        self.assertEqual(list(blob_set().to_dict()), ["palette", "sprites", "anims"])

    def test_sprite_palette_is_written_only_when_it_has_entries(self):
        sprites = blob_set().to_dict()["sprites"]
        self.assertEqual(list(sprites["blob_0"]), ["rows"])
        self.assertEqual(list(sprites["blob_1"]), ["rows", "palette"])
        self.assertEqual(sprites["blob_1"]["palette"], {"g": "#7cc86a"})

    def test_sprite_made_with_an_empty_palette_has_no_palette_key(self):
        spriteset = SpriteSet()
        spriteset.add(Sprite("a", ["o"], {}))
        self.assertEqual(spriteset.to_dict()["sprites"], {"a": {"rows": ["o"]}})

    def test_whole_fps_is_written_as_an_int(self):
        spriteset = SpriteSet()
        spriteset.add_anim("walk", ["a"], 10.0)
        fps = spriteset.to_dict()["anims"]["walk"]["fps"]
        self.assertEqual(fps, 10)
        self.assertIsInstance(fps, int)

    def test_int_fps_stays_an_int(self):
        fps = blob_set().to_dict()["anims"]["blob_idle"]["fps"]
        self.assertEqual(fps, 3)
        self.assertIsInstance(fps, int)

    def test_fps_with_a_fraction_is_kept(self):
        spriteset = SpriteSet()
        spriteset.add_anim("walk", ["a"], 7.5)
        fps = spriteset.to_dict()["anims"]["walk"]["fps"]
        self.assertEqual(fps, 7.5)
        self.assertIsInstance(fps, float)

    def test_rows_and_frames_are_lists(self):
        data = blob_set().to_dict()
        self.assertIsInstance(data["sprites"]["blob_0"]["rows"], list)
        self.assertIsInstance(data["anims"]["blob_idle"]["frames"], list)

    def test_goes_straight_to_json(self):
        self.assertEqual(json.loads(json.dumps(blob_set().to_dict())), FILE)

    def test_sprites_and_anims_keep_the_order_added(self):
        spriteset = SpriteSet()
        for name in ("zed", "bee", "ay"):
            spriteset.add(Sprite(name, ["o"]))
            spriteset.add_anim(name + "_clip", [name], 4)
        data = spriteset.to_dict()
        self.assertEqual(list(data["sprites"]), ["zed", "bee", "ay"])
        self.assertEqual(list(data["anims"]), ["zed_clip", "bee_clip", "ay_clip"])

    def test_changing_the_data_does_not_change_the_set(self):
        spriteset = blob_set()
        data = spriteset.to_dict()
        data["palette"]["o"] = "#ffffff"
        data["sprites"]["blob_0"]["rows"][0] = "oooooo"
        data["anims"]["blob_idle"]["frames"].append("blob_9")
        self.assertEqual(spriteset, blob_set())


class FromDictTest(unittest.TestCase):
    def assert_refused(self, message, data):
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.from_dict(data)
        self.assertEqual(str(caught.exception), message)

    def test_reads_the_set_file(self):
        spriteset = SpriteSet.from_dict(FILE)
        self.assertIsInstance(spriteset, SpriteSet)
        self.assertEqual(spriteset, blob_set())
        self.assertEqual(spriteset.palette, Palette(PALETTE))
        self.assertEqual(list(spriteset.sprites), ["blob_0", "blob_1"])
        self.assertEqual(spriteset.sprite("blob_1").palette, Palette({"g": "#7cc86a"}))
        self.assertIsNone(spriteset.sprite("blob_0").palette)
        self.assertEqual(spriteset.anim("blob_idle"), Anim("blob_idle", ("blob_0", "blob_1"), 3))

    def test_to_dict_comes_back_as_the_same_set(self):
        self.assertEqual(SpriteSet.from_dict(blob_set().to_dict()), blob_set())
        self.assertEqual(SpriteSet.from_dict(FILE).to_dict(), FILE)

    def test_all_three_keys_may_be_missing(self):
        self.assertEqual(SpriteSet.from_dict({}), SpriteSet())

    def test_any_one_key_may_stand_alone(self):
        self.assertEqual(SpriteSet.from_dict({"palette": PALETTE}), SpriteSet(PALETTE))
        only_sprites = SpriteSet.from_dict({"sprites": {"a": {"rows": ["o"]}}})
        self.assertEqual(only_sprites.palette, Palette())
        self.assertEqual(only_sprites.sprites, {"a": Sprite("a", ["o"])})
        self.assertEqual(only_sprites.anims, {})
        only_anims = SpriteSet.from_dict({"anims": {"walk": {"frames": ["a_0"], "fps": 10}}})
        self.assertEqual(only_anims.sprites, {})
        self.assertEqual(only_anims.anims, {"walk": Anim("walk", ("a_0",), 10)})

    def test_sprite_may_be_a_bare_list_of_rows(self):
        spriteset = SpriteSet.from_dict({"sprites": {"a": ["ab", "cd"], "b": {"rows": ["ef"]}}})
        self.assertEqual(spriteset.sprite("a"), Sprite("a", ["ab", "cd"]))
        self.assertEqual(spriteset.sprite("b"), Sprite("b", ["ef"]))
        self.assertEqual(spriteset.to_dict()["sprites"]["a"], {"rows": ["ab", "cd"]})

    def test_empty_sprite_palette_is_no_palette(self):
        spriteset = SpriteSet.from_dict({"sprites": {"a": {"rows": ["o"], "palette": {}}}})
        self.assertIsNone(spriteset.sprite("a").palette)

    def test_fps_with_a_fraction_is_read(self):
        spriteset = SpriteSet.from_dict({"anims": {"walk": {"frames": ["a"], "fps": 7.5}}})
        self.assertEqual(spriteset.anim("walk").fps, 7.5)

    def test_unknown_key_at_the_top(self):
        self.assert_refused(
            "unknown key 'sprite' at the top (the keys are 'palette', 'sprites', 'anims')",
            {"palette": {}, "sprite": {}},
        )

    def test_unknown_key_in_a_sprite(self):
        self.assert_refused(
            "unknown key 'row' in sprites.blob_0 (the keys are 'rows', 'palette')",
            {"sprites": {"blob_0": {"rows": ["o"], "row": ["o"]}}},
        )

    def test_unknown_key_in_an_anim(self):
        self.assert_refused(
            "unknown key 'frame' in anims.walk (the keys are 'frames', 'fps')",
            {"anims": {"walk": {"frames": ["a"], "fps": 3, "frame": "a"}}},
        )

    def test_wrong_type_says_where(self):
        cases = (
            ("a set must be an object with 'palette', 'sprites' and 'anims'", []),
            ("a set must be an object with 'palette', 'sprites' and 'anims'", "{}"),
            ("a set must be an object with 'palette', 'sprites' and 'anims'", None),
            ("palette must be an object", {"palette": []}),
            ("palette must be an object", {"palette": None}),
            ("sprites must be an object", {"sprites": []}),
            ("sprites must be an object", {"sprites": "blob_0"}),
            ("anims must be an object", {"anims": []}),
            ("sprites.blob_0 must be an object or a list of strings", {"sprites": {"blob_0": "oo"}}),
            ("sprites.blob_0 must be an object or a list of strings", {"sprites": {"blob_0": None}}),
            ("sprites.blob_0 must be an object or a list of strings", {"sprites": {"blob_0": ["oo", 3]}}),
            ("sprites.blob_0.rows must be a list of strings", {"sprites": {"blob_0": {"rows": "oo"}}}),
            ("sprites.blob_0.rows must be a list of strings", {"sprites": {"blob_0": {"rows": ["oo", 3]}}}),
            ("sprites.blob_0.rows must be a list of strings", {"sprites": {"blob_0": {"rows": {"0": "oo"}}}}),
            ("sprites.blob_0.rows must be a list of strings", {"sprites": {"blob_0": {"rows": None}}}),
            ("sprites.blob_0.palette must be an object", {"sprites": {"blob_0": {"rows": ["o"], "palette": []}}}),
            ("sprites.blob_0.palette must be an object", {"sprites": {"blob_0": {"rows": ["o"], "palette": None}}}),
            ("anims.walk must be an object", {"anims": {"walk": ["a_0", "a_1"]}}),
            ("anims.walk must be an object", {"anims": {"walk": 10}}),
            ("anims.walk.frames must be a list of strings", {"anims": {"walk": {"frames": "a_0", "fps": 3}}}),
            ("anims.walk.frames must be a list of strings", {"anims": {"walk": {"frames": ["a_0", 1], "fps": 3}}}),
            ("anims.walk.fps must be a number", {"anims": {"walk": {"frames": ["a_0"], "fps": "3"}}}),
            ("anims.walk.fps must be a number", {"anims": {"walk": {"frames": ["a_0"], "fps": None}}}),
            ("anims.walk.fps must be a number", {"anims": {"walk": {"frames": ["a_0"], "fps": True}}}),
            ("anims.walk.fps must be a number", {"anims": {"walk": {"frames": ["a_0"], "fps": [3]}}}),
        )
        for message, data in cases:
            with self.subTest(data=data):
                self.assert_refused(message, data)

    def test_sprite_without_rows_and_anim_without_frames_or_fps(self):
        self.assert_refused("sprites.blob_0.rows is missing", {"sprites": {"blob_0": {}}})
        self.assert_refused("sprites.blob_0.rows is missing", {"sprites": {"blob_0": {"palette": {"o": "#000"}}}})
        self.assert_refused("anims.walk.frames is missing", {"anims": {"walk": {"fps": 3}}})
        self.assert_refused("anims.walk.fps is missing", {"anims": {"walk": {"frames": ["a_0"]}}})

    def test_wrong_sprite_is_named_among_right_ones(self):
        data = {"sprites": {"a": ["oo"], "b": {"rows": ["oo"]}, "c": {"rows": [1]}}}
        self.assert_refused("sprites.c.rows must be a list of strings", data)

    def test_errors_from_sprite_pass_through(self):
        self.assert_refused("sprite 'hat': row 1 is 1 wide, the others are 2", {"sprites": {"hat": ["oo", "o"]}})
        self.assert_refused("sprite 'hat': there are no rows", {"sprites": {"hat": {"rows": []}}})
        self.assert_refused("sprite 'hat': row 0 has whitespace at column 1", {"sprites": {"hat": {"rows": ["o o"]}}})

    def test_errors_from_anim_pass_through(self):
        self.assert_refused("anim 'walk': there are no frames", {"anims": {"walk": {"frames": [], "fps": 3}}})
        self.assert_refused(
            "anim 'walk': fps is a number above 0, got 0", {"anims": {"walk": {"frames": ["a"], "fps": 0}}}
        )
        self.assert_refused(
            "anim 'walk': fps is a number above 0, got -1.5", {"anims": {"walk": {"frames": ["a"], "fps": -1.5}}}
        )

    def test_errors_from_palette_pass_through(self):
        self.assert_refused("not a colour: 'black' (expected '#rrggbb')", {"palette": {"o": "black"}})
        self.assert_refused("a palette key is one character, got 'oo'", {"palette": {"oo": "#000000"}})
        self.assert_refused(
            "not a colour: 'green' (expected '#rrggbb')",
            {"sprites": {"a": {"rows": ["g"], "palette": {"g": "green"}}}},
        )

    def test_data_it_was_read_from_can_change_without_it(self):
        data = json.loads(json.dumps(FILE))
        spriteset = SpriteSet.from_dict(data)
        data["palette"]["o"] = "#ffffff"
        data["sprites"]["blob_0"]["rows"][0] = "oooooo"
        data["anims"]["blob_idle"]["frames"].append("blob_9")
        self.assertEqual(spriteset, blob_set())


class EqualityTest(unittest.TestCase):
    def test_same_palette_sprites_and_anims_are_equal(self):
        self.assertEqual(blob_set(), blob_set())
        self.assertEqual(SpriteSet(), SpriteSet())

    def test_another_palette_is_not_equal(self):
        other = blob_set()
        other.palette.set("o", "#000000")
        self.assertNotEqual(other, blob_set())

    def test_another_sprite_is_not_equal(self):
        other = blob_set()
        other.add(Sprite("blob_0", BLOB_1))
        self.assertNotEqual(other, blob_set())
        more = blob_set()
        more.add(Sprite("blob_2", BLOB_0))
        self.assertNotEqual(more, blob_set())

    def test_another_anim_is_not_equal(self):
        other = blob_set()
        other.add_anim("blob_idle", ["blob_0", "blob_1"], 4)
        self.assertNotEqual(other, blob_set())
        more = blob_set()
        more.add_anim("blob_blink", ["blob_1"], 1)
        self.assertNotEqual(more, blob_set())

    def test_sprites_in_another_order_are_not_equal(self):
        one = SpriteSet(PALETTE)
        one.add(Sprite("a", ["o"]))
        one.add(Sprite("b", ["g"]))
        two = SpriteSet(PALETTE)
        two.add(Sprite("b", ["g"]))
        two.add(Sprite("a", ["o"]))
        self.assertEqual(one.sprites, two.sprites)
        self.assertNotEqual(one, two)

    def test_anims_in_another_order_are_not_equal(self):
        one = SpriteSet(PALETTE)
        one.add_anim("walk", ["a"], 10)
        one.add_anim("idle", ["a"], 2)
        two = SpriteSet(PALETTE)
        two.add_anim("idle", ["a"], 2)
        two.add_anim("walk", ["a"], 10)
        self.assertEqual(one.anims, two.anims)
        self.assertNotEqual(one, two)

    def test_not_equal_to_what_is_not_a_set(self):
        self.assertNotEqual(blob_set(), FILE)
        self.assertNotEqual(SpriteSet(), None)


class LoadTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def write(self, name, text):
        path = self.folder / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def test_reads_a_set_file(self):
        path = self.write("blob.json", json.dumps(FILE))
        self.assertEqual(SpriteSet.load(path), blob_set())

    def test_takes_a_path_or_a_string(self):
        path = self.write("blob.json", json.dumps(FILE))
        self.assertEqual(SpriteSet.load(str(path)), SpriteSet.load(path))

    def test_reads_utf_8(self):
        text = '{"palette": {"\u2588": "#102030"}, "sprites": {"caf\u00e9": ["\u2588.", ".\u2588"]}}'
        spriteset = SpriteSet.load(self.write("block.json", text))
        self.assertEqual(spriteset.palette.to_dict(), {"\u2588": "#102030"})
        self.assertEqual(spriteset.sprite("caf\u00e9").rows, ("\u2588.", ".\u2588"))

    def test_reads_a_file_with_windows_line_ends(self):
        text = json.dumps(FILE, indent=2).replace("\n", "\r\n") + "\r\n"
        self.assertEqual(SpriteSet.load(self.write("blob.json", text)), blob_set())

    def test_bad_json_gives_the_path_the_line_and_the_column(self):
        path = self.write("broken.json", '{\n  "palette": {}\n  "sprites": {}\n}\n')
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.load(path)
        message = str(caught.exception)
        self.assertTrue(message.startswith(f"{path}: not JSON at line 3, column 3: "), message)
        self.assertGreater(len(message), len(f"{path}: not JSON at line 3, column 3: "))

    def test_bad_json_further_along_a_line(self):
        path = self.write("broken.json", '{"palette": {},\n "sprites": {"a": ["oo", oo]}}\n')
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.load(str(path))
        message = str(caught.exception)
        self.assertIn(str(path), message)
        self.assertIn("line 2, column 26", message)

    def test_empty_file_is_bad_json(self):
        path = self.write("empty.json", "")
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.load(path)
        self.assertIn(str(path), str(caught.exception))
        self.assertIn("line 1, column 1", str(caught.exception))

    def test_file_that_is_not_utf_8_names_the_path(self):
        path = self.folder / "latin.json"
        path.write_bytes(b'{"sprites": {"caf\xe9": ["o"]}}')
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.load(path)
        self.assertEqual(str(caught.exception), f"{path}: not UTF-8 at byte 17")

    def test_json_that_is_not_a_set_is_refused(self):
        with self.assertRaises(PixelRowsError):
            SpriteSet.load(self.write("list.json", "[1, 2, 3]"))
        with self.assertRaises(PixelRowsError) as caught:
            SpriteSet.load(self.write("typo.json", '{"sprite": {}}'))
        self.assertIn("'sprite'", str(caught.exception))

    def test_missing_file_is_the_usual_os_error(self):
        with self.assertRaises(OSError) as caught:
            SpriteSet.load(self.folder / "nothing.json")
        self.assertIsInstance(caught.exception, FileNotFoundError)
        self.assertNotIsInstance(caught.exception, PixelRowsError)


class SaveTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_whole_file_for_a_small_set(self):
        spriteset = SpriteSet({"o": "#000000"})
        spriteset.add(Sprite("dot", ["o.", ".o"]))
        spriteset.add_anim("blink", ["dot"], 2.0)
        path = self.folder / "dot.json"
        spriteset.save(path)
        expected = (
            "{\n"
            '  "palette": {\n'
            '    "o": "#000000"\n'
            "  },\n"
            '  "sprites": {\n'
            '    "dot": {\n'
            '      "rows": [\n'
            '        "o.",\n'
            '        ".o"\n'
            "      ]\n"
            "    }\n"
            "  },\n"
            '  "anims": {\n'
            '    "blink": {\n'
            '      "frames": [\n'
            '        "dot"\n'
            "      ],\n"
            '      "fps": 2\n'
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(path.read_bytes(), expected.encode("utf-8"))

    def test_file_is_the_json_of_to_dict_with_indent_2(self):
        path = self.folder / "blob.json"
        blob_set().save(path)
        expected = json.dumps(FILE, indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(path.read_bytes(), expected.encode("utf-8"))

    def test_line_ends_are_plain_newlines(self):
        path = self.folder / "blob.json"
        blob_set().save(path)
        data = path.read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertGreater(data.count(b"\n"), 20)

    def test_file_ends_with_one_newline(self):
        path = self.folder / "blob.json"
        blob_set().save(path)
        data = path.read_bytes()
        self.assertTrue(data.endswith(b"}\n"))
        self.assertFalse(data.endswith(b"\n\n"))

    def test_each_row_sits_on_its_own_line(self):
        path = self.folder / "blob.json"
        blob_set().save(path)
        lines = path.read_bytes().decode("utf-8").split("\n")
        start = lines.index('      "rows": [')
        self.assertEqual(
            lines[start + 1:start + 6],
            ['        "..oo..",', '        ".oggo.",', '        "oggggo",', '        "oooooo"', "      ]"],
        )
        for row in BLOB_0 + BLOB_1:
            with self.subTest(row=row):
                self.assertTrue(any(line.strip().rstrip(",") == f'"{row}"' for line in lines))

    def test_parent_folders_are_made(self):
        path = self.folder / "art" / "blobs" / "blob.json"
        blob_set().save(path)
        self.assertTrue(path.is_file())
        self.assertEqual(SpriteSet.load(path), blob_set())

    def test_takes_a_string_path(self):
        path = str(self.folder / "blob.json")
        blob_set().save(path)
        self.assertEqual(SpriteSet.load(path), blob_set())

    def test_saving_again_writes_over_the_file(self):
        path = self.folder / "blob.json"
        blob_set().save(path)
        SpriteSet().save(path)
        self.assertEqual(path.read_bytes(), b'{\n  "palette": {},\n  "sprites": {},\n  "anims": {}\n}\n')

    def test_characters_outside_ascii_are_written_as_themselves_in_utf_8(self):
        spriteset = SpriteSet({"\u2588": "#102030"})
        spriteset.add(Sprite("caf\u00e9", ["\u2588.", ".\u2588"]))
        path = self.folder / "block.json"
        spriteset.save(path)
        data = path.read_bytes()
        self.assertNotIn(b"\\u", data)
        self.assertIn("\u2588.".encode("utf-8"), data)
        self.assertIn("caf\u00e9".encode("utf-8"), data)
        self.assertEqual(SpriteSet.load(path), spriteset)


class SaveThenLoadTest(unittest.TestCase):
    def round_trip(self, spriteset):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "set.json"
            spriteset.save(path)
            return SpriteSet.load(path)

    def test_the_set_of_the_design_comes_back_equal(self):
        self.assertEqual(self.round_trip(blob_set()), blob_set())

    def test_an_empty_set_comes_back_equal(self):
        self.assertEqual(self.round_trip(SpriteSet()), SpriteSet())

    def test_saved_twice_the_file_is_the_same(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.json"
            second = Path(folder) / "second.json"
            blob_set().save(first)
            SpriteSet.load(first).save(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
