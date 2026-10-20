#!/usr/bin/env python3
"""Build every header-selected preset and inspect the actual embedded bundle."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/io/github/kristopher/DestructiveConfirm/"
PRESETS = {
    "tall-ring": "ANIMATION_TALL_RING",
    "svg-flames": "ANIMATION_SVG_FLAMES",
    "fire-ring": "ANIMATION_FIRE_RING",
    "real-fire": "ANIMATION_REAL_FIRE",
    "none": "ANIMATION_NONE",
}


class PresetBuildTests(unittest.TestCase):
    def run_make(self, scratch, config, *goals, success=True):
        result = subprocess.run(
            ["make", "--no-print-directory", f"BUILD_DIR={scratch / 'build'}",
             f"CONFIG_H={config}", *goals],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def assert_resources(self, binary, preset):
        folder = ROOT / "data/presets" / preset
        manifest = ET.parse(folder / "destructive-confirm.gresource.xml")
        resources = {
            PREFIX + element.get("alias", element.text): folder / element.text
            for element in manifest.iter("file")
        }
        embedded = subprocess.check_output(
            ["gresource", "list", str(binary)], text=True).splitlines()
        self.assertEqual(sorted(embedded), sorted(resources))
        for path, source in resources.items():
            self.assertEqual(subprocess.check_output(
                ["gresource", "extract", str(binary), path]), source.read_bytes())
        # Non-overlay presets do not even link the texture player.
        symbols = subprocess.check_output(["nm", str(binary)], text=True)
        self.assertEqual(" fire_overlay_new\n" in symbols,
                         preset in ("tall-ring", "real-fire"))

    def test_selection_resources_and_incremental_switching(self):
        # Never place test builds/configs in the source tree or rely on TMPDIR.
        with tempfile.TemporaryDirectory(prefix="destructive-confirm-presets.",
                                         dir="/tmp") as directory:
            scratch = Path(directory)
            config = scratch / "config.h"
            sizes = {}
            for preset, macro in PRESETS.items():
                with self.subTest(preset=preset):
                    config.write_text(f"#define CONFIRM_ANIMATION {macro}\n")
                    self.run_make(scratch, config, "check")
                    binary = scratch / "build/destructive-confirm"
                    self.assert_resources(binary, preset)
                    help_text = subprocess.check_output(
                        [str(binary), "--help"], text=True)
                    self.assertNotIn("--animation", help_text)
                    sizes[preset] = binary.stat().st_size
                    print(f"{preset}: {sizes[preset]:,} bytes", flush=True)
            self.assertLess(sizes["none"], sizes["fire-ring"])
            self.assertLess(sizes["svg-flames"], sizes["fire-ring"])
            self.assertLess(sizes["fire-ring"], sizes["tall-ring"])

            # A different, older header must invalidate selection in the same
            # build directory; no "make clean" or timestamp luck is required.
            older = scratch / "older.h"
            older.write_text("#define CONFIRM_ANIMATION ANIMATION_SVG_FLAMES\n")
            os.utime(older, (1, 1))
            self.run_make(scratch, older, "check")
            binary = scratch / "build/destructive-confirm"
            self.assert_resources(binary, "svg-flames")

            unchanged = binary.stat().st_mtime_ns
            self.run_make(scratch, older, "all")
            self.assertEqual(binary.stat().st_mtime_ns, unchanged,
                             "An unchanged selection should not rebuild")

            for invalid in ("ANIMATION_MISSPELLED", "0", "99"):
                with self.subTest(invalid=invalid):
                    config.write_text(f"#define CONFIRM_ANIMATION {invalid}\n")
                    result = self.run_make(scratch, config, "all", success=False)
                    self.assertIn("Invalid CONFIRM_ANIMATION", result.stdout)

            # Existing custom headers must never be overwritten by the template.
            self.assertEqual(older.read_text(),
                             "#define CONFIRM_ANIMATION ANIMATION_SVG_FLAMES\n")
            self.run_make(scratch, older, "clean")
            self.assertFalse((scratch / "build").exists())


if __name__ == "__main__":
    unittest.main()
