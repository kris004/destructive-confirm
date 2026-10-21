# SPDX-License-Identifier: GPL-3.0-or-later
APP := destructive-confirm
COMPAT_APP := power-confirm
BUILD_DIR := build
CONFIG_H ?= config.h
PYTHON ?= python3
APP_VERSION = $(shell cat VERSION)
RELEASE_REF ?= HEAD
OUTPUT_DIR ?=
PRESET_MK := $(BUILD_DIR)/preset.mk
# Escape spaces at Make syntax boundaries, not inside shell-quoted paths.
empty :=
space := $(empty) $(empty)
make_path = $(subst $(space),\$(space),$(1))
# abspath splits on spaces. Inspect only the first character (with a sentinel
# so leading spaces are preserved) and leave the full header path intact.
CONFIG_PATH = $(if $(filter x/%,$(firstword x$(CONFIG_H))),$(CONFIG_H),$(CURDIR)/$(CONFIG_H))
CONFIG_CPPFLAGS = -DDC_CONFIG_HEADER='"$(CONFIG_PATH)"' -DDC_VERSION='"$(APP_VERSION)"'
.DEFAULT_GOAL := all

# An included makefile lets resource dependencies follow the C header selection.
# Recheck each invocation, but replace it only on a real selection change.
# This also handles switching to an older CONFIG_H in the same BUILD_DIR.
ifneq ($(filter-out clean uninstall dist check-release,$(if $(MAKECMDGOALS),$(MAKECMDGOALS),all)),)
include $(call make_path,$(PRESET_MK))
endif

