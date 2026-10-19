# destructive-confirm design

## Goal

`destructive-confirm` is a tiny native confirmation dialog for destructive
desktop actions.

It exists because `zenity --question` is good for simple confirmation, but does
not provide a supported way to mark only the confirm button as destructive or to
fix that button's foreground color independently from the rest of the dialog.

The first caller is the Sway power menu, but the helper is intentionally general
so other scripts can confirm deletion, replacement, reset, or similar actions
without growing their own GTK code.

## Requirements

- Provide a small executable suitable for `~/.local/bin/destructive-confirm`.
- Keep a compatibility `power-confirm` symlink for existing callers.
- Provide a script-friendly command-line interface:
  - `--title <text>`
  - `--text <text>` for optional explanatory text
  - `--confirm-label <text>`
  - `--cancel-label <text>`
- Exit `0` only when the user confirms.
- Exit non-zero for Escape, Cancel, close, parse errors, or display failures.
- Make Enter activate the confirm response.
- Make Escape/window-close activate cancel.
- Use native GTK/libadwaita destructive response semantics.
- Scope any CSS fixes to this process only.

## Implementation choice

The helper is written in C against GTK 4 and libadwaita. This keeps startup and
runtime overhead low while using Adwaita's destructive response semantics.

When explanatory text is supplied, the dialog is an `AdwAlertDialog` with a
heading and two responses:

- `confirm`: default response, destructive appearance
- `cancel`: close response

Callers should omit heading text when the button labels are already clear, such
as a two-button `Restart now` / `Cancel` prompt.

When text is omitted, the helper uses a compact undecorated GTK window containing
only the two buttons. `AdwAlertDialog` keeps alert-message spacing even with no
heading/body, so the custom compact path avoids a blank reserved text area.

The current local theme did not give the destructive response the high-contrast
red button treatment expected for this prompt, so the helper also installs a
small process-local CSS provider for `button.destructive-action`. The destructive
button has an ember-red face, white label, and a transparent decorative border
containing Blender-rendered fire. A spark ignites at the top-left, the flame
travels clockwise, and after 1.5 seconds a two-second burning loop takes over.
The label and button face are not part of the artwork. Cancel and the rest of
the GTK theme are unchanged.

The border reserves 16 logical pixels around the red face so fire does not
overlap adjacent controls. Native nine-slice border images preserve corner
shape and flame thickness at different label lengths. They stretch, never tile.
The native focus outline follows the full button, including this border.

GTK CSS keyframes select frames at 24 fps with discrete steps, rather than
cross-fading or rerendering fire. Only painting changes during the sequence;
geometry, focus, keyboard activation, and hit targets remain stable. Both the
compact window and native alert responses use the same stylesheet, without
reaching into libadwaita's private widget tree.

The effect follows `GtkSettings:gtk-enable-animations` and, when built with GTK
4.22 or newer, `GtkSettings:gtk-interface-reduced-motion`. With motion disabled,
the ring is shown already ignited and still. High-contrast mode removes the fire
and decorative border in favor of a normally sized solid red button with a
white border. Preference changes are applied while the dialog is open; no
global GTK settings or CSS are written.

The stylesheet and 84 original RGBA frames live in `data/` and are compiled into
a GResource inside the executable using `glib-compile-resources`. PNG files are
already compressed and are not compressed again in the resource bundle. The
installed helper remains a single self-contained binary, with no Blender,
video decoder, playback process, or on-disk asset directory needed at runtime.

`art/render-fire.py` creates a deterministic Blender 5.0 scene with a rounded
emissive perimeter, turbulent translucent flame ribbons, sparks, and compositor
glow. This is procedural rendered artwork, not a baked fluid simulation or
stock footage. `art/pack-fire.py` validates frames, strips metadata, and writes
the stepped animations and resource manifest. These tools are not run during
an ordinary build; the rendered assets are checked in.

The application uses `G_APPLICATION_NON_UNIQUE` because it is a command-line
prompt helper. Each invocation must use its own arguments instead of activating
an older still-running prompt with the same application ID.

## Installation

The project builds a single binary at `build/destructive-confirm` and installs
it to `$(PREFIX)/bin/destructive-confirm`, defaulting to
`~/.local/bin/destructive-confirm`. `make install` also creates a
`power-confirm` symlink for older callers.
