/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef ANIMATION_CONFIG_H
#define ANIMATION_CONFIG_H

/* Zero is deliberately invalid: a misspelled macro must not select "none". */
#define ANIMATION_SVG_FLAMES 1
#define ANIMATION_FIRE_RING 2
#define ANIMATION_TALL_RING 3
#define ANIMATION_NONE 4
#define ANIMATION_REAL_FIRE 5

#ifndef DC_CONFIG_HEADER
#error "Build with the Makefile to select the configuration header"
#endif
#include DC_CONFIG_HEADER

#if CONFIRM_ANIMATION == ANIMATION_SVG_FLAMES
#define DC_PRESET_NAME "svg-flames"
#elif CONFIRM_ANIMATION == ANIMATION_FIRE_RING
#define DC_PRESET_NAME "fire-ring"
#elif CONFIRM_ANIMATION == ANIMATION_TALL_RING
#define DC_PRESET_NAME "tall-ring"
#elif CONFIRM_ANIMATION == ANIMATION_NONE
#define DC_PRESET_NAME "none"
#elif CONFIRM_ANIMATION == ANIMATION_REAL_FIRE
#define DC_PRESET_NAME "real-fire"
#else
#error "Invalid CONFIRM_ANIMATION: choose ANIMATION_SVG_FLAMES, ANIMATION_FIRE_RING, ANIMATION_TALL_RING, ANIMATION_REAL_FIRE, or ANIMATION_NONE"
#endif

#if CONFIRM_ANIMATION == ANIMATION_TALL_RING
#define DC_FIRE_ART_HEADER "../data/presets/tall-ring/fire-art.h"
#elif CONFIRM_ANIMATION == ANIMATION_REAL_FIRE
#define DC_FIRE_ART_HEADER "../data/presets/real-fire/fire-art.h"
#endif
#define DC_ANIMATION_OVERLAY (CONFIRM_ANIMATION == ANIMATION_TALL_RING || CONFIRM_ANIMATION == ANIMATION_REAL_FIRE)
#define DC_ANIMATION_ENABLED (CONFIRM_ANIMATION != ANIMATION_NONE)

#endif
