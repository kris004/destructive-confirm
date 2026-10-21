# Contributing

Keep changes small and explain the user-visible behavior they change.
Bug reports should include the command used, expected/actual behavior, selected
animation preset, GTK/libadwaita versions, and display backend. Redact personal
paths, private hostnames, and sensitive text before sharing logs or screenshots.
See [SECURITY.md](SECURITY.md) for sensitive reports.

## Build and test

Use the dependencies in the [README](README.md). Full validation additionally
needs Python 3 with Pillow, GNU `timeout`, GLib's `gresource`, and binutils `nm`.

```sh
make check
make smoke-gui
make check-presets
python3 -B -m unittest discover -s art
git diff --check
```

`make check` verifies help and invalid arguments without needing a display.
`make smoke-gui` tests native responses, keyboard activation, motion preferences,
and both dialog layouts. Its two six-second timeouts are expected successes.
Do not interact with those dialogs while the test runs.

On systems whose GTK includes X11 support, a headless session can use:

```sh
dbus-run-session -- xvfb-run -a env \
    GDK_BACKEND=x11 GSK_RENDERER=cairo GTK_A11Y=none make smoke-gui
```

This is the Ubuntu 24.04 CI path; it needs Xvfb, xauth, and a session D-Bus.
An Xvfb server cannot test a Wayland-only GTK build. For those builds, run in a
Wayland session or use a private headless Wayland compositor. Disabling the
accessibility bus in this isolated test does not change desktop preferences;
also check real keyboard/focus and accessibility behavior on a normal desktop.

`make check-presets` builds all five selections in temporary directories,
compares every embedded resource with its manifest, tests incremental switching,
rejects invalid selectors, and checks staged installation/removal. It does not
change your local `config.h` or installed binary.

## Compatibility boundaries

- Keep the existing options stable. Any non-zero result must prevent callers
  from proceeding; help is the explicit non-dialog success case.
- Preserve `power-confirm` as a compatibility symlink.
- Keep response widgets native and decorative layers non-interactive.
- Keep styling process-local. Never modify global GTK CSS or user preferences.
- Preserve reduced-motion and high-contrast behavior.
- Do not execute caller-supplied shell commands or add privilege escalation.

## Artwork

Builds use the checked-in frames, not Blender. To change artwork, follow
[art/README.md](art/README.md); keep renders, fluid caches, and Blender state
outside the checkout, then remove them after validating the packed assets.
Commit recipe, timing metadata, manifest, and affected frames together.
Do not regenerate the other saved presets as a side effect.

## Licensing and review

Contributions must be available under GPL-3.0-or-later, including any artwork.
Preserve third-party attribution and explain the provenance of new assets.
Do not include secrets, internal infrastructure details, or personal data.
Use focused commits and include the tests run. CI is validation only: it does
not install on a user's machine, publish packages, or create releases.
