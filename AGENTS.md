# Repository Guidelines

This repository contains a tiny GTK/libadwaita C helper for desktop power-action
confirmation.

## Structure

- `src/power-confirm.c` contains the application.
- `docs/design.md` explains behavior and tradeoffs.
- `Makefile` builds and installs the single binary.

## Editing Guidelines

- Keep the command-line interface stable unless `power-menu` is updated at the
  same time.
- Preserve the exit-status contract: `0` only confirms; non-zero cancels or
  reports an error.
- Keep styling scoped inside the process; do not write global GTK CSS.
- Prefer GTK/libadwaita semantics over manually recreated widget behavior.

## Validation

Run:

```sh
make check
make smoke-gui
```

`make smoke-gui` intentionally opens a dialog and expects it to be killed by
`timeout`, proving the dialog stays alive awaiting a response.
