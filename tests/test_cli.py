import argparse
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pixelrows
from pixelrows import commands
from pixelrows.cli import main
from pixelrows.commands import emit, load_set, scale_list
from pixelrows.errors import PixelRowsError
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

PALETTE = {"o": "#1a1a22", "g": "#58a84c"}
BLOB_0 = ["..oo..", ".oggo.", "oggggo", "oooooo"]
BLOB_1 = ["......", ".oooo.", "oggggo", "oooooo"]

#: A command module written by the tests. `{name}` is its file's name and its command's.
PROBE = '''\
"""A command made by the tests."""
from pixelrows.commands import emit
from pixelrows.errors import PixelRowsError

NAME = "{name}"
HELP = "a command made by the tests"


def configure(parser):
    parser.add_argument("--code", type=int, default=0)
    parser.add_argument("--fail", choices=("pixelrows", "os"))


def run(args):
    if args.fail == "pixelrows":
        raise PixelRowsError("row 3 is 11 wide, the others are 12")
    if args.fail == "os":
        raise OSError("the disk is full")
    emit({{"ran": NAME, "code": args.code}})
    return args.code
'''


def blob_set():
    """Two frames of a blob and the clip that plays them."""
    spriteset = SpriteSet(PALETTE)
    spriteset.add(Sprite("blob_0", BLOB_0))
    spriteset.add(Sprite("blob_1", BLOB_1, {"g": "#7cc86a"}))
    spriteset.add_anim("blob_idle", ["blob_0", "blob_1"], 3)
    return spriteset


def run_main(argv):
    """What `main(argv)` returned, what it printed to standard output and what it printed to standard error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def exit_of(argv):
    """The code `main(argv)` left with through SystemExit, and what it printed on the way."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            main(argv)
        except SystemExit as left:
            return left.code, out.getvalue(), err.getvalue()
    raise AssertionError(f"main({argv!r}) did not leave through SystemExit")


@contextlib.contextmanager
def probes(*names):
    """A PROBE command file of each name in the commands package, for as long as the block runs."""
    with tempfile.TemporaryDirectory() as folder:
        for name in names:
            Path(folder, f"{name}.py").write_text(PROBE.format(name=name), encoding="utf-8")
        commands.__path__.append(folder)
        try:
            yield
        finally:
            commands.__path__.remove(folder)
            sys.path_importer_cache.pop(folder, None)
            for name in names:
                sys.modules.pop(f"{commands.__name__}.{name}", None)
                if hasattr(commands, name):
                    delattr(commands, name)


def listed(help_text):
    """The commands a help text offers, in the order it lists them."""
    return re.search(r"\{([^}]*)\}", help_text).group(1).split(",")


