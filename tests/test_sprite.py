import unittest

from pixelrows.errors import PixelRowsError
from pixelrows.sprite import Sprite

BLOB = ["..oo..", ".oggo.", "oggggo", "oooooo"]


class SpriteMakingTest(unittest.TestCase):
    def test_name_rows_and_size_are_kept(self):
        sprite = Sprite("blob", BLOB)
        self.assertEqual(sprite.name, "blob")
        self.assertEqual(sprite.rows, ("..oo..", ".oggo.", "oggggo", "oooooo"))
        self.assertEqual(sprite.width, 6)
        self.assertEqual(sprite.height, 4)

    def test_rows_become_a_tuple_whatever_they_came_in(self):
        self.assertEqual(Sprite("a", (row for row in ["ab", "cd"])).rows, ("ab", "cd"))
        self.assertIsInstance(Sprite("a", ["ab", "cd"]).rows, tuple)

    def test_one_pixel_is_a_sprite(self):
        sprite = Sprite("dot", ["o"])
        self.assertEqual((sprite.width, sprite.height), (1, 1))

    def test_repr_gives_name_and_size(self):
        self.assertEqual(repr(Sprite("blob", BLOB)), "Sprite('blob', 6x4)")


class SpriteRulesTest(unittest.TestCase):
    def assert_refused(self, message, *args):
        with self.assertRaises(PixelRowsError) as caught:
            Sprite(*args)
        self.assertEqual(str(caught.exception), message)

    def test_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            Sprite("hat", [])

    def test_name_must_be_a_non_empty_string(self):
        self.assert_refused("a sprite's name is a non-empty string, got ''", "", ["o"])
        self.assert_refused("a sprite's name is a non-empty string, got None", None, ["o"])
        self.assert_refused("a sprite's name is a non-empty string, got 7", 7, ["o"])

    def test_at_least_one_row(self):
        self.assert_refused("sprite 'hat': there are no rows", "hat", [])

    def test_uneven_row_is_named_with_both_widths(self):
        rows = ["oooooooooooo", "oooooooooooo", "oooooooooooo", "ooooooooooo", "oooooooooooo"]
        self.assert_refused("sprite 'hat': row 3 is 11 wide, the others are 12", "hat", rows)

    def test_uneven_first_row_is_the_one_named(self):
        self.assert_refused("sprite 'hat': row 0 is 2 wide, the others are 3", "hat", ["oo", "ooo", "ooo"])

    def test_two_rows_that_differ_name_the_second(self):
        self.assert_refused("sprite 'hat': row 1 is 3 wide, the others are 2", "hat", ["oo", "ooo"])

    def test_empty_row_is_named(self):
        self.assert_refused("sprite 'hat': row 1 is empty", "hat", ["oo", "", "oo"])
        self.assert_refused("sprite 'hat': row 0 is empty", "hat", [""])

    def test_whitespace_is_named_by_row_and_column(self):
        self.assert_refused("sprite 'hat': row 2 has whitespace at column 1", "hat", ["ooo", "ooo", "o o"])
        self.assert_refused("sprite 'hat': row 0 has whitespace at column 2", "hat", ["oo\t", "ooo"])
        self.assert_refused("sprite 'hat': row 1 has whitespace at column 3", "hat", ["ooo", "ooo\n"])
        self.assert_refused("sprite 'hat': row 0 has whitespace at column 0", "hat", ["\u00a0oo"])

    def test_row_that_is_not_a_string_is_named(self):
        self.assert_refused("sprite 'hat': row 1 is not a string, got 12", "hat", ["oo", 12])
        self.assert_refused("sprite 'hat': row 0 is not a string, got ['o', 'o']", "hat", [["o", "o"]])

    def test_rows_must_be_a_list_not_one_string(self):
        self.assert_refused("sprite 'hat': rows are a list of strings, got one string 'ooo'", "hat", "ooo")

    def test_rows_that_cannot_be_read_as_a_list(self):
        self.assert_refused("sprite 'hat': rows are a list of strings, got None", "hat", None)
        self.assert_refused("sprite 'hat': rows are a list of strings, got 5", "hat", 5)


class SpriteNotChangedTest(unittest.TestCase):
    def setUp(self):
        self.sprite = Sprite("blob", BLOB)

    def test_name_and_rows_cannot_be_set(self):
        for field, value in (("name", "x"), ("rows", ("o",)), ("width", 3), ("height", 3)):
            with self.subTest(field=field):
                with self.assertRaises(AttributeError):
                    setattr(self.sprite, field, value)

    def test_nothing_new_can_be_hung_on_it(self):
        with self.assertRaises(AttributeError):
            self.sprite.note = "x"

    def test_list_it_was_made_from_can_change_without_it(self):
        rows = ["oo", "oo"]
        sprite = Sprite("a", rows)
        rows[0] = "xx"
        self.assertEqual(sprite.rows, ("oo", "oo"))


class SpriteReadingTest(unittest.TestCase):
    def setUp(self):
        self.sprite = Sprite("blob", BLOB)

    def test_at_inside(self):
        self.assertEqual(self.sprite.at(0, 0), ".")
        self.assertEqual(self.sprite.at(2, 0), "o")
        self.assertEqual(self.sprite.at(2, 1), "g")
        self.assertEqual(self.sprite.at(5, 3), "o")

    def test_at_outside_is_a_dot(self):
        for x, y in ((-1, 0), (0, -1), (-1, -1), (6, 0), (0, 4), (6, 4), (100, 100), (-6, 3), (5, -4)):
            with self.subTest(x=x, y=y):
                self.assertEqual(self.sprite.at(x, y), ".")

    def test_at_does_not_wrap_from_the_far_edge(self):
        sprite = Sprite("a", ["ab", "cd"])
        self.assertEqual(sprite.at(-1, -1), ".")
        self.assertEqual(sprite.at(1, 1), "d")


class SpriteEqualityTest(unittest.TestCase):
    def test_same_name_and_rows_are_equal(self):
        self.assertEqual(Sprite("a", ["ab"]), Sprite("a", ("ab",)))

    def test_another_name_is_not_equal(self):
        self.assertNotEqual(Sprite("a", ["ab"]), Sprite("b", ["ab"]))

    def test_other_rows_are_not_equal(self):
        self.assertNotEqual(Sprite("a", ["ab"]), Sprite("a", ["ba"]))
        self.assertNotEqual(Sprite("a", ["ab"]), Sprite("a", ["ab", "ab"]))

    def test_not_equal_to_what_is_not_a_sprite(self):
        self.assertNotEqual(Sprite("a", ["ab"]), ("ab",))
        self.assertNotEqual(Sprite("a", ["ab"]), "a")
        self.assertNotEqual(Sprite("a", ["ab"]), None)


if __name__ == "__main__":
    unittest.main()
