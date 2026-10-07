import random
import struct
import tempfile
import unittest
from pathlib import Path

from pixelrows.errors import PixelRowsError
from pixelrows.gif import encode_gif, write_gif


# A GIF reader for these tests, written from the format's definition. It takes
# nothing from the package: it only reads the bytes that encode_gif returns.


def read_blocks(data, pos):
    """The data sub-blocks starting at `pos`, and the position just past the empty block that ends them."""
    blocks = []
    while True:
        size = data[pos]
        pos += 1
        if size == 0:
            return blocks, pos
        if pos + size > len(data):
            raise AssertionError("a sub-block runs past the end of the file")
        blocks.append(data[pos:pos + size])
        pos += size


def lzw_decode(data, min_code_size):
    """
    Reads a GIF code stream back into indices.

    Returns the indices, one (code size, table length) pair for each clear code
    as it was read, and the set of code sizes that codes were read at.
    """
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    strings = None    # code to the indices it stands for; None until the first clear code
    previous = None   # the string of the code before this one; None straight after a clear code
    out = bytearray()
    clears = []
    sizes = set()
    buffer = 0
    held = 0
    pos = 0
    while True:
        while held < code_size:
            if pos == len(data):
                raise AssertionError("the code stream stops before an end code")
            buffer |= data[pos] << held
            held += 8
            pos += 1
        code = buffer & ((1 << code_size) - 1)
        buffer >>= code_size
        held -= code_size
        sizes.add(code_size)
        if code == clear:
            clears.append((code_size, 0 if strings is None else len(strings)))
            # The single indices, then two places kept for the clear code and the end code.
            strings = [bytes([i]) for i in range(clear)] + [None, None]
            code_size = min_code_size + 1
            previous = None
            continue
        if code == end:
            break
        if strings is None:
            raise AssertionError("the code stream does not start with a clear code")
        if previous is None:
            if code > end:
                raise AssertionError(f"code {code} straight after a clear code is not a single index")
            string = strings[code]
        else:
            if code < len(strings):
                string = strings[code]
            elif code == len(strings):
                # The one code that may come before it is in the table:
                # the string before it, plus that string's own first index.
                string = previous + previous[:1]
            else:
                raise AssertionError(f"code {code} is beyond the table of {len(strings)}")
            if len(strings) < 4096:
                strings.append(previous + string[:1])
        out += string
        previous = string
        if len(strings) == 1 << code_size and code_size < 12:
            code_size += 1
    if pos != len(data):
        raise AssertionError("bytes follow the end code")
    return bytes(out), clears, sizes


def read_gif(data):
    """Takes a GIF file apart block by block and returns what it holds."""
    width, height, packed, background, aspect = struct.unpack_from("<HHBBB", data, 6)
    gif = {
        "signature": bytes(data[:6]),
        "width": width,
        "height": height,
        "has_table": bool(packed & 0x80),
        "background": background,
        "aspect": aspect,
        "table": [],
        "loop": None,
        "frames_before_loop": None,
        "frames": [],
    }
    pos = 13
    if packed & 0x80:
        count = 2 << (packed & 7)
        gif["table"] = [tuple(data[pos + 3 * i:pos + 3 * i + 3]) for i in range(count)]
        pos += 3 * count
    control = None
    while True:
        kind = data[pos]
        pos += 1
        if kind == 0x3B:
            break
        if kind == 0x21:
            label = data[pos]
            blocks, pos = read_blocks(data, pos + 1)
            if label == 0xF9:
                if [len(block) for block in blocks] != [4]:
                    raise AssertionError("a graphic control extension is one block of 4 bytes")
                flags, delay, index = struct.unpack("<BHB", blocks[0])
                control = {
                    "delay": delay,
                    "disposal": (flags >> 2) & 7,
                    "user_input": bool(flags & 2),
                    "has_transparent": bool(flags & 1),
                    "transparent": index,
                }
            elif label == 0xFF:
                if blocks[0] != b"NETSCAPE2.0" or len(blocks) != 2 or len(blocks[1]) != 3 or blocks[1][0] != 1:
                    raise AssertionError(f"an application extension that is not a loop count: {blocks!r}")
                gif["loop"] = struct.unpack("<H", blocks[1][1:])[0]
                gif["frames_before_loop"] = len(gif["frames"])
            else:
                raise AssertionError(f"an extension with the label {label:#04x}")
        elif kind == 0x2C:
            left, top, frame_width, frame_height, flags = struct.unpack_from("<HHHHB", data, pos)
            pos += 9
            if flags & 0x80:
                raise AssertionError("a frame has a colour table of its own")
            if flags & 0x40:
                raise AssertionError("a frame is interlaced")
            min_code_size = data[pos]
            blocks, pos = read_blocks(data, pos + 1)
            pixels, clears, sizes = lzw_decode(b"".join(blocks), min_code_size)
            if len(pixels) != frame_width * frame_height:
                raise AssertionError(
                    f"a frame of {frame_width}x{frame_height} decodes to {len(pixels)} pixels"
                )
            gif["frames"].append({
                "left": left,
                "top": top,
                "width": frame_width,
                "height": frame_height,
                "min_code_size": min_code_size,
                "pixels": pixels,
                "clears": clears,
                "code_sizes": sizes,
                "blocks": [len(block) for block in blocks],
                "control": control,
            })
            control = None
        else:
            raise AssertionError(f"a block that starts with {kind:#04x} at byte {pos - 1}")
    if pos != len(data):
        raise AssertionError("bytes follow the trailer")
    return gif


