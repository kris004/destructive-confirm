APP := power-confirm
BUILD_DIR := build
SRC := src/power-confirm.c
PKGS := gtk4 libadwaita-1

PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
CC ?= cc
PKG_CONFIG ?= pkg-config
INSTALL ?= install
TIMEOUT ?= timeout

WARN_CFLAGS := -std=c17 -Wall -Wextra -Wpedantic -Wformat=2 -Wshadow \
	-Wstrict-prototypes -Wmissing-prototypes -Werror=implicit-function-declaration
PKG_CFLAGS := $(shell $(PKG_CONFIG) --cflags $(PKGS))
PKG_LIBS := $(shell $(PKG_CONFIG) --libs $(PKGS))
CFLAGS ?= -O2 -g

.PHONY: all check smoke-gui install clean

all: $(BUILD_DIR)/$(APP)

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/$(APP): $(SRC) | $(BUILD_DIR)
	$(CC) $(WARN_CFLAGS) $(CFLAGS) $(CPPFLAGS) $(PKG_CFLAGS) $< -o $@ $(LDFLAGS) $(PKG_LIBS) $(LDLIBS)

check: $(BUILD_DIR)/$(APP)
	$(BUILD_DIR)/$(APP) --help >/dev/null
	$(BUILD_DIR)/$(APP) --text '' >/dev/null 2>&1; test $$? -eq 2

smoke-gui: $(BUILD_DIR)/$(APP)
	$(TIMEOUT) 2 $(BUILD_DIR)/$(APP) --title 'Power menu test' --text 'Restart now?' --confirm-label 'Restart now' --cancel-label 'Cancel'; test $$? -eq 124

install: $(BUILD_DIR)/$(APP)
	$(INSTALL) -Dm0755 $(BUILD_DIR)/$(APP) $(DESTDIR)$(BINDIR)/$(APP)

clean:
	rm -rf $(BUILD_DIR)
