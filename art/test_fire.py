"""Optional artwork checks: python3 -B -m unittest discover -s art."""

import importlib.util
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
spec = importlib.util.spec_from_file_location("pack_fire", ROOT / "art/pack-fire.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class FireArtworkTests(unittest.TestCase):
    def test_complete_portable_resource_bundle(self):
        manifest = ET.parse(DATA / "destructive-confirm.gresource.xml")
        files = [element.text for element in manifest.iter("file")]
        expected = ["style.css", "fire-animation.css"]
        expected += [f"fire/{frame:03d}.png" for frame in range(84)]
        self.assertEqual(files, expected)
        self.assertTrue(all((DATA / name).is_file() for name in files))

    def test_frame_format_alpha_and_metadata(self):
        paths = sorted((DATA / "fire").glob("*.png"))
        self.assertEqual(len(paths), 84)
        for path in paths:
            with self.subTest(frame=path.name), Image.open(path) as image:
                self.assertEqual(image.size, (384, 128))
                self.assertEqual(image.mode, "RGBA")
                self.assertFalse(image.info, "Strip render timestamps and metadata")
                self.assertEqual(image.getpixel((192, 64))[3], 0)
                self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_frame_steps_match_gtk_animation_duration(self):
        css = (DATA / "fire-animation.css").read_text()
        # GTK applies steps to the entire animation, not each keyframe segment.
        # steps(1, end) would hold a whole sequence on its first frame.
        self.assertIn("fire-ignite 1.5s steps(36, end) 1 both", css)
        self.assertIn("fire-burn 2s steps(48, end) 1.5s infinite", css)
        intro = pack.keyframes("fire-ignite", 0, 36, False)
        loop = pack.keyframes("fire-burn", 36, 48, True)
        self.assertIn(intro, css)
        self.assertIn(loop, css)
        self.assertEqual(len(re.findall("border-image-source:", intro)), 37)
        self.assertEqual(len(re.findall("border-image-source:", loop)), 49)
        self.assertIn("/fire/036.png", loop.splitlines()[-2])

    def test_ignition_and_burn_are_not_static(self):
        with Image.open(DATA / "fire/003.png") as initial:
            initial_count = sum(initial.getchannel("A").histogram()[33:])
        with Image.open(DATA / "fire/050.png") as burning:
            burning_count = sum(burning.getchannel("A").histogram()[33:])
        self.assertGreater(burning_count, initial_count * 3)
        with Image.open(DATA / "fire/036.png") as first, \
             Image.open(DATA / "fire/060.png") as later:
            self.assertNotEqual(first.tobytes(), later.tobytes())


if __name__ == "__main__":
    unittest.main()
