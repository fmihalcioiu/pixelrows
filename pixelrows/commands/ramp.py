"""The ramp command: a colour ramp as data, as a palette and as a swatch."""
from __future__ import annotations

import argparse

from ..errors import PixelRowsError
from ..image import Image
from ..palette import Palette
from ..ramp import Step, even_lightness, ramp
from . import emit

NAME = "ramp"
HELP = "print a colour ramp: one material from dark to light"

#: The side of one square of the swatch, in pixels.
_SQUARE = 32


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("--hue", type=float, required=True, metavar="H",
                        help="the hue at the middle of the ramp, in degrees")
    parser.add_argument("--chroma", type=float, required=True, metavar="C",
                        help="the chroma at the middle of the ramp")
    parser.add_argument("--steps", type=int, default=5, metavar="N", help="how many steps (default: 5)")
    parser.add_argument("--darkest", type=float, default=0.30, metavar="L",
                        help="the lightness of the first step, 0 to 1 (default: 0.30)")
    parser.add_argument("--lightest", type=float, default=0.82, metavar="L",
                        help="the lightness of the last step, 0 to 1 (default: 0.82)")
    parser.add_argument("--hue-shift", type=float, default=0.0, metavar="D",
                        help="degrees the hue turns from one step to the next (default: 0)")
    parser.add_argument("--taper", type=float, default=0.0, metavar="T",
                        help="the share of chroma lost at the two ends, 0 to 1 (default: 0)")
    parser.add_argument("--chars", metavar="CHARS",
                        help="one character a step, to print the ramp as a palette as well")
    parser.add_argument("--out", metavar="PATH", help="a PNG file to write a swatch of the ramp to")


def run(args: argparse.Namespace) -> int:
    """
    Prints the steps of the ramp and returns 0.

    With `--chars` the ramp is printed as a palette as well, one character a
    step. With `--out` a swatch is written: one square a step, left to right
    in the order of the steps.
    """
    lightness = even_lightness(args.steps, args.darkest, args.lightest)
    steps = ramp(args.hue, args.chroma, lightness, args.hue_shift, args.taper)
    data: dict = {"steps": [step.to_dict() for step in steps]}
    if args.chars is not None:
        data["palette"] = _palette(args.chars, steps)
    if args.out is not None:
        swatch = Image(_SQUARE * len(steps), _SQUARE)
        for index, step in enumerate(steps):
            swatch.fill(index * _SQUARE, 0, _SQUARE, _SQUARE, step.hex)
        swatch.save(args.out)
    emit(data)
    return 0


def _palette(chars: str, steps: list[Step]) -> dict[str, str]:
    """
    Character to '#rrggbb', the characters of `chars` given to the steps in order.

    PixelRowsError unless `chars` is one character a step, each of them once
    and each of them a character a palette can hold.
    """
    if len(chars) != len(steps):
        raise PixelRowsError(f"--chars has {len(chars)} characters for {len(steps)} steps, it takes one a step")
    if len(set(chars)) != len(chars):
        raise PixelRowsError(f"--chars has a character twice in {chars!r}, each step takes its own")
    return Palette({ch: step.hex for ch, step in zip(chars, steps)}).to_dict()
