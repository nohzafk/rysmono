# RysMono

RysMono Nerd Font Mono: [Rysana Mono](https://github.com/rysana-os/type) less
its Hangul, patched with every [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts)
glyph set at a fixed one-cell width. It is the monospace font of
[bendmacs](https://github.com/nohzafk/bendmacs). CI builds it and publishes
the ten faces (Regular, Italic, Medium, MediumItalic, SemiBold, SemiBoldItalic,
Bold, BoldItalic, ExtraBold, ExtraBoldItalic) as a release.

## Install

Download `RysMono-<tag>.zip` and its `.sha256` from the
[latest release](https://github.com/nohzafk/rysmono/releases/latest), then:

```sh
shasum -a 256 -c RysMono-<tag>.zip.sha256
unzip RysMono-<tag>.zip
cp RysMono/RysMono-*.ttf ~/Library/Fonts/
```

The family is `RysMono Nerd Font Mono`.

## What differs from Rysana Mono

- **Name.** "Rysana" is a Reserved Font Name in the OFL, so a modified font
  may not carry it: every name record except the copyright and license ones
  says "Rys" instead (`scripts/rename.py`), and the files are
  `RysMono-<Face>.ttf`. `post.isFixedPitch` is set back to 1, because the
  patcher clears it.
- **No Hangul.** The codepoints Emacs 31.1's `char-script-table` gives the
  `hangul` script are removed before patching (`scripts/subset.py`):
  11,223 of the font's 29,383 glyphs and a quarter of each file. bendmacs
  draws that script with its CJK font. Every other codepoint, OpenType
  feature and the hinting are kept.
- **Nerd Fonts glyphs**, with `--complete --single-width-glyphs --careful
  --cell 0:600:-300:1010`. Not `--mono`: it would squash the font's own
  two-cell glyphs (fractions, arrows) into one cell. The cell is forced
  because the patcher would otherwise guess it from the font's advances (with
  Hangul in the font the most common was 1200) and icons could come out two
  cells wide; 600 is the Latin advance. `--careful` keeps Rysana's own
  powerline glyphs.
- bendmacs lays out diagram text assuming 600/1000 em for a narrow glyph and
  1200/1000 em for a wide one. A change to the cell width breaks that layout,
  so coordinate it with bendmacs.

## Build

```sh
brew install fontforge
scripts/build.sh build
```

`build/fonts/` gets the faces, and `build/` the release zip and its
`.sha256`. Rysana Type 1.0.0 (`rysana-type.zip`) and Nerd Fonts
`font-patcher` 3.5.1 are pinned by version and SHA-256 in `font.lock`. The
patcher runs under `fontforge`: put it on `PATH` or point
`RYSMONO_FONTFORGE` at it.

## Tests

```sh
python3 tests/test_build.py                          # offline
RYSMONO_DIST=build build/venv/bin/python tests/test_build.py  # also checks the built fonts
```

## Release

Every push builds the fonts and checks them. A release is published only by
dispatching the workflow by hand: it publishes the fonts that run built, under
the tag `v<Rysana version>.<RYSMONO_BUILD_NUMBER>`, and refuses a tag that
exists. A change to `font.lock`, the flags or the scripts changes the fonts,
so bump `RYSMONO_BUILD_NUMBER` with it.

## License

The fonts are under the SIL Open Font License 1.1, as Rysana Mono is;
`OFL.txt` ships in the zip.