def colours(count):
    """`count` different colours, none of them black."""
    return [(i, 255 - i, (i * 7 + 1) % 256) for i in range(count)]


def noise(count, indices, seed=1):
    """`count` indices below `indices`, from a seeded generator."""
    rng = random.Random(seed)
    return bytes(rng.randrange(indices) for _ in range(count))


class GifTestCase(unittest.TestCase):
    def assertSamePixels(self, got, want):
        """Compares two frames without printing them whole when they differ."""
        self.assertEqual(len(got), len(want))
        if got != want:
            at = next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)
            self.fail(f"pixel {at} is {got[at]}, expected {want[at]}")

    def round_trip(self, width, height, frame, palette):
        """Encodes one frame, reads it back, holds its pixels, and returns what was read of the frame."""
        gif = read_gif(encode_gif(width, height, [frame], palette, [0]))
        self.assertEqual(len(gif["frames"]), 1)
        self.assertSamePixels(gif["frames"][0]["pixels"], bytes(frame))
        return gif["frames"][0]


class FileLayoutTest(GifTestCase):
    def test_starts_with_the_gif89a_signature_and_ends_with_the_trailer(self):
        data = encode_gif(1, 1, [b"\x00"], [(1, 2, 3)], [0])
        self.assertEqual(data[:6], b"GIF89a")
        self.assertEqual(data[-1:], b"\x3b")
        self.assertEqual(read_gif(data)["signature"], b"GIF89a")

    def test_screen_size_is_read_back(self):
        gif = read_gif(encode_gif(300, 2, [bytes(600)], colours(2), [0]))
        self.assertEqual((gif["width"], gif["height"]), (300, 2))

    def test_table_is_the_next_power_of_two_that_holds_the_palette(self):
        sizes = {1: 2, 2: 2, 3: 4, 4: 4, 5: 8, 8: 8, 9: 16, 16: 16, 17: 32, 32: 32,
                 33: 64, 64: 64, 65: 128, 128: 128, 129: 256, 255: 256, 256: 256}
        for count, size in sizes.items():
            with self.subTest(colours=count):
                palette = colours(count)
                gif = read_gif(encode_gif(1, 1, [bytes([count - 1])], palette, [0]))
                self.assertTrue(gif["has_table"])
                self.assertEqual(len(gif["table"]), size)
                self.assertEqual(gif["table"][:count], palette)

    def test_three_colours_sit_in_a_table_of_four_padded_with_black(self):
        palette = [(255, 0, 0), (0, 255, 0), (10, 20, 30)]
        gif = read_gif(encode_gif(3, 1, [b"\x00\x01\x02"], palette, [0]))
        self.assertEqual(gif["table"], palette + [(0, 0, 0)])

    def test_every_entry_past_the_palette_is_black(self):
        for count in (1, 5, 17, 100, 129):
            with self.subTest(colours=count):
                gif = read_gif(encode_gif(1, 1, [b"\x00"], colours(count), [0]))
                padding = gif["table"][count:]
                self.assertTrue(padding)
                self.assertEqual(set(padding), {(0, 0, 0)})

    def test_256_colours_fill_the_table_with_no_padding(self):
        palette = colours(256)
        gif = read_gif(encode_gif(1, 1, [b"\xff"], palette, [0]))
        self.assertEqual(gif["table"], palette)

    def test_minimum_code_size_is_the_bits_of_the_table_and_never_below_two(self):
        expected = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 8: 3, 9: 4, 16: 4, 17: 5, 32: 5,
                    33: 6, 64: 6, 65: 7, 128: 7, 129: 8, 256: 8}
        for count, code_size in expected.items():
            with self.subTest(colours=count):
                frame = self.round_trip(1, 1, bytes([count - 1]), colours(count))
                self.assertEqual(frame["min_code_size"], code_size)

    def test_frames_cover_the_screen(self):
        gif = read_gif(encode_gif(5, 4, [bytes(20), bytes(20)], colours(2), [1, 1]))
        for frame in gif["frames"]:
            self.assertEqual((frame["left"], frame["top"], frame["width"], frame["height"]), (0, 0, 5, 4))


