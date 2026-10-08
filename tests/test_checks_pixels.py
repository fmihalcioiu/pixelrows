import unittest

from pixelrows import checks
from pixelrows.checks import Finding, Options, pixels
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet


def set_of(*sprites):
    """A set holding those sprites, in that order."""
    spriteset = SpriteSet()
    for sprite in sprites:
        spriteset.add(sprite)
    return spriteset


def found(*sprites, **options):
    """What the module finds in a set of those sprites, on those options."""
    return pixels.check(set_of(*sprites), Options(**options))


class FindingTest(unittest.TestCase):
    def test_fields_are_kept(self):
        finding = Finding("lone_pixel", "hat", "2 lone pixels", ((1, 0), (3, 2)))
        self.assertEqual(finding.rule, "lone_pixel")
        self.assertEqual(finding.target, "hat")
        self.assertEqual(finding.message, "2 lone pixels")
        self.assertEqual(finding.points, ((1, 0), (3, 2)))

    def test_points_are_empty_when_none_are_given(self):
        self.assertEqual(Finding("a_rule", "hat", "a message").points, ())

    def test_to_dict_is_plain_data_with_each_point_a_list(self):
        finding = Finding("lone_pixel", "hat", "2 lone pixels", ((1, 0), (3, 2)))
        self.assertEqual(
            finding.to_dict(),
            {"rule": "lone_pixel", "target": "hat", "message": "2 lone pixels", "points": [[1, 0], [3, 2]]},
        )
        self.assertEqual(list(finding.to_dict()), ["rule", "target", "message", "points"])

    def test_to_dict_without_points_has_an_empty_list(self):
        self.assertEqual(Finding("a_rule", "hat", "a message").to_dict()["points"], [])

    def test_equal_when_every_field_matches(self):
        finding = Finding("a_rule", "hat", "a message", ((1, 0),))
        self.assertEqual(finding, Finding("a_rule", "hat", "a message", ((1, 0),)))
        self.assertNotEqual(finding, Finding("a_rule", "hat", "a message"))
        self.assertNotEqual(finding, Finding("a_rule", "cap", "a message", ((1, 0),)))

    def test_cannot_be_changed(self):
        finding = Finding("a_rule", "hat", "a message")
        with self.assertRaises(AttributeError):
            finding.message = "another message"


class OptionsTest(unittest.TestCase):
    def test_cannot_be_changed(self):
        options = Options()
        with self.assertRaises(AttributeError):
            options.lone_allow = frozenset("e")


class LonePixelTest(unittest.TestCase):
    def test_a_cell_with_none_of_its_character_around_it_is_flagged(self):
        gem = Sprite("gem", ["ooo", "oxo", "ooo"])
        self.assertEqual(found(gem), [Finding("lone_pixel", "gem", "1 lone pixel", ((1, 1),))])

    def test_cells_beside_or_below_one_of_their_own_are_not_flagged(self):
        self.assertEqual(found(Sprite("bars", ["oooo", "xxxx"])), [])
        self.assertEqual(found(Sprite("posts", ["ox", "ox"])), [])

    def test_a_cell_joined_only_diagonally_is_not_lone(self):
        self.assertEqual(found(Sprite("down", ["x..", ".x.", "..x"])), [])
        self.assertEqual(found(Sprite("up", ["..x", ".x.", "x.."])), [])

    def test_a_neighbour_of_another_character_does_not_join(self):
        tile = Sprite("tile", ["xo", "oo"])
        self.assertEqual(found(tile), [Finding("lone_pixel", "tile", "1 lone pixel", ((0, 0),))])

    def test_two_of_a_character_with_a_gap_between_are_both_lone(self):
        pair = Sprite("pair", ["x.x"])
        self.assertEqual(found(pair), [Finding("lone_pixel", "pair", "2 lone pixels", ((0, 0), (2, 0)))])

    def test_a_cell_on_the_border_is_lone_with_nothing_past_the_border_to_join_it(self):
        corners = Sprite("corners", ["x..", "...", "..x"])
        self.assertEqual(found(corners), [Finding("lone_pixel", "corners", "2 lone pixels", ((0, 0), (2, 2)))])
        dot = Sprite("dot", ["x"])
        self.assertEqual(found(dot), [Finding("lone_pixel", "dot", "1 lone pixel", ((0, 0),))])

    def test_points_are_listed_row_by_row(self):
        sparks = Sprite("sparks", ["...a", "a...", "..a."])
        self.assertEqual(found(sparks), [Finding("lone_pixel", "sparks", "3 lone pixels", ((3, 0), (0, 1), (2, 2)))])

    def test_lone_allow_lets_its_characters_stand_alone(self):
        face = Sprite("face", ["ooooo", "oeoeo", "ooooo"])
        self.assertEqual(found(face), [Finding("lone_pixel", "face", "2 lone pixels", ((1, 1), (3, 1)))])
        self.assertEqual(found(face, lone_allow=frozenset("e")), [])

    def test_lone_allow_lets_no_other_character_off(self):
        face = Sprite("face", ["ooooo", "oeoxo", "ooooo"])
        self.assertEqual(
            found(face, lone_allow=frozenset("e")),
            [Finding("lone_pixel", "face", "1 lone pixel", ((3, 1),))],
        )

    def test_one_finding_a_sprite_in_the_order_of_the_set(self):
        pair = Sprite("pair", ["x.x"])
        bar = Sprite("bar", ["oo"])
        dot = Sprite("dot", ["x"])
        self.assertEqual(
            found(pair, bar, dot),
            [
                Finding("lone_pixel", "pair", "2 lone pixels", ((0, 0), (2, 0))),
                Finding("lone_pixel", "dot", "1 lone pixel", ((0, 0),)),
            ],
        )

    def test_nothing_painted_is_nothing_found(self):
        self.assertEqual(found(Sprite("blank", ["..", ".."])), [])
        self.assertEqual(found(), [])