PRESET_DIR := data/presets/$(ANIMATION_PRESET)
SRC := src/destructive-confirm.c
HEADERS := src/animation-config.h $(call make_path,$(CONFIG_H)) $(call make_path,$(PRESET_MK)) VERSION
ifneq ($(filter tall-ring real-fire,$(ANIMATION_PRESET)),)
SRC += src/fire-overlay.c
HEADERS += src/fire-overlay.h $(PRESET_DIR)/fire-art.h
endif
RESOURCE_XML := $(PRESET_DIR)/destructive-confirm.gresource.xml
RESOURCE_FILES := $(wildcard $(PRESET_DIR)/*.css $(PRESET_DIR)/*.svg $(PRESET_DIR)/fire/*.png)
RESOURCE_SRC := $(BUILD_DIR)/resources.c
RESOURCE_OBJ := $(BUILD_DIR)/resources.o
PKGS := 'gtk4 >= 4.14' 'libadwaita-1 >= 1.5'

PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
DOCDIR ?= $(PREFIX)/share/doc/$(APP)
CC ?= cc
PKG_CONFIG ?= pkg-config
INSTALL ?= install
LN ?= ln
TIMEOUT ?= timeout
GLIB_COMPILE_RESOURCES ?= glib-compile-resources

WARN_CFLAGS := -std=c17 -Wall -Wextra -Wpedantic -Wformat=2 -Wshadow \
	-Wstrict-prototypes -Wmissing-prototypes -Werror=implicit-function-declaration
PKG_CFLAGS = $(shell $(PKG_CONFIG) --cflags $(PKGS))
PKG_LIBS = $(shell $(PKG_CONFIG) --libs $(PKGS))
CFLAGS ?= -O2 -g
LDLIBS += -lm

.PHONY: all check-deps check check-presets check-release dist smoke-gui preview-tool install uninstall clean FORCE

all: $(call make_path,$(BUILD_DIR)/$(APP))

$(call make_path,$(BUILD_DIR)):
	mkdir -p "$@"

$(call make_path,$(CONFIG_H)):
	cp config.def.h "$@"

FORCE:

check-deps:
	$(PKG_CONFIG) --print-errors --exists $(PKGS)

$(call make_path,$(PRESET_MK)): FORCE $(call make_path,$(CONFIG_H)) src/animation-config.h tools/preset.mk.in | $(call make_path,$(BUILD_DIR))
	@$(CC) $(CPPFLAGS) $(CONFIG_CPPFLAGS) -E -P -x c tools/preset.mk.in -o "$@.cpp"
	@sed -n 's/^DC_SELECTED_PRESET = "\(.*\)"$$/override ANIMATION_PRESET := \1/p' "$@.cpp" > "$@.tmp"
	@test -s "$@.tmp"
	@cmp -s "$@.tmp" "$@" || mv "$@.tmp" "$@"
	@rm -f "$@.tmp" "$@.cpp"

$(call make_path,$(RESOURCE_SRC)): $(RESOURCE_XML) $(RESOURCE_FILES) $(call make_path,$(PRESET_MK)) | $(call make_path,$(BUILD_DIR))
	$(GLIB_COMPILE_RESOURCES) --sourcedir=$(PRESET_DIR) --generate-source \
		--c-name=destructive_confirm --internal --target="$@" "$<"

# Generated GLib byte strings exceed the ISO C minimum string length.
$(call make_path,$(RESOURCE_OBJ)): $(call make_path,$(RESOURCE_SRC)) | check-deps
	$(CC) $(CFLAGS) $(CPPFLAGS) $(PKG_CFLAGS) -c "$<" -o "$@"

$(call make_path,$(BUILD_DIR)/$(APP)): $(SRC) $(HEADERS) $(call make_path,$(RESOURCE_OBJ)) | $(call make_path,$(BUILD_DIR))
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(CONFIG_CPPFLAGS) $(PKG_CFLAGS) $(SRC) "$(RESOURCE_OBJ)" -o "$@" $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

$(call make_path,$(BUILD_DIR)/test-dialog): tests/test-dialog.c $(SRC) $(HEADERS) $(call make_path,$(RESOURCE_OBJ))
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(CONFIG_CPPFLAGS) $(PKG_CFLAGS) tests/test-dialog.c $(filter-out src/destructive-confirm.c,$(SRC)) "$(RESOURCE_OBJ)" -o "$@" $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

$(call make_path,$(BUILD_DIR)/capture-preview): tools/capture-preview.c $(SRC) $(HEADERS) $(call make_path,$(RESOURCE_OBJ))
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(CONFIG_CPPFLAGS) $(PKG_CFLAGS) tools/capture-preview.c $(filter-out src/destructive-confirm.c,$(SRC)) "$(RESOURCE_OBJ)" -o "$@" $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

preview-tool: $(call make_path,$(BUILD_DIR)/capture-preview)

check: $(call make_path,$(BUILD_DIR)/$(APP))
	"$(BUILD_DIR)/$(APP)" --help >/dev/null
	"$(BUILD_DIR)/$(APP)" --version | grep -Fx 'destructive-confirm $(APP_VERSION)'
	@for arg in --title --text --confirm-label --cancel-label; do \
		LC_ALL=C.UTF-8 "$(BUILD_DIR)/$(APP)" "$$arg" 'café_删除' --version \
			| grep -Fqx 'destructive-confirm $(APP_VERSION)' || exit 1; \
	done
	@for arg in --does-not-exist --title --text --confirm-label --cancel-label unexpected; do \
		$(TIMEOUT) 5 "$(BUILD_DIR)/$(APP)" "$$arg" >/dev/null 2>&1; \
		status=$$?; test $$status -eq 2 || { \
			echo "Expected usage error for $$arg, got $$status" >&2; exit 1; }; \
	done

check-presets:
	$(PYTHON) -B tests/test-presets.py

check-release:
	$(PYTHON) -B -m unittest discover -s tests -p 'test_release.py' -v

dist:
	@test -n "$(OUTPUT_DIR)" || { echo "Set OUTPUT_DIR to an external artifact directory" >&2; exit 2; }
	$(PYTHON) -B tools/package-release.py --ref "$(RELEASE_REF)" --output-dir "$(OUTPUT_DIR)"

smoke-gui: $(call make_path,$(BUILD_DIR)/$(APP)) $(call make_path,$(BUILD_DIR)/test-dialog)
	G_DEBUG=fatal-warnings "$(BUILD_DIR)/test-dialog"
	G_DEBUG=fatal-warnings $(TIMEOUT) 6 "$(BUILD_DIR)/$(APP)" --title 'Destructive action test' --confirm-label 'Delete' --cancel-label 'Cancel'; test $$? -eq 124
	G_DEBUG=fatal-warnings $(TIMEOUT) 6 "$(BUILD_DIR)/$(APP)" --title 'Destructive action test' --text 'Delete this item?' --confirm-label 'Delete' --cancel-label 'Cancel'; test $$? -eq 124

install: $(call make_path,$(BUILD_DIR)/$(APP))
	$(INSTALL) -Dm0755 "$(BUILD_DIR)/$(APP)" "$(DESTDIR)$(BINDIR)/$(APP)"
	$(LN) -sf $(APP) "$(DESTDIR)$(BINDIR)/$(COMPAT_APP)"
	$(INSTALL) -Dm0644 README.md "$(DESTDIR)$(DOCDIR)/README.md"
	$(INSTALL) -Dm0644 LICENSE "$(DESTDIR)$(DOCDIR)/LICENSE"
	$(INSTALL) -Dm0644 COPYRIGHT "$(DESTDIR)$(DOCDIR)/COPYRIGHT"

uninstall:
	rm -f -- "$(DESTDIR)$(BINDIR)/$(APP)" "$(DESTDIR)$(BINDIR)/$(COMPAT_APP)"
	rm -f -- "$(DESTDIR)$(DOCDIR)/README.md" "$(DESTDIR)$(DOCDIR)/LICENSE" "$(DESTDIR)$(DOCDIR)/COPYRIGHT"
	-rmdir -- "$(DESTDIR)$(DOCDIR)"

clean:
	rm -rf -- "$(BUILD_DIR)"
