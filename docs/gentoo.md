# Gentoo packaging

The [kris004 overlay](https://github.com/kris004/gentoo-overlay) packages
`gui-apps/destructive-confirm` from immutable, signed upstream releases.
It builds locally from a source archive pinned to the exact release commit;
there is no live ebuild or prebuilt upstream binary.

## Installation and animation choice

After adding/synchronizing that overlay, review the ebuild and use:

```sh
emerge --ask gui-apps/destructive-confirm::kris004
```

Packages begin with `~amd64` testing keywords. Normal Gentoo keyword acceptance
and dependency resolution apply. The default matches upstream `tall-ring`.
Four mutually exclusive USE flags choose the embedded preset:

| USE flag | Compile-time selection |
| --- | --- |
| `animation-tall-ring` (default) | `ANIMATION_TALL_RING` |
| `animation-real-fire` | `ANIMATION_REAL_FIRE` |
| `animation-fire-ring` | `ANIMATION_FIRE_RING` |
| `animation-svg` | `ANIMATION_SVG_FLAMES` |
| All four disabled | `ANIMATION_NONE` |

For fluid fire, a package.use entry is:

```text
gui-apps/destructive-confirm -animation-tall-ring animation-real-fire
```

The ebuild writes a build-local `config.h`; it does not consume your source
checkout's local header. Only one preset is embedded. It installs
`/usr/bin/destructive-confirm`, the `power-confirm` compatibility symlink,
and documentation/license notices. It installs no service and changes no GTK
preferences. A pre-existing `~/.local/bin` installation can shadow the package;
check `command -v destructive-confirm` before assuming the package is active.

## Build contract

- EAPI 8; a C17 compiler and GNU Make.
- Runtime/build: `>=gui-libs/gtk-4.14:4` and `>=gui-libs/libadwaita-1.5:1`.
- Build tools: `virtual/pkgconfig` and GLib's `glib-compile-resources`.
- Optional `test`: a compatible Python with Pillow, `gresource`, `nm`, and
  GNU `timeout`. Tests use `PYTHON` and `DC_TEST_TMPDIR="${T}"`.
- `src_compile`: export the Gentoo toolchain and run `emake`.
- `src_test`: CLI, all-preset resource/install checks, release-contract tests,
  and artwork checks. GUI tests run in upstream CI, not against the builder's
  desktop or a forced X11 GTK dependency.
- `src_install`: stage with `DESTDIR="${D}"` and an EPREFIX-aware `/usr` prefix.
- License: `GPL-3+`; no runtime Blender/Python/video-player dependency.

Portage's CFLAGS, CPPFLAGS, LDFLAGS, compiler, and pkg-config selection are
honored. Do not run `make install` into a live prefix from an ebuild.

## Automatic updates

The overlay registry uses `kind = "generic"` and a reviewed C/GTK template.
Its required upstream check is **Build, presets, and native dialogs**.
It requires a direct annotated OpenPGP tag, the pinned full signer fingerprint,
an immutable published GitHub Release, reachability from the default branch,
passing CI, safe source extraction, generated Manifests, and strict package QA.
Routine releases require no manual ebuild bump.

Changes to dependencies, installed paths, services, or animation flags require a
reviewed overlay-template update. Do not alter the workstation's separate
localrepo or unattended update providers as part of this public overlay flow.