class ColourCountTest(unittest.TestCase):
    def assert_flagged(self, message, sprite, **options):
        self.assertEqual(found(sprite, **options), [Finding("colour_count", sprite.name, message)])

    def test_as_many_colours_as_the_size_allows_are_not_flagged(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "dddddd"])
        self.assertEqual(found(flag), [])

    def test_one_colour_more_than_the_size_allows_is_flagged(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "ddddee"])
        self.assert_flagged("uses 5 colours, 4 allowed for 24 painted pixels", flag)

    def test_the_finding_has_no_points(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "ddddee"])
        self.assertEqual(found(flag)[0].points, ())

    def test_a_part_of_a_share_of_pixels_allows_a_whole_colour(self):
        quilt = Sprite("quilt", ["aaaaa", "bbbbb", "ccccc", "ddddd", "eeeee"])
        self.assertEqual(found(quilt), [])
        quilt = Sprite("quilt", ["aaaaa", "bbbbb", "ccccc", "ddddd", "eeeff"])
        self.assert_flagged("uses 6 colours, 5 allowed for 25 painted pixels", quilt)

    def test_only_painted_cells_count_towards_the_size(self):
        steps = Sprite("steps", ["aaaaaa", "bbbbbb", "ccc...", "ddd..."])
        self.assert_flagged("uses 4 colours, 3 allowed for 18 painted pixels", steps)

    def test_three_colours_are_allowed_however_small_the_sprite(self):
        chip = Sprite("chip", ["aabbcc"])
        self.assertEqual(found(chip), [])
        chip = Sprite("chip", ["aabbccdd"])
        self.assert_flagged("uses 4 colours, 3 allowed for 8 painted pixels", chip)

    def test_max_colours_takes_the_place_of_the_size_rule(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "dddddd"])
        self.assert_flagged("uses 4 colours, 3 allowed for 24 painted pixels", flag, max_colours=3)
        chip = Sprite("chip", ["aabbccdd"])
        self.assertEqual(found(chip, max_colours=4), [])

    def test_max_colours_may_be_fewer_than_three(self):
        chip = Sprite("chip", ["aabbcc"])
        self.assert_flagged("uses 3 colours, 2 allowed for 6 painted pixels", chip, max_colours=2)

    def test_pixels_per_colour_sets_how_many_pixels_allow_a_colour(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "ddddee"])
        self.assertEqual(found(flag, pixels_per_colour=5), [])
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "dddddd"])
        self.assert_flagged("uses 4 colours, 3 allowed for 24 painted pixels", flag, pixels_per_colour=8)

    def test_nothing_painted_is_nothing_found(self):
        self.assertEqual(found(Sprite("blank", ["..", ".."]), max_colours=0), [])

    def test_findings_come_sprite_by_sprite_with_the_lone_pixels_first(self):
        scrap = Sprite("scrap", ["aabb", "ccdx"])
        chip = Sprite("chip", ["aabbcc"])
        patch = Sprite("patch", ["aabb", "ccdd", "...x"])
        self.assertEqual(
            found(scrap, chip, patch),
            [
                Finding("lone_pixel", "scrap", "2 lone pixels", ((2, 1), (3, 1))),
                Finding("colour_count", "scrap", "uses 5 colours, 3 allowed for 8 painted pixels"),
                Finding("lone_pixel", "patch", "1 lone pixel", ((3, 2),)),
                Finding("colour_count", "patch", "uses 5 colours, 3 allowed for 9 painted pixels"),
            ],
        )


class RunTest(unittest.TestCase):
    def test_run_finds_the_rule_and_hands_it_the_options(self):
        spriteset = set_of(Sprite("gem", ["ooo", "oxo", "ooo"]))
        lone = Finding("lone_pixel", "gem", "1 lone pixel", ((1, 1),))
        self.assertIn(lone, checks.run(spriteset))
        self.assertNotIn(lone, checks.run(spriteset, Options(lone_allow=frozenset("x"))))


if __name__ == "__main__":
    unittest.main()
