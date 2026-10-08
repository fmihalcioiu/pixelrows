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


class RunTest(unittest.TestCase):
    def test_run_finds_the_rule_and_hands_it_the_options(self):
        spriteset = set_of(Sprite("gem", ["ooo", "oxo", "ooo"]))
        lone = Finding("lone_pixel", "gem", "1 lone pixel", ((1, 1),))
        self.assertIn(lone, checks.run(spriteset))
        self.assertNotIn(lone, checks.run(spriteset, Options(lone_allow=frozenset("x"))))


if __name__ == "__main__":
    unittest.main()