class PixelsTest(GifTestCase):
    def test_one_by_one(self):
        frame = self.round_trip(1, 1, b"\x00", [(9, 9, 9)])
        self.assertEqual(frame["pixels"], b"\x00")

    def test_two_colours(self):
        self.round_trip(4, 3, bytes([0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]), colours(2))

    def test_three_colours(self):
        self.round_trip(3, 3, bytes([0, 1, 2, 2, 2, 1, 1, 0, 0]), colours(3))

    def test_all_256_colours(self):
        self.round_trip(16, 16, bytes(range(256)), colours(256))
        self.round_trip(16, 16, bytes(reversed(range(256))), colours(256))

    def test_frames_may_be_bytearrays(self):
        self.round_trip(2, 2, bytearray([3, 2, 1, 0]), colours(4))

    def test_noise_over_256_indices_fills_and_clears_the_table_more_than_once(self):
        frame = self.round_trip(200, 200, noise(200 * 200, 256), colours(256))
        clears = frame["clears"]
        # The first clear code opens the stream, at the starting size of 9 bits.
        self.assertEqual(clears[0], (9, 0))
        self.assertGreater(len(clears), 2)
        # Every later one is 12 bits wide and comes as the table fills: the
        # reader, which makes each entry one code after the writer, holds 4095.
        self.assertEqual(set(clears[1:]), {(12, 4095)})
        self.assertEqual(frame["code_sizes"], {9, 10, 11, 12})

    def test_noise_over_two_indices_is_read_at_every_code_size_from_3_to_12(self):
        frame = self.round_trip(300, 300, noise(300 * 300, 2), colours(2))
        self.assertEqual(frame["code_sizes"], set(range(3, 13)))
        self.assertEqual(frame["clears"][0], (3, 0))
        self.assertGreater(len(frame["clears"]), 1)
        self.assertEqual(set(frame["clears"][1:]), {(12, 4095)})

    def test_300_by_300_of_one_index(self):
        for count, index in ((2, 1), (8, 5), (256, 255)):
            with self.subTest(colours=count, index=index):
                frame = self.round_trip(300, 300, bytes([index]) * 90000, colours(count))
                # Runs that grow by one pixel a code: far fewer codes than the table holds.
                self.assertEqual(len(frame["clears"]), 1)
                self.assertLess(sum(frame["blocks"]), 1000)

    def test_long_runs_of_several_indices(self):
        pixels = b"".join(bytes([index]) * 5000 for index in (0, 3, 0, 1, 2, 2, 3, 0))
        self.round_trip(200, 200, pixels, colours(4))

    def test_every_length_reads_back_whichever_code_the_stream_ends_on(self):
        # One pixel more at a time, so the last code lands on each side of every
        # step in the code size, and the end code has to be the right width.
        for count, longest in ((2, 250), (4, 400), (256, 600)):
            pixels = noise(longest, count, seed=7)
            palette = colours(count)
            for length in range(1, longest + 1):
                with self.subTest(colours=count, length=length):
                    self.round_trip(length, 1, pixels[:length], palette)

    def test_every_table_size_reads_back(self):
        for count in (1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 33, 64, 65, 128, 129, 255, 256):
            with self.subTest(colours=count):
                self.round_trip(64, 64, noise(64 * 64, count, seed=count), colours(count))

    def test_data_blocks_are_full_but_for_the_last(self):
        frame = self.round_trip(200, 200, noise(200 * 200, 256), colours(256))
        blocks = frame["blocks"]
        self.assertGreater(len(blocks), 1)
        self.assertEqual(set(blocks[:-1]), {255})
        self.assertTrue(1 <= blocks[-1] <= 255)

    def test_a_stream_of_exactly_255_bytes_is_one_full_block(self):
        # Widths around the one whose stream is 255 bytes long: none may leave an empty block behind.
        pixels = noise(400, 256, seed=3)
        seen = set()
        for length in range(200, 260):
            frame = self.round_trip(length, 1, pixels[:length], colours(256))
            self.assertNotIn(0, frame["blocks"])
            seen.add(tuple(frame["blocks"]))
        self.assertIn((255,), seen)
        self.assertIn((255, 1), seen)


