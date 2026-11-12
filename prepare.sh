#!/usr/bin/env bash
# Prepare private build inputs; this does not download or distribute game data.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work="$root/work"
mkdir -p "$work"
for d in upstream SDL sdl3-switch; do
    if [ -e "$work/$d" ]; then
        printf 'Refusing to replace existing %s\n' "$work/$d" >&2
        exit 1
    fi
done
command -v git >/dev/null
command -v magick >/dev/null || { printf 'ImageMagick 7 (magick) is required to render the icon.\n' >&2; exit 1; }
git clone --no-checkout https://github.com/huntergdavis/quarantine-recomp.git "$work/upstream"
git -C "$work/upstream" checkout --detach 4b785beba28ada9105ac42d7f58431cb9b851fee
python3 "$root/tools/apply_switch.py" "$work/upstream"
cp "$root/overlay/rt_fmv.c" "$work/upstream/runtime/rt_fmv.c"
cp "$root/Makefile.switch" "$work/upstream/Makefile.switch"
mkdir -p "$work/upstream/assets"
magick -background '#12151c' "$root/assets/icon.svg" -colorspace sRGB -sampling-factor 4:2:0 -quality 90 "$work/upstream/assets/icon.jpg"
git clone --no-checkout https://github.com/libsdl-org/SDL.git "$work/SDL"
git -C "$work/SDL" checkout --detach 683181b47cfabd293e3ea409f838915b8297a4fd
git clone --no-checkout https://github.com/neomody77/sdl3-switch.git "$work/sdl3-switch"
git -C "$work/sdl3-switch" checkout --detach 182e511214d7600e4bdab8606d7caf0ef744afd6
printf '%s  %s\n' 9f694599723d78b08c09d99f8203ddea52ee5178575a807263fe79f8ab1f28dc "$work/sdl3-switch/sdl3-switch.patch" | sha256sum -c -
git -C "$work/SDL" apply -p3 --check "$work/sdl3-switch/sdl3-switch.patch"
git -C "$work/SDL" apply -p3 "$work/sdl3-switch/sdl3-switch.patch"
git -C "$work/SDL" apply --unidiff-zero --check "$root/patches/sdl3-switch-audio-prime.patch"
git -C "$work/SDL" apply --unidiff-zero "$root/patches/sdl3-switch-audio-prime.patch"
printf '\nPrepared private source checkouts under %s. See README.md for build steps.\n' "$work"
