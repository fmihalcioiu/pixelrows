import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.font import FONT, GLYPH_H, GLYPH_W, draw_text, text_width
from pixelrows.image import Image

CAPITALS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
MARKS = ".,:;!?'\"-_+=/\\()[]<>%#*&"
LISTED = CAPITALS + DIGITS + " " + MARKS

# Characters the font has no glyph for.
UNKNOWN = "~@{}|^`$\u00e9\n\t"

BLACK = "#000000"
WHITE = "#ffffff"
RED = "#ff0000"

CLEAR = (0, 0, 0, 0)
INK = (255, 255, 255, 255)

BLANK_ROW = "." * 5


def picture(image, ink=INK):
    """The image as rows of text: '#' where a pixel is `ink` and '.' anywhere else."""
    return [
        "".join("#" if image.get(x, y) == ink else "." for x in range(image.width))
        for y in range(image.height)
    ]


def written(text, scale=1):
    """`text` drawn in white on a black image that it just fills."""
    image = Image(text_width(text, scale), GLYPH_H * scale, BLACK)
    draw_text(image, text, 0, 0, WHITE, scale)
    return image


def cells_apart(a, b):
    """In how many cells the glyphs of two characters differ."""
    return sum(
        cell_a != cell_b
        for row_a, row_b in zip(FONT[a], FONT[b])
        for cell_a, cell_b in zip(row_a, row_b)
    )


def mirrored(ch):
    """The glyph of `ch` turned left to right."""
    return tuple(row[::-1] for row in FONT[ch])


def inside(ch):
    """The glyph of `ch` without its outermost rows and columns."""
    return [row[1:4] for row in FONT[ch][1:6]]


class GlyphTableTest(unittest.TestCase):
    def test_a_glyph_is_five_wide_and_seven_high(self):
        self.assertEqual((GLYPH_W, GLYPH_H), (5, 7))

    def test_every_glyph_is_seven_rows_of_five(self):
        for ch, glyph in FONT.items():
            with self.subTest(ch=ch):
                self.assertIsInstance(glyph, tuple)
                self.assertEqual(len(glyph), GLYPH_H)
                for row in glyph:
                    self.assertIsInstance(row, str)
                    self.assertEqual(len(row), GLYPH_W)

    def test_every_glyph_uses_only_ink_and_blank(self):
        for ch, glyph in FONT.items():
            with self.subTest(ch=ch):
                self.assertLessEqual(set("".join(glyph)), {"#", "."})

    def test_every_listed_character_has_a_glyph(self):
        self.assertEqual(len(set(LISTED)), 61)
        for ch in LISTED:
            with self.subTest(ch=ch):
                self.assertIn(ch, FONT)

    def test_no_other_character_has_a_glyph(self):
        self.assertEqual(sorted(FONT), sorted(LISTED))

    def test_no_two_characters_share_a_glyph(self):
        owner = {}
        for ch, glyph in FONT.items():
            with self.subTest(ch=ch):
                self.assertNotIn(glyph, owner)
            owner[glyph] = ch

    def test_space_is_the_only_blank_glyph(self):
        blank = (BLANK_ROW,) * 7
        self.assertEqual(FONT[" "], blank)
        self.assertEqual([ch for ch, glyph in FONT.items() if glyph == blank], [" "])


class GlyphShapeTest(unittest.TestCase):
    def test_capitals_and_digits_are_seven_rows_tall(self):
        for ch in CAPITALS + DIGITS:
            with self.subTest(ch=ch):
                self.assertIn("#", FONT[ch][0])
                self.assertIn("#", FONT[ch][6])

    def test_strokes_are_one_pixel_wide(self):
        # A stroke two pixels thick would hold a 2 by 2 block of ink. Only the
        # two dots of the per cent sign are such blocks.
        for ch, glyph in FONT.items():
            blocks = [
                (x, y)
                for y in range(GLYPH_H - 1)
                for x in range(GLYPH_W - 1)
                if glyph[y][x:x + 2] == glyph[y + 1][x:x + 2] == "##"
            ]
            with self.subTest(ch=ch):
                self.assertEqual(blocks, [(0, 0), (3, 5)] if ch == "%" else [])

    def test_round_glyphs_have_cut_corners(self):
        for ch in "CGOQS0689":
            top, bottom = FONT[ch][0], FONT[ch][6]
            with self.subTest(ch=ch):
                self.assertEqual(top[0] + top[4] + bottom[0], "...")
                # The tail of Q ends in the corner the others leave empty.
                self.assertEqual(bottom[4], "#" if ch == "Q" else ".")

    def test_look_alikes_differ_in_three_cells_or_more(self):
        for a, b in ("0O", "1I", "5S", "8B", "2Z", "UV", "DO"):
            with self.subTest(a=a, b=b):
                self.assertGreaterEqual(cells_apart(a, b), 3)

    def test_zero_has_a_stroke_inside_and_o_is_empty(self):
        self.assertEqual(inside("O"), ["..."] * 5)
        self.assertEqual(inside("0"), ["...", "..#", ".#.", "#..", "..."])

    def test_full_stop_comma_and_underscore_sit_at_the_bottom(self):
        for ch, rows_used in ((".", 1), (",", 2), ("_", 1)):
            with self.subTest(ch=ch):
                self.assertEqual(FONT[ch][:7 - rows_used], (BLANK_ROW,) * (7 - rows_used))
                self.assertIn("#", FONT[ch][6])

    def test_hyphen_and_equals_sit_in_the_middle(self):
        self.assertEqual([y for y, row in enumerate(FONT["-"]) if "#" in row], [3])
        self.assertEqual([y for y, row in enumerate(FONT["="]) if "#" in row], [2, 4])

    def test_quotes_sit_at_the_top(self):
        for ch in "'\"":
            with self.subTest(ch=ch):
                self.assertIn("#", FONT[ch][0])
                self.assertEqual(FONT[ch][2:], (BLANK_ROW,) * 5)

    def test_brackets_and_slashes_mirror_each_other(self):
        for left, right in ("()", "[]", "<>", "/\\"):
            with self.subTest(left=left, right=right):
                self.assertEqual(mirrored(left), FONT[right])


