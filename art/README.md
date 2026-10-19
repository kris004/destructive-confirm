# Original Blender fire artwork

`render-fire.py` builds and renders the scene from scratch with Blender 5.0.
The rounded emissive perimeter, turbulent translucent flame ribbons, sparks,
and compositor glow are original procedural artwork. There are no downloaded
textures, stock footage, external add-ons, fluid caches, or user startup files.
The Python scene recipe is the editable source; a `.blend` file is not needed
for reproduction.

The sequence is 24 fps:

- `000` through `035`: spark, clockwise ignition, and settling (1.5 seconds).
- `036` through `083`: seamlessly repeating burning ring (2 seconds).

Frames are transparent 384 x 128 PNGs. The reference face is 320 x 64 pixels,
with 32 pixels of transparent space on each side. GTK uses 52-pixel source
slices at 26 logical pixels, reserving a 16-pixel decorative border. The
remaining 10 pixels preserve the rounded corners of the red button face.
Nothing is rendered into the label area.

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

For a quick art check, add `--frames 3,18,50` after the output argument. To save
the constructed scene for manual editing, add `--scene "$scratch/fire.blend"`.
The scene shows the last rendered frame; the script drives animation geometry.
The packer requires the complete 84-frame render, not just preview frames.

After verifying the shipped files, remove the task-owned scratch directory:

```sh
rm -r -- "$scratch"
```

`pack-fire.py` strips render metadata and generates `data/fire-animation.css`
and `data/destructive-confirm.gresource.xml`. Commit these together with all
84 frames. Changes to frame count, timing, reference geometry, or nine-slice
dimensions must be kept consistent between the two scripts and `data/style.css`.
