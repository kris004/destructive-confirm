#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package an exact committed source tree; never include local build/config state."""

import argparse
import gzip
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

VERSION_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def package(repo, ref, output):
    repo = Path(repo).resolve()
    output = Path(output).resolve()
    if output == repo or repo in output.parents:
        raise ValueError("release output must be outside the source checkout")
    commit = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    version = git(repo, "show", f"{commit}:VERSION").decode().strip()
    if not VERSION_RE.fullmatch(version):
        raise ValueError("committed VERSION must be MAJOR.MINOR.PATCH")
    archive = f"destructive-confirm-{version}-src.tar.gz"
    names = (archive, "SHA256SUMS")
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() or (output / name).is_symlink() for name in names):
        raise ValueError("refusing to overwrite existing release artifacts")

    # All intermediate files stay beside the external output, not in the tree.
    with tempfile.TemporaryDirectory(prefix=".source-package.", dir=output) as tmp:
        tmp = Path(tmp)
        content = git(repo, "archive", "--format=tar",
                      f"--prefix=destructive-confirm-{version}/", commit)
        with (tmp / archive).open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(content)
        digest = hashlib.sha256((tmp / archive).read_bytes()).hexdigest()
        (tmp / "SHA256SUMS").write_text(f"{digest}  {archive}\n")
        created = []
        try:
            for name in names:
                # Exclusive creation also protects against a late collision.
                with (output / name).open("xb") as destination:
                    created.append(output / name)
                    destination.write((tmp / name).read_bytes())
        except Exception:
            for path in created:
                path.unlink()
            raise
    return [output / name for name in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        for path in package(root, args.ref, args.output_dir):
            print(path)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"package-release: {error}\n")


if __name__ == "__main__":
    main()
