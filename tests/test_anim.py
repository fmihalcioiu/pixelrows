import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pixelrows.anim import delays, frame_images, gif_bytes, save_gif
from pixelrows.errors import PixelRowsError
from pixelrows.image import Image
from pixelrows.render import render_sprite
from pixelrows.sprite import Sprite
from pixelrows.spriteset import SpriteSet

DARK = (26, 26, 34)
GREEN = (88, 168, 76)
LIGHT = (124, 200, 106)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

CLEAR = (0, 0, 0, 0)


def solid(rgb):
    """A colour as the pixel it paints."""
    return (*rgb, 255)


def blob_set():
    """
    A set with one clip, 'idle', of three frames at 3 a second.

    Its two sprites are 6 by 4. The second has a green of its own, and the
    clip plays it first and twice, so play order is not the order of the set
    and the clip does not read the same backwards.
    """
    sprites = SpriteSet({"o": DARK, "g": GREEN})
    sprites.add(Sprite("blob_0", ["..oo..", ".oggo.", "oggggo", "oooooo"]))
    sprites.add(Sprite("blob_1", ["......", ".oooo.", "oggggo", "oooooo"], {"g": LIGHT}))
    sprites.add_anim("idle", ["blob_1", "blob_1", "blob_0"], 3)
    return sprites


