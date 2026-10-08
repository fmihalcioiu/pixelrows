"""The render command: one sprite as a PNG file."""
from __future__ import annotations

import argparse

from ..render import render_sprite
from . import emit, load_set

NAME = "render"
HELP = "write one sprite as a PNG"


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("file", metavar="FILE", help="the set file")
    parser.add_argument("name", metavar="NAME", help="the sprite to draw")
    parser.add_argument("--out", required=True, metavar="PATH", help="the PNG file to write")
    parser.add_argument("--scale", type=int, default=8, metavar="N", help="pixels to the cell (default: 8)")
    parser.add_argument("--background", metavar="COLOUR", help="'#rrggbb' behind the sprite (default: transparent)")
    parser.add_argument("--flip", action="store_true", help="draw the sprite turned left to right")


def run(args: argparse.Namespace) -> int:
    """Writes the sprite as a PNG, prints the path and the picture's size, and returns 0."""
    spriteset = load_set(args.file)
    sprite = spriteset.sprite(args.name)
    image = render_sprite(sprite, spriteset.palette_for(sprite), args.scale, args.background, args.flip)
    image.save(args.out)
    emit({"wrote": args.out, "width": image.width, "height": image.height})
    return 0
