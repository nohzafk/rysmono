#!/usr/bin/env python3
"""RysMono build checks.

The lock, script and workflow checks are offline. BuiltFontTests check real
output and run only when RYSMONO_DIST names a directory scripts/build.sh
filled; they need fontTools (the build's venv has it).
"""
import hashlib
import os
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = (ROOT / "font.lock").read_text()
SH = (ROOT / "scripts/build.sh").read_text()
CI = (ROOT / ".github/workflows/build.yml").read_text()
FACES = ["Regular", "Italic", "Medium", "MediumItalic", "SemiBold", "SemiBoldItalic",
         "Bold", "BoldItalic", "ExtraBold", "ExtraBoldItalic"]
FAMILY = "RysMono Nerd Font Mono"
HANGUL = ((0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7FF), (0xFFA0, 0xFFDF))


def lock_value(name):
    return re.search(rf'^readonly {name}="(.*)"$', LOCK, re.M)[1]


class LockTests(unittest.TestCase):
    def test_pins_are_full_sha256(self):
        for name in ("RYSANA_SHA256", "PATCHER_SHA256"):
            self.assertRegex(lock_value(name), r"^[0-9a-f]{64}$", name)

    def test_inputs_are_the_pinned_releases(self):
        self.assertEqual(lock_value("RYSANA_VERSION"), "1.0.0")
        self.assertEqual(lock_value("PATCHER_VERSION"), "3.5.1")
        self.assertIn("rysana-os/type/releases/download/v${RYSANA_VERSION}/rysana-type.zip", LOCK)
        self.assertIn("ryanoasis/nerd-fonts/releases/download/v${PATCHER_VERSION}/FontPatcher.zip", LOCK)

    def test_release_tag_is_version_dot_build(self):
        self.assertRegex(lock_value("RYSMONO_BUILD_NUMBER"), r"^[1-9]\d*$")
        self.assertEqual(lock_value("RYSMONO_RELEASE_TAG"), "v${RYSANA_VERSION}.${RYSMONO_BUILD_NUMBER}")
        self.assertEqual(lock_value("RYSMONO_ARTIFACT"), "RysMono-${RYSMONO_RELEASE_TAG}.zip")


class ScriptTests(unittest.TestCase):
    def test_ten_faces(self):
        m = re.search(r"RYSMONO_FACES=\(\n(.*?)\n\)", SH, re.S)
        self.assertEqual(m[1].split(), FACES)

    def test_patch_flags(self):
        m = re.search(r"RYSMONO_PATCH_FLAGS=\(\n(.*?)\n\)", SH, re.S)
        self.assertEqual(m[1].split(), ["--complete", "--single-width-glyphs", "--careful",
                                        "--cell", "0:600:-300:1010", "--quiet", "--no-progressbars"])
        self.assertNotIn("--mono", m[1])

    def test_rename_keeps_license_records_and_sets_fixed_pitch(self):
        py = (ROOT / "scripts/rename.py").read_text()
        self.assertIn("KEEP = (0, 13, 14)", py)
        self.assertIn("isFixedPitch = 1", py)
        self.assertIn('"Rysana"', py)

    def test_hangul_is_removed_before_patching(self):
        py = (ROOT / "scripts/subset.py").read_text()
        for lo, hi in HANGUL:
            self.assertIn(f"(0x{lo:04X}, 0x{hi:04X})", py)
        build = SH.split("rysmono_build() {", 1)[1]
        self.assertLess(build.index("scripts/subset.py"), build.index("font-patcher"))
        self.assertLess(build.index("font-patcher"), build.index("scripts/rename.py"))


class WorkflowTests(unittest.TestCase):
    def test_every_push_builds_and_checks_the_fonts(self):
        build = CI.split("\n  build:\n", 1)[1]
        self.assertNotIn("if: github.event_name", build.split("steps:", 1)[0])
        self.assertIn("brew install fontforge", build)
        self.assertIn("scripts/build.sh", build)
        self.assertLess(build.index("scripts/build.sh"), build.index("RYSMONO_DIST="))

    def test_only_a_dispatch_releases(self):
        release = CI.split("\n  release:\n", 1)[1]
        self.assertIn("if: github.event_name == 'workflow_dispatch'", release)
        self.assertIn("needs: [tests, build]", release)
        self.assertIn("git ls-remote --exit-code --tags origin", release)

    def test_release_notes_name_the_inputs(self):
        notes = CI.split("name: Write release notes", 1)[1]
        for var in ("$RYSANA_VERSION", "$RYSANA_SHA256", "$PATCHER_VERSION"):
            self.assertIn(var, notes)


def dist():
    d = os.environ.get("RYSMONO_DIST")
    return Path(d) if d else None


@unittest.skipUnless(dist(), "set RYSMONO_DIST to a directory scripts/build.sh filled")
class BuiltFontTests(unittest.TestCase):
    def fonts(self):
        from fontTools.ttLib import TTFont
        for face in FACES:
            yield face, TTFont(dist() / f"fonts/RysMono-{face}.ttf")

    def test_family_fixed_pitch_and_names(self):
        for face, font in self.fonts():
            with self.subTest(face=face):
                self.assertEqual(font["name"].getBestFamilyName(), FAMILY)
                self.assertEqual(font["post"].isFixedPitch, 1)
                for rec in font["name"].names:
                    if rec.nameID not in (0, 13, 14):
                        self.assertNotIn("Rysana", rec.toUnicode(), rec.nameID)

    def test_no_hangul_and_nerd_glyphs_present(self):
        for face, font in self.fonts():
            with self.subTest(face=face):
                cmap = font.getBestCmap()
                self.assertFalse([cp for cp in cmap if any(lo <= cp <= hi for lo, hi in HANGUL)])
                self.assertIn(0xE0B0, cmap)  # powerline
                self.assertIn(0xF015, cmap)  # Font Awesome "home"

    def test_zip_and_digest(self):
        tag = next(p.name for p in dist().glob("RysMono-v*.zip"))
        zpath = dist() / tag
        with zipfile.ZipFile(zpath) as z:
            names = sorted(z.namelist())
        expected = sorted(["RysMono/"] + [f"RysMono/RysMono-{f}.ttf" for f in FACES] + ["RysMono/OFL.txt"])
        self.assertEqual([n for n in names if n != "RysMono/"], [n for n in expected if n != "RysMono/"])
        digest = (dist() / f"{tag}.sha256").read_text().split()
        self.assertEqual(digest, [hashlib.sha256(zpath.read_bytes()).hexdigest(), tag])


if __name__ == "__main__":
    unittest.main(verbosity=2)