class TextWidthTest(unittest.TestCase):
    def test_empty_text_is_nothing_wide(self):
        self.assertEqual(text_width(""), 0)
        self.assertEqual(text_width("", 4), 0)

    def test_one_glyph_is_five_wide(self):
        self.assertEqual(text_width("A"), 5)

    def test_glyphs_sit_six_apart(self):
        for count in range(1, 12):
            with self.subTest(count=count):
                self.assertEqual(text_width("A" * count), count * 6 - 1)

    def test_scale_multiplies_the_width(self):
        self.assertEqual(text_width("A", 3), 15)
        self.assertEqual(text_width("AB", 2), 22)
        self.assertEqual(text_width("12X16", 4), 116)

    def test_every_character_counts_glyph_or_not(self):
        self.assertEqual(text_width("a b"), 17)
        self.assertEqual(text_width("   "), 17)
        self.assertEqual(text_width(UNKNOWN), len(UNKNOWN) * 6 - 1)

    def test_scale_must_be_a_whole_number_of_one_or_more(self):
        for bad in (0, -1, 1.5, 2.0, "2", None, True):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "scale"):
                    text_width("AB", bad)
                with self.assertRaisesRegex(PixelRowsError, "scale"):
                    text_width("", bad)

    def test_text_must_be_a_string(self):
        for bad in (None, 12, b"AB", ["A", "B"]):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "text"):
                    text_width(bad)


