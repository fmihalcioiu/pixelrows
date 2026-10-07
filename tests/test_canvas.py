import unittest

from pixelrows.canvas import Canvas
from pixelrows.errors import PixelRowsError
from pixelrows.palette import Palette
from pixelrows.sprite import Sprite

BLOB = ["..oo..", ".oggo.", "oggggo", "oooooo"]

LETTERS = ["abc", "def", "ghi"]

# Every drawing method that takes a character, drawing inside a canvas of 3 by 3.
WITH_A_CHARACTER = (
    ("px", lambda canvas, ch: canvas.px(1, 1, ch)),
    ("rect", lambda canvas, ch: canvas.rect(0, 0, 2, 2, ch)),
    ("line", lambda canvas, ch: canvas.line(0, 0, 2, 2, ch)),
    ("outline", lambda canvas, ch: canvas.outline(ch)),
)


class CanvasMakingTest(unittest.TestCase):
    def assert_refused(self, message, *args):
        with self.assertRaises(PixelRowsError) as caught:
            Canvas(*args)
        self.assertEqual(str(caught.exception), message)

    def test_starts_all_dots(self):
        self.assertEqual(Canvas(4, 3).rows(), ["....", "....", "...."])

    def test_width_and_height_are_kept(self):
        canvas = Canvas(4, 3)
        self.assertEqual((canvas.width, canvas.height), (4, 3))

    def test_one_pixel_is_a_canvas(self):
        self.assertEqual(Canvas(1, 1).rows(), ["."])

    def test_width_must_be_a_whole_number_of_1_or_more(self):
        self.assert_refused("canvas width must be a whole number of 1 or more, got 0", 0, 3)
        self.assert_refused("canvas width must be a whole number of 1 or more, got -4", -4, 3)
        self.assert_refused("canvas width must be a whole number of 1 or more, got 2.0", 2.0, 3)
        self.assert_refused("canvas width must be a whole number of 1 or more, got '4'", "4", 3)
        self.assert_refused("canvas width must be a whole number of 1 or more, got True", True, 3)
        self.assert_refused("canvas width must be a whole number of 1 or more, got None", None, 3)

    def test_height_must_be_a_whole_number_of_1_or_more(self):
        self.assert_refused("canvas height must be a whole number of 1 or more, got 0", 4, 0)
        self.assert_refused("canvas height must be a whole number of 1 or more, got -3", 4, -3)
        self.assert_refused("canvas height must be a whole number of 1 or more, got 1.5", 4, 1.5)
        self.assert_refused("canvas height must be a whole number of 1 or more, got None", 4, None)

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            Canvas(0, 0)

    def test_width_and_height_cannot_be_set(self):
        canvas = Canvas(4, 3)
        for field in ("width", "height"):
            with self.subTest(field=field):
                with self.assertRaises(AttributeError):
                    setattr(canvas, field, 9)


class CanvasFromRowsTest(unittest.TestCase):
    def assert_refused(self, message, rows):
        with self.assertRaises(PixelRowsError) as caught:
            Canvas.from_rows(rows)
        self.assertEqual(str(caught.exception), message)

    def test_rows_and_size_are_taken_from_the_rows(self):
        canvas = Canvas.from_rows(BLOB)
        self.assertEqual(canvas.rows(), BLOB)
        self.assertEqual((canvas.width, canvas.height), (6, 4))

    def test_rows_can_come_in_a_tuple_or_one_at_a_time(self):
        self.assertEqual(Canvas.from_rows(("ab", "cd")).rows(), ["ab", "cd"])
        self.assertEqual(Canvas.from_rows(row for row in ["ab", "cd"]).rows(), ["ab", "cd"])

    def test_list_it_was_made_from_can_change_without_it(self):
        rows = ["oo", "oo"]
        canvas = Canvas.from_rows(rows)
        rows[0] = "xx"
        self.assertEqual(canvas.rows(), ["oo", "oo"])

    def test_drawing_leaves_the_list_it_was_made_from(self):
        rows = ["oo", "oo"]
        Canvas.from_rows(rows).px(0, 0, "x")
        self.assertEqual(rows, ["oo", "oo"])

    def test_at_least_one_row(self):
        self.assert_refused("canvas: there are no rows", [])

    def test_uneven_row_is_named_with_both_widths(self):
        self.assert_refused("canvas: row 3 is 2 wide, the others are 3", ["ooo", "ooo", "ooo", "oo", "ooo"])
        self.assert_refused("canvas: row 1 is 3 wide, the others are 2", ["oo", "ooo"])

    def test_empty_row_is_named(self):
        self.assert_refused("canvas: row 1 is empty", ["oo", "", "oo"])

    def test_whitespace_is_named_by_row_and_column(self):
        self.assert_refused("canvas: row 2 has whitespace at column 1", ["ooo", "ooo", "o o"])
        self.assert_refused("canvas: row 0 has whitespace at column 2", ["oo\t", "ooo"])

    def test_row_that_is_not_a_string_is_named(self):
        self.assert_refused("canvas: row 1 is not a string, got 12", ["oo", 12])

    def test_rows_must_be_a_list_not_one_string(self):
        self.assert_refused("canvas: rows are a list of strings, got one string 'ooo'", "ooo")

    def test_rows_that_cannot_be_read_as_a_list(self):
        self.assert_refused("canvas: rows are a list of strings, got None", None)


