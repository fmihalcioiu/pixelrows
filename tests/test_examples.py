import unittest
from pathlib import Path

from pixelrows.spriteset import SpriteSet

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ExampleSetsTest(unittest.TestCase):
    def test_every_set_file_loads_without_problems(self):
        files = sorted(EXAMPLES.glob("*.json"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.name):
                self.assertEqual(SpriteSet.load(path).problems(), [])

    def test_every_clip_plays(self):
        for path in sorted(EXAMPLES.glob("*.json")):
            sprites = SpriteSet.load(path)
            for name in sprites.anims:
                with self.subTest(path=path.name, anim=name):
                    self.assertTrue(sprites.frames_of(name))


if __name__ == "__main__":
    unittest.main()
