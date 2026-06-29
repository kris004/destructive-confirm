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
  - `--text <text>`
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

The dialog is an `AdwAlertDialog` with two responses:

- `confirm`: default response, destructive appearance
- `cancel`: close response

The current local theme did not give the destructive response the high-contrast
red button treatment expected for this prompt, so the helper also installs a
small process-local CSS provider for `button.destructive-action`. That CSS gives
the destructive button a red background and white text while leaving the rest of
the GTK theme alone.

## Installation

The project builds a single binary at `build/destructive-confirm` and installs
it to `$(PREFIX)/bin/destructive-confirm`, defaulting to
`~/.local/bin/destructive-confirm`. `make install` also creates a
`power-confirm` symlink for older callers.
