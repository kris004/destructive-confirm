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

The build also needs GLib's `glib-compile-resources`. Styling and flame artwork
are embedded in the binary; no asset directory is needed after installation.

The destructive button has a Blender-rendered fire border: a spark ignites,
flame travels clockwise around the button, then settles into a burning ring.
Animation follows GTK's animation preference (and reduced-motion preference on
GTK 4.22+); high-contrast mode uses a plain red button instead. Blender is only
needed to regenerate the artwork, not to build or run the helper. See
[`art/README.md`](art/README.md) for the reproducible scene recipe.

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
