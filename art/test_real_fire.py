"""Check the fluid-fire bundle and the premultiplied loop seam."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/presets/real-fire"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


cfg = module("real_fire_config", ROOT / "art/real-fire/fire_config.py")
with patch.dict(sys.modules, {"fire_config": cfg}):
    pack = module("pack_real_fire", ROOT / "art/real-fire/pack-fire.py")


class RealFireTests(unittest.TestCase):
    def test_bundle_and_header(self):
        manifest = ET.parse(DATA / "destructive-confirm.gresource.xml")
        self.assertEqual([item.text for item in manifest.iter("file")],
                         ["style.css"] + [f"fire/{i:03d}.png"
                          for i in range(cfg.INTRO + cfg.LOOP)])
        self.assertEqual(len(list((DATA / "fire").glob("*.png"))),
                         cfg.INTRO + cfg.LOOP)
        header = (DATA / "fire-art.h").read_text()
        for name, value in (
                ("FPS", cfg.FPS), ("INTRO_FRAMES", cfg.INTRO),
                ("LOOP_FRAMES", cfg.LOOP), ("FRAME_WIDTH", cfg.WIDTH),
                ("FRAME_HEIGHT", cfg.HEIGHT), ("PADDING_X", cfg.PADDING_X),
                ("PADDING_Y", cfg.PADDING_Y), ("SLICE_X", cfg.SLICE_X),
                ("SLICE_Y", cfg.SLICE_Y), ("CORNER", cfg.CORNER)):
            self.assertIn(f"#define FIRE_{name} {value}\n", header)

    def test_frame_format_and_native_face(self):
        for path in sorted((DATA / "fire").glob("*.png")):
            with self.subTest(frame=path.name), Image.open(path) as image:
                self.assertEqual(image.size, (cfg.WIDTH, cfg.HEIGHT))
                self.assertEqual(image.mode, "RGBA")
                self.assertFalse(image.info)
                self.assertEqual(image.getpixel((320, 160)), (0, 0, 0, 0))
                self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))

    def test_buoyant_flames_not_radial_ribbons(self):
        with Image.open(DATA / "fire/090.png") as image:
            above = sum(image.getchannel("A").crop((0, 0, 640, 128)).histogram()[65:])
            below = sum(image.getchannel("A").crop((0, 192, 640, 320)).histogram()[65:])
            self.assertGreater(above, below * 2)
            bounds = image.getchannel("A").point(
                lambda a: 255 if a > 32 else 0).getbbox()
            self.assertGreater(bounds[1], 0, "Do not cut off bright flame tips")
            self.assertLess(bounds[1], 90, "The fire must extend above its rim")

    def test_loop_joins_consecutive_simulation_frames(self):
        # Last loop image is the frame immediately before the first loop image.
        with Image.open(DATA / f"fire/{cfg.INTRO - 1:03d}.png") as previous, \
             Image.open(DATA / f"fire/{cfg.INTRO + cfg.LOOP - 1:03d}.png") as last:
            self.assertEqual(previous.tobytes(), last.tobytes())

    def test_loop_blending_does_not_leak_transparent_rgb(self):
        images = [Image.new("RGBA", (1, 1), (255, 0, 0, 0))
                  for _ in range(cfg.INTRO + cfg.LOOP)]
        for index in range(cfg.INTRO - cfg.SEAM_BLEND, cfg.INTRO):
            images[index] = Image.new("RGBA", (1, 1), (0, 0, 255, 255))
        image = pack.loop_frame(images, cfg.INTRO + cfg.LOOP - cfg.SEAM_BLEND // 2)
        red, green, blue, alpha = image.getpixel((0, 0))
        self.assertEqual((red, green, blue), (0, 0, 255))
        self.assertGreater(alpha, 0)
        self.assertLess(alpha, 255)


if __name__ == "__main__":
    unittest.main()
