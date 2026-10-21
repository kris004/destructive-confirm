# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline release-contract tests; no real tags, keys, or GitHub writes."""

import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(os.environ.get("DC_TEST_TMPDIR", "/tmp")).resolve()
if not TMP.is_dir() or TMP == ROOT or ROOT in TMP.parents:
    raise RuntimeError("DC_TEST_TMPDIR must exist outside the source tree")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name.replace('_', '-')}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pack = load("package_release")
verify = load("verify_release")


class PackagingTests(unittest.TestCase):
    def test_exact_reproducible_source_and_no_overwrites(self):
        with tempfile.TemporaryDirectory(prefix="release-test.", dir=TMP) as directory:
            tmp = Path(directory)
            repo = tmp / "source"
            repo.mkdir()
            env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+00:00",
                   "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+00:00"}
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], env=env)
            git("init", "-q", "-b", "main")
            git("config", "user.name", "Release Test")
            git("config", "user.email", "release-test@example.invalid")
            (repo / "VERSION").write_text("0.1.0\n")
            (repo / "LICENSE").write_text("Test fixture license\n")
            (repo / "source.c").write_text("/* source fixture */\n")
            git("add", "VERSION", "LICENSE", "source.c")
            git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
            (repo / "config.h").write_text("untracked personal selection\n")
            (repo / "build").mkdir()
            (repo / "build/binary").write_text("untracked build output\n")
            first = pack.package(repo, "HEAD", tmp / "one")
            second = pack.package(repo, "HEAD", tmp / "two")
            self.assertEqual(first[0].read_bytes(), second[0].read_bytes())
            with tarfile.open(first[0]) as archive:
                self.assertEqual(archive.getnames(), [
                    "destructive-confirm-0.1.0",
                    "destructive-confirm-0.1.0/LICENSE",
                    "destructive-confirm-0.1.0/VERSION",
                    "destructive-confirm-0.1.0/source.c"])
            digest = hashlib.sha256(first[0].read_bytes()).hexdigest()
            self.assertEqual(first[1].read_text(),
                             f"{digest}  destructive-confirm-0.1.0-src.tar.gz\n")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                pack.package(repo, "HEAD", tmp / "one")
            with self.assertRaisesRegex(ValueError, "outside"):
                pack.package(repo, "HEAD", repo / "dist")
            # An uncommitted version edit cannot leak into an exact source release.
            (repo / "VERSION").write_text("99.0.0\n")
            third = pack.package(repo, "HEAD", tmp / "three")
            self.assertEqual(first[0].read_bytes(), third[0].read_bytes())


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.commit = "a" * 40
        self.ref = {"ref": "refs/tags/v0.1.0",
                    "object": {"type": "tag", "sha": "b" * 40}}
        self.obj = {"sha": "b" * 40, "tag": "v0.1.0",
                    "object": {"type": "commit", "sha": self.commit},
                    "verification": {"verified": True, "reason": "valid"}}

    def validate(self, ref=None, obj=None, version="0.1.0"):
        verify.validate_tag("v0.1.0", ref or self.ref, obj or self.obj,
                            self.commit, version)

    def test_valid_direct_verified_tag(self):
        self.validate()

    def test_unsigned_lightweight_indirect_or_wrong_commit_rejected(self):
        for name, field, value in (
                ("lightweight", "ref", {"type": "commit", "sha": self.commit}),
                ("indirect", "target", {"type": "tag", "sha": self.commit}),
                ("wrong commit", "target", {"type": "commit", "sha": "c" * 40}),
                ("unsigned", "verification", {"verified": False, "reason": "unsigned"}),
                ("bad reason", "verification", {"verified": True, "reason": "invalid"})):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ref, obj = copy.deepcopy(self.ref), copy.deepcopy(self.obj)
                if field == "ref":
                    ref["object"] = value
                elif field == "target":
                    obj["object"] = value
                else:
                    obj["verification"] = value
                self.validate(ref, obj)
        with self.assertRaisesRegex(ValueError, "VERSION"):
            self.validate(version="0.2.0")

    def test_required_checks_are_actions_successes(self):
        run = {"name": verify.REQUIRED_CHECKS[0], "status": "completed",
               "conclusion": "success", "app": {"slug": "github-actions"}}
        verify.validate_checks([run])
        for mutation in ({}, {"status": "in_progress"},
                         {"conclusion": "failure"}, {"app": {"slug": "other-app"}}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify.validate_checks([{**run, **mutation}] if mutation else [])

    def test_full_pinned_fingerprint_required(self):
        status = f"[GNUPG:] VALIDSIG {verify.TRUSTED_SIGNER} 2001-01-01 1 0 4 0 1 10 00\n"
        verify.validate_gpg_status(status)
        for invalid in ("", status.replace(verify.TRUSTED_SIGNER, "0" * 40),
                        status + status):
            with self.subTest(status=invalid), self.assertRaises(ValueError):
                verify.validate_gpg_status(invalid)


if __name__ == "__main__":
    unittest.main()