class CanvasFromSpriteTest(unittest.TestCase):
    def test_rows_and_size_are_taken_from_the_sprite(self):
        canvas = Canvas.from_sprite(Sprite("blob", BLOB))
        self.assertEqual(canvas.rows(), BLOB)
        self.assertEqual((canvas.width, canvas.height), (6, 4))

    def test_drawing_leaves_the_sprite_as_it_was(self):
        sprite = Sprite("blob", BLOB)
        Canvas.from_sprite(sprite).rect(0, 0, 6, 4, "x")
        self.assertEqual(sprite.rows, ("..oo..", ".oggo.", "oggggo", "oooooo"))

    def test_what_is_not_a_sprite_is_refused(self):
        for given, kind in ((BLOB, "list"), ("blob", "str"), (None, "NoneType"), (Canvas(2, 2), "Canvas")):
            with self.subTest(kind=kind):
                with self.assertRaises(PixelRowsError) as caught:
                    Canvas.from_sprite(given)
                self.assertEqual(str(caught.exception), f"from_sprite takes a Sprite, got {kind}")


class CanvasGetTest(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas.from_rows(BLOB)

    def test_get_inside(self):
        self.assertEqual(self.canvas.get(0, 0), ".")
        self.assertEqual(self.canvas.get(2, 0), "o")
        self.assertEqual(self.canvas.get(2, 1), "g")
        self.assertEqual(self.canvas.get(5, 3), "o")

    def test_get_outside_is_a_dot(self):
        for x, y in ((-1, 0), (0, -1), (-1, -1), (6, 0), (0, 4), (6, 4), (100, 100), (-6, 3), (5, -4)):
            with self.subTest(x=x, y=y):
                self.assertEqual(self.canvas.get(x, y), ".")

    def test_get_does_not_wrap_from_the_far_edge(self):
        canvas = Canvas.from_rows(["ab", "cd"])
        self.assertEqual(canvas.get(-1, -1), ".")
        self.assertEqual(canvas.get(1, 1), "d")

    def test_get_reads_what_was_drawn(self):
        canvas = Canvas(3, 3)
        self.assertEqual(canvas.get(1, 2), ".")
        canvas.px(1, 2, "o")
        self.assertEqual(canvas.get(1, 2), "o")


class CanvasCharacterTest(unittest.TestCase):
    def assert_refused(self, ch):
        for method, draw in WITH_A_CHARACTER:
            with self.subTest(method=method, ch=ch):
                canvas = Canvas.from_rows(LETTERS)
                with self.assertRaises(PixelRowsError) as caught:
                    draw(canvas, ch)
                self.assertEqual(str(caught.exception), f"ch is one character that is not whitespace, got {ch!r}")
                self.assertEqual(canvas.rows(), LETTERS)

    def test_more_than_one_character_is_refused(self):
        self.assert_refused("ab")
        self.assert_refused("oo")

    def test_no_character_is_refused(self):
        self.assert_refused("")

    def test_whitespace_is_refused(self):
        self.assert_refused(" ")
        self.assert_refused("\t")
        self.assert_refused("\n")
        self.assert_refused("\u00a0")

    def test_what_is_not_a_string_is_refused(self):
        self.assert_refused(7)
        self.assert_refused(None)
        self.assert_refused(["o"])

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            Canvas(3, 3).px(1, 1, "ab")

    def test_character_is_checked_when_nothing_would_be_drawn(self):
        canvas = Canvas(3, 3)
        with self.assertRaises(PixelRowsError):
            canvas.px(9, 9, "ab")
        with self.assertRaises(PixelRowsError):
            canvas.rect(0, 0, 0, 0, "ab")
        with self.assertRaises(PixelRowsError):
            canvas.line(9, 9, 12, 9, "ab")

    def test_any_character_that_is_not_whitespace_paints(self):
        for ch in ("o", "O", "#", "0", "_", "\u00e9"):
            with self.subTest(ch=ch):
                self.assertEqual(Canvas(1, 1).px(0, 0, ch).rows(), [ch])

    def test_dot_is_allowed_and_erases(self):
        full = ["ooo", "ooo", "ooo"]
        self.assertEqual(Canvas.from_rows(full).px(1, 1, ".").rows(), ["ooo", "o.o", "ooo"])
        self.assertEqual(Canvas.from_rows(full).rect(0, 0, 2, 2, ".").rows(), ["..o", "..o", "ooo"])
        self.assertEqual(Canvas.from_rows(full).line(0, 0, 2, 2, ".").rows(), [".oo", "o.o", "oo."])


class CanvasPxTest(unittest.TestCase):
    def test_one_cell_is_painted(self):
        self.assertEqual(Canvas(3, 2).px(1, 0, "o").rows(), [".o.", "..."])

    def test_corners_are_inside(self):
        canvas = Canvas(3, 2).px(0, 0, "a").px(2, 0, "b").px(0, 1, "c").px(2, 1, "d")
        self.assertEqual(canvas.rows(), ["a.b", "c.d"])

    def test_painted_cell_is_painted_over(self):
        self.assertEqual(Canvas.from_rows(LETTERS).px(1, 1, "o").rows(), ["abc", "dof", "ghi"])

    def test_outside_is_dropped(self):
        for x, y in ((-1, 0), (0, -1), (-1, -1), (3, 0), (0, 3), (3, 3), (100, 100), (-3, 1), (2, -3)):
            with self.subTest(x=x, y=y):
                self.assertEqual(Canvas.from_rows(LETTERS).px(x, y, "o").rows(), LETTERS)

    def test_returns_the_canvas(self):
        canvas = Canvas(3, 3)
        self.assertIs(canvas.px(1, 1, "o"), canvas)
        self.assertIs(canvas.px(9, 9, "o"), canvas)


class CanvasRectTest(unittest.TestCase):
    def test_box_is_filled(self):
        self.assertEqual(Canvas(5, 4).rect(1, 1, 3, 2, "o").rows(), [".....", ".ooo.", ".ooo.", "....."])

    def test_1_by_1_is_one_cell(self):
        self.assertEqual(Canvas(3, 3).rect(2, 1, 1, 1, "o").rows(), ["...", "..o", "..."])

    def test_whole_canvas_can_be_filled(self):
        self.assertEqual(Canvas(3, 2).rect(0, 0, 3, 2, "o").rows(), ["ooo", "ooo"])

    def test_what_is_underneath_is_painted_over(self):
        self.assertEqual(Canvas.from_rows(LETTERS).rect(1, 0, 2, 2, "o").rows(), ["aoo", "doo", "ghi"])

    def test_part_outside_is_dropped(self):
        self.assertEqual(Canvas(4, 4).rect(-1, -1, 3, 3, "o").rows(), ["oo..", "oo..", "....", "...."])
        self.assertEqual(Canvas(4, 4).rect(2, 3, 5, 5, "o").rows(), ["....", "....", "....", "..oo"])
        self.assertEqual(Canvas(4, 4).rect(-2, 1, 9, 1, "o").rows(), ["....", "oooo", "....", "...."])

    def test_box_larger_than_the_canvas_fills_it(self):
        self.assertEqual(Canvas(3, 2).rect(-5, -5, 20, 20, "o").rows(), ["ooo", "ooo"])

    def test_box_all_outside_draws_nothing(self):
        for x, y in ((3, 0), (0, 3), (-2, 0), (0, -2), (-9, -9), (50, 50)):
            with self.subTest(x=x, y=y):
                self.assertEqual(Canvas.from_rows(LETTERS).rect(x, y, 2, 2, "o").rows(), LETTERS)

    def test_width_or_height_of_0_or_less_draws_nothing(self):
        for w, h in ((0, 2), (2, 0), (0, 0), (-1, 2), (2, -1), (-2, -2), (-50, 3)):
            with self.subTest(w=w, h=h):
                self.assertEqual(Canvas.from_rows(LETTERS).rect(1, 1, w, h, "o").rows(), LETTERS)

    def test_size_below_0_does_not_draw_backwards(self):
        self.assertEqual(Canvas.from_rows(LETTERS).rect(2, 2, -2, -2, "o").rows(), LETTERS)
        self.assertEqual(Canvas.from_rows(LETTERS).rect(-1, -1, -1, -1, "o").rows(), LETTERS)

    def test_returns_the_canvas(self):
        canvas = Canvas(3, 3)
        self.assertIs(canvas.rect(0, 0, 2, 2, "o"), canvas)
        self.assertIs(canvas.rect(0, 0, 0, 0, "o"), canvas)
        self.assertIs(canvas.rect(9, 9, 2, 2, "o"), canvas)


class CanvasLineTest(unittest.TestCase):
    def test_horizontal_line(self):
        self.assertEqual(Canvas(5, 3).line(1, 1, 3, 1, "o").rows(), [".....", ".ooo.", "....."])

    def test_vertical_line(self):
        self.assertEqual(Canvas(3, 5).line(1, 1, 1, 3, "o").rows(), ["...", ".o.", ".o.", ".o.", "..."])

    def test_diagonal_at_45_degrees(self):
        self.assertEqual(Canvas(4, 4).line(0, 0, 3, 3, "o").rows(), ["o...", ".o..", "..o.", "...o"])
        self.assertEqual(Canvas(4, 4).line(0, 3, 3, 0, "o").rows(), ["...o", "..o.", ".o..", "o..."])

    def test_shallow_line_has_one_cell_in_every_column(self):
        self.assertEqual(Canvas(6, 3).line(0, 0, 5, 2, "o").rows(), ["oo....", "..oo..", "....oo"])

    def test_shallow_line_going_up(self):
        self.assertEqual(
            Canvas(8, 6).line(1, 4, 6, 1, "o").rows(),
            ["........", "......o.", "....oo..", "..oo....", ".o......", "........"],
        )

    def test_steep_line_has_one_cell_in_every_row(self):
        self.assertEqual(Canvas(3, 6).line(0, 0, 2, 5, "o").rows(), ["o..", "o..", ".o.", ".o.", "..o", "..o"])

    def test_steep_line_going_left(self):
        self.assertEqual(
            Canvas(5, 7).line(3, 0, 1, 6, "o").rows(),
            ["...o.", "...o.", "..o..", "..o..", "..o..", ".o...", ".o..."],
        )

    def test_cell_half_way_between_two_stays_with_the_left_or_top_end(self):
        self.assertEqual(Canvas(3, 2).line(0, 0, 2, 1, "o").rows(), ["oo.", "..o"])
        self.assertEqual(Canvas(2, 3).line(0, 0, 1, 2, "o").rows(), ["o.", "o.", ".o"])

    def test_both_directions_give_the_same_cells(self):
        lines = (
            (0, 0, 5, 2), (0, 0, 2, 5), (0, 0, 2, 1), (0, 0, 1, 2), (1, 4, 6, 1), (3, 0, 1, 6),
            (0, 6, 7, 0), (0, 0, 6, 6), (0, 3, 7, 3), (2, 0, 2, 6), (7, 1, 0, 2), (5, 6, 4, 0),
        )
        for x0, y0, x1, y1 in lines:
            with self.subTest(line=(x0, y0, x1, y1)):
                there = Canvas(8, 7).line(x0, y0, x1, y1, "o")
                back = Canvas(8, 7).line(x1, y1, x0, y0, "o")
                self.assertEqual(there.rows(), back.rows())
                self.assertEqual((there.get(x0, y0), there.get(x1, y1)), ("o", "o"))

    def test_single_point(self):
        self.assertEqual(Canvas(3, 3).line(1, 1, 1, 1, "o").rows(), ["...", ".o.", "..."])

    def test_both_ends_are_included(self):
        canvas = Canvas(6, 4).line(1, 3, 4, 0, "o")
        self.assertEqual((canvas.get(1, 3), canvas.get(4, 0)), ("o", "o"))
        self.assertEqual(canvas.to_sprite("line").painted(), 4)

    def test_part_outside_is_dropped(self):
        self.assertEqual(Canvas(4, 3).line(-2, 1, 1, 1, "o").rows(), ["....", "oo..", "...."])
        self.assertEqual(Canvas(3, 4).line(1, 2, 1, 9, "o").rows(), ["...", "...", ".o.", ".o."])
        self.assertEqual(Canvas(3, 3).line(-2, -2, 5, 5, "o").rows(), ["o..", ".o.", "..o"])

    def test_cells_inside_are_not_moved_by_the_part_outside(self):
        self.assertEqual(Canvas(3, 3).line(-2, 0, 3, 2, "o").rows(), ["...", "oo.", "..o"])
        self.assertEqual(Canvas(3, 3).line(0, -2, 2, 3, "o").rows(), [".o.", ".o.", "..o"])

    def test_line_all_outside_draws_nothing(self):
        for line in ((-5, -1, 8, -1), (3, 0, 3, 9), (-4, 0, -1, 2), (0, 5, 9, 3)):
            with self.subTest(line=line):
                self.assertEqual(Canvas.from_rows(LETTERS).line(*line, "o").rows(), LETTERS)

    def test_what_is_underneath_is_painted_over(self):
        self.assertEqual(Canvas.from_rows(LETTERS).line(0, 2, 2, 0, "o").rows(), ["abo", "dof", "ohi"])

    def test_returns_the_canvas(self):
        canvas = Canvas(3, 3)
        self.assertIs(canvas.line(0, 0, 2, 1, "o"), canvas)
        self.assertIs(canvas.line(9, 9, 12, 9, "o"), canvas)


class CanvasStampTest(unittest.TestCase):
    def assert_refused(self, message, rows):
        canvas = Canvas.from_rows(LETTERS)
        with self.assertRaises(PixelRowsError) as caught:
            canvas.stamp(0, 0, rows)
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(canvas.rows(), LETTERS)

    def test_rows_are_laid_down_from_their_top_left_corner(self):
        self.assertEqual(Canvas(5, 4).stamp(1, 1, ["ab", "cd"]).rows(), [".....", ".ab..", ".cd..", "....."])
        self.assertEqual(Canvas(3, 3).stamp(0, 0, ["ab", "cd"]).rows(), ["ab.", "cd.", "..."])

    def test_dot_keeps_what_is_underneath(self):
        self.assertEqual(Canvas.from_rows(LETTERS).stamp(0, 0, ["x.", ".y"]).rows(), ["xbc", "dyf", "ghi"])

    def test_rows_of_dots_change_nothing(self):
        self.assertEqual(Canvas.from_rows(LETTERS).stamp(0, 0, ["...", "...", "..."]).rows(), LETTERS)

    def test_rows_can_come_in_a_tuple_or_one_at_a_time(self):
        self.assertEqual(Canvas(2, 2).stamp(0, 0, ("ab", "cd")).rows(), ["ab", "cd"])
        self.assertEqual(Canvas(2, 2).stamp(0, 0, (row for row in ["ab", "cd"])).rows(), ["ab", "cd"])

    def test_sprite_can_be_stamped(self):
        sprite = Sprite("s", ["ab.", ".cd"])
        self.assertEqual(Canvas(4, 3).stamp(1, 1, sprite).rows(), ["....", ".ab.", "..cd"])

    def test_canvas_can_be_stamped(self):
        other = Canvas(2, 2).px(0, 0, "a").px(1, 1, "b")
        self.assertEqual(Canvas(4, 3).stamp(1, 0, other).rows(), [".a..", "..b.", "...."])

    def test_dot_of_a_sprite_or_a_canvas_keeps_what_is_underneath(self):
        for stamped in (Sprite("s", ["x.", ".y"]), Canvas.from_rows(["x.", ".y"])):
            with self.subTest(stamped=type(stamped).__name__):
                self.assertEqual(Canvas.from_rows(LETTERS).stamp(1, 1, stamped).rows(), ["abc", "dxf", "ghy"])

    def test_canvas_stamped_on_itself_is_read_as_it_was(self):
        canvas = Canvas.from_rows(["ab.."])
        canvas.stamp(1, 0, canvas)
        self.assertEqual(canvas.rows(), ["aab."])

    def test_flip_lays_the_rows_down_turned_left_to_right(self):
        rows = ["ab.", "c.."]
        self.assertEqual(Canvas(5, 4).stamp(1, 1, rows).rows(), [".....", ".ab..", ".c...", "....."])
        self.assertEqual(Canvas(5, 4).stamp(1, 1, rows, flip=True).rows(), [".....", "..ba.", "...c.", "....."])

    def test_flip_can_be_given_by_place(self):
        self.assertEqual(Canvas(3, 1).stamp(0, 0, ["ab."], True).rows(), [".ba"])
        self.assertEqual(Canvas(3, 1).stamp(0, 0, ["ab."], False).rows(), ["ab."])

    def test_flip_turns_a_sprite_and_a_canvas(self):
        rows = ["ab.", "c.."]
        self.assertEqual(Canvas(3, 2).stamp(0, 0, Sprite("s", rows), flip=True).rows(), [".ba", "..c"])
        self.assertEqual(Canvas(3, 2).stamp(0, 0, Canvas.from_rows(rows), flip=True).rows(), [".ba", "..c"])

    def test_flip_keeps_what_is_under_a_dot(self):
        canvas = Canvas.from_rows(LETTERS).stamp(0, 0, ["x..", "..."], flip=True)
        self.assertEqual(canvas.rows(), ["abx", "def", "ghi"])

    def test_part_outside_is_dropped(self):
        rows = ["ab", "cd"]
        self.assertEqual(Canvas(3, 3).stamp(-1, -1, rows).rows(), ["d..", "...", "..."])
        self.assertEqual(Canvas(3, 3).stamp(2, -1, rows).rows(), ["..c", "...", "..."])
        self.assertEqual(Canvas(3, 3).stamp(-1, 2, rows).rows(), ["...", "...", "b.."])
        self.assertEqual(Canvas(3, 3).stamp(2, 2, rows).rows(), ["...", "...", "..a"])

    def test_flipped_rows_are_turned_before_the_edge_cuts_them(self):
        self.assertEqual(Canvas(3, 1).stamp(-1, 0, ["ab"], flip=True).rows(), ["a.."])
        self.assertEqual(Canvas(3, 1).stamp(2, 0, ["ab"], flip=True).rows(), ["..b"])

    def test_rows_larger_than_the_canvas_are_cut_to_it(self):
        rows = ["abcd", "efgh", "ijkl", "mnop"]
        self.assertEqual(Canvas(2, 2).stamp(-1, -1, rows).rows(), ["fg", "jk"])

    def test_rows_all_outside_draw_nothing(self):
        for x, y in ((3, 0), (0, 3), (-2, 0), (0, -2), (50, 50), (-50, -50)):
            with self.subTest(x=x, y=y):
                self.assertEqual(Canvas.from_rows(LETTERS).stamp(x, y, ["xx", "xx"]).rows(), LETTERS)

    def test_what_is_stamped_is_left_as_it_was(self):
        rows = ["ab", "cd"]
        other = Canvas.from_rows(rows)
        Canvas(3, 3).stamp(1, 1, rows).stamp(0, 0, other, flip=True)
        self.assertEqual(rows, ["ab", "cd"])
        self.assertEqual(other.rows(), ["ab", "cd"])

    def test_stamped_canvas_can_change_without_the_one_it_went_on(self):
        other = Canvas(1, 1).px(0, 0, "a")
        canvas = Canvas(2, 1).stamp(0, 0, other)
        other.px(0, 0, "z")
        self.assertEqual(canvas.rows(), ["a."])

    def test_list_of_strings_needs_at_least_one_row(self):
        self.assert_refused("stamp: there are no rows", [])

    def test_uneven_row_is_named_with_both_widths(self):
        self.assert_refused("stamp: row 1 is 3 wide, the others are 2", ["oo", "ooo"])
        self.assert_refused("stamp: row 2 is 1 wide, the others are 2", ["oo", "oo", "o"])

    def test_empty_row_is_named(self):
        self.assert_refused("stamp: row 1 is empty", ["oo", "", "oo"])

    def test_whitespace_is_named_by_row_and_column(self):
        self.assert_refused("stamp: row 0 has whitespace at column 1", ["o o"])
        self.assert_refused("stamp: row 1 has whitespace at column 0", ["oo", "\to"])

    def test_row_that_is_not_a_string_is_named(self):
        self.assert_refused("stamp: row 1 is not a string, got 12", ["oo", 12])

    def test_rows_must_be_a_list_not_one_string(self):
        self.assert_refused("stamp: rows are a list of strings, got one string 'ooo'", "ooo")

    def test_rows_that_cannot_be_read_as_a_list(self):
        self.assert_refused("stamp: rows are a list of strings, got None", None)
        self.assert_refused("stamp: rows are a list of strings, got 5", 5)

    def test_rows_are_checked_when_they_would_fall_outside(self):
        with self.assertRaises(PixelRowsError):
            Canvas(3, 3).stamp(9, 9, ["oo", "o"])

    def test_returns_the_canvas(self):
        canvas = Canvas(3, 3)
        self.assertIs(canvas.stamp(0, 0, ["ab"]), canvas)
        self.assertIs(canvas.stamp(0, 0, Sprite("s", ["ab"]), flip=True), canvas)
        self.assertIs(canvas.stamp(9, 9, ["ab"]), canvas)


class CanvasMirrorTest(unittest.TestCase):
    def test_even_width_copies_the_left_half_over_the_right(self):
        self.assertEqual(Canvas.from_rows(["ab..", "c..."]).mirror().rows(), ["abba", "c..c"])
        self.assertEqual(Canvas.from_rows(["abcdef"]).mirror().rows(), ["abccba"])

    def test_odd_width_keeps_the_middle_column(self):
        self.assertEqual(Canvas.from_rows(["abc..", "d.e.."]).mirror().rows(), ["abcba", "d.e.d"])
        self.assertEqual(Canvas.from_rows(["ab.", "c.d", "..."]).mirror().rows(), ["aba", "c.c", "..."])

    def test_right_half_is_lost(self):
        self.assertEqual(Canvas.from_rows(["a.xy", "..zz"]).mirror().rows(), ["a..a", "...."])
        self.assertEqual(Canvas.from_rows(["a.mxy", "...zz"]).mirror().rows(), ["a.m.a", "....."])

    def test_width_of_1_stays_as_it_is(self):
        self.assertEqual(Canvas.from_rows(["a", "b", "."]).mirror().rows(), ["a", "b", "."])

    def test_width_of_2_copies_the_left_column(self):
        self.assertEqual(Canvas.from_rows(["ab", ".c"]).mirror().rows(), ["aa", ".."])

    def test_every_row_reads_the_same_from_both_ends(self):
        for rows in (["abcdef", "..x..y", "q....."], ["abcdefg", "..x.y.z", "q......"]):
            with self.subTest(width=len(rows[0])):
                for row in Canvas.from_rows(rows).mirror().rows():
                    self.assertEqual(row, row[::-1])

    def test_mirror_again_changes_nothing(self):
        canvas = Canvas.from_rows(["abc..", "d.e.."]).mirror()
        self.assertEqual(canvas.mirror().rows(), ["abcba", "d.e.d"])

    def test_size_stays(self):
        canvas = Canvas.from_rows(["abc..", "d.e.."]).mirror()
        self.assertEqual((canvas.width, canvas.height), (5, 2))

    def test_returns_the_canvas(self):
        canvas = Canvas(4, 2)
        self.assertIs(canvas.mirror(), canvas)


class CanvasOutlineTest(unittest.TestCase):
    def test_empty_cells_above_below_left_and_right_get_the_character(self):
        canvas = Canvas(5, 5).px(2, 2, "o").outline("k")
        self.assertEqual(canvas.rows(), [".....", "..k..", ".kok.", "..k..", "....."])

    def test_diagonal_adds_the_four_corners(self):
        canvas = Canvas(5, 5).px(2, 2, "o").outline("k", diagonal=True)
        self.assertEqual(canvas.rows(), [".....", ".kkk.", ".kok.", ".kkk.", "....."])

    def test_cell_touched_only_at_a_corner_needs_diagonal(self):
        rows = ["o..", "...", "..."]
        self.assertEqual(Canvas.from_rows(rows).outline("k").rows(), ["ok.", "k..", "..."])
        self.assertEqual(Canvas.from_rows(rows).outline("k", diagonal=True).rows(), ["ok.", "kk.", "..."])

    def test_painted_cells_stay_as_they_are(self):
        rows = [".....", ".ab..", ".cd..", "....."]
        self.assertEqual(Canvas.from_rows(rows).outline("k").rows(), [".kk..", "kabk.", "kcdk.", ".kk.."])
        self.assertEqual(
            Canvas.from_rows(rows).outline("k", diagonal=True).rows(),
            ["kkkk.", "kabk.", "kcdk.", "kkkk."],
        )

    def test_outline_cell_does_not_grow_a_second_ring(self):
        self.assertEqual(Canvas(7, 1).px(0, 0, "o").outline("k").rows(), ["ok....."])
        self.assertEqual(Canvas(7, 1).px(6, 0, "o").outline("k").rows(), [".....ko"])
        self.assertEqual(Canvas(1, 5).px(0, 0, "o").outline("k").rows(), ["o", "k", ".", ".", "."])
        self.assertEqual(Canvas(4, 3).px(0, 0, "o").outline("k", diagonal=True).rows(), ["ok..", "kk..", "...."])

    def test_second_call_outlines_the_first_outline(self):
        canvas = Canvas(7, 7).px(3, 3, "o").outline("a").outline("b")
        self.assertEqual(
            canvas.rows(),
            [".......", "...b...", "..bab..", ".baoab.", "..bab..", "...b...", "......."],
        )

    def test_character_of_the_art_can_be_the_outline(self):
        self.assertEqual(Canvas(5, 1).px(2, 0, "k").outline("k").rows(), [".kkk."])

    def test_empty_cell_inside_the_art_is_outlined(self):
        self.assertEqual(Canvas.from_rows(["ooo", "o.o", "ooo"]).outline("k").rows(), ["ooo", "oko", "ooo"])
        self.assertEqual(
            Canvas.from_rows(["ooooo", "o...o", "o...o", "o...o", "ooooo"]).outline("k").rows(),
            ["ooooo", "okkko", "ok.ko", "okkko", "ooooo"],
        )

    def test_empty_cell_between_two_painted_cells_is_outlined_once(self):
        self.assertEqual(Canvas.from_rows([".o", "o."]).outline("k").rows(), ["ko", "ok"])
        self.assertEqual(Canvas.from_rows(["a.b"]).outline("k").rows(), ["akb"])

    def test_canvas_with_nothing_painted_gets_no_outline(self):
        self.assertEqual(Canvas(3, 2).outline("k").rows(), ["...", "..."])
        self.assertEqual(Canvas(3, 2).outline("k", diagonal=True).rows(), ["...", "..."])

    def test_edge_of_the_canvas_cuts_the_outline_off(self):
        self.assertEqual(Canvas.from_rows(["ab", "cd"]).outline("k").rows(), ["ab", "cd"])
        self.assertEqual(Canvas.from_rows(["o..", "..."]).outline("k").rows(), ["ok.", "k.."])
        self.assertEqual(Canvas(3, 3).px(0, 1, "o").outline("k").rows(), ["k..", "ok.", "k.."])
        self.assertEqual(Canvas(3, 2).px(2, 1, "o").outline("k", diagonal=True).rows(), [".kk", ".ko"])

    def test_size_stays_without_grow(self):
        canvas = Canvas.from_rows(["ab.", "cd."]).outline("k")
        self.assertEqual((canvas.width, canvas.height), (3, 2))

    def test_grow_adds_2_to_the_width_and_the_height(self):
        canvas = Canvas.from_rows(["ab.", "cd."]).outline("k", grow=True)
        self.assertEqual((canvas.width, canvas.height), (5, 4))
        self.assertEqual([len(row) for row in canvas.rows()], [5, 5, 5, 5])

    def test_grow_moves_the_art_by_1_and_1(self):
        canvas = Canvas.from_rows(["ab", "cd"]).outline("k", grow=True)
        self.assertEqual(canvas.rows(), [".kk.", "kabk", "kcdk", ".kk."])
        self.assertEqual((canvas.get(0, 0), canvas.get(1, 1), canvas.get(2, 2)), (".", "a", "d"))

    def test_grow_loses_no_part_of_the_outline(self):
        self.assertEqual(Canvas.from_rows(["o"]).outline("k", grow=True).rows(), [".k.", "kok", ".k."])
        self.assertEqual(
            Canvas.from_rows(["o"]).outline("k", grow=True, diagonal=True).rows(),
            ["kkk", "kok", "kkk"],
        )
        self.assertEqual(
            Canvas.from_rows(["ab", "cd"]).outline("k", grow=True, diagonal=True).rows(),
            ["kkkk", "kabk", "kcdk", "kkkk"],
        )

    def test_grow_with_nothing_painted_only_grows(self):
        self.assertEqual(Canvas(2, 1).outline("k", grow=True).rows(), ["....", "....", "...."])

    def test_every_call_with_grow_grows_again(self):
        canvas = Canvas.from_rows(["o"]).outline("a", grow=True).outline("b", grow=True)
        self.assertEqual(canvas.rows(), ["..b..", ".bab.", "baoab", ".bab.", "..b.."])
        self.assertEqual((canvas.width, canvas.height), (5, 5))

    def test_drawing_after_grow_goes_by_the_new_size(self):
        canvas = Canvas(1, 1).outline("k", grow=True).px(2, 2, "x").px(3, 3, "y")
        self.assertEqual(canvas.rows(), ["...", "...", "..x"])

    def test_grow_and_diagonal_can_be_given_by_place(self):
        self.assertEqual(Canvas.from_rows(["o"]).outline("k", True).rows(), [".k.", "kok", ".k."])
        self.assertEqual(Canvas.from_rows(["o"]).outline("k", True, True).rows(), ["kkk", "kok", "kkk"])
        self.assertEqual(Canvas.from_rows(["o.", ".."]).outline("k", False, True).rows(), ["ok", "kk"])

    def test_dot_is_allowed_and_outlines_nothing(self):
        self.assertEqual(Canvas(3, 3).px(1, 1, "o").outline(".").rows(), ["...", ".o.", "..."])
        self.assertEqual(Canvas.from_rows(["o"]).outline(".", grow=True).rows(), ["...", ".o.", "..."])

    def test_character_is_checked_when_nothing_would_be_outlined(self):
        with self.assertRaises(PixelRowsError):
            Canvas(3, 3).outline("ab")

    def test_refused_character_does_not_grow_the_canvas(self):
        canvas = Canvas.from_rows(["ab", "cd"])
        with self.assertRaises(PixelRowsError):
            canvas.outline(" ", grow=True)
        self.assertEqual(canvas.rows(), ["ab", "cd"])

    def test_returns_the_canvas(self):
        canvas = Canvas(3, 3).px(1, 1, "o")
        self.assertIs(canvas.outline("k"), canvas)
        self.assertIs(canvas.outline("k", grow=True), canvas)
        self.assertIs(canvas.outline("k", diagonal=True), canvas)


class CanvasRowsTest(unittest.TestCase):
    def test_rows_are_a_list_of_strings(self):
        rows = Canvas(3, 2).px(1, 0, "o").rows()
        self.assertIsInstance(rows, list)
        self.assertEqual(rows, [".o.", "..."])

    def test_rows_follow_the_drawing(self):
        canvas = Canvas(2, 2)
        self.assertEqual(canvas.rows(), ["..", ".."])
        canvas.px(0, 0, "a")
        self.assertEqual(canvas.rows(), ["a.", ".."])
        canvas.px(1, 1, "b")
        self.assertEqual(canvas.rows(), ["a.", ".b"])

    def test_list_handed_out_can_change_without_the_canvas(self):
        canvas = Canvas.from_rows(["ab", "cd"])
        rows = canvas.rows()
        rows[0] = "xx"
        rows.append("yy")
        self.assertEqual(canvas.rows(), ["ab", "cd"])
        self.assertEqual(canvas.height, 2)


class CanvasToSpriteTest(unittest.TestCase):
    def test_sprite_has_the_name_and_the_rows(self):
        sprite = Canvas(3, 2).rect(0, 0, 2, 1, "o").to_sprite("bar")
        self.assertIsInstance(sprite, Sprite)
        self.assertEqual(sprite.name, "bar")
        self.assertEqual(sprite.rows, ("oo.", "..."))

    def test_no_palette_is_none(self):
        self.assertIsNone(Canvas.from_rows(BLOB).to_sprite("blob").palette)

    def test_palette_is_passed_on(self):
        canvas = Canvas.from_rows(BLOB)
        self.assertEqual(canvas.to_sprite("blob", {"g": "#7CC86A"}).palette, Palette({"g": "#7cc86a"}))
        self.assertEqual(canvas.to_sprite("blob", Palette({"g": "#7cc86a"})).palette, Palette({"g": "#7cc86a"}))

    def test_empty_canvas_is_a_sprite_with_nothing_painted(self):
        sprite = Canvas(2, 2).to_sprite("none")
        self.assertEqual(sprite.rows, ("..", ".."))
        self.assertEqual(sprite.painted(), 0)

    def test_sprite_stays_when_the_canvas_is_drawn_on(self):
        canvas = Canvas(2, 2)
        sprite = canvas.to_sprite("none")
        canvas.rect(0, 0, 2, 2, "o")
        self.assertEqual(sprite.rows, ("..", ".."))

    def test_sprite_and_back_is_the_same_sprite(self):
        sprite = Sprite("blob", BLOB, {"g": "#7cc86a"})
        self.assertEqual(Canvas.from_sprite(sprite).to_sprite("blob", sprite.palette), sprite)

    def test_name_is_held_to_the_rules_of_a_sprite(self):
        with self.assertRaises(PixelRowsError) as caught:
            Canvas(2, 2).to_sprite("")
        self.assertEqual(str(caught.exception), "a sprite's name is a non-empty string, got ''")

    def test_palette_is_held_to_the_rules_of_a_sprite(self):
        with self.assertRaises(PixelRowsError) as caught:
            Canvas(2, 2).to_sprite("hat", ["o"])
        self.assertEqual(str(caught.exception), "sprite 'hat': the palette is a Palette or a mapping, got ['o']")


class CanvasFigureTest(unittest.TestCase):
    def test_mushroom_drawn_in_one_chain_of_calls(self):
        canvas = (
            Canvas(7, 6)
            .rect(0, 2, 4, 2, "r")
            .line(2, 0, 0, 2, "r")
            .rect(2, 1, 2, 1, "r")
            .px(3, 0, "r")
            .rect(2, 4, 2, 2, "s")
            .mirror()
            .stamp(1, 1, ["w.", ".w"])
            .stamp(4, 1, ["w.", ".w"], flip=True)
            .outline("k", grow=True)
        )
        self.assertEqual(
            canvas.rows(),
            [
                "...kkk...",
                "..krrrk..",
                ".kwrrrwk.",
                "krrwrwrrk",
                "krrrrrrrk",
                ".kkssskk.",
                "..ksssk..",
                "...kkk...",
            ],
        )
        self.assertEqual((canvas.width, canvas.height), (9, 8))


if __name__ == "__main__":
    unittest.main()
