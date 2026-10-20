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

By default the destructive button catches fire: a visible spark ignites, flame
travels clockwise around the button, then settles into a tall burning ring. The fire
can overlap nearby space, without changing native button sizes or hit targets.
Rendered frames are blended at the display's frame rate for smoother motion.
Animation follows GTK's animation preference (and reduced-motion preference on
GTK 4.22+); high-contrast mode uses a plain red button instead. Blender is only
needed to regenerate the artwork, not to build or run the helper. See
[`art/README.md`](art/README.md) for the reproducible scene recipe.

## Compile-time animation selection

The first build copies `config.def.h` to the ignored local `config.h`. Edit
that header to select one preset, then rebuild:

```c
#define CONFIRM_ANIMATION ANIMATION_TALL_RING
```

| Header value | Preset | Appearance |
| --- | --- | --- |
| `ANIMATION_TALL_RING` | `tall-ring` (default) | Current tall Blender flames, visible spark, smooth playback |
| `ANIMATION_FIRE_RING` | `fire-ring` | Original smaller Blender ring and stepped ignition |
| `ANIMATION_SVG_FLAMES` | `svg-flames` | Original animated SVG flames inside the button |
| `ANIMATION_REAL_FIRE` | `real-fire` | Fluid-simulated rising flames with a visible ignition spark |
| `ANIMATION_NONE` | `none` | Plain red destructive button, no decorative animation |

```sh
make
make check
make smoke-gui
# Install the new selection when ready:
make install
```

Only the selected preset's stylesheet and artwork are embedded. `none` embeds
no flame images and links no fire-overlay player. The CLI and exit statuses are
identical for every preset; there is no runtime animation option.

Local `config.h` is never overwritten, including by `make clean`. Compare it
with `config.def.h` after updating the source. Packagers/tests can use an
existing alternate header with `make CONFIG_H=/path/to/config.h`. Selection
changes rebuild the resource bundle automatically; no clean build or Blender
render is required.

The named presets and their sources are preserved in the repository; see
[`data/presets/README.md`](data/presets/README.md). Optional
`make check-presets` builds all five selections and verifies their actual
embedded resources, incremental switching, and invalid-selection errors
(requires Python 3, `gresource`, and `nm`). Artwork checks additionally use
Pillow: `python3 -B -m unittest discover -s art`.

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
