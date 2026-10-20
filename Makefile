APP := destructive-confirm
COMPAT_APP := power-confirm
BUILD_DIR := build
CONFIG_H ?= config.h
PRESET_MK := $(BUILD_DIR)/preset.mk
CONFIG_CPPFLAGS = -DDC_CONFIG_HEADER='"$(abspath $(CONFIG_H))"'
.DEFAULT_GOAL := all

# An included makefile lets resource dependencies follow the C header selection.
# Recheck each invocation, but replace it only on a real selection change.
# This also handles switching to an older CONFIG_H in the same BUILD_DIR.
ifneq ($(MAKECMDGOALS),clean)
include $(PRESET_MK)
endif

PRESET_DIR := data/presets/$(ANIMATION_PRESET)
SRC := src/destructive-confirm.c
HEADERS := src/animation-config.h $(CONFIG_H) $(PRESET_MK)
ifneq ($(filter tall-ring real-fire,$(ANIMATION_PRESET)),)
SRC += src/fire-overlay.c
HEADERS += src/fire-overlay.h $(PRESET_DIR)/fire-art.h
endif
RESOURCE_XML := $(PRESET_DIR)/destructive-confirm.gresource.xml
RESOURCE_FILES := $(wildcard $(PRESET_DIR)/*.css $(PRESET_DIR)/*.svg $(PRESET_DIR)/fire/*.png)
RESOURCE_SRC := $(BUILD_DIR)/resources.c
RESOURCE_OBJ := $(BUILD_DIR)/resources.o
PKGS := gtk4 libadwaita-1

PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
CC ?= cc
PKG_CONFIG ?= pkg-config
INSTALL ?= install
LN ?= ln
TIMEOUT ?= timeout
GLIB_COMPILE_RESOURCES ?= glib-compile-resources

WARN_CFLAGS := -std=c17 -Wall -Wextra -Wpedantic -Wformat=2 -Wshadow \
	-Wstrict-prototypes -Wmissing-prototypes -Werror=implicit-function-declaration
PKG_CFLAGS := $(shell $(PKG_CONFIG) --cflags $(PKGS))
PKG_LIBS := $(shell $(PKG_CONFIG) --libs $(PKGS))
CFLAGS ?= -O2 -g
LDLIBS += -lm

.PHONY: all check check-presets smoke-gui install clean FORCE

all: $(BUILD_DIR)/$(APP)

$(BUILD_DIR):
	mkdir -p $@

$(CONFIG_H):
	cp config.def.h $@

FORCE:

$(PRESET_MK): FORCE $(CONFIG_H) src/animation-config.h tools/preset.mk.in | $(BUILD_DIR)
	@$(CC) $(CPPFLAGS) $(CONFIG_CPPFLAGS) -E -P -x c tools/preset.mk.in -o $@.cpp
	@sed -n 's/^DC_SELECTED_PRESET = "\(.*\)"$$/override ANIMATION_PRESET := \1/p' $@.cpp > $@.tmp
	@test -s $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp $@.cpp

$(RESOURCE_SRC): $(RESOURCE_XML) $(RESOURCE_FILES) $(PRESET_MK) | $(BUILD_DIR)
	$(GLIB_COMPILE_RESOURCES) --sourcedir=$(PRESET_DIR) --generate-source \
		--c-name=destructive_confirm --internal --target=$@ $<

# Generated GLib byte strings exceed the ISO C minimum string length.
$(RESOURCE_OBJ): $(RESOURCE_SRC)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(PKG_CFLAGS) -c $< -o $@

$(BUILD_DIR)/$(APP): $(SRC) $(HEADERS) $(RESOURCE_OBJ) | $(BUILD_DIR)
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(CONFIG_CPPFLAGS) $(PKG_CFLAGS) $(SRC) $(RESOURCE_OBJ) -o $@ $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

$(BUILD_DIR)/test-dialog: tests/test-dialog.c $(SRC) $(HEADERS) $(RESOURCE_OBJ)
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(CONFIG_CPPFLAGS) $(PKG_CFLAGS) tests/test-dialog.c $(filter-out src/destructive-confirm.c,$(SRC)) $(RESOURCE_OBJ) -o $@ $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

check: $(BUILD_DIR)/$(APP)
	$(BUILD_DIR)/$(APP) --help >/dev/null
	$(BUILD_DIR)/$(APP) --does-not-exist >/dev/null 2>&1; test $$? -eq 2

check-presets:
	python3 -B tests/test-presets.py

smoke-gui: $(BUILD_DIR)/$(APP) $(BUILD_DIR)/test-dialog
	G_DEBUG=fatal-warnings $(BUILD_DIR)/test-dialog
	G_DEBUG=fatal-warnings $(TIMEOUT) 6 $(BUILD_DIR)/$(APP) --title 'Destructive action test' --confirm-label 'Delete' --cancel-label 'Cancel'; test $$? -eq 124
	G_DEBUG=fatal-warnings $(TIMEOUT) 6 $(BUILD_DIR)/$(APP) --title 'Destructive action test' --text 'Delete this item?' --confirm-label 'Delete' --cancel-label 'Cancel'; test $$? -eq 124

install: $(BUILD_DIR)/$(APP)
	$(INSTALL) -Dm0755 $(BUILD_DIR)/$(APP) $(DESTDIR)$(BINDIR)/$(APP)
	$(LN) -sf $(APP) $(DESTDIR)$(BINDIR)/$(COMPAT_APP)

clean:
	rm -rf $(BUILD_DIR)