class ParserTest(unittest.TestCase):
    def test_no_command_prints_the_help_to_standard_error_and_returns_2(self):
        code, out, err = run_main([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("usage: pixelrows "), err)
        self.assertIn("info", listed(err))

    def test_the_help_flag_prints_the_help_and_exits_with_0(self):
        code, out, err = exit_of(["--help"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("usage: pixelrows "), out)
        self.assertEqual(err, "")

    def test_a_command_has_a_help_of_its_own(self):
        code, out, err = exit_of(["info", "--help"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("usage: pixelrows info "), out)

    def test_an_unknown_command_exits_with_2(self):
        code, out, err = exit_of(["polish"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("polish", err)

    def test_a_command_missing_an_argument_exits_with_2(self):
        code, out, err = exit_of(["info"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("FILE", err)

    def test_a_new_file_in_the_commands_package_is_a_new_command(self):
        with probes("probe"):
            code, out, err = run_main(["probe"])
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(json.loads(out), {"ran": "probe", "code": 0})
            self.assertIn("probe", listed(run_main([])[2]))
        self.assertNotIn("probe", listed(run_main([])[2]))

    def test_commands_are_listed_in_name_order(self):
        with probes("zzz", "aaa"):
            names = listed(run_main([])[2])
        self.assertEqual(names[0], "aaa")
        self.assertEqual(names[-1], "zzz")
        self.assertIn("info", names)
        self.assertEqual(names, sorted(names))

    def test_the_code_of_the_command_is_returned(self):
        with probes("probe"):
            self.assertEqual(run_main(["probe"])[0], 0)
            self.assertEqual(run_main(["probe", "--code", "1"])[0], 1)
            self.assertEqual(run_main(["probe", "--code", "7"])[0], 7)


class ErrorPathTest(unittest.TestCase):
    def test_a_pixelrows_error_is_printed_to_standard_error_and_the_code_is_2(self):
        with probes("probe"):
            code, out, err = run_main(["probe", "--fail", "pixelrows"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: row 3 is 11 wide, the others are 12\n")

    def test_an_os_error_is_printed_to_standard_error_and_the_code_is_2(self):
        with probes("probe"):
            code, out, err = run_main(["probe", "--fail", "os"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "error: the disk is full\n")

    def test_a_file_that_is_not_a_set_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "broken.json")
            path.write_text("{", encoding="utf-8")
            code, out, err = run_main(["info", str(path)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith(f"error: {path}: not JSON at line 1"), err)

    def test_a_folder_given_as_the_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, err = run_main(["info", folder])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: "), err)
        self.assertEqual(err.count("\n"), 1)


class ModuleRunTest(unittest.TestCase):
    def test_python_m_pixelrows_runs_a_command(self):
        root = Path(pixelrows.__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "blob.json")
            blob_set().save(path)
            done = subprocess.run(
                [sys.executable, "-m", "pixelrows", "info", str(path)],
                cwd=root, capture_output=True, text=True,
            )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "")
        data = json.loads(done.stdout)
        self.assertEqual([sprite["name"] for sprite in data["sprites"]], ["blob_0", "blob_1"])

    def test_python_m_pixelrows_leaves_with_the_code_of_main(self):
        root = Path(pixelrows.__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run(
                [sys.executable, "-m", "pixelrows", "info", str(Path(folder, "none.json"))],
                cwd=root, capture_output=True, text=True,
            )
        self.assertEqual(done.returncode, 2)
        self.assertEqual(done.stdout, "")
        self.assertTrue(done.stderr.startswith("error: no such file: "), done.stderr)


class EmitTest(unittest.TestCase):
    def test_prints_one_json_document_indented_by_2(self):
        data = {"wrote": "out/hat.png", "width": 96, "sizes": [1, 8], "bbox": None}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            emit(data)
        self.assertEqual(out.getvalue(), json.dumps(data, indent=2) + "\n")
        self.assertEqual(json.loads(out.getvalue()), data)
        self.assertIn('\n  "width": 96,\n', out.getvalue())


class LoadSetTest(unittest.TestCase):
    def test_reads_a_set_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "blob.json")
            blob_set().save(path)
            self.assertEqual(load_set(path), blob_set())
            self.assertEqual(load_set(str(path)), blob_set())

    def test_a_missing_file_is_a_pixelrows_error_naming_the_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder, "none.json"))
            with self.assertRaises(PixelRowsError) as raised:
                load_set(path)
        self.assertEqual(str(raised.exception), f"no such file: {path}")

    def test_an_error_in_the_file_passes_through(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "odd.json")
            path.write_text('{"sprites": {"hat": {"rows": ["oo", "o"]}}}', encoding="utf-8")
            with self.assertRaises(PixelRowsError) as raised:
                load_set(path)
        self.assertIn("sprite 'hat'", str(raised.exception))


class ScaleListTest(unittest.TestCase):
    def test_one_number_is_a_list_of_one(self):
        self.assertEqual(scale_list("8"), [8])

    def test_numbers_with_commas_between_them_stay_in_order(self):
        self.assertEqual(scale_list("1,8"), [1, 8])
        self.assertEqual(scale_list("8,1,4"), [8, 1, 4])

    def test_spaces_around_a_number_are_dropped(self):
        self.assertEqual(scale_list("1, 8"), [1, 8])

    def test_anything_but_whole_numbers_of_1_or_more_is_refused(self):
        for text in ("", "0", "1,0", "-2", "1.5", "x", "1,,8", "1,8,", "1 8"):
            with self.subTest(text=text):
                with self.assertRaises(argparse.ArgumentTypeError) as raised:
                    scale_list(text)
                self.assertIn(repr(text), str(raised.exception))


if __name__ == "__main__":
    unittest.main()
