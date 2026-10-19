# Saved animation presets

Each directory is a self-contained resource bundle. All bundles expose the same
application resource prefix, but the build embeds exactly one. Stylesheets keep
their original resource paths, so changing a preset does not require changing
the dialog's command-line interface.

| Preset | Saved version | Editable artwork source |
| --- | --- | --- |
| `svg-flames` | `7927349` | `flames.svg` and `flames-core.svg` in this preset |
| `fire-ring` | `ff90dc7` | `art/fire-ring/render-fire.py` and `art/fire-ring/pack-fire.py` |
| `tall-ring` | `c135d4f` | `art/render-fire.py`, `art/fire_config.py`, and `art/pack-fire.py` |
| `none` | Static fallback | This preset's stylesheet; no image files |

All artwork is original procedural artwork, not downloaded stock assets.
Historical styles and frames are preserved, not regenerated approximations.
The smaller `fire-ring` retains its original 16-pixel decorative button border
and 24 fps CSS playback. `svg-flames` paints inside the native button.
`tall-ring` retains the current normal button geometry, display-rate frame
blending, and non-interactive overhanging fire layer.

Selection is in the repository root's local `config.h`; `config.def.h` documents
the default. Ordinary builds use the checked-in assets and require no Blender
or Python. Each preset's XML manifest is authoritative for the embedded files.
Do not add other presets' files to a manifest.

Both rendered rings retain their original transparent PNGs and metadata-free
resource bundles. Their generation recipes are separate because their geometry,
timing, compositing, and playback differ.
