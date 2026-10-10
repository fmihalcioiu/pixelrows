"""A gem drawn in code: the left half painted, mirrored, shaded on one side, then outlined.

From the repo root:

    python -m examples.gem

It prints the rows it drew and writes gem.json and gem.png beside this file.
"""
from pathlib import Path

from pixelrows.canvas import Canvas
from pixelrows.render import render_sprite
from pixelrows.spriteset import SpriteSet

HERE = Path(__file__).resolve().parent

sprites = SpriteSet({"o": "#1b1b26", "w": "#e9fbff", "c": "#59c3e8", "C": "#2a7fb8"})

canvas = Canvas(9, 7)

# The left half and the middle column: a flat top, the widest row, a slope down to the point.
canvas.rect(2, 0, 3, 1, "c")
canvas.rect(1, 1, 4, 1, "c")
canvas.rect(0, 2, 5, 1, "c")
canvas.line(1, 3, 4, 6, "c")
canvas.rect(2, 3, 3, 1, "c").rect(3, 4, 2, 1, "c").px(4, 5, "c")

# The right half is the left half, mirrored.
canvas.mirror()

# Light comes from the upper left: a glint there, and the right side in shade.
canvas.px(2, 1, "w").px(1, 2, "w").px(2, 2, "w")
canvas.rect(6, 1, 2, 1, "C").rect(6, 2, 3, 1, "C")
canvas.line(7, 3, 4, 6, "C").rect(5, 3, 2, 1, "C").px(5, 4, "C")

# One pixel of outline all round, with room made for it.
canvas.outline("o", grow=True)

gem = sprites.add(canvas.to_sprite("gem"))
print("\n".join(gem.rows))

sprites.save(HERE / "gem.json")
render_sprite(gem, sprites.palette_for(gem), scale=12).save(HERE / "gem.png")
