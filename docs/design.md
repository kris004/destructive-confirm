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
button uses an ember-red background, two layers of flame artwork, and a warm
glow. A dark scrim behind the white label keeps the action readable. Cancel and
the rest of the GTK theme are unchanged.

GTK CSS keyframes gently vary flame size, position, and glow. They only change
painting, never button geometry, focus, keyboard activation, or hit targets.
Both the compact window and the native alert responses use the same CSS without
reaching into libadwaita's private widget tree.

The effect follows `GtkSettings:gtk-enable-animations` and, when built with GTK
4.22 or newer, `GtkSettings:gtk-interface-reduced-motion`. With motion disabled,
the flames remain still. High-contrast mode removes flames and glow entirely in
favor of a solid red button with a white border. Preference changes are applied
while the dialog is open; no global GTK settings or CSS are written.

The stylesheet and original SVG flame layers live in `data/` and are compiled
into a GResource inside the executable using `glib-compile-resources`. The
installed helper remains a single self-contained binary.

The flame layers cover the button once rather than using `repeat-x`, which
produced horizontal seams with GTK's GPU renderer. Transparent bottom padding
is positioned below the button's clip.

The application uses `G_APPLICATION_NON_UNIQUE` because it is a command-line
prompt helper. Each invocation must use its own arguments instead of activating
an older still-running prompt with the same application ID.

## Installation

The project builds a single binary at `build/destructive-confirm` and installs
it to `$(PREFIX)/bin/destructive-confirm`, defaulting to
`~/.local/bin/destructive-confirm`. `make install` also creates a
`power-confirm` symlink for older callers.
