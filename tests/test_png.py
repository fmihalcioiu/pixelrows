import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pixelrows.errors import PixelRowsError
from pixelrows.png import encode_png, write_png

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_chunks(data):
    """
    Every chunk of a PNG file as (kind, body), in file order.

    Written from the format's definition: eight signature bytes, then chunks of
    a four-byte length, a four-letter kind, the body, and a CRC over kind and body.
    """
    if data[:8] != SIGNATURE:
        raise AssertionError(f"not a PNG signature: {data[:8]!r}")
    chunks = []
    at = 8
    while at < len(data):
        if len(data) - at < 12:
            raise AssertionError(f"{len(data) - at} stray bytes at {at}")
        (length,) = struct.unpack(">I", data[at:at + 4])
        kind = data[at + 4:at + 8]
        body = data[at + 8:at + 8 + length]
        if len(body) != length:
            raise AssertionError(f"chunk {kind!r} says {length} bytes and has {len(body)}")
        crc_bytes = data[at + 8 + length:at + 12 + length]
        if len(crc_bytes) != 4:
            raise AssertionError(f"chunk {kind!r} has no CRC")
        (crc,) = struct.unpack(">I", crc_bytes)
        if crc != zlib.crc32(kind + body) & 0xFFFFFFFF:
            raise AssertionError(f"chunk {kind!r} has a wrong CRC")
        chunks.append((kind, body))
        at += 12 + length
    return chunks


def read_header(body):
    """The IHDR fields by name."""
    names = ("width", "height", "depth", "colour_type", "compression", "filter", "interlace")
    return dict(zip(names, struct.unpack(">IIBBBBB", body)))


def decode(data):
    """A PNG file of the kind this package writes, as (width, height, RGBA bytes)."""
    chunks = read_chunks(data)
    kinds = [kind for kind, _ in chunks]
    if kinds[0] != b"IHDR" or kinds[-1] != b"IEND":
        raise AssertionError(f"chunks out of order: {kinds}")
    header = read_header(chunks[0][1])
    expected = {"depth": 8, "colour_type": 6, "compression": 0, "filter": 0, "interlace": 0}
    for name, value in expected.items():
        if header[name] != value:
            raise AssertionError(f"IHDR {name} is {header[name]}, expected {value}")
    width, height = header["width"], header["height"]
    rows = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    stride = width * 4
    if len(rows) != height * (stride + 1):
        raise AssertionError(f"{len(rows)} bytes inflated, expected {height * (stride + 1)}")
    pixels = bytearray()
    for y in range(height):
        line = rows[y * (stride + 1):(y + 1) * (stride + 1)]
        if line[0] != 0:
            raise AssertionError(f"row {y} has filter {line[0]}, expected 0")
        pixels += line[1:]
    return width, height, bytes(pixels)


def pixel_list(rgba):
    """RGBA bytes as a list of (r, g, b, a)."""
    return [tuple(rgba[at:at + 4]) for at in range(0, len(rgba), 4)]


def pattern(width, height):
    """RGBA bytes in which every channel, alpha included, changes from pixel to pixel."""
    out = bytearray()
    for y in range(height):
        for x in range(width):
            out += bytes(((x * 4 + y) % 256, (y * 4) % 256, (x * y) % 256, (255 - x - y * 3) % 256))
    return bytes(out)


THREE_BY_TWO = bytes([
    255, 0, 0, 255,      0, 255, 0, 128,      0, 0, 255, 0,
    17, 34, 51, 1,       250, 240, 230, 254,  9, 8, 7, 77,
])


class FileLayoutTest(unittest.TestCase):
    def setUp(self):
        self.data = encode_png(3, 2, THREE_BY_TWO)

    def test_returns_bytes(self):
        self.assertIsInstance(self.data, bytes)

    def test_starts_with_the_png_signature(self):
        self.assertEqual(self.data[:8], SIGNATURE)

    def test_chunks_are_header_one_idat_and_end(self):
        self.assertEqual([kind for kind, _ in read_chunks(self.data)], [b"IHDR", b"IDAT", b"IEND"])

    def test_every_chunk_length_and_crc_holds(self):
        at = 8
        seen = 0
        while at < len(self.data):
            (length,) = struct.unpack(">I", self.data[at:at + 4])
            kind_and_body = self.data[at + 4:at + 8 + length]
            self.assertEqual(len(kind_and_body), 4 + length)
            (crc,) = struct.unpack(">I", self.data[at + 8 + length:at + 12 + length])
            self.assertEqual(crc, zlib.crc32(kind_and_body) & 0xFFFFFFFF)
            at += 12 + length
            seen += 1
        self.assertEqual(at, len(self.data))
        self.assertEqual(seen, 3)

    def test_header_is_thirteen_bytes_of_eight_bit_rgba_not_interlaced(self):
        body = read_chunks(self.data)[0][1]
        self.assertEqual(len(body), 13)
        self.assertEqual(read_header(body), {
            "width": 3, "height": 2, "depth": 8, "colour_type": 6,
            "compression": 0, "filter": 0, "interlace": 0,
        })

    def test_end_chunk_is_empty(self):
        self.assertEqual(read_chunks(self.data)[-1], (b"IEND", b""))

    def test_every_row_is_a_filter_byte_of_zero_and_then_its_pixels(self):
        rows = zlib.decompress(read_chunks(self.data)[1][1])
        self.assertEqual(rows, b"\x00" + THREE_BY_TWO[:12] + b"\x00" + THREE_BY_TWO[12:])

    def test_rows_are_deflated_at_level_nine(self):
        idat = read_chunks(self.data)[1][1]
        self.assertEqual(idat, zlib.compress(zlib.decompress(idat), 9))

    def test_the_reader_notices_a_damaged_file(self):
        damaged = bytearray(self.data)
        damaged[20] ^= 0xFF
        with self.assertRaises(AssertionError):
            read_chunks(bytes(damaged))


