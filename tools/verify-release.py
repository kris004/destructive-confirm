#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail closed unless a direct, trusted signed tag targets a tested main commit."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

TRUSTED_SIGNER = "BE592562E6131A53F4BADE4A046928E9A919BAF9"
REQUIRED_CHECKS = ("Build, presets, and native dialogs",)
PUBLIC_KEY_URL = "https://github.com/kris004.gpg"


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path]))


def validate_tag(tag, ref, obj, commit, version):
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("tag must be vMAJOR.MINOR.PATCH")
    if ref.get("ref") != f"refs/tags/{tag}" or ref.get("object", {}).get("type") != "tag":
        raise ValueError("release requires a direct annotated tag, not a lightweight tag")
    if obj.get("sha") != ref["object"].get("sha") or obj.get("tag") != tag:
        raise ValueError("annotated tag identity mismatch")
    target = obj.get("object", {})
    if target.get("type") != "commit" or target.get("sha") != commit:
        raise ValueError("tag must directly target the checked-out commit")
    verification = obj.get("verification", {})
    if verification.get("verified") is not True or verification.get("reason") != "valid":
        raise ValueError("GitHub must report a valid OpenPGP tag signature")
    if tag != f"v{version}":
        raise ValueError("release tag does not match committed VERSION")


def validate_checks(runs):
    for name in REQUIRED_CHECKS:
        matching = [run for run in runs if run.get("name") == name]
        if not matching or any(
                run.get("status") != "completed" or run.get("conclusion") != "success"
                or run.get("app", {}).get("slug") != "github-actions"
                for run in matching):
            raise ValueError(f"required CI check is missing, pending, or failed: {name}")


def validate_gpg_status(status):
    valid = [line.split() for line in status.splitlines()
             if line.startswith("[GNUPG:] VALIDSIG ")]
    if len(valid) != 1 or valid[0][2] != TRUSTED_SIGNER:
        raise ValueError("tag was not signed by the pinned full OpenPGP fingerprint")


def verify_local_signature(root, tag, temporary):
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("GH_TOKEN", "GITHUB_TOKEN")}
    with tempfile.TemporaryDirectory(prefix="release-gpg.", dir=temporary) as home:
        environment["GNUPGHOME"] = home
        key = Path(home) / "public-key.asc"
        with urllib.request.urlopen(PUBLIC_KEY_URL, timeout=60) as response:
            content = response.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            raise ValueError("unexpectedly large public-key response")
        key.write_bytes(content)
        try:
            subprocess.run(["gpg", "--batch", "--import", str(key)],
                           env=environment, check=True, capture_output=True)
            result = subprocess.run(
                ["git", "-C", str(root), "-c", "gpg.format=openpgp",
                 "-c", "gpg.program=gpg", "verify-tag", "--raw", tag],
                env=environment, text=True, capture_output=True, check=True)
            validate_gpg_status(result.stderr)
        finally:
            subprocess.run(["gpgconf", "--homedir", home, "--kill", "all"],
                           env=environment, check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--temporary-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    temporary = args.temporary_dir.resolve()
    try:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
            raise ValueError("invalid GitHub repository")
        if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.tag):
            raise ValueError("invalid release tag")
        if not temporary.is_dir() or temporary == root or root in temporary.parents:
            raise ValueError("temporary directory must exist outside the checkout")
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        version = subprocess.check_output(
            ["git", "-C", str(root), "show", f"{commit}:VERSION"], text=True).strip()
        base = f"repos/{args.repository}"
        ref = api(f"{base}/git/ref/tags/{args.tag}")
        obj = api(f"{base}/git/tags/{ref['object']['sha']}")
        validate_tag(args.tag, ref, obj, commit, version)
        branch = api(base)["default_branch"]
        comparison = api(f"{base}/compare/{commit}...{branch}")
        if comparison.get("status") not in ("ahead", "identical"):
            raise ValueError("tagged commit is not reachable from the default branch")
        runs = []
        for page in range(1, 101):
            batch = api(f"{base}/commits/{commit}/check-runs?filter=latest&per_page=100&page={page}")["check_runs"]
            runs.extend(batch)
            if len(batch) < 100:
                break
        else:
            raise ValueError("too many check runs")
        validate_checks(runs)
        verify_local_signature(root, args.tag, temporary)
        print(f"Verified {args.repository}@{args.tag}: {commit}; signer {TRUSTED_SIGNER}")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"verify-release: {error}\n")


if __name__ == "__main__":
    main()
