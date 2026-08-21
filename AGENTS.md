# Repository Guidelines

This repository contains a tiny GTK/libadwaita C helper for destructive-action
confirmation dialogs.

## Structure

- `src/destructive-confirm.c` contains the application.
- `docs/design.md` explains behavior and tradeoffs.
- `Makefile` builds and installs the binary plus a compatibility symlink.

## Editing Guidelines

- Keep the command-line interface script-friendly and stable unless callers are
  updated at the same time.
- Preserve the exit-status contract: `0` only confirms; non-zero cancels or
  reports an error.
- Keep styling scoped inside the process; do not write global GTK CSS.
- Prefer GTK/libadwaita semantics over manually recreated widget behavior.
- Keep `power-confirm` as a compatibility symlink unless all callers have been
  migrated and the user explicitly wants it removed.

## Validation

Run:

```sh
make check
make smoke-gui
```

`make smoke-gui` intentionally opens a dialog and expects it to be killed by
`timeout`, proving the dialog stays alive awaiting a response.

## Publication Boundary

- Treat every file, commit, branch, tag, and reachable history as potentially
  public, even while the remote repository is private or absent.
- Do not commit secrets, private network details, personal data, private issue
  links, environment identifiers, or unnecessary absolute local paths.
- Keep documentation, examples, fixtures, and defaults portable for external
  users and contributors.
- Preserve unrelated dirty work and stage exact paths.
- Before exposing previously private history, scan both the current tree and
  reachable Git history for private or environment-specific material.
- Do not change visibility, publish, push, or create a release without explicit
  authorization.
