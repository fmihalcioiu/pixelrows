import unittest

from pixelrows import checks
from pixelrows.checks import Finding, Options, pixels
from pixelrows.errors import PixelRowsError
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
    def assert_refused(self, message, **options):
        with self.assertRaises(PixelRowsError) as caught:
            Options(**options)
        self.assertEqual(str(caught.exception), message)

    def test_cannot_be_changed(self):
        options = Options()
        with self.assertRaises(AttributeError):
            options.lone_allow = frozenset("e")

    def test_what_is_not_given_has_its_default(self):
        options = Options()
        self.assertIsNone(options.outline)
        self.assertEqual(options.lone_allow, frozenset())
        self.assertIsNone(options.max_colours)
        self.assertEqual(options.pixels_per_colour, 6)
        self.assertEqual(options.frame_slack, 0.15)
        self.assertEqual(options.feet_slack, 1)

    def test_outline_may_be_none_or_any_one_character_that_paints(self):
        for outline in (None, "o", "O", "#", "0", "_", "\u00e9"):
            with self.subTest(outline=outline):
                self.assertEqual(Options(outline=outline).outline, outline)

    def test_outline_that_is_not_one_character_is_refused(self):
        for outline in ("", "og", "ooo", 7, True, ["o"], ("o",)):
            with self.subTest(outline=outline):
                self.assert_refused(
                    f"outline must be one character that is not whitespace and not '.', got {outline!r}",
                    outline=outline,
                )

    def test_outline_of_whitespace_or_a_dot_is_refused(self):
        for outline in (" ", "\t", "\n", "\u00a0", "."):
            with self.subTest(outline=outline):
                self.assert_refused(
                    f"outline must be one character that is not whitespace and not '.', got {outline!r}",
                    outline=outline,
                )

    def test_lone_allow_is_kept_as_a_frozenset_however_it_is_given(self):
        given = ("eg", ["e", "g"], ("g", "e"), {"e", "g"}, frozenset("eg"), (ch for ch in "eg"), "egge")
        for lone_allow in given:
            with self.subTest(lone_allow=lone_allow):
                kept = Options(lone_allow=lone_allow).lone_allow
                self.assertIsInstance(kept, frozenset)
                self.assertEqual(kept, frozenset({"e", "g"}))

    def test_lone_allow_may_be_empty(self):
        for lone_allow in ("", [], (), set(), frozenset()):
            with self.subTest(lone_allow=lone_allow):
                self.assertEqual(Options(lone_allow=lone_allow).lone_allow, frozenset())

    def test_lone_allow_may_hold_any_single_character(self):
        self.assertEqual(Options(lone_allow=". \u00e9").lone_allow, frozenset({".", " ", "\u00e9"}))

    def test_lone_allow_that_is_not_single_characters_is_refused(self):
        for lone_allow in (None, 7, True, ["eg"], ["e", ""], ["e", 7], [["e"]], b"eg"):
            with self.subTest(lone_allow=lone_allow):
                self.assert_refused(
                    f"lone_allow must be a string or an iterable of single characters, got {lone_allow!r}",
                    lone_allow=lone_allow,
                )

    def test_max_colours_may_be_none_or_a_whole_number_of_1_or_more(self):
        for max_colours in (None, 1, 2, 16, 1000):
            with self.subTest(max_colours=max_colours):
                self.assertEqual(Options(max_colours=max_colours).max_colours, max_colours)

    def test_max_colours_below_1_or_not_a_whole_number_is_refused(self):
        for max_colours in (0, -1, -16, 1.5, 4.0, "4", True, False, [4]):
            with self.subTest(max_colours=max_colours):
                self.assert_refused(
                    f"max_colours must be a whole number of 1 or more, got {max_colours!r}",
                    max_colours=max_colours,
                )

    def test_pixels_per_colour_may_be_any_whole_number_of_1_or_more(self):
        for pixels_per_colour in (1, 2, 6, 1000):
            with self.subTest(pixels_per_colour=pixels_per_colour):
                self.assertEqual(Options(pixels_per_colour=pixels_per_colour).pixels_per_colour, pixels_per_colour)

    def test_pixels_per_colour_below_1_or_not_a_whole_number_is_refused(self):
        for pixels_per_colour in (0, -1, -6, 0.5, 6.0, "6", None, True, False):
            with self.subTest(pixels_per_colour=pixels_per_colour):
                self.assert_refused(
                    f"pixels_per_colour must be a whole number of 1 or more, got {pixels_per_colour!r}",
                    pixels_per_colour=pixels_per_colour,
                )

    def test_frame_slack_may_be_any_finite_number_of_0_or_more(self):
        for frame_slack in (0, 0.0, 0.15, 1, 2.5, 1000):
            with self.subTest(frame_slack=frame_slack):
                self.assertEqual(Options(frame_slack=frame_slack).frame_slack, frame_slack)

    def test_frame_slack_below_0_or_not_a_finite_number_is_refused(self):
        refused = (-0.01, -1, -1.0, float("nan"), float("inf"), float("-inf"), 10 ** 400, "0.15", None, True, False)
        for frame_slack in refused:
            with self.subTest(frame_slack=frame_slack):
                self.assert_refused(
                    f"frame_slack must be a finite number of 0 or more, got {frame_slack!r}",
                    frame_slack=frame_slack,
                )

    def test_feet_slack_may_be_any_whole_number_of_0_or_more(self):
        for feet_slack in (0, 1, 2, 1000):
            with self.subTest(feet_slack=feet_slack):
                self.assertEqual(Options(feet_slack=feet_slack).feet_slack, feet_slack)

    def test_feet_slack_below_0_or_not_a_whole_number_is_refused(self):
        for feet_slack in (-1, -5, 0.5, 1.0, "1", None, True, False):
            with self.subTest(feet_slack=feet_slack):
                self.assert_refused(
                    f"feet_slack must be a whole number of 0 or more, got {feet_slack!r}",
                    feet_slack=feet_slack,
                )

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            Options(pixels_per_colour=0)

    def test_equal_when_every_option_matches_however_lone_allow_was_given(self):
        self.assertEqual(Options(outline="o", lone_allow="eg"), Options(outline="o", lone_allow=["g", "e"]))
        self.assertEqual(hash(Options(lone_allow="eg")), hash(Options(lone_allow=frozenset("ge"))))
        self.assertNotEqual(Options(lone_allow="eg"), Options(lone_allow="e"))


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

    def test_lone_allow_may_be_given_as_a_string(self):
        face = Sprite("face", ["ooooo", "oeoxo", "ooooo"])
        self.assertEqual(found(face, lone_allow="ex"), [])
        self.assertEqual(found(face, lone_allow="e"), [Finding("lone_pixel", "face", "1 lone pixel", ((3, 1),))])

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

    def test_max_colours_of_1_allows_one_colour(self):
        self.assertEqual(found(Sprite("bar", ["aaaa"]), max_colours=1), [])
        self.assert_flagged("uses 2 colours, 1 allowed for 4 painted pixels", Sprite("bar", ["aabb"]), max_colours=1)

    def test_pixels_per_colour_sets_how_many_pixels_allow_a_colour(self):
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "ddddee"])
        self.assertEqual(found(flag, pixels_per_colour=5), [])
        flag = Sprite("flag", ["aaaaaa", "bbbbbb", "cccccc", "dddddd"])
        self.assert_flagged("uses 4 colours, 3 allowed for 24 painted pixels", flag, pixels_per_colour=8)

    def test_pixels_per_colour_of_1_allows_a_colour_for_every_pixel(self):
        chip = Sprite("chip", ["abcd", "efgh"])
        self.assertEqual(found(chip, pixels_per_colour=1, lone_allow="abcdefgh"), [])
        self.assert_flagged(
            "uses 8 colours, 4 allowed for 8 painted pixels", chip, pixels_per_colour=2, lone_allow="abcdefgh"
        )

    def test_pixels_per_colour_of_0_is_refused_before_anything_is_divided(self):
        with self.assertRaises(PixelRowsError) as caught:
            found(Sprite("chip", ["aabbcc"]), pixels_per_colour=0)
        self.assertEqual(str(caught.exception), "pixels_per_colour must be a whole number of 1 or more, got 0")

    def test_nothing_painted_is_nothing_found(self):
        self.assertEqual(found(Sprite("blank", ["..", ".."]), max_colours=1), [])

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
