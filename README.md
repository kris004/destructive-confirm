# power-confirm

Native GTK/libadwaita confirmation dialog for destructive power actions.

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

By default this installs to `~/.local/bin/power-confirm`. Override `PREFIX` or
`BINDIR` if needed.

## Usage

```sh
power-confirm \
  --title "Power menu" \
  --text "Restart now?" \
  --confirm-label "Restart now" \
  --cancel-label "Cancel"
```

Exit status:

- `0`: confirmed
- non-zero: cancelled, closed, Escape, or error
