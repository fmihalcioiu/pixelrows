# Drawing in code

Write rows by hand when a sprite is small and irregular. Draw in code when the subject is symmetric, when it is built from boxes and lines, or when frames differ by a few pixels: the code keeps the copies exact.

A script builds sprites on a `Canvas`, adds them to a `SpriteSet`, and saves the set file. After that the loop is the same: `check`, `sheet`, look, fix the script, run it again.

If the package is not installed, run the script with the repo's root folder in `PYTHONPATH`, or `import pixelrows` fails.

```python
from pixelrows import Canvas, SpriteSet

sprites = SpriteSet({"o": "#1b1b26", "w": "#e9fbff", "c": "#59c3e8", "C": "#2a7fb8"})

canvas = Canvas(9, 7)
canvas.rect(2, 0, 3, 1, "c")          # the left half and the middle column
canvas.rect(1, 1, 4, 1, "c")
canvas.rect(0, 2, 5, 1, "c")
canvas.line(1, 3, 4, 6, "c")
canvas.rect(2, 3, 3, 1, "c").rect(3, 4, 2, 1, "c").px(4, 5, "c")
canvas.mirror()                       # the right half from the left
canvas.px(2, 1, "w").px(1, 2, "w")    # a glint, upper left
canvas.rect(6, 1, 2, 1, "C").rect(6, 2, 3, 1, "C")   # shade, right side
canvas.outline("o", grow=True)        # one pixel of outline all round

sprites.add(canvas.to_sprite("gem"))
sprites.save("gem.json")
```

## Canvas

Coordinates count from the top-left corner: x across, y down. Every drawing call returns the canvas, so calls chain. Whatever falls outside the canvas is dropped without an error. A character is one character; `"."` erases.

| Call | Does |
|---|---|
| `Canvas(width, height)` | An empty canvas |
| `Canvas.from_rows(rows)`, `Canvas.from_sprite(sprite)` | A canvas holding existing art, to change it |
| `px(x, y, ch)` | One pixel |
| `rect(x, y, w, h, ch)` | A filled rectangle |
| `line(x0, y0, x1, y1, ch)` | A straight line, both ends included |
| `stamp(x, y, rows, flip=False)` | Lays rows, a sprite or another canvas down at (x, y). A `.` in them keeps what is underneath |
| `mirror()` | Copies the left half over the right half, mirrored. With an odd width the middle column stays |
| `outline(ch, grow=False, diagonal=False)` | Gives `ch` to every empty cell beside a painted one. `grow=True` first adds an empty cell on every side so the outline has room |
| `get(x, y)` | The character at a cell, `.` outside |
| `rows()` | The rows as strings |
| `to_sprite(name, palette=None)` | The canvas as a sprite |

Coordinates must be whole numbers: write `width // 2`, not `width / 2`.

`outline(ch, grow=True)` makes the canvas two wider and two taller and moves the art one pixel right and one down. The points `check` reports are counted on the finished sprite, so a pixel drawn at (x, y) before the outline is reported at (x + 1, y + 1).

## Frames from one drawing

Draw the pose once, then make each frame from a copy.

```python
base = Canvas(12, 16)
# ... draw the body ...

frames = []
for step, lift in enumerate([0, 1, 0, 1]):
    frame = Canvas(12, 17)                 # one row of headroom
    frame.stamp(0, 1 - lift, base.rows())  # the whole body, one pixel up on the passing frames
    sprites.add(frame.to_sprite(f"hero_{step}"))
    frames.append(f"hero_{step}")

sprites.add_anim("hero_walk", frames, fps=10)
```

Stamp parts separately when they move separately: the body at one offset, an arm or a leg at another.

## Sets, sprites and pictures

| Call | Does |
|---|---|
| `SpriteSet(palette)` | A new set. The palette is a dict of character to `#rrggbb` |
| `SpriteSet.load(path)`, `.save(path)` | Reads and writes the set file |
| `.add(sprite)`, `.add_anim(name, frames, fps)` | Adds or replaces a sprite or a clip |
| `.sprite(name)`, `.anim(name)` | Looks one up |
| `.palette.set(ch, colour)` | Adds or changes a colour |
| `.problems()` | What is wrong with the set, as a list of sentences |
| `Sprite(name, rows, palette=None)` | A sprite from rows written out. `palette` holds its own colours |
| `sprite.flipped()` | The sprite turned left to right |

To make a picture without the command line:

```python
from pixelrows import render_sprite
from pixelrows.anim import save_gif
from pixelrows.sheet import anim_strip, contact_sheet

sprite = sprites.sprite("gem")
render_sprite(sprite, sprites.palette_for(sprite), scale=8).save("out/gem.png")
contact_sheet(sprites, scales=(1, 8)).save("out/sheet.png")
anim_strip(sprites, "hero_walk").save("out/hero_walk_strip.png")
save_gif("out/hero_walk.gif", sprites, "hero_walk", scale=8)
```

Bad input raises `pixelrows.PixelRowsError` with a message that names the sprite and the row or key at fault.
