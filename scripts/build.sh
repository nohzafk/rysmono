#!/usr/bin/env bash
# Build RysMono: Rysana Mono without its Hangul, patched with Nerd Fonts glyphs,
# renamed RysMono. The local build and CI run this same script; pins are in
# font.lock.
#
#   scripts/build.sh DIR
#
# leaves in DIR:
#   fonts/RysMono-<Face>.ttf   the ten faces
#   OFL.txt                    Rysana's license, which the fonts keep
#   RysMono-<tag>.zip          RysMono/ holding the faces and OFL.txt
#   RysMono-<tag>.zip.sha256
#
# Needs `fontforge` on PATH (override with RYSMONO_FONTFORGE), plus curl,
# unzip, zip and python3 with venv. DIR's previous output is replaced; the
# downloads in it are reused once their SHA-256 checks.
set -euo pipefail
_RYSMONO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$_RYSMONO_ROOT/font.lock"

# The ten faces: body, bold and the weights between, each with its italic.
readonly RYSMONO_FACES=(
  Regular Italic Medium MediumItalic SemiBold SemiBoldItalic
  Bold BoldItalic ExtraBold ExtraBoldItalic
)
# --single-width-glyphs, not --mono: --mono would also squash the font's own
#   two-cell glyphs (fractions, arrows) into one cell.
# --cell 0:600:-300:1010 fixes the cell: left to itself the patcher guesses it
#   from the font's advances (with Hangul, the most common was 1200) and icons
#   can come out two cells wide. 600 is the Latin advance; -300 and 1010 are the font's
#   descent and ascent.
# --careful keeps Rysana's own powerline glyphs.
readonly RYSMONO_PATCH_FLAGS=(
  --complete --single-width-glyphs --careful --cell 0:600:-300:1010
  --quiet --no-progressbars
)
readonly RYSMONO_FAMILY="RysMono Nerd Font Mono"

rysmono_fetch() { # URL SHA256 OUT
  [[ -f "$3" ]] || curl --fail --retry 5 --retry-delay 5 --location --silent --show-error -o "$3" "$1" || return 1
  local got
  got="$(shasum -a 256 "$3" | cut -d' ' -f1)"
  if [[ "$got" != "$2" ]]; then
    echo "RysMono: $1 has SHA-256 $got, expected $2" >&2
    return 1
  fi
}

rysmono_build() {
  local dir="$1" fontforge="${RYSMONO_FONTFORGE:-fontforge}" face out
  command -v "$fontforge" >/dev/null || { echo "RysMono: fontforge not found (set RYSMONO_FONTFORGE)" >&2; return 1; }
  mkdir -p "$dir"
  dir="$(cd "$dir" && pwd)"
  rm -rf "$dir/fonts" "$dir/src" "$dir/patcher" "$dir/RysMono" "$dir/$RYSMONO_ARTIFACT" "$dir/$RYSMONO_ARTIFACT.sha256"
  mkdir -p "$dir/fonts" "$dir/src" "$dir/patcher"
  rysmono_fetch "$RYSANA_URL" "$RYSANA_SHA256" "$dir/rysana-type.zip"
  rysmono_fetch "$PATCHER_URL" "$PATCHER_SHA256" "$dir/FontPatcher.zip"
  unzip -q -o "$dir/rysana-type.zip" -d "$dir/src"
  unzip -q -o "$dir/FontPatcher.zip" -d "$dir/patcher"
  [[ -x "$dir/venv/bin/python" ]] || python3 -m venv "$dir/venv"
  "$dir/venv/bin/pip" install --quiet "fonttools==$FONTTOOLS_VERSION"
  # Hangul goes before patching, so the patcher works on the smaller font.
  local src=()
  for face in "${RYSMONO_FACES[@]}"; do
    src+=("$dir/src/rysana-type/ttf/RysanaMono-$face.ttf")
  done
  "$dir/venv/bin/python" "$_RYSMONO_ROOT/scripts/subset.py" "${src[@]}"
  for face in "${RYSMONO_FACES[@]}"; do
    "$fontforge" -quiet -script "$dir/patcher/font-patcher" "${RYSMONO_PATCH_FLAGS[@]}" \
      --outputdir "$dir/fonts" "$dir/src/rysana-type/ttf/RysanaMono-$face.ttf" >&2
  done
  "$dir/venv/bin/python" "$_RYSMONO_ROOT/scripts/rename.py" "$dir"/fonts/*.ttf
  for face in "${RYSMONO_FACES[@]}"; do
    out="$dir/fonts/RysMono-$face.ttf"
    # The patcher names its output <Family>NerdFontMono-<Style>.ttf.
    mv "$dir/fonts/RysanaMonoNerdFontMono-$face.ttf" "$out"
  done
  cp "$dir/src/rysana-type/LICENSE.txt" "$dir/OFL.txt"
  mkdir "$dir/RysMono"
  cp "$dir"/fonts/RysMono-*.ttf "$dir/OFL.txt" "$dir/RysMono/"
  (cd "$dir" && zip -q -X -r "$RYSMONO_ARTIFACT" RysMono && shasum -a 256 "$RYSMONO_ARTIFACT" > "$RYSMONO_ARTIFACT.sha256")
  rm -rf "$dir/RysMono"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  [[ $# -eq 1 ]] || { echo "usage: scripts/build.sh DIR" >&2; exit 2; }
  rysmono_build "$1"
fi