def strip(name, numbers, lead=""):
    """A sprite one row tall: the cells of `lead`, then one cell of a colour of its own for each of `numbers`."""
    keys = [chr(0x100 + number) for number in numbers]
    own = {key: (number % 256, number // 256, 7) for key, number in zip(keys, numbers)}
    return Sprite(name, [lead + "".join(keys)], own)


def strip_set(*strips):
    """A set with the given sprites and one clip, 'strip', that plays them in turn."""
    sprites = SpriteSet()
    for sprite in strips:
        sprites.add(sprite)
    sprites.add_anim("strip", [sprite.name for sprite in strips], 10)
    return sprites


def pixels(image):
    """An image's pixels as (r, g, b, a), row by row."""
    return [image.get(x, y) for y in range(image.height) for x in range(image.width)]


# A small GIF reader for these tests, written from the format's definition. It
# takes nothing from the package: it only reads the bytes that gif_bytes returns.


def read_blocks(data, pos):
    """The data sub-blocks from `pos` joined into one, and the position just past the empty block that ends them."""
    out = bytearray()
    while data[pos]:
        out += data[pos + 1:pos + 1 + data[pos]]
        pos += 1 + data[pos]
    return bytes(out), pos + 1


def lzw_decode(data, min_code_size):
    """Reads a GIF code stream back into palette indices."""
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    strings = []      # code to the indices it stands for; empty until the first clear code
    previous = None   # the string of the code before this one; None straight after a clear code
    out = bytearray()
    buffer = held = pos = 0
    while True:
        while held < code_size:
            buffer |= data[pos] << held
            held += 8
            pos += 1
        code = buffer & ((1 << code_size) - 1)
        buffer >>= code_size
        held -= code_size
        if code == clear:
            # The single indices, then two places kept for the clear code and the end code.
            strings = [bytes([i]) for i in range(clear)] + [b"", b""]
            code_size = min_code_size + 1
            previous = None
            continue
        if code == end:
            return bytes(out)
        if previous is None:
            string = strings[code]
        else:
            # A code may come one step before it is in the table. It then stands
            # for the string before it, plus that string's own first index.
            string = strings[code] if code < len(strings) else previous + previous[:1]
            if len(strings) < 4096:
                strings.append(previous + string[:1])
        out += string
        previous = string
        if len(strings) == 1 << code_size and code_size < 12:
            code_size += 1


def read_gif(data):
    """
    Takes a GIF file apart block by block.

    Returns its size, colour table and loop count (None without a loop
    block), and for each frame its box, delay, transparent index (None when
    it has none) and palette indices.
    """
    if data[:6] != b"GIF89a":
        raise AssertionError("the file does not start with GIF89a")
    width, height, packed = struct.unpack_from("<HHB", data, 6)
    pos = 13
    table = []
    if packed & 0x80:
        count = 2 << (packed & 7)
        table = [tuple(data[pos + 3 * i:pos + 3 * i + 3]) for i in range(count)]
        pos += 3 * count
    gif = {"width": width, "height": height, "table": table, "loop": None, "frames": []}
    delay = transparent = None
    while data[pos] != 0x3B:
        if data[pos] == 0x21:
            label = data[pos + 1]
            body, pos = read_blocks(data, pos + 2)
            if label == 0xF9 and len(body) == 4:
                flags, delay, index = struct.unpack("<BHB", body)
                transparent = index if flags & 1 else None
            elif label == 0xFF and body[:12] == b"NETSCAPE2.0\x01" and len(body) == 14:
                gif["loop"] = struct.unpack("<H", body[12:])[0]
            else:
                raise AssertionError(f"an extension with the label {label:#04x} that cannot be read")
        elif data[pos] == 0x2C:
            left, top, frame_width, frame_height, flags = struct.unpack_from("<HHHHB", data, pos + 1)
            if flags & 0xC0:
                raise AssertionError("a frame is interlaced or has a colour table of its own")
            codes, after = read_blocks(data, pos + 11)
            indices = lzw_decode(codes, data[pos + 10])
            if len(indices) != frame_width * frame_height:
                raise AssertionError(f"a frame of {frame_width}x{frame_height} decodes to {len(indices)} pixels")
            gif["frames"].append({
                "box": (left, top, frame_width, frame_height),
                "delay": delay,
                "transparent": transparent,
                "indices": indices,
            })
            delay = transparent = None
            pos = after
        else:
            raise AssertionError(f"a block that starts with {data[pos]:#04x} at byte {pos}")
    if pos != len(data) - 1:
        raise AssertionError("bytes follow the trailer")
    return gif


def shown(gif, frame):
    """What a frame read from a GIF shows, as (r, g, b, a) pixel by pixel: nothing at its transparent index."""
    return [
        CLEAR if index == frame["transparent"] else solid(gif["table"][index])
        for index in frame["indices"]
    ]


class FrameImagesTest(unittest.TestCase):
    def setUp(self):
        self.sprites = blob_set()
        self.blob_0 = self.sprites.sprite("blob_0")
        self.blob_1 = self.sprites.sprite("blob_1")

    def test_one_image_a_frame_in_play_order(self):
        images = frame_images(self.sprites, "idle")
        first = render_sprite(self.blob_0, self.sprites.palette_for(self.blob_0))
        second = render_sprite(self.blob_1, self.sprites.palette_for(self.blob_1))
        self.assertNotEqual(first, second)
        self.assertEqual(len(images), 3)
        for image in images:
            self.assertIsInstance(image, Image)
        self.assertEqual(images, [second, second, first])

    def test_a_sprite_played_twice_gives_two_images_of_their_own(self):
        images = frame_images(self.sprites, "idle")
        self.assertEqual(images[0], images[1])
        images[0].set(0, 0, WHITE)
        self.assertEqual(images[1].get(0, 0), CLEAR)

    def test_anim_is_taken_by_name_or_as_an_anim(self):
        self.assertEqual(
            frame_images(self.sprites, self.sprites.anim("idle")),
            frame_images(self.sprites, "idle"),
        )

    def test_images_are_the_size_of_the_frames_at_scale_one(self):
        for image in frame_images(self.sprites, "idle"):
            self.assertEqual((image.width, image.height), (6, 4))

    def test_images_are_the_frames_at_the_scale(self):
        plain = frame_images(self.sprites, "idle")
        for scale in (2, 3, 8):
            with self.subTest(scale=scale):
                images = frame_images(self.sprites, "idle", scale)
                for image in images:
                    self.assertEqual((image.width, image.height), (6 * scale, 4 * scale))
                self.assertEqual(images, [image.scaled(scale) for image in plain])

    def test_without_a_background_an_empty_cell_is_transparent(self):
        for image in frame_images(self.sprites, "idle", 2):
            self.assertEqual(image.get(0, 0), CLEAR)
            self.assertEqual(image.get(11, 7), solid(DARK))

    def test_with_a_background_an_empty_cell_is_the_background(self):
        for background in (WHITE, "#ffffff"):
            with self.subTest(background=background):
                images = frame_images(self.sprites, "idle", 2, background)
                for image in images:
                    self.assertEqual(image.get(0, 0), solid(WHITE))
                    self.assertEqual(image.get(11, 7), solid(DARK))
                    self.assertNotIn(CLEAR, image.colours())
                self.assertEqual(
                    images[2],
                    render_sprite(self.blob_0, self.sprites.palette_for(self.blob_0), 2, WHITE),
                )

    def test_a_sprites_own_palette_entry_shows_in_its_frame(self):
        images = frame_images(self.sprites, "idle")
        # The cell at (1, 2) is 'g' in both sprites.
        self.assertEqual(images[0].get(1, 2), solid(LIGHT))
        self.assertEqual(images[1].get(1, 2), solid(LIGHT))
        self.assertEqual(images[2].get(1, 2), solid(GREEN))

    def test_a_frame_that_names_no_sprite_is_refused(self):
        self.sprites.add_anim("hop", ["blob_0", "blob_9"], 3)
        with self.assertRaises(PixelRowsError) as caught:
            frame_images(self.sprites, "hop")
        self.assertEqual(str(caught.exception), "anim 'hop' names 'blob_9', which is not a sprite")

    def test_frames_of_two_sizes_are_refused(self):
        self.sprites.add(Sprite("tall", ["..oo..", ".oggo.", ".oggo.", "oggggo", "oooooo"]))
        self.sprites.add_anim("hop", ["blob_0", "tall"], 3)
        with self.assertRaises(PixelRowsError) as caught:
            frame_images(self.sprites, "hop")
        self.assertEqual(str(caught.exception), "anim 'hop': frame 'tall' is 6x5, the first frame is 6x4")

    def test_an_anim_the_set_does_not_have_is_refused(self):
        with self.assertRaisesRegex(PixelRowsError, "no anim named 'hop'"):
            frame_images(self.sprites, "hop")

    def test_a_frame_using_a_character_without_a_colour_is_refused(self):
        self.sprites.add(Sprite("odd", ["..oo..", ".oxxo.", "oggggo", "oooooo"]))
        self.sprites.add_anim("hop", ["blob_0", "odd"], 3)
        with self.assertRaisesRegex(PixelRowsError, "sprite 'odd'.*'x'"):
            frame_images(self.sprites, "hop")

    def test_a_scale_below_one_or_not_a_whole_number_is_refused(self):
        for bad in (0, -1, 1.5, "2", None):
            with self.subTest(bad=bad):
                with self.assertRaises(PixelRowsError):
                    frame_images(self.sprites, "idle", bad)


class DelaysTest(unittest.TestCase):
    def test_one_whole_number_a_frame(self):
        for fps in (1, 3, 12.5, 60):
            for count in (1, 2, 7):
                with self.subTest(fps=fps, count=count):
                    times = delays(fps, count)
                    self.assertEqual(len(times), count)
                    for time in times:
                        self.assertIs(type(time), int)

    def test_fps_10_is_10_every_frame(self):
        self.assertEqual(delays(10, 1), [10])
        self.assertEqual(delays(10, 6), [10] * 6)
        self.assertEqual(delays(10.0, 6), [10] * 6)

    def test_fps_3_is_33_34_33_and_three_frames_take_one_second(self):
        times = delays(3, 3)
        self.assertEqual(times, [33, 34, 33])
        self.assertEqual(sum(times), 100)
        self.assertEqual(delays(3, 7), [33, 34, 33, 33, 34, 33, 33])

    def test_fps_1_6_is_62_or_63_and_eight_frames_take_five_seconds(self):
        times = delays(1.6, 8)
        self.assertEqual(times, [62, 63, 63, 62, 62, 63, 63, 62])
        self.assertEqual(sum(times), 500)

    def test_fps_60_is_never_below_2(self):
        self.assertEqual(delays(60, 12), [2] * 12)

    def test_no_fps_however_high_goes_below_2(self):
        for fps in (50, 51, 75, 100, 144, 1000, 1e9):
            with self.subTest(fps=fps):
                self.assertEqual(delays(fps, 9), [2] * 9)

    def test_every_frame_ends_within_half_a_hundredth_of_its_true_time(self):
        for fps in (0.5, 1, 1.6, 2.5, 3, 7, 12, 15, 24, 30, 40, 50):
            times = delays(fps, 48)
            for done in range(1, 49):
                with self.subTest(fps=fps, frames=done):
                    self.assertLessEqual(abs(sum(times[:done]) - done * 100 / fps), 0.5)

    def test_a_longer_clip_starts_with_the_times_of_a_shorter_one(self):
        for fps in (1.6, 3, 7, 24, 60):
            with self.subTest(fps=fps):
                self.assertEqual(delays(fps, 20)[:5], delays(fps, 5))

    def test_fps_that_is_not_a_number_above_0_is_refused(self):
        for bad in (0, 0.0, -1, -2.5, True, False, "10", None, float("inf"), float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "fps"):
                    delays(bad, 3)

    def test_count_below_1_is_refused(self):
        for bad in (0, -1, -30):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "count"):
                    delays(10, bad)

    def test_count_that_is_not_a_whole_number_is_refused(self):
        for bad in (1.5, 2.0, True, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "count"):
                    delays(10, bad)

    def test_errors_say_what_was_given(self):
        with self.assertRaises(PixelRowsError) as caught:
            delays(0, 3)
        self.assertEqual(str(caught.exception), "fps must be a number above 0, got 0")
        with self.assertRaises(PixelRowsError) as caught:
            delays(10, 0)
        self.assertEqual(str(caught.exception), "count must be a whole number of 1 or more, got 0")

    def test_fps_too_low_for_a_frame_to_be_timed_is_refused(self):
        with self.assertRaisesRegex(PixelRowsError, "too low"):
            delays(1e-310, 2)


class GifBytesTest(unittest.TestCase):
    def setUp(self):
        self.sprites = blob_set()

    def test_gives_the_bytes_of_a_gif_file(self):
        data = gif_bytes(self.sprites, "idle")
        self.assertIsInstance(data, bytes)
        self.assertEqual(data[:6], b"GIF89a")
        self.assertEqual(data[-1:], b"\x3b")

    def test_one_frame_for_each_frame_of_the_anim(self):
        self.assertEqual(len(read_gif(gif_bytes(self.sprites, "idle"))["frames"]), 3)
        self.sprites.add_anim("long", ["blob_0", "blob_1"] * 4, 12)
        self.assertEqual(len(read_gif(gif_bytes(self.sprites, "long"))["frames"]), 8)

    def test_size_is_the_size_of_the_frames_at_the_scale(self):
        for scale in (1, 2, 5):
            with self.subTest(scale=scale):
                gif = read_gif(gif_bytes(self.sprites, "idle", scale))
                self.assertEqual((gif["width"], gif["height"]), (6 * scale, 4 * scale))
                for frame in gif["frames"]:
                    self.assertEqual(frame["box"], (0, 0, 6 * scale, 4 * scale))

    def test_each_frame_has_its_delay(self):
        expected = {10: [10, 10, 10], 3: [33, 34, 33], 1.6: [62, 63, 63], 60: [2, 2, 2]}
        for fps, times in expected.items():
            with self.subTest(fps=fps):
                self.sprites.add_anim("clip", ["blob_0", "blob_1", "blob_0"], fps)
                gif = read_gif(gif_bytes(self.sprites, "clip"))
                self.assertEqual([frame["delay"] for frame in gif["frames"]], times)
                self.assertEqual(times, delays(fps, 3))

    def test_loop_count_is_0_unless_one_is_given(self):
        self.assertEqual(read_gif(gif_bytes(self.sprites, "idle"))["loop"], 0)

    def test_loop_count_given_is_kept(self):
        for loop in (1, 4, 65535):
            with self.subTest(loop=loop):
                self.assertEqual(read_gif(gif_bytes(self.sprites, "idle", loop=loop))["loop"], loop)

    def test_without_a_background_index_0_is_the_transparent_one_in_every_frame(self):
        for scale in (1, 3):
            with self.subTest(scale=scale):
                gif = read_gif(gif_bytes(self.sprites, "idle", scale))
                self.assertEqual([frame["transparent"] for frame in gif["frames"]], [0, 0, 0])

    def test_with_a_background_no_index_is_transparent(self):
        for background in (WHITE, "#ffffff", BLACK):
            with self.subTest(background=background):
                gif = read_gif(gif_bytes(self.sprites, "idle", background=background))
                self.assertEqual([frame["transparent"] for frame in gif["frames"]], [None, None, None])

    def test_every_pixel_is_the_colour_frame_images_gives(self):
        for scale in (1, 2, 5):
            for background in (None, WHITE, "#102030", DARK):
                with self.subTest(scale=scale, background=background):
                    gif = read_gif(gif_bytes(self.sprites, "idle", scale, background))
                    images = frame_images(self.sprites, "idle", scale, background)
                    self.assertEqual(len(gif["frames"]), len(images))
                    for frame, image in zip(gif["frames"], images):
                        self.assertEqual(shown(gif, frame), pixels(image))

    def test_without_a_background_every_fully_transparent_pixel_is_index_0_and_no_other_is(self):
        gif = read_gif(gif_bytes(self.sprites, "idle", 2))
        for frame, image in zip(gif["frames"], frame_images(self.sprites, "idle", 2)):
            self.assertEqual(
                [index == 0 for index in frame["indices"]],
                [pixel == CLEAR for pixel in pixels(image)],
            )

    def test_table_is_the_colours_of_all_frames_in_order_of_first_appearance(self):
        # The clip plays blob_1 first: dark then its own green, and blob_0 brings the set's green.
        gif = read_gif(gif_bytes(self.sprites, "idle", background=WHITE))
        self.assertEqual(gif["table"], [WHITE, DARK, LIGHT, GREEN])

    def test_without_a_background_the_table_starts_with_the_transparent_entry(self):
        gif = read_gif(gif_bytes(self.sprites, "idle"))
        self.assertEqual(gif["table"], [BLACK, DARK, LIGHT, GREEN])

    def test_table_follows_play_order_not_the_order_of_the_set(self):
        self.sprites.add_anim("back", ["blob_0", "blob_1"], 3)
        gif = read_gif(gif_bytes(self.sprites, "back", background=WHITE))
        self.assertEqual(gif["table"], [WHITE, DARK, GREEN, LIGHT])

    def test_table_is_the_same_at_any_scale(self):
        for background in (None, WHITE):
            with self.subTest(background=background):
                plain = read_gif(gif_bytes(self.sprites, "idle", 1, background))
                large = read_gif(gif_bytes(self.sprites, "idle", 4, background))
                self.assertEqual(large["table"], plain["table"])

    def test_solid_black_is_not_the_transparent_index(self):
        sprites = SpriteSet({"k": BLACK, "w": WHITE})
        sprites.add(Sprite("a", ["k.w"]))
        sprites.add(Sprite("b", [".kk"]))
        sprites.add_anim("blink", ["a", "b"], 5)
        gif = read_gif(gif_bytes(sprites, "blink"))
        self.assertEqual(gif["table"][:3], [BLACK, BLACK, WHITE])
        self.assertEqual([frame["indices"] for frame in gif["frames"]], [bytes([1, 0, 2]), bytes([0, 1, 1])])
        self.assertEqual(shown(gif, gif["frames"][0]), [solid(BLACK), CLEAR, solid(WHITE)])

    def test_background_of_a_colour_the_frames_use_shares_its_entry(self):
        gif = read_gif(gif_bytes(self.sprites, "idle", background=DARK))
        self.assertEqual(gif["table"][:3], [DARK, LIGHT, GREEN])
        self.assertEqual(gif["table"][3:], [BLACK])

    def test_anim_is_taken_by_name_or_as_an_anim(self):
        self.assertEqual(
            gif_bytes(self.sprites, self.sprites.anim("idle"), 2, WHITE, 3),
            gif_bytes(self.sprites, "idle", 2, WHITE, 3),
        )

    def test_a_clip_of_one_frame_is_a_gif_of_one_frame(self):
        self.sprites.add_anim("still", ["blob_0"], 4)
        gif = read_gif(gif_bytes(self.sprites, "still", 2))
        self.assertEqual(len(gif["frames"]), 1)
        self.assertEqual(gif["frames"][0]["delay"], 25)
        self.assertEqual(shown(gif, gif["frames"][0]), pixels(frame_images(self.sprites, "still", 2)[0]))

    def test_256_colours_fit_with_a_background(self):
        sprites = strip_set(strip("a", range(256)))
        gif = read_gif(gif_bytes(sprites, "strip", background=WHITE))
        self.assertEqual(len(gif["table"]), 256)
        self.assertEqual(shown(gif, gif["frames"][0]), pixels(frame_images(sprites, "strip")[0]))

    def test_255_colours_and_the_transparent_one_fit_without_a_background(self):
        sprites = strip_set(strip("a", range(255), lead="."))
        gif = read_gif(gif_bytes(sprites, "strip"))
        self.assertEqual(len(gif["table"]), 256)
        self.assertEqual(shown(gif, gif["frames"][0]), pixels(frame_images(sprites, "strip")[0]))

    def test_more_than_256_colours_are_refused(self):
        sprites = strip_set(strip("a", range(257)))
        with self.assertRaises(PixelRowsError) as caught:
            gif_bytes(sprites, "strip", background=WHITE)
        self.assertEqual(str(caught.exception), "anim 'strip' needs 257 colours, a GIF holds 256 at most")

    def test_the_background_counts_as_a_colour_where_it_shows(self):
        sprites = strip_set(strip("a", range(256), lead="."))
        with self.assertRaisesRegex(PixelRowsError, "257 colours"):
            gif_bytes(sprites, "strip", background=WHITE)

    def test_without_a_background_the_transparent_one_takes_a_place_of_the_256(self):
        for lead in ("", "."):
            with self.subTest(lead=lead):
                sprites = strip_set(strip("a", range(256), lead=lead))
                with self.assertRaises(PixelRowsError) as caught:
                    gif_bytes(sprites, "strip")
                self.assertEqual(
                    str(caught.exception),
                    "anim 'strip' needs 257 colours, the transparent one counted, a GIF holds 256 at most",
                )

    def test_colours_of_all_frames_are_counted_together(self):
        halves = strip("a", range(0, 200)), strip("b", range(200, 400))
        with self.assertRaisesRegex(PixelRowsError, "400 colours"):
            gif_bytes(strip_set(*halves), "strip", background=WHITE)
        shared = strip("a", range(0, 200)), strip("b", range(56, 256))
        gif = read_gif(gif_bytes(strip_set(*shared), "strip", background=WHITE))
        self.assertEqual(len(gif["frames"]), 2)

    def test_a_pixel_that_is_partly_transparent_is_refused(self):
        for background in (None, WHITE):
            with self.subTest(background=background):
                images = frame_images(self.sprites, "idle", 1, background)
                images[2].data[3] = 128
                wrong = "anim 'idle': frame 'blob_0' has a pixel of alpha 128"
                with mock.patch("pixelrows.anim.frame_images", return_value=images):
                    with self.assertRaisesRegex(PixelRowsError, wrong):
                        gif_bytes(self.sprites, "idle", 1, background)

    def test_a_clip_that_cannot_play_is_refused(self):
        self.sprites.add_anim("hop", ["blob_0", "blob_9"], 3)
        with self.assertRaisesRegex(PixelRowsError, "'blob_9', which is not a sprite"):
            gif_bytes(self.sprites, "hop")
        with self.assertRaisesRegex(PixelRowsError, "no anim named 'run'"):
            gif_bytes(self.sprites, "run")

    def test_a_loop_count_a_gif_cannot_hold_is_refused(self):
        for bad in (-1, 65536, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(PixelRowsError, "loop"):
                    gif_bytes(self.sprites, "idle", loop=bad)


class SaveGifTest(unittest.TestCase):
    def setUp(self):
        self.sprites = blob_set()

    def test_writes_the_bytes_gif_bytes_gives_and_makes_the_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "clips" / "idle.gif"
            save_gif(path, self.sprites, "idle", 2, WHITE, 3)
            self.assertEqual(path.read_bytes(), gif_bytes(self.sprites, "idle", 2, WHITE, 3))

    def test_left_alone_scale_background_and_loop_are_those_of_gif_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "idle.gif"
            save_gif(path, self.sprites, "idle")
            self.assertEqual(path.read_bytes(), gif_bytes(self.sprites, "idle"))

    def test_takes_the_path_as_text_and_the_options_by_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "idle.gif"
            anim = self.sprites.anim("idle")
            self.assertIsNone(save_gif(str(path), self.sprites, anim, scale=3, background="#ffffff", loop=2))
            gif = read_gif(path.read_bytes())
            self.assertEqual((gif["width"], gif["height"], gif["loop"]), (18, 12, 2))
            self.assertEqual(gif["table"][0], WHITE)

    def test_writes_over_a_file_that_is_there(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "idle.gif"
            path.write_bytes(b"old")
            save_gif(path, self.sprites, "idle")
            self.assertEqual(path.read_bytes(), gif_bytes(self.sprites, "idle"))

    def test_a_clip_that_cannot_play_writes_nothing(self):
        self.sprites.add_anim("hop", ["blob_0", "blob_9"], 3)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "hop.gif"
            with self.assertRaises(PixelRowsError):
                save_gif(path, self.sprites, "hop")
            self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
