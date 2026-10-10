import unittest

from pixelrows import checks
from pixelrows.checks import Finding, Options, outline
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
    return outline.check(set_of(*sprites), Options(**options))


class OutlineGapTest(unittest.TestCase):
    def assert_flagged(self, message, points, sprite, **options):
        self.assertEqual(found(sprite, **options), [Finding("outline_gap", sprite.name, message, points)])

    def test_edge_cells_that_are_not_the_outline_are_flagged(self):
        blob = Sprite("blob", ["..gg..", ".oggo.", "oggggo", "oooooo"])
        self.assert_flagged("2 of 12 edge pixels are not the outline 'o'", ((2, 0), (3, 0)), blob, outline="o")

    def test_the_message_says_is_for_one_gap_and_are_for_more(self):
        blob = Sprite("blob", ["..og..", ".oggo.", "oggggo", "oooooo"])
        self.assert_flagged("1 of 12 edge pixels is not the outline 'o'", ((3, 0),), blob, outline="o")
        blob = Sprite("blob", ["..gg..", ".oggo.", "oggggo", "ooogoo"])
        points = ((2, 0), (3, 0), (3, 3))
        self.assert_flagged("3 of 12 edge pixels are not the outline 'o'", points, blob, outline="o")

    def test_a_sprite_outlined_all_the_way_round_is_not_flagged(self):
        blob = Sprite("blob", ["..oo..", ".oggo.", "oggggo", "oooooo"])
        self.assertEqual(found(blob, outline="o"), [])

    def test_skipped_without_an_outline_character(self):
        blob = Sprite("blob", ["..gg..", ".oggo.", "oggggo", "oooooo"])
        self.assertEqual(found(blob), [])

    def test_skipped_for_a_sprite_that_does_not_use_the_outline_character(self):
        puff = Sprite("puff", [".gg.", "gggg", ".gg."])
        self.assertEqual(found(puff, outline="o"), [])

    def test_the_border_of_the_sprite_counts_as_an_edge(self):
        crate = Sprite("crate", ["ogoo", "oggg", "oooo"])
        self.assert_flagged("2 of 10 edge pixels are not the outline 'o'", ((1, 0), (3, 1)), crate, outline="o")

    def test_an_empty_cell_inside_the_sprite_makes_edges(self):
        ring = Sprite("ring", ["ooooo", "og.go", "ooooo"])
        self.assert_flagged("2 of 14 edge pixels are not the outline 'o'", ((1, 1), (3, 1)), ring, outline="o")

    def test_an_empty_cell_at_a_corner_does_not_make_an_edge(self):
        tile = Sprite("tile", [".oo", "ogo", "ooo"])
        self.assertEqual(found(tile, outline="o"), [])

    def test_the_message_counts_the_gaps_among_the_edge_cells_only(self):
        slab = Sprite("slab", ["ggggg", "ogggo", "ogggo", "ooooo"])
        points = ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))
        self.assert_flagged("5 of 14 edge pixels are not the outline 'o'", points, slab, outline="o")

    def test_points_are_listed_row_by_row(self):
        strip = Sprite("strip", ["ooog", "gooo"])
        self.assert_flagged("2 of 8 edge pixels are not the outline 'o'", ((3, 0), (0, 1)), strip, outline="o")

    def test_the_outline_is_the_character_the_options_name(self):
        crate = Sprite("crate", ["kgk", "kgg", "kkk"])
        self.assert_flagged("2 of 8 edge pixels are not the outline 'k'", ((1, 0), (2, 1)), crate, outline="k")
        points = ((0, 0), (2, 0), (0, 1), (0, 2), (1, 2), (2, 2))
        self.assert_flagged("6 of 8 edge pixels are not the outline 'g'", points, crate, outline="g")

    def test_one_finding_a_sprite_in_the_order_of_the_set(self):
        strip = Sprite("strip", ["ooog", "gooo"])
        tile = Sprite("tile", ["ooo", "ogo", "ooo"])
        puff = Sprite("puff", [".gg.", "gggg", ".gg."])
        crate = Sprite("crate", ["ogoo", "oggg", "oooo"])
        self.assertEqual(
            found(strip, tile, puff, crate, outline="o"),
            [
                Finding("outline_gap", "strip", "2 of 8 edge pixels are not the outline 'o'", ((3, 0), (0, 1))),
                Finding("outline_gap", "crate", "2 of 10 edge pixels are not the outline 'o'", ((1, 0), (3, 1))),
            ],
        )

    def test_nothing_painted_is_nothing_found(self):
        self.assertEqual(found(Sprite("blank", ["..", ".."]), outline="o"), [])
        self.assertEqual(found(outline="o"), [])

    def test_an_outline_that_is_no_character_to_paint_with_is_refused(self):
        crate = Sprite("crate", ["ogoo", "oggg", "oooo"])
        for refused in ("", "og", " ", "."):
            with self.subTest(outline=refused):
                with self.assertRaises(PixelRowsError) as caught:
                    found(crate, outline=refused)
                self.assertEqual(
                    str(caught.exception),
                    f"outline must be one character that is not whitespace and not '.', got {refused!r}",
                )


class RunTest(unittest.TestCase):
    def test_run_finds_the_rule_and_hands_it_the_options(self):
        spriteset = set_of(Sprite("blob", ["..gg..", ".oggo.", "oggggo", "oooooo"]))
        gap = Finding("outline_gap", "blob", "2 of 12 edge pixels are not the outline 'o'", ((2, 0), (3, 0)))
        self.assertIn(gap, checks.run(spriteset, Options(outline="o")))
        self.assertNotIn(gap, checks.run(spriteset))


if __name__ == "__main__":
    unittest.main()
