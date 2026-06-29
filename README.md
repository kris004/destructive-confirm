# destructive-confirm

Native GTK/libadwaita confirmation dialog for destructive actions.

It is useful from shell scripts that need a small GUI confirmation step before
running an action such as restart, shutdown, deletion, or data replacement.

## Build

```sh
make
```

Dependencies are discovered with `pkg-config`:

- GTK 4
- libadwaita 1

## Install

```sh
make install
```

By default this installs to `~/.local/bin/destructive-confirm` and creates a
compatibility symlink at `~/.local/bin/power-confirm`.

## Usage

```sh
destructive-confirm \
  --title "Confirm action" \
  --text "Delete this item?" \
  --confirm-label "Delete" \
  --cancel-label "Cancel"
```

Exit status:

- `0`: confirmed
- non-zero: cancelled, closed, Escape, or error
