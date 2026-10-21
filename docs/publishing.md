# Publication checklist

The repository can be prepared locally without publishing it. Creating a
remote, pushing, changing visibility, tagging, and releasing are separate
maintainer decisions, not effects of a build or test.

## Before making source history public

- Review the current tree **and all reachable Git history** for credentials,
  private paths/hosts, personal data, binary metadata, and unlicensed assets.
  A clean working tree alone is not a history audit. Review author/committer
  identities too; ordinary attribution is public when history is published.
- Run a secret scanner over the complete history, for example
  `gitleaks git --redact --log-opts="--all" .`, and review findings rather than
  suppressing them indiscriminately. Also inspect environment-specific text
  and image metadata; secret scanning alone cannot establish privacy.
- Confirm GPL-3.0-or-later coverage and preserve LICENSE, COPYRIGHT, recipes,
  and editable artwork sources.
- Test a clean source snapshot, not just a developer's ignored build output.
  Run the documented CLI, GUI, preset, artwork, and staged-install checks.
- Review the exact commits and files to be published. Do not rewrite history
  automatically; rotate an exposed credential before considering removal.

The upstream repository is
[kris004/destructive-confirm](https://github.com/kris004/destructive-confirm).
CI validates branches and pull requests; it does not publish anything.

## Repository setup

On the chosen hosting service, protect the default branch with reviewed pull
requests, required CI, and deletion/force-push prevention. Enable secret
protection and private vulnerability reporting where available. Use read-only
workflow permissions by default; pin actions to reviewed full commit hashes.
Do not expose signing keys or personal tokens to pull-request code.

## Source-only releases

`VERSION` is authoritative for the program's `--version` output, source archive,
and signed `vMAJOR.MINOR.PATCH` tag. There are no upstream binary packages:
GTK/libadwaita and the selected artwork are built on the destination system.

1. Review and merge version/release preparation through a pull request.
2. Require CI on the exact reviewed default-branch commit and protect version
   tags against update/deletion.
3. Authorize the release with a hardware-backed OpenPGP signature on an
   annotated tag. Verify the signature and direct commit target locally;
   never substitute a lightweight or unsigned tag if signing is unavailable.
4. Run the non-publishing manual `Release` workflow on that commit. It builds,
   tests, archives the exact Git tree, rebuilds the extracted archive, uploads
   checksums, and attests the artifact. It does not create a GitHub Release.
5. Enable and verify repository immutable releases **before pushing the tag**.
   Push only the already-verified tag. The release workflow independently
   verifies GitHub's tag signature status, direct target, committed VERSION,
   default-branch reachability, required CI, and the pinned full signer
   fingerprint using GnuPG with the signer's public key.
6. Verify the public source, downloads, checksums, attestations, and immutability.
   Never recreate a published tag or rebuild under an existing version.

The workflow uploads and attests the tested source archive and `SHA256SUMS`.
Publication downloads those **same artifacts**, assembles a draft with every
asset, then publishes it as immutable. It never rebuilds in the publishing job.
Signing-key rotation requires a reviewed change to both `tools/verify-release.py`
and the Gentoo overlay's trusted-fingerprint registry.

## Commands

Local packaging is non-publishing and refuses output inside the checkout or
overwriting existing artifacts:

```sh
scratch=$(mktemp -d "${TMPDIR:-/tmp}/destructive-confirm-release.XXXXXXXX")
make check-release
make OUTPUT_DIR="$scratch/dist" RELEASE_REF=HEAD dist
(cd "$scratch/dist" && sha256sum --check SHA256SUMS)
```

Use the `Release` workflow's manual run as the hosted dry run:

```sh
gh workflow run release.yml --repo kris004/destructive-confirm --ref main
```

After its success and fresh main CI, create the authorized tag at that exact
commit with the hardware-backed signing key:

```sh
version=$(cat VERSION)
commit=$(git rev-parse origin/main)
git tag -s "v$version" "$commit" -m "destructive-confirm v$version"
git verify-tag --raw "v$version"
test "$(git cat-file -t "v$version")" = tag
test "$(git rev-parse "v$version^{commit}")" = "$commit"
git push origin "refs/tags/v$version"
```

Download the published source archive and `SHA256SUMS` together, verify the
checksums, and use `gh attestation verify ARCHIVE --repo kris004/destructive-confirm`.
Source includes license notices and editable artwork recipes. Remove local
scratch after preserving any needed result; Git history is the source of truth.

If a tagged run fails, preserve the tag and recover the exact original tested
artifact. Do not rerun a build under that version, use `--clobber`, or delete
and recreate the tag/release. A partial draft must be reviewed against the
original checksums before completing publication.
