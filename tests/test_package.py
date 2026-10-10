import re
import unittest
from pathlib import Path

import pixelrows
from pixelrows.canvas import Canvas
from pixelrows.errors import PixelRowsError
from pixelrows.image import Image
from pixelrows.palette import Palette
from pixelrows.render import render_sprite
from pixelrows.sprite import Sprite
from pixelrows.spriteset import Anim, SpriteSet

ROOT = Path(__file__).resolve().parent.parent


class PackageTest(unittest.TestCase):
    def test_the_main_names_come_from_the_package_itself(self):
        self.assertIs(pixelrows.Anim, Anim)
        self.assertIs(pixelrows.Canvas, Canvas)
        self.assertIs(pixelrows.Image, Image)
        self.assertIs(pixelrows.Palette, Palette)
        self.assertIs(pixelrows.PixelRowsError, PixelRowsError)
        self.assertIs(pixelrows.Sprite, Sprite)
        self.assertIs(pixelrows.SpriteSet, SpriteSet)
        self.assertIs(pixelrows.render_sprite, render_sprite)

    def test_all_lists_what_is_there(self):
        for name in pixelrows.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(pixelrows, name))

    def test_the_version_is_the_one_in_pyproject(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        version = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE).group(1)
        self.assertEqual(pixelrows.__version__, version)


if __name__ == "__main__":
    unittest.main()
