"""The anim command: one anim as a GIF file and as a strip of its frames."""
from __future__ import annotations

import argparse
import os

from ..anim import save_gif
from ..info import anim_info
from ..sheet import PLATE, anim_strip
from . import emit, load_set

NAME = "anim"
HELP = "write one anim as a GIF and as a strip of its frames"


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("file", metavar="FILE", help="the set file")
    parser.add_argument("name", metavar="NAME", help="the anim to play")
    parser.add_argument("--out", required=True, metavar="DIR",
                        help="the folder that NAME.gif and NAME_strip.png are written to")
    parser.add_argument("--scale", type=int, default=8, metavar="N", help="pixels to the cell (default: 8)")
    parser.add_argument("--background", metavar="COLOUR",
                        help=f"'#rrggbb' behind the frames (default: a transparent GIF, and {PLATE} in the strip)")
    parser.add_argument("--no-labels", dest="labels", action="store_false",
                        help="leave the title, the numbers and the names out of the strip")


def run(args: argparse.Namespace) -> int:
    """
    Writes the anim as a GIF and its frames as a strip, prints the two paths and the clip's timing, and returns 0.

    The GIF is on the background when one is given, else it is transparent.
    The strip's plates are the background, or PLATE without one.
    """
    spriteset = load_set(args.file)
    anim = spriteset.anim(args.name)
    gif = os.path.join(args.out, f"{anim.name}.gif")
    strip = os.path.join(args.out, f"{anim.name}_strip.png")
    plate = PLATE if args.background is None else args.background
    page = anim_strip(spriteset, anim, args.scale, plate, args.labels)
    save_gif(gif, spriteset, anim, args.scale, args.background)
    page.save(strip)
    info = anim_info(spriteset, anim)
    emit({"gif": gif, "strip": strip, "frames": info["frames"], "fps": info["fps"], "seconds": info["seconds"]})
    return 0
