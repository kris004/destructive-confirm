# power-confirm design

## Goal

`power-confirm` is a tiny native confirmation dialog for destructive desktop
power actions such as restart and shutdown.

It exists because `zenity --question` is good for simple confirmation, but does
not provide a supported way to mark only the confirm button as destructive or to
fix that button's foreground color independently from the rest of the dialog.

## Requirements

- Provide a small executable suitable for `~/.local/bin/power-confirm`.
- Keep the command-line interface used by `power-menu`:
  - `--title <text>`
  - `--text <text>`
  - `--confirm-label <text>`
  - `--cancel-label <text>`
- Exit `0` only when the user confirms.
- Exit non-zero for Escape, Cancel, close, parse errors, or display failures.
- Make Enter activate the confirm response.
- Make Escape/window-close activate cancel.
- Use native GTK/libadwaita destructive response styling.
- Scope any CSS fixes to this process only.

## Implementation choice

The helper is written in C against GTK 4 and libadwaita. This keeps startup and
runtime overhead low while using Adwaita's native destructive button semantics.

The dialog is an `AdwAlertDialog` with two responses:

- `confirm`: default response, destructive appearance
- `cancel`: close response

A small CSS provider forces the destructive button text to white. The background
is still supplied by the theme's destructive-action styling, so this only fixes
the low-contrast red-on-red foreground seen with the current theme.

## Installation

The project builds a single binary at `build/power-confirm` and installs it to
`$(PREFIX)/bin/power-confirm`, defaulting to `~/.local/bin/power-confirm`.
