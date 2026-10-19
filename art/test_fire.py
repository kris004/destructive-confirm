"""Optional artwork checks: python3 -B -m unittest discover -s art."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from PIL import Image

from fire_config import (
    FPS, INTRO, LOOP, WIDTH, HEIGHT, PADDING_X, PADDING_Y,
    SLICE_X, SLICE_Y, CORNER, FLAME_HEIGHT_MIN, FLAME_HEIGHT_MAX,
    SPARK_HOLD, SWEEP_TIME,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def rgba_pixels(image):
    data = image.tobytes()
    return zip(data[0::4], data[1::4], data[2::4], data[3::4])


class FireArtworkTests(unittest.TestCase):
    def test_complete_portable_resource_bundle(self):
        manifest = ET.parse(DATA / "destructive-confirm.gresource.xml")
        files = [element.text for element in manifest.iter("file")]
        expected = ["style.css"]
        expected += [f"fire/{frame:03d}.png" for frame in range(INTRO + LOOP)]
        self.assertEqual(files, expected)
        self.assertTrue(all((DATA / name).is_file() for name in files))

    def test_frame_format_alpha_and_metadata(self):
        paths = sorted((DATA / "fire").glob("*.png"))
        self.assertEqual(len(paths), INTRO + LOOP)
        for path in paths:
            with self.subTest(frame=path.name), Image.open(path) as image:
                self.assertEqual(image.size, (WIDTH, HEIGHT))
                self.assertEqual(image.mode, "RGBA")
                self.assertFalse(image.info, "Strip render timestamps and metadata")
                self.assertEqual(image.getpixel((WIDTH // 2, HEIGHT // 2)), (0, 0, 0, 0))
                self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))
                # Black out invisible render noise without quantizing edges.
                self.assertTrue(all(pixel == (0, 0, 0, 0) or pixel[3] != 0
                                    for pixel in rgba_pixels(image)))

    def test_playback_header_matches_artwork(self):
        header = (DATA / "fire-art.h").read_text()
        constants = {
            "FPS": FPS, "INTRO_FRAMES": INTRO, "LOOP_FRAMES": LOOP,
            "FRAME_WIDTH": WIDTH, "FRAME_HEIGHT": HEIGHT,
            "PADDING_X": PADDING_X, "PADDING_Y": PADDING_Y,
            "SLICE_X": SLICE_X, "SLICE_Y": SLICE_Y, "CORNER": CORNER,
        }
        for name, value in constants.items():
            self.assertIn(f"#define FIRE_{name} {value}\n", header)
        self.assertLess(SPARK_HOLD + SWEEP_TIME, INTRO / FPS)
        self.assertEqual((FLAME_HEIGHT_MIN, FLAME_HEIGHT_MAX), (44, 116))

    def test_spark_is_visible_before_ignition(self):
        # The core must survive the native button's opaque face below it.
        for frame in (4, 12):
            with self.subTest(frame=frame), Image.open(
                    DATA / "fire" / f"{frame:03d}.png") as image:
                outside_face = image.crop((160, 100, 200, 126))
                bright = sum(r > 220 and g > 190 and b > 120 and a > 180
                             for r, g, b, a in rgba_pixels(outside_face))
                self.assertGreater(bright, 30)

    def test_ignition_and_burn_are_not_static(self):
        with Image.open(DATA / "fire/004.png") as initial:
            initial_count = sum(initial.getchannel("A").histogram()[33:])
        with Image.open(DATA / "fire/090.png") as burning:
            burning_count = sum(burning.getchannel("A").histogram()[33:])
            bounds = burning.getchannel("A").point(
                lambda alpha: 255 if alpha > 32 else 0).getbbox()
            # Visible flame height, not just low-alpha compositor glow.
            self.assertLess(bounds[1], 70)
            self.assertGreater(bounds[3], HEIGHT - 70)
        self.assertGreater(burning_count, initial_count * 3)
        with Image.open(DATA / f"fire/{INTRO:03d}.png") as first, \
             Image.open(DATA / f"fire/{INTRO + LOOP // 2:03d}.png") as later:
            self.assertNotEqual(first.tobytes(), later.tobytes())


if __name__ == "__main__":
    unittest.main()
