"""The info command: plain numbers about what a set file holds."""
from __future__ import annotations

import argparse

from ..errors import PixelRowsError
from ..info import set_info
from . import emit, load_set

NAME = "info"
HELP = "print what a set file holds: its palette, sprites, anims and problems"


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("file", metavar="FILE", help="the set file")
    parser.add_argument("names", nargs="*", metavar="NAME", help="show only these sprites and anims")


def run(args: argparse.Namespace) -> int:
    """
    Prints the set's info and returns 0.

    With names, only the sprites and anims of those names are listed, in the
    set's order. PixelRowsError for a name that is neither.
    """
    spriteset = load_set(args.file)
    for name in args.names:
        if name not in spriteset.sprites and name not in spriteset.anims:
            raise PixelRowsError(f"no sprite or anim named {name!r}")
    info = set_info(spriteset)
    if args.names:
        for key in ("sprites", "anims"):
            info[key] = [entry for entry in info[key] if entry["name"] in args.names]
    emit(info)
    return 0
