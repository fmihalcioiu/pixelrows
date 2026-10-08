"""The sheet command: a contact sheet of sprites as a PNG file."""
from __future__ import annotations

import argparse

from ..sheet import PLATE, contact_sheet
from . import emit, load_set, scale_list

NAME = "sheet"
HELP = "write a contact sheet of sprites as a PNG"


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("file", metavar="FILE", help="the set file")
    parser.add_argument("names", nargs="*", metavar="NAME",
                        help="the sprites to show, in this order (default: every sprite of the set)")
    parser.add_argument("--out", required=True, metavar="PATH", help="the PNG file to write")
    parser.add_argument("--scale", type=scale_list, default=[8], metavar="N,N",
                        help="the scales each sprite is drawn at, with commas between them (default: 8)")
    parser.add_argument("--background", default=PLATE, metavar="COLOUR",
                        help=f"'#rrggbb' of the plate behind each sprite (default: {PLATE})")
    parser.add_argument("--columns", type=int, metavar="N",
                        help="how many sprites go in a row (default: as many as fit the page)")
    parser.add_argument("--no-labels", dest="labels", action="store_false",
                        help="leave out the names and the sizes")


def run(args: argparse.Namespace) -> int:
    """Writes the contact sheet as a PNG, prints the path, the page's size and the sprites on it, and returns 0."""
    spriteset = load_set(args.file)
    names = args.names or list(spriteset.sprites)
    page = contact_sheet(spriteset, names, args.scale, args.background, args.columns, args.labels)
    page.save(args.out)
    emit({"wrote": args.out, "width": page.width, "height": page.height, "sprites": names})
    return 0
