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

No remote host, repository URL, CI badge, or release version is assumed here.
The included GitHub Actions workflow is non-publishing and needs its first
hosted run after an explicitly authorized repository setup/push.

## Repository setup

On the chosen hosting service, protect the default branch with reviewed pull
requests, required CI, and deletion/force-push prevention. Enable secret
protection and private vulnerability reporting where available. Use read-only
workflow permissions by default; pin actions to reviewed full commit hashes.
Do not expose signing keys or personal tokens to pull-request code.

## If versioned releases are introduced

There is no release automation or versioned binary distribution at present.
Do not create an arbitrary version or an unsigned tag merely to publish source.
Before the first versioned release:

1. Define the version contract (tag, source/package version, and `--version`
   output), supported platforms, source archive, and any binary deliverables.
2. Require CI on the exact reviewed default-branch commit and protect version
   tags against update/deletion.
3. Authorize the release with a hardware-backed OpenPGP signature on an
   annotated tag. Verify the signature and direct commit target locally;
   never substitute a lightweight or unsigned tag if signing is unavailable.
4. Make release automation independently verify the annotated tag's signature
   and target before building. Build/test/package once; use those same bytes
   for checksums, attestations, and publication.
5. Exercise the complete artifact path with a non-publishing manual dry run.
   Assemble every asset before publishing an immutable release.
6. Verify the public source, downloads, checksums, attestations, and immutability.
   Never recreate a published tag or rebuild under an existing version.

Release tooling must also carry corresponding source and license notices
appropriate to GPL-3.0-or-later distribution. This checklist is not a substitute
for implementing and testing the release path before using it.
