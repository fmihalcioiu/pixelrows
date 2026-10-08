"""The commands of the command line, one module each, and what they share."""
from __future__ import annotations

import argparse
import json
from os import PathLike

from ..errors import PixelRowsError
from ..spriteset import SpriteSet


def emit(data: object) -> None:
    """Prints `data` to standard output as one JSON document."""
    print(json.dumps(data, indent=2))


def load_set(path: str | PathLike[str]) -> SpriteSet:
    """Reads a set file. PixelRowsError if there is no such file, or if it is not a set."""
    try:
        return SpriteSet.load(path)
    except FileNotFoundError:
        raise PixelRowsError(f"no such file: {path}") from None


def scale_list(text: str) -> list[int]:
    """
    '1,8' as [1, 8]: whole numbers of 1 or more with commas between them.

    It is an argparse `type`, so anything else raises
    argparse.ArgumentTypeError and argparse reports the argument as wrong.
    """
    scales = []
    for part in text.split(","):
        part = part.strip()
        if not (part.isascii() and part.isdigit()) or int(part) < 1:
            raise argparse.ArgumentTypeError(
                f"scales are whole numbers of 1 or more with commas between them, got {text!r}"
            )
        scales.append(int(part))
    return scales
