#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build every header-selected preset and inspect the actual embedded bundle."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEST_TMP_ROOT = Path(os.environ.get("DC_TEST_TMPDIR", "/tmp")).resolve()
if not TEST_TMP_ROOT.is_dir() or TEST_TMP_ROOT == ROOT or ROOT in TEST_TMP_ROOT.parents:
    raise RuntimeError("DC_TEST_TMPDIR must be an existing directory outside the source tree")
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

    def assert_staged_install(self, scratch, config, binary):
        stage = scratch / "stage"
        options = (f"DESTDIR={stage}", "PREFIX=/usr")
        self.run_make(scratch, config, "install", *options)
        installed = stage / "usr/bin/destructive-confirm"
        compat = stage / "usr/bin/power-confirm"
        docs = stage / "usr/share/doc/destructive-confirm"
        self.assertEqual(installed.read_bytes(), binary.read_bytes())
        self.assertEqual(installed.stat().st_mode & 0o777, 0o755)
        self.assertTrue(compat.is_symlink())
        self.assertEqual(os.readlink(compat), "destructive-confirm")
        for name in ("README.md", "LICENSE", "COPYRIGHT"):
            self.assertEqual((docs / name).read_bytes(), (ROOT / name).read_bytes())
        expected = {
            "usr/bin/destructive-confirm", "usr/bin/power-confirm",
            *(f"usr/share/doc/destructive-confirm/{name}"
              for name in ("README.md", "LICENSE", "COPYRIGHT")),
        }
        self.assertEqual(
            {str(path.relative_to(stage)) for path in stage.rglob("*")
             if not path.is_dir()}, expected)

        # Uninstall only project-owned paths; custom documentation must survive.
        extra = docs / "keep.txt"
        extra.write_text("packager-owned documentation\n")
        self.run_make(scratch, config, "uninstall", *options, "CC=false")
        self.assertFalse(installed.exists())
        self.assertFalse(compat.is_symlink())
        self.assertEqual(extra.read_text(), "packager-owned documentation\n")
        self.assertEqual(list(docs.iterdir()), [extra])
        extra.unlink()
        self.run_make(scratch, config, "uninstall", *options)
        self.assertFalse(docs.exists())

    def test_clean_without_build_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="destructive-confirm-clean.",
                                         dir=TEST_TMP_ROOT) as directory:
            scratch = Path(directory)
            disposable = scratch / "output with spaces"
            disposable.mkdir()
            (disposable / "generated").write_text("temporary build output\n")
            sibling = scratch / "output"
            sibling.mkdir()
            (sibling / "keep").write_text("unrelated sibling\n")
            config = scratch / "missing.h"
            self.run_make(scratch, config, "clean",
                          f"BUILD_DIR={disposable}", "CC=false", "PKG_CONFIG=false")
            self.assertFalse(disposable.exists())
            self.assertEqual((sibling / "keep").read_text(), "unrelated sibling\n")
            self.assertFalse(config.exists())

    def test_install_directory_overrides(self):
        with tempfile.TemporaryDirectory(prefix="destructive-confirm-install.",
                                         dir=TEST_TMP_ROOT) as directory:
            scratch = Path(directory)
            config = scratch / "config.h"
            config.write_text("#define CONFIRM_ANIMATION ANIMATION_NONE\n")
            stage = scratch / "stage with spaces"
            options = (f"DESTDIR={stage}", "PREFIX=/opt/unused",
                       "BINDIR=/opt/custom bin", "DOCDIR=/opt/custom docs")
            self.run_make(scratch, config, "install", *options)
            self.assertEqual(
                (stage / "opt/custom bin/destructive-confirm").read_bytes(),
                (scratch / "build/destructive-confirm").read_bytes())
            self.assertEqual(
                os.readlink(stage / "opt/custom bin/power-confirm"),
                "destructive-confirm")
            self.assertTrue((stage / "opt/custom docs/LICENSE").is_file())
            self.assertFalse((stage / "opt/unused").exists())
            self.run_make(scratch, config, "uninstall", *options,
                          "CC=false", "PKG_CONFIG=false")
            self.assertFalse((stage / "opt/custom bin/destructive-confirm").exists())
            self.assertFalse((stage / "opt/custom bin/power-confirm").is_symlink())
            self.assertFalse((stage / "opt/custom docs").exists())

    def test_build_and_config_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="destructive-confirm-spaces.",
                                         dir=TEST_TMP_ROOT) as directory:
            scratch = Path(directory)
            build = scratch / "output with spaces"
            config = scratch / "custom config.h"
            config.write_text("#define CONFIRM_ANIMATION ANIMATION_NONE\n")
            options = (f"BUILD_DIR={build}",)
            self.run_make(scratch, config, *options, "check", "preview-tool",
                          str(build / "test-dialog"))
            binary = build / "destructive-confirm"
            self.assert_resources(binary, "none")

            stage = scratch / "staged output"
            install_options = (*options, f"DESTDIR={stage}", "PREFIX=/usr")
            self.run_make(scratch, config, *install_options, "install")
            self.assertEqual(
                (stage / "usr/bin/destructive-confirm").read_bytes(),
                binary.read_bytes())
            self.assertEqual(os.readlink(stage / "usr/bin/power-confirm"),
                             "destructive-confirm")

            # Relative configuration paths must also preserve embedded spaces.
            config.write_text("#define CONFIRM_ANIMATION ANIMATION_SVG_FLAMES\n")
            relative = Path(os.path.relpath(config, ROOT))
            self.run_make(scratch, relative, *options, "check")
            self.assert_resources(binary, "svg-flames")
            unchanged = binary.stat().st_mtime_ns
            self.run_make(scratch, relative, *options, "all")
            self.assertEqual(binary.stat().st_mtime_ns, unchanged)

            self.run_make(scratch, config, *options, "clean")
            self.assertFalse(build.exists())
            self.assertTrue(config.is_file())
            self.run_make(scratch, config, *install_options, "uninstall",
                          "CC=false", "PKG_CONFIG=false")
            self.assertFalse((stage / "usr/bin/destructive-confirm").exists())
            self.assertFalse((stage / "usr/bin/power-confirm").is_symlink())
            self.assertFalse((stage / "usr/share/doc/destructive-confirm").exists())

    def test_selection_resources_and_incremental_switching(self):
        # The explicit override supports Portage's sandbox-owned ${T}.
        with tempfile.TemporaryDirectory(prefix="destructive-confirm-presets.",
                                         dir=TEST_TMP_ROOT) as directory:
            scratch = Path(directory)
            config = scratch / "config.h"
            sizes = {}
            for preset, macro in PRESETS.items():
                with self.subTest(preset=preset):
                    config.write_text(f"#define CONFIRM_ANIMATION {macro}\n")
                    self.run_make(scratch, config, "check")
                    binary = scratch / "build/destructive-confirm"
                    self.assert_resources(binary, preset)
                    self.assert_staged_install(scratch, config, binary)
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
