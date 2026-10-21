# README demo

`real-fire.gif` shows the native compact dialog with the `ANIMATION_REAL_FIRE`
preset. It is not a desktop screenshot, mockup, or replacement button drawing:
`tools/capture-preview.c` snapshots the actual GTK widget and embedded artwork.
It forces dark mode only inside the capture process and runs no action.
The GIF restarts ignition; an open dialog instead continues its burning loop.

The preview and its capture source are GPL-3.0-or-later, like the rest of this
project. Recreate it with the normal build dependencies, a graphical session,
and FFmpeg:

```sh
scratch=$(mktemp -d "${TMPDIR:-/tmp}/destructive-confirm-preview.XXXXXXXX")
printf '#define CONFIRM_ANIMATION ANIMATION_REAL_FIRE\n' > "$scratch/config.h"
make BUILD_DIR="$scratch/build" CONFIG_H="$scratch/config.h" preview-tool
"$scratch/build/capture-preview" "$scratch/frames"

ffmpeg -v error -framerate 30 -i "$scratch/frames/%03d.png" \
  -filter_complex \
  'split[a][b];[a]palettegen=stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a' \
  -loop 0 "$scratch/real-fire.gif"
```

Review the complete dialog, ignition, loop, label, and transparent fringe before
copying the GIF to this directory. The capture tool uses the selected preset,
not the installed binary, so your local selection and installation are unchanged.
Leave the demo buttons alone while capturing; it closes itself after six seconds.
After copying the required result, remove the disposable capture:

```sh
make BUILD_DIR="$scratch/build" clean
rm -r -- "$scratch"
```
