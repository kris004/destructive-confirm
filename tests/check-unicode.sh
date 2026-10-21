#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Exercise CLI conversion using a locale this system actually supports.

is_utf8_locale() {
    charmap=$(LC_ALL="$1" locale charmap 2>/dev/null) || return 1
    case $charmap in
        [Uu][Tt][Ff]-8|[Uu][Tt][Ff]8) return 0 ;;
        *) return 1 ;;
    esac
}

# Prefer the caller's character locale, but use it for every category so an
# unrelated invalid LC_* value cannot make the application's setlocale fail.
utf8_locale=${LC_ALL:-${LC_CTYPE:-${LANG:-C}}}
if ! is_utf8_locale "$utf8_locale"; then
    utf8_locale=
    locales=$(locale -a) || exit 1
    while IFS= read -r candidate; do
        [ -n "$candidate" ] || continue
        if is_utf8_locale "$candidate"; then
            utf8_locale=$candidate
            break
        fi
    done <<EOF
$locales
EOF
fi

if [ -z "$utf8_locale" ]; then
    echo "SKIP Unicode option checks: no available UTF-8 locale"
    exit 0
fi
LC_ALL=$utf8_locale
export LC_ALL
printf 'Unicode option checks: LC_ALL=%s\n' "$LC_ALL"
for arg in --title --text --confirm-label --cancel-label; do
    output=$("$1" "$arg" 'café_删除' --version) || exit 1
    if [ "$output" != "destructive-confirm $2" ]; then
        printf 'Unexpected version output for %s: %s\n' "$arg" "$output" >&2
        exit 1
    fi
done