class FramesTest(GifTestCase):
    def setUp(self):
        self.palette = colours(4)
        self.frames = [bytes([0, 1, 2, 3, 3, 2]), bytes([3, 3, 3, 0, 0, 0]),
                       bytes([1, 0, 1, 0, 1, 0]), bytes([2, 2, 2, 2, 2, 2])]

    def test_frames_come_back_in_order_each_with_its_own_delay(self):
        delays = [0, 7, 100, 65535]
        gif = read_gif(encode_gif(3, 2, self.frames, self.palette, delays))
        self.assertEqual([frame["pixels"] for frame in gif["frames"]], self.frames)
        self.assertEqual([frame["control"]["delay"] for frame in gif["frames"]], delays)

    def test_every_frame_has_a_control_block_of_its_own(self):
        gif = read_gif(encode_gif(3, 2, self.frames, self.palette, [5, 5, 5, 5]))
        self.assertEqual(len(gif["frames"]), 4)
        for frame in gif["frames"]:
            self.assertIsNotNone(frame["control"])
            self.assertFalse(frame["control"]["user_input"])

    def test_a_single_frame_has_a_control_block_with_its_delay(self):
        gif = read_gif(encode_gif(3, 2, self.frames[:1], self.palette, [12]))
        self.assertEqual(gif["frames"][0]["control"]["delay"], 12)

    def test_without_transparent_the_flag_is_off_and_the_disposal_is_1(self):
        gif = read_gif(encode_gif(3, 2, self.frames, self.palette, [5, 5, 5, 5]))
        for frame in gif["frames"]:
            self.assertFalse(frame["control"]["has_transparent"])
            self.assertEqual(frame["control"]["transparent"], 0)
            self.assertEqual(frame["control"]["disposal"], 1)

    def test_with_transparent_the_flag_is_on_the_index_is_kept_and_the_disposal_is_2(self):
        gif = read_gif(encode_gif(3, 2, self.frames, self.palette, [5, 5, 5, 5], transparent=3))
        for frame in gif["frames"]:
            self.assertTrue(frame["control"]["has_transparent"])
            self.assertEqual(frame["control"]["transparent"], 3)
            self.assertEqual(frame["control"]["disposal"], 2)
        self.assertEqual([frame["pixels"] for frame in gif["frames"]], self.frames)

    def test_index_0_can_be_the_transparent_one(self):
        gif = read_gif(encode_gif(3, 2, self.frames[:1], self.palette, [5], transparent=0))
        control = gif["frames"][0]["control"]
        self.assertTrue(control["has_transparent"])
        self.assertEqual(control["transparent"], 0)
        self.assertEqual(control["disposal"], 2)

    def test_one_frame_has_no_loop_block(self):
        gif = read_gif(encode_gif(3, 2, self.frames[:1], self.palette, [5]))
        self.assertIsNone(gif["loop"])
        gif = read_gif(encode_gif(3, 2, self.frames[:1], self.palette, [5], loop=3))
        self.assertIsNone(gif["loop"])

    def test_two_frames_or_more_carry_the_loop_count(self):
        for count in (2, 3, 4):
            for loop in (0, 1, 5, 300, 65535):
                with self.subTest(frames=count, loop=loop):
                    data = encode_gif(3, 2, self.frames[:count], self.palette, [5] * count, loop=loop)
                    self.assertEqual(read_gif(data)["loop"], loop)

    def test_loop_count_is_0_when_none_is_given(self):
        gif = read_gif(encode_gif(3, 2, self.frames[:2], self.palette, [5, 5]))
        self.assertEqual(gif["loop"], 0)

    def test_loop_block_sits_before_the_first_frame(self):
        gif = read_gif(encode_gif(3, 2, self.frames, self.palette, [5, 5, 5, 5], loop=2))
        self.assertEqual(gif["frames_before_loop"], 0)

    def test_large_frames_each_start_from_a_fresh_table(self):
        frames = [noise(120 * 120, 256, seed=seed) for seed in (1, 2, 3)]
        gif = read_gif(encode_gif(120, 120, frames, colours(256), [2, 3, 4]))
        for got, want in zip(gif["frames"], frames):
            self.assertSamePixels(got["pixels"], want)
            self.assertEqual(got["clears"][0], (9, 0))


