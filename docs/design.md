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
button has an ember-red face, white label, and Blender-rendered fire around its
outside. A white-hot spark remains visible at the top-left for 0.55 seconds,
then sweeps clockwise over 1.3 seconds. At 2.2 seconds a seamless three-second
burning loop takes over. Flame geometry is four times taller than the original
small border effect. The label and button face are not part of the artwork.

The dialog retains ordinary button sizes, spacing, focus outlines, and hit
targets. `src/fire-overlay.c` draws the decoration behind the original content
using `GtkOverlay`. Neither response buttons nor their labels are replaced.
For the alert path, the public `AdwDialog:child` API wraps the existing content,
and `AdwDialog:default-widget` supplies the native confirm button. Production
code does not traverse libadwaita's private widget tree.

Eight nine-slice patches preserve corner shape and flame thickness at different
label lengths; they stretch, never tile. The center is not drawn. Flames may
spill over the surrounding dialog space, but opaque native controls keep their
labels clear. A transparent 56-pixel outer window fringe avoids clipping fire
outside the normal-sized dialog card. It is not button padding. The surface
input region is limited to the card so this invisible fringe does not intercept
clicks intended for other applications.

The first mapped GTK frame starts the ignition, so startup work does not consume
the spark. The frame clock blends adjacent 30 fps rendered frames at the
display's frame rate. A four-texture cache bounds decoded artwork memory.
Only painting changes during the sequence; layout and response behavior remain
native.

The effect follows `GtkSettings:gtk-enable-animations` and, when built with GTK
4.22 or newer, `GtkSettings:gtk-interface-reduced-motion`. With motion disabled,
the ring is shown already ignited and still, with no animation tick.
High-contrast mode removes the fire and transparent fringe in favor of a solid
red button with a white border. Preference changes are applied while the dialog
is open; no global GTK settings or CSS are written.

The stylesheet and 156 original RGBA frames live in `data/` and are compiled into
a GResource inside the executable using `glib-compile-resources`. PNG files are
already compressed and are not compressed again in the resource bundle. The
installed helper remains a single self-contained binary, with no Blender,
video decoder, playback process, or on-disk asset directory needed at runtime.

`art/render-fire.py` creates a deterministic Blender 5.0 scene with a rounded
emissive perimeter, turbulent translucent flame ribbons, sparks, and compositor
glow. This is procedural rendered artwork, not a baked fluid simulation or
stock footage. `art/fire_config.py` shares render geometry and playback timing.
`art/pack-fire.py` validates frames, strips metadata and invisible RGB noise,
and generates the playback header and resource manifest. It does not quantize
visible color or alpha. These tools are not run during an ordinary build; the
rendered assets are checked in.

The application uses `G_APPLICATION_NON_UNIQUE` because it is a command-line
prompt helper. Each invocation must use its own arguments instead of activating
an older still-running prompt with the same application ID.

## Installation

The project builds a single binary at `build/destructive-confirm` and installs
it to `$(PREFIX)/bin/destructive-confirm`, defaulting to
`~/.local/bin/destructive-confirm`. `make install` also creates a
`power-confirm` symlink for older callers.
