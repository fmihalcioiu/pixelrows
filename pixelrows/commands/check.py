"""The check command: what a set file has wrong, and what the rules find in it."""
from __future__ import annotations

import argparse

from .. import checks
from . import emit, load_set

NAME = "check"
HELP = "print the problems of a set file and what the rules find in it"


def configure(parser: argparse.ArgumentParser) -> None:
    """Gives the parser the command's arguments."""
    parser.add_argument("file", metavar="FILE", help="the set file")
    parser.add_argument("--outline", metavar="CH",
                        help="the outline character (default: outlines are not checked)")
    parser.add_argument("--allow-lone", default="", metavar="CHARS",
                        help="the characters a lone pixel may be, such as eyes and glints")
    parser.add_argument("--max-colours", type=int, metavar="N",
                        help="how many colours a sprite may use (default: worked out from its size)")


def run(args: argparse.Namespace) -> int:
    """
    Prints the set's problems and the findings of every rule.

    Returns 1 when there is a problem or a finding, else 0. PixelRowsError for
    an option the rules refuse, raised before the file is read.
    """
    options = checks.Options(
        outline=args.outline,
        lone_allow=frozenset(args.allow_lone),
        max_colours=args.max_colours,
    )
    spriteset = load_set(args.file)
    problems = spriteset.problems()
    findings = [finding.to_dict() for finding in checks.run(spriteset, options)]
    emit({"problems": problems, "findings": findings})
    return 1 if problems or findings else 0
