# Original Blender fire artwork

`render-fire.py` builds and renders the scene from scratch with Blender 5.0.
The rounded emissive perimeter, turbulent translucent flame ribbons, sparks,
and compositor glow are original procedural artwork. There are no downloaded
textures, stock footage, external add-ons, fluid caches, or user startup files.
The Python scene recipe is the editable source; a `.blend` file is not needed
for reproduction.

The sequence is 30 fps, interpolated by GTK at the display's frame rate:

- `000` through `065`: visible spark, clockwise ignition, and settling (2.2 seconds).
- `066` through `155`: seamlessly repeating burning ring (3 seconds).

The spark holds for 0.55 seconds before its 1.3-second sweep. Its white-hot
core sits outside the opaque native button face, where it remains visible.
Flame ribbons range from 44 to 116 source pixels tall, four times the earlier
11–29 pixel geometry, with more mesh segments and slower billowing motion.

Frames are transparent 640 x 320 PNGs. The reference face is 320 x 64 source
pixels, at half scale in logical pixels. Shared constants in `fire_config.py`
describe the source slices and native drawing geometry. The overlay draws
eight patches around the actual button bounds, not into the label area. The
larger flames can overlap surrounding space; no decorative padding enlarges
the native button or its hit target.

## Regenerate

Only artwork generation needs Blender 5.0 and Python 3 with Pillow. Normal
builds use the checked-in PNGs and require neither tool.

Use a task-owned scratch directory outside the checkout. For example:

```sh
scratch=$(mktemp -d "${TMPDIR:-/tmp}/destructive-confirm-art.XXXXXXXX")
mkdir -p "$scratch/cache" "$scratch/config" "$scratch/tmp"

XDG_CACHE_HOME="$scratch/cache" BLENDER_USER_CONFIG="$scratch/config" \
TMPDIR="$scratch/tmp" \
blender --background --factory-startup --disable-autoexec --threads 4 \
  --python-exit-code 1 --python art/render-fire.py -- \
  --output "$scratch/frames"

python3 art/pack-fire.py "$scratch/frames"
python3 -B -m unittest discover -s art
make check
make smoke-gui
```

Some distributions version the Blender executable, for example `blender-5.0`.
The renderer uses four CPU threads and does not change the running desktop
Blender instance or its preferences. It does not require a GPU.

For a quick art check, add `--frames 4,36,90` after the output argument. To save
the constructed scene for manual editing, add `--scene "$scratch/fire.blend"`.
The scene shows the last rendered frame; the script drives animation geometry.
The packer requires the complete 156-frame render, not just preview frames.

After verifying the shipped files, remove the task-owned scratch directory:

```sh
rm -r -- "$scratch"
```

`pack-fire.py` strips render metadata, clears noisy RGB under zero alpha, and
generates `data/fire-art.h` and `data/destructive-confirm.gresource.xml`. Visible
RGBA pixels are not quantized. Commit these together with all 156 frames.
Change frame count, timing, reference geometry, or nine-slice dimensions in
`fire_config.py` and regenerate the header and artwork together.

`make smoke-gui` also exercises the real native button/alert constructors and
response handlers, including normal hit bounds, Cancel, Escape, close, keyboard
activation, and motion preferences. For a motion preview, prefer a display-rate
video capture over a low-frame-rate GIF, which can hide interpolation quality.
