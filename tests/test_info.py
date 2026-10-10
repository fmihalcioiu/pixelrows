import json
import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.info import anim_info, set_info, sprite_info
from pixelrows.palette import Palette
from pixelrows.sprite import Sprite
from pixelrows.spriteset import Anim, SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]


def blob_set():
    """Two frames of a blob, the second with a green of its own, and the clip that plays them."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1, {"g": "#7cc86a"}))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    return spriteset


def half_drawn_set():
    """The blob set with an empty sprite, a character no palette has, a missing frame and frames of two sizes."""
    spriteset = blob_set()
    spriteset.add(Sprite("blank", ["...", "..."]))
    spriteset.add(Sprite("odd", ["oq"]))
    spriteset.add_anim("walk", ["blob_0", "blob_9", "blob_1"], 7.5)
    spriteset.add_anim("grow", ["blob_0", "odd"], 12)
    return spriteset


class SpriteInfoTest(unittest.TestCase):
    def test_every_key_and_its_value(self):
        sprite = Sprite("dot", [".....", ".oo..", ".ogo.", "....."])
        info = sprite_info(sprite, Palette(PALETTE))
        self.assertEqual(info, {
            "name": "dot",
            "width": 5,
            "height": 4,
            "painted": 5,
            "bbox": [1, 1, 3, 2],
            "colours": [
                {"char": "o", "hex": "#1a1a22", "count": 4},
                {"char": "g", "hex": "#58a84c", "count": 1},
            ],
        })
        self.assertEqual(list(info), ["name", "width", "height", "painted", "bbox", "colours"])
        self.assertEqual(list(info["colours"][0]), ["char", "hex", "count"])

    def test_bbox_is_none_for_an_empty_sprite(self):
        info = sprite_info(Sprite("blank", ["...", "..."]), Palette(PALETTE))
        self.assertIsNone(info["bbox"])
        self.assertEqual(info["painted"], 0)
        self.assertEqual(info["colours"], [])

    def test_colours_are_in_order_of_first_appearance_with_their_counts(self):
        sprite = Sprite("mix", ["..b.", "abba", "caac"])
        palette = Palette({"a": "#111111", "b": "#222222", "c": "#333333"})
        self.assertEqual(sprite_info(sprite, palette)["colours"], [
            {"char": "b", "hex": "#222222", "count": 3},
            {"char": "a", "hex": "#111111", "count": 4},
            {"char": "c", "hex": "#333333", "count": 2},
        ])

    def test_hex_is_none_for_a_character_the_palette_lacks(self):
        info = sprite_info(Sprite("odd", ["oq"]), Palette(PALETTE))
        self.assertEqual(info["colours"], [
            {"char": "o", "hex": "#1a1a22", "count": 1},
            {"char": "q", "hex": None, "count": 1},
        ])

    def test_palette_may_be_a_dict(self):
        for name, rows in (("dot", [".....", ".oo..", ".ogo.", "....."]), ("odd", ["oq"]), ("blank", ["..."])):
            with self.subTest(sprite=name):
                sprite = Sprite(name, rows)
                self.assertEqual(sprite_info(sprite, PALETTE), sprite_info(sprite, Palette(PALETTE)))
        self.assertEqual(sprite_info(Sprite("odd", ["oq"]), PALETTE)["colours"], [
            {"char": "o", "hex": "#1a1a22", "count": 1},
            {"char": "q", "hex": None, "count": 1},
        ])

    def test_colour_in_a_dict_is_given_as_lower_case_hex(self):
        info = sprite_info(Sprite("dot", ["ab"]), {"a": "#ABC", "b": (16, 32, 48)})
        self.assertEqual([colour["hex"] for colour in info["colours"]], ["#aabbcc", "#102030"])

    def test_dict_is_left_as_it_was(self):
        plain = {"o": "#1A1A22"}
        sprite_info(Sprite("odd", ["oq"]), plain)
        self.assertEqual(plain, {"o": "#1A1A22"})

    def test_error_of_a_dict_no_palette_can_be_made_from_passes_through(self):
        for plain in ({"og": "#1a1a22"}, {"o": "black"}, {"o": None}, {" ": "#1a1a22"}):
            with self.subTest(plain=plain):
                with self.assertRaises(PixelRowsError) as expected:
                    Palette(plain)
                with self.assertRaises(PixelRowsError) as caught:
                    sprite_info(Sprite("dot", ["o"]), plain)
                self.assertEqual(str(caught.exception), str(expected.exception))

    def test_what_is_not_a_palette_or_a_dict_is_refused(self):
        sprite = Sprite("dot", ["o"])
        for refused in (None, [("o", "#1a1a22")], {"o", "g"}, "#1a1a22", 7, sprite):
            with self.subTest(refused=refused):
                with self.assertRaises(PixelRowsError) as caught:
                    sprite_info(sprite, refused)
                self.assertEqual(str(caught.exception), "palette must be a Palette or a dict of character to colour")

    def test_palette_is_checked_when_nothing_is_painted(self):
        with self.assertRaises(PixelRowsError):
            sprite_info(Sprite("blank", ["...", "..."]), None)


class AnimInfoTest(unittest.TestCase):
    def test_every_key_and_its_value_for_a_good_clip(self):
        info = anim_info(blob_set(), "blob_idle")
        self.assertEqual(info, {
            "name": "blob_idle",
            "frames": ["blob_0", "blob_1"],
            "fps": 3,
            "seconds": 0.6667,
            "size": [6, 4],
            "painted": [18, 16],
        })
        self.assertEqual(list(info), ["name", "frames", "fps", "seconds", "size", "painted"])

    def test_an_anim_may_be_given_itself_or_by_name(self):
        spriteset = blob_set()
        self.assertEqual(anim_info(spriteset, spriteset.anim("blob_idle")), anim_info(spriteset, "blob_idle"))

    def test_seconds_is_the_duration_rounded_to_4_places(self):
        spriteset = blob_set()
        for frames, fps, seconds in ((2, 3, 0.6667), (3, 7, 0.4286), (4, 10, 0.4), (1, 0.5, 2.0)):
            with self.subTest(frames=frames, fps=fps):
                anim = Anim("clip", ["blob_0"] * frames, fps)
                self.assertEqual(anim_info(spriteset, anim)["seconds"], seconds)

    def test_a_missing_frame_gives_no_size_and_none_for_its_painted(self):
        spriteset = blob_set()
        spriteset.add_anim("walk", ["blob_0", "blob_9", "blob_1"], 10)
        self.assertEqual(anim_info(spriteset, "walk"), {
            "name": "walk",
            "frames": ["blob_0", "blob_9", "blob_1"],
            "fps": 10,
            "seconds": 0.3,
            "size": None,
            "painted": [18, None, 16],
        })

    def test_a_clip_with_every_frame_missing_is_not_refused(self):
        spriteset = SpriteSet(PALETTE)
        spriteset.add_anim("walk", ["a_0", "a_1"], 10)
        info = anim_info(spriteset, "walk")
        self.assertIsNone(info["size"])
        self.assertEqual(info["painted"], [None, None])

    def test_frames_of_different_sizes_give_no_size(self):
        spriteset = blob_set()
        spriteset.add(Sprite("wide", ["ooooooo"] * 4))
        spriteset.add_anim("grow", ["blob_0", "wide"], 10)
        info = anim_info(spriteset, "grow")
        self.assertIsNone(info["size"])
        self.assertEqual(info["painted"], [18, 28])

    def test_an_unknown_anim_name_is_refused(self):
        with self.assertRaises(PixelRowsError) as caught:
            anim_info(blob_set(), "jump")
        self.assertEqual(str(caught.exception), "no anim named 'jump'")


class SetInfoTest(unittest.TestCase):
    def test_every_key_and_its_value(self):
        info = set_info(blob_set())
        self.assertEqual(info, {
            "palette": {"o": "#1a1a22", "g": "#58a84c"},
            "sprites": [
                {
                    "name": "blob_0",
                    "width": 6,
                    "height": 4,
                    "painted": 18,
                    "bbox": [0, 0, 6, 4],
                    "colours": [
                        {"char": "o", "hex": "#1a1a22", "count": 12},
                        {"char": "g", "hex": "#58a84c", "count": 6},
                    ],
                },
                {
                    "name": "blob_1",
                    "width": 6,
                    "height": 4,
                    "painted": 16,
                    "bbox": [0, 1, 6, 3],
                    "colours": [
                        {"char": "o", "hex": "#1a1a22", "count": 12},
                        {"char": "g", "hex": "#7cc86a", "count": 4},
                    ],
                },
            ],
            "anims": [
                {
                    "name": "blob_idle",
                    "frames": ["blob_0", "blob_1"],
                    "fps": 3,
                    "seconds": 0.6667,
                    "size": [6, 4],
                    "painted": [18, 16],
                },
            ],
            "problems": [],
        })
        self.assertEqual(list(info), ["palette", "sprites", "anims", "problems"])

    def test_a_sprites_own_palette_entry_shows_in_its_colours(self):
        spriteset = blob_set()
        spriteset.add(Sprite("eye", ["w"], {"w": "#ffffff"}))
        info = set_info(spriteset)
        self.assertEqual(info["sprites"][0]["colours"][1], {"char": "g", "hex": "#58a84c", "count": 6})
        self.assertEqual(info["sprites"][1]["colours"][1], {"char": "g", "hex": "#7cc86a", "count": 4})
        self.assertEqual(info["sprites"][2]["colours"], [{"char": "w", "hex": "#ffffff", "count": 1}])
        self.assertEqual(info["palette"], PALETTE)

    def test_sprites_and_anims_are_listed_in_the_sets_order(self):
        spriteset = SpriteSet(PALETTE)
        for name in ("zed", "alpha", "mid"):
            spriteset.add(Sprite(name, ["o"]))
        spriteset.add_anim("run", ["zed", "mid"], 10)
        spriteset.add_anim("idle", ["alpha"], 2)
        info = set_info(spriteset)
        self.assertEqual([entry["name"] for entry in info["sprites"]], ["zed", "alpha", "mid"])
        self.assertEqual([entry["name"] for entry in info["anims"]], ["run", "idle"])

    def test_problems_are_those_of_the_set(self):
        spriteset = half_drawn_set()
        info = set_info(spriteset)
        self.assertEqual(info["problems"], spriteset.problems())
        self.assertEqual(info["problems"], [
            "sprite 'odd' uses 'q', which is not in the palette",
            "anim 'walk' names 'blob_9', which is not a sprite",
            "anim 'grow': frame 'odd' is 2x1, the first frame is 6x4",
        ])

    def test_the_whole_result_goes_through_json_and_back_unchanged(self):
        for name, spriteset in (("drawn", blob_set()), ("half drawn", half_drawn_set())):
            with self.subTest(set=name):
                info = set_info(spriteset)
                self.assertEqual(json.loads(json.dumps(info)), info)


if __name__ == "__main__":
    unittest.main()
