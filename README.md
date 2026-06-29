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
  --confirm-label "Delete" \
  --cancel-label "Cancel"
```

`--text` is optional. Omit it for a button-only prompt, or supply it when the
button labels alone do not carry enough context.

Exit status:

- `0`: confirmed
- non-zero: cancelled, closed, Escape, or error
