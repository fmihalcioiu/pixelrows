---
name: pixelrows
description: Draw pixel art as rows of text with the pixelrows Python package, then check it and render it to PNG sheets and animated GIFs. Use this skill whenever the user asks for pixel art, a sprite, a sprite sheet, a game icon, a tile, an idle or walk cycle, or an animated GIF of pixel art, and whenever they ask to change, recolour or review a pixelrows set file, even if they do not name pixelrows.
---

# Drawing pixel art with pixelrows

pixelrows keeps pixel art as text. A sprite is a list of strings, one character per pixel, read against a palette. You write the rows; the package checks them and renders them to PNG and GIF.

A grid of letters does not show you what you drew. Rows that look right as text come out lopsided, noisy or unreadable at their real size. So the work is a loop: write, check, render, look at the picture, fix. Never hand over a sprite you have not looked at as an image.

## Before you start

See that the package answers:

```
python -m pixelrows -h
```

If it does not, it is not installed. In a clone of the pixelrows repo, run `pip install .`, or work from the repo's root folder, where `python -m pixelrows` runs with nothing installed. A script of your own that imports `pixelrows` without an install needs the repo's root in the `PYTHONPATH` environment variable, since Python looks beside the script and not in the working folder.

## The loop

1. Decide the size, the palette and where the light comes from. If the user did not give them, choose and say what you chose in one line.
2. Write the set file (next section). Draw in code instead when the subject is symmetric, when frames differ by a few pixels, or when frames share a part that stays the same while another part moves: read `references/python.md`.
3. Run `check`. Fix every problem. Look at every finding and either fix it or decide it is meant.
4. Render a sheet at 1x and 8x and open the PNG. The 1x drawing is tiny on purpose: it is what a player sees, and the one question to ask of it is whether the subject can still be told. The 8x drawing is where you find the pixel to change.
5. For a clip, render it and open the strip. Read its frames left to right as motion.
6. Fix what reads badly and go back to step 3. Two or three rounds is normal.
7. Hand over the set file and the images. Say what `check` still reports and why you left it.

```
python -m pixelrows check art.json --outline o --allow-lone ow
python -m pixelrows sheet art.json --scale 1,8 --out out/sheet.png
python -m pixelrows anim art.json hero_walk --out out
```

`anim` writes `out/hero_walk.gif` and `out/hero_walk_strip.png`, at 8 pixels to the cell unless `--scale` says otherwise. The GIF is for the user. The strip is for you: an image viewer shows you one frame of a GIF, and the strip shows them all with their numbers.

## The set file

One JSON file holds a palette, the sprites, and the clips made of them.

```json
{
  "palette": { "o": "#1b1b26", "g": "#4fae5b", "G": "#2f7d4a", "l": "#8ed97a" },
  "sprites": {
    "blob_0": {
      "rows": [
        "..oooo..",
        ".ollggo.",
        "olggggGo",
        "oggggGGo",
        ".oooooo."
      ]
    },
    "blob_1": {
      "rows": [
        "........",
        ".oooooo.",
        "ollgggGo",
        "oggggGGo",
        ".oooooo."
      ]
    }
  },
  "anims": {
    "blob_idle": { "frames": ["blob_0", "blob_1"], "fps": 3 }
  }
}
```

- A palette key is one character and its value a colour as `#rrggbb`.
- `.` is transparent, always. It has no palette entry.
- Every row of a sprite has the same length, and every frame of a clip has the same size.
- A sprite may carry a `"palette"` of its own beside its `"rows"`. Its entries are laid over the set's for that sprite only, which is how one drawing is recoloured.
- A clip is sprite names in play order and a speed in frames per second. Repeat a name to show it again: `["a", "b", "a", "c"]`.

Keep one row per line, straight under the row above, so the rows read as the picture and a short row stands out. When a row is off, the error names it: `sprite 'hat': row 3 is 11 wide, the others are 12`.

Choose characters that help you read the rows: `o` for the outline, a lower-case letter for a material and its capital for the shade of it.

## Drawing well at this size