class ErrorsTest(unittest.TestCase):
    def test_no_frames(self):
        with self.assertRaisesRegex(PixelRowsError, "no frames"):
            encode_gif(2, 2, [], colours(2), [])

    def test_frame_of_the_wrong_length(self):
        for frame in (bytes(3), bytes(5), b""):
            with self.subTest(length=len(frame)):
                with self.assertRaisesRegex(PixelRowsError, "frame 1"):
                    encode_gif(2, 2, [bytes(4), frame], colours(2), [1, 1])

    def test_frame_that_is_not_bytes(self):
        for frame in ("....", [0, 0, 0, 0], None):
            with self.subTest(frame=frame):
                with self.assertRaisesRegex(PixelRowsError, "frame 0"):
                    encode_gif(2, 2, [frame], colours(2), [1])

    def test_empty_palette(self):
        with self.assertRaisesRegex(PixelRowsError, "palette"):
            encode_gif(1, 1, [b"\x00"], [], [1])

    def test_palette_above_256_colours(self):
        with self.assertRaisesRegex(PixelRowsError, "257"):
            encode_gif(1, 1, [b"\x00"], colours(256) + [(1, 1, 1)], [1])

    def test_palette_entry_that_is_not_a_colour(self):
        for bad in ((1, 2), (0, 0, 256), None):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "palette entry 1"):
                    encode_gif(1, 1, [b"\x00"], [(0, 0, 0), bad], [1])

    def test_index_outside_the_palette(self):
        with self.assertRaisesRegex(PixelRowsError, r"frame 1 has index 2 at \(1, 2\)"):
            encode_gif(2, 3, [bytes(6), bytes([0, 1, 0, 1, 0, 2])], colours(2), [1, 1])

    def test_index_in_the_padding_of_the_table_is_outside_the_palette(self):
        with self.assertRaises(PixelRowsError):
            encode_gif(1, 1, [b"\x03"], colours(3), [1])

    def test_delay_count_that_differs_from_the_frame_count(self):
        for delays in ([], [1], [1, 1, 1]):
            with self.subTest(delays=delays):
                with self.assertRaisesRegex(PixelRowsError, "2 frames"):
                    encode_gif(1, 1, [b"\x00", b"\x01"], colours(2), delays)

    def test_delay_out_of_range(self):
        for bad in (-1, 65536, 1.5, "2", None, True):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "delay 1"):
                    encode_gif(1, 1, [b"\x00", b"\x01"], colours(2), [1, bad])

    def test_loop_out_of_range(self):
        for bad in (-1, 65536, 0.5, None):
            for count in (1, 2):
                with self.subTest(bad=bad, frames=count):
                    with self.assertRaisesRegex(PixelRowsError, "loop"):
                        encode_gif(1, 1, [b"\x00"] * count, colours(2), [1] * count, loop=bad)

    def test_transparent_outside_the_palette(self):
        for bad in (-1, 3, 4, 256, 1.0, "0"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "transparent"):
                    encode_gif(1, 1, [b"\x00"], colours(3), [1], transparent=bad)

    def test_width_or_height_that_cannot_be_stored(self):
        for width, height in ((0, 1), (1, 0), (-1, 1), (65536, 1), (1, 65536), (1.0, 1)):
            with self.subTest(width=width, height=height):
                with self.assertRaises(PixelRowsError):
                    encode_gif(width, height, [b"\x00"], colours(2), [1])

    def test_the_largest_delay_and_loop_are_taken(self):
        data = encode_gif(1, 1, [b"\x00", b"\x01"], colours(2), [65535, 0], loop=65535)
        self.assertEqual(read_gif(data)["loop"], 65535)


class WriteGifTest(unittest.TestCase):
    def setUp(self):
        self.args = (2, 1, [b"\x00\x01", b"\x01\x00"], colours(2), [5, 9])

    def test_writes_what_encode_gif_returns_and_makes_the_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "clips" / "blink.gif"
            write_gif(path, *self.args, loop=2, transparent=0)
            self.assertEqual(path.read_bytes(), encode_gif(*self.args, loop=2, transparent=0))

    def test_takes_the_path_as_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blink.gif"
            write_gif(str(path), *self.args)
            gif = read_gif(path.read_bytes())
            self.assertEqual([frame["control"]["delay"] for frame in gif["frames"]], [5, 9])

    def test_bad_input_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "blink.gif"
            with self.assertRaises(PixelRowsError):
                write_gif(path, 2, 1, [b"\x00"], colours(2), [5])
            self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
