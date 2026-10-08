"""The command line: python -m pixelrows <command> ..."""
from __future__ import annotations

import argparse
import pkgutil
import sys
from collections.abc import Sequence
from importlib import import_module

from . import commands
from .errors import PixelRowsError


def main(argv: Sequence[str] | None = None) -> int:
    """
    Runs the command that `argv` names and returns its exit code.

    `argv` is the command line after the program's name, read from `sys.argv`
    when None. Every module of `pixelrows.commands` is a command, and they are
    listed in the order of their names. A PixelRowsError or an OSError from
    the command is printed to standard error as `error: <message>` and the
    code is 2. With no command the help is printed to standard error and the
    code is 2.
    """
    parser = argparse.ArgumentParser(prog="pixelrows", description="Pixel art as rows of text.")
    subparsers = parser.add_subparsers(dest="command", title="commands")
    runs = {}
    for name in sorted(module.name for module in pkgutil.iter_modules(commands.__path__)):
        module = import_module(f"{commands.__name__}.{name}")
        module.configure(subparsers.add_parser(module.NAME, help=module.HELP, description=module.HELP))
        runs[module.NAME] = module.run
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return runs[args.command](args)
    except (PixelRowsError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