- Shape first. Paint the silhouette in one colour with its outline, render it, and see whether the subject can be told from its shape alone. Shading does not rescue a shape that does not read.
- Size to the subject: about 8x8 for a pickup or an icon, 12x16 for a person, 16x16 for a tile, 24 to 32 for something large. Every pixel is one you have to place, so do not go larger than the subject needs.
- One light. Unless the user says otherwise it comes from the upper left: lighter pixels on the top and left of a form, shade on the lower right. Shading inward from every edge makes a pillow, not a form.
- Few colours. At these sizes a material is a base and a shade, plus a highlight where it earns one. `check` counts them.
- An outline in one dark colour that is not pure black, on every edge pixel. Name it with `--outline` and `check` lists the gaps.
- Even slopes. A diagonal keeps a steady step, such as one pixel a row or two pixels a row. A step that changes from row to row looks broken.
- No stray pixels. One pixel of a colour with no neighbour of its kind reads as dirt, unless it is an eye or a glint. `check` lists them: a pixel is lone when none of the eight pixels round it, the diagonal ones included, has its character. Join a shade pixel to others of its colour, and pass the characters that are meant to stand alone with `--allow-lone`.
- Faces stay simple: at 12 pixels wide an eye is one pixel.

Get the shades of a material from `ramp`, so they step evenly in lightness:

```
python -m pixelrows ramp --hue 150 --chroma 0.13 --steps 3 --hue-shift 8 --taper 0.4 --chars Ggl
```

The output has a `"palette"` to paste into the set file. Hue is in degrees: about 30 is red, 55 orange, 110 yellow, 145 green, 195 cyan, 265 blue, 295 purple, 330 magenta. Chroma is 0 for grey, about 0.1 for a muted colour and 0.2 for a vivid one. A positive `--hue-shift` turns the shades one way and the highlights the other, which is livelier than one flat hue.

## Animation

- Change little from frame to frame. Draw the first frame, copy its rows, and edit the copy. A frame redrawn from nothing wobbles against its neighbours.
- Keep the feet on one row and the painted area about the same. `check` reports a clip whose lowest row moves (`feet_drift`) and a frame that paints far more or fewer pixels than the others (`frame_pixels`).
- Speeds that work: an idle of two frames at 2 to 4 fps, with the body one pixel lower in the second; a walk of four frames at 8 to 12; a spin or a flash of three or four frames at 8 to 12.
- Leave headroom. If a frame needs a row the others do not have, give every frame that row.

## Reading `check`

The output has two lists.

- `"problems"` are what stops the file working: a character the palette lacks, a clip naming a sprite that is not there, frames of different sizes. Fix them all.
- `"findings"` come from the drawing rules. Each has a `"rule"`, a `"target"` (the sprite or the clip), a `"message"`, and `"points"` as `[x, y]` pairs counted from the top-left corner, x across and y down. Row `y` of the sprite, character `x`, is the pixel to look at.

A finding can be meant. A coin turning edge-on does lose pixels, and a sparkle is a lone pixel. Say so when you hand the work over.

## Commands

Every command prints JSON. `python -m pixelrows COMMAND -h` lists its options.

| Command | Use |
|---|---|
| `info FILE [NAME ...]` | Sizes, painted counts and the colours each sprite uses |
| `check FILE [--outline CH] [--allow-lone CHARS] [--max-colours N]` | Problems and findings; exit code 1 when there are any |
| `render FILE NAME --out PATH [--scale N] [--background '#rrggbb'] [--flip]` | One sprite as a PNG |
| `sheet FILE [NAME ...] --out PATH [--scale 1,8] [--columns N]` | Sprites on one labelled page; names go straight after FILE |
| `anim FILE NAME --out DIR [--scale N] [--background '#rrggbb']` | A clip as a GIF and as a strip of its frames |
| `ramp --hue H --chroma C [--steps N] [--hue-shift D] [--taper T] [--chars CHARS] [--out PATH]` | The shades of one material |

Sheets and strips put each sprite on a grey plate. If the sprite will sit on a known colour in use, pass it as `--background` and judge it there.