class RoundTripTest(unittest.TestCase):
    def check(self, width, height, rgba):
        got_width, got_height, got = decode(encode_png(width, height, rgba))
        self.assertEqual((got_width, got_height), (width, height))
        self.assertEqual(pixel_list(got), pixel_list(rgba))

    def test_one_by_one(self):
        self.check(1, 1, bytes([12, 34, 56, 78]))

    def test_one_by_one_fully_transparent(self):
        self.check(1, 1, bytes(4))

    def test_three_by_two_of_distinct_colours_with_mixed_alpha(self):
        self.assertEqual(len(set(pixel_list(THREE_BY_TWO))), 6)
        self.check(3, 2, THREE_BY_TWO)

    def test_three_by_two_is_not_read_as_two_by_three(self):
        width, height, _ = decode(encode_png(3, 2, THREE_BY_TWO))
        self.assertEqual((width, height), (3, 2))
        width, height, _ = decode(encode_png(2, 3, THREE_BY_TWO))
        self.assertEqual((width, height), (2, 3))

    def test_sixty_four_by_sixty_four(self):
        self.check(64, 64, pattern(64, 64))

    def test_one_row_and_one_column(self):
        self.check(7, 1, pattern(7, 1))
        self.check(1, 7, pattern(1, 7))

    def test_a_bytearray_gives_the_same_file_as_bytes(self):
        self.assertEqual(encode_png(3, 2, bytearray(THREE_BY_TWO)), encode_png(3, 2, THREE_BY_TWO))

    def test_the_same_pixels_give_the_same_file(self):
        self.assertEqual(encode_png(64, 64, pattern(64, 64)), encode_png(64, 64, pattern(64, 64)))


class BadInputTest(unittest.TestCase):
    def test_width_below_one(self):
        for width in (0, -1):
            with self.subTest(width=width):
                with self.assertRaisesRegex(PixelRowsError, "width"):
                    encode_png(width, 1, b"")

    def test_height_below_one(self):
        for height in (0, -1):
            with self.subTest(height=height):
                with self.assertRaisesRegex(PixelRowsError, "height"):
                    encode_png(1, height, b"")

    def test_a_size_that_is_not_a_whole_number(self):
        for bad in (1.0, "1", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    encode_png(bad, 1, bytes(4))
                with self.assertRaises(PixelRowsError):
                    encode_png(1, bad, bytes(4))

    def test_too_few_bytes(self):
        with self.assertRaisesRegex(PixelRowsError, "3x2 needs 24 bytes of RGBA, got 23"):
            encode_png(3, 2, THREE_BY_TWO[:-1])

    def test_too_many_bytes(self):
        with self.assertRaisesRegex(PixelRowsError, "3x2 needs 24 bytes of RGBA, got 25"):
            encode_png(3, 2, THREE_BY_TWO + b"\x00")

    def test_rgb_without_alpha_is_the_wrong_length(self):
        with self.assertRaises(PixelRowsError):
            encode_png(2, 2, bytes(12))

    def test_pixels_that_are_not_bytes(self):
        for bad in ([0, 0, 0, 0], "abcd", None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    encode_png(1, 1, bad)

    def test_the_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            encode_png(0, 0, b"")


class WritePngTest(unittest.TestCase):
    def test_writes_what_encode_png_gives(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "three.png"
            write_png(path, 3, 2, THREE_BY_TWO)
            self.assertEqual(path.read_bytes(), encode_png(3, 2, THREE_BY_TWO))

    def test_the_file_reads_back_pixel_for_pixel(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pattern.png"
            write_png(path, 64, 64, pattern(64, 64))
            width, height, got = decode(path.read_bytes())
        self.assertEqual((width, height), (64, 64))
        self.assertEqual(pixel_list(got), pixel_list(pattern(64, 64)))

    def test_creates_parent_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "sheets" / "deep" / "one.png"
            write_png(path, 1, 1, bytes([1, 2, 3, 4]))
            self.assertTrue(path.is_file())
            self.assertEqual(decode(path.read_bytes()), (1, 1, bytes([1, 2, 3, 4])))

    def test_takes_a_path_as_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sub" / "text.png"
            write_png(str(path), 1, 1, bytes([9, 9, 9, 255]))
            self.assertEqual(decode(path.read_bytes()), (1, 1, bytes([9, 9, 9, 255])))

    def test_writes_over_a_file_that_is_there(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "again.png"
            write_png(path, 3, 2, THREE_BY_TWO)
            write_png(path, 1, 1, bytes([5, 6, 7, 8]))
            self.assertEqual(decode(path.read_bytes()), (1, 1, bytes([5, 6, 7, 8])))

    def test_bad_input_raises_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "never" / "bad.png"
            with self.assertRaises(PixelRowsError):
                write_png(path, 2, 2, bytes(15))
            self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