class DrawTextTest(unittest.TestCase):
    def test_i_is_drawn_at_known_pixels(self):
        self.assertEqual(picture(written("I")), [
            ".###.",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            ".###.",
        ])

    def test_l_is_drawn_at_known_pixels(self):
        self.assertEqual(picture(written("L")), [
            "#....",
            "#....",
            "#....",
            "#....",
            "#....",
            "#....",
            "#####",
        ])

    def test_t_is_drawn_at_known_pixels(self):
        self.assertEqual(picture(written("T")), [
            "#####",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
        ])

    def test_every_glyph_is_drawn_as_its_rows(self):
        for ch, glyph in FONT.items():
            with self.subTest(ch=ch):
                self.assertEqual(picture(written(ch)), list(glyph))

    def test_draws_from_the_top_left_corner(self):
        image = Image(9, 10, BLACK)
        draw_text(image, "L", 3, 2)
        self.assertEqual(picture(image), [
            ".........",
            ".........",
            "...#.....",
            "...#.....",
            "...#.....",
            "...#.....",
            "...#.....",
            "...#.....",
            "...#####.",
            ".........",
        ])

    def test_glyphs_are_drawn_six_apart(self):
        self.assertEqual(picture(written("LIT")), [
            "#......###..#####",
            "#.......#.....#..",
            "#.......#.....#..",
            "#.......#.....#..",
            "#.......#.....#..",
            "#.......#.....#..",
            "#####..###....#..",
        ])

    def test_lower_case_draws_what_upper_case_draws(self):
        for ch in CAPITALS:
            with self.subTest(ch=ch):
                self.assertEqual(written(ch.lower()), written(ch))
        self.assertEqual(written("Lazy dog, 10 fps"), written("LAZY DOG, 10 FPS"))

    def test_a_character_without_a_glyph_is_drawn_as_a_blank(self):
        for ch in UNKNOWN:
            with self.subTest(ch=ch):
                self.assertEqual(written(ch), written(" "))
                self.assertEqual(written("T" + ch + "L"), written("T L"))

    def test_returns_the_x_just_past_the_last_glyph(self):
        image = Image(40, 9, BLACK)
        self.assertEqual(draw_text(image, "A", 0, 0), 5)
        self.assertEqual(draw_text(image, "ABC", 2, 1), 2 + 17)
        self.assertEqual(draw_text(image, "a~ ", 7, 1), 7 + 17)
        self.assertEqual(draw_text(image, "AB", -30, 0), -30 + 11)
        self.assertEqual(draw_text(image, "AB", 100, 100), 100 + 11)

    def test_returned_x_follows_the_scale(self):
        image = Image(40, 9, BLACK)
        for scale in (1, 2, 3, 8):
            with self.subTest(scale=scale):
                self.assertEqual(draw_text(image, "ABCD", 3, 0, WHITE, scale), 3 + text_width("ABCD", scale))
                self.assertEqual(draw_text(image, "ABCD", 3, 0, WHITE, scale), 3 + 23 * scale)

    def test_empty_text_draws_nothing_and_returns_x(self):
        image = Image(8, 8, BLACK)
        self.assertEqual(draw_text(image, "", 3, 2), 3)
        self.assertEqual(draw_text(image, "", 3, 2, WHITE, 4), 3)
        self.assertEqual(image, Image(8, 8, BLACK))

    def test_scale_makes_each_pixel_of_ink_a_block(self):
        for scale in (1, 2, 3, 5):
            with self.subTest(scale=scale):
                self.assertEqual(written("IT?", scale), written("IT?").scaled(scale))

    def test_scaled_text_starts_at_the_same_corner(self):
        image = Image(12, 16, BLACK)
        draw_text(image, "L", 1, 1, WHITE, 2)
        expected = Image(12, 16, BLACK)
        expected.blit(written("L", 2), 1, 1)
        self.assertEqual(image, expected)
        self.assertEqual(image.get(1, 1), INK)
        self.assertEqual(image.get(0, 1), (0, 0, 0, 255))
        self.assertEqual(image.get(10, 14), INK)
        self.assertEqual(image.get(11, 14), (0, 0, 0, 255))

    def test_default_colour_is_white(self):
        image = Image(5, 7, BLACK)
        draw_text(image, "T", 0, 0)
        self.assertEqual(image, written("T"))
        self.assertEqual(image.colours(), [INK, (0, 0, 0, 255)])

    def test_colour_as_hex_or_numbers(self):
        for colour in (RED, "#f00", (255, 0, 0)):
            with self.subTest(colour=colour):
                image = Image(5, 7, BLACK)
                draw_text(image, "T", 0, 0, colour)
                self.assertEqual(picture(image, (255, 0, 0, 255)), list(FONT["T"]))
                self.assertEqual(image.colours(), [(255, 0, 0, 255), (0, 0, 0, 255)])

    def test_leaves_what_is_underneath_where_there_is_no_ink(self):
        image = Image(17, 7)
        draw_text(image, "X Y", 0, 0, RED)
        self.assertEqual(picture(image, (255, 0, 0, 255)), picture(written("X Y")))
        self.assertEqual(image.colours(), [(255, 0, 0, 255), CLEAR])

    def test_what_falls_outside_the_image_is_dropped(self):
        whole = Image(60, 40, BLACK)
        draw_text(whole, "QW", 20, 10, WHITE, 2)
        for left, top in ((17, 8), (25, 13), (38, 20), (10, 2), (20, 10)):
            with self.subTest(left=left, top=top):
                part = Image(9, 8, BLACK)
                draw_text(part, "QW", 20 - left, 10 - top, WHITE, 2)
                for y in range(part.height):
                    for x in range(part.width):
                        self.assertEqual(part.get(x, y), whole.get(left + x, top + y))

    def test_text_wholly_outside_changes_nothing(self):
        for x, y in ((-40, 0), (0, -20), (9, 0), (0, 8), (500, 500)):
            with self.subTest(x=x, y=y):
                image = Image(9, 8, BLACK)
                self.assertEqual(draw_text(image, "QW", x, y), x + 11)
                self.assertEqual(image, Image(9, 8, BLACK))

    def test_scale_must_be_a_whole_number_of_one_or_more(self):
        for bad in (0, -1, 1.5, 2.0, "2", None, True):
            with self.subTest(bad=bad):
                image = Image(12, 8, BLACK)
                with self.assertRaisesRegex(PixelRowsError, "scale"):
                    draw_text(image, "AB", 0, 0, WHITE, bad)
                self.assertEqual(image, Image(12, 8, BLACK))

    def test_colour_must_be_a_colour(self):
        for bad in ("white", "#12345", (256, 0, 0), (1, 2), None):
            with self.subTest(bad=bad):
                image = Image(12, 8, BLACK)
                with self.assertRaises(PixelRowsError):
                    draw_text(image, "AB", 0, 0, bad)
                with self.assertRaises(PixelRowsError):
                    draw_text(image, "", 0, 0, bad)
                self.assertEqual(image, Image(12, 8, BLACK))

    def test_text_must_be_a_string(self):
        for bad in (None, 12, b"AB", ["A", "B"]):
            with self.subTest(bad=bad):
                image = Image(12, 8, BLACK)
                with self.assertRaisesRegex(PixelRowsError, "text"):
                    draw_text(image, bad, 0, 0)
                self.assertEqual(image, Image(12, 8, BLACK))


if __name__ == "__main__":
    unittest.main()
