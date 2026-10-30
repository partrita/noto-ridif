"""Integrity checks for generated noto-ridif fonts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont, TTLibError

from noto_ridif.coverage import find_missing, format_coverage

# A hinted build should carry instructions for at least this many glyphs.
MIN_HINTED_GLYPHS = 100


def _hinted_glyph_count(font: TTFont, glyph_names: list[str]) -> int:
    glyf = font["glyf"]
    count = 0
    for name in glyph_names:
        program = getattr(glyf[name], "program", None)
        if program is not None and program.getBytecode():
            count += 1
    return count


def verify_font(font_path: Path, *, require_hinting: bool = False) -> list[str]:
    """Return a list of human-readable integrity problems (empty if valid)."""
    font_path = Path(font_path)
    issues: list[str] = []

    try:
        font = TTFont(str(font_path))
    except TTLibError as err:
        return [f"cannot open font: {err}"]

    try:
        glyph_names = font.getGlyphOrder()
        num_glyphs = font["maxp"].numGlyphs

        if num_glyphs != len(glyph_names):
            issues.append(
                f"maxp.numGlyphs={num_glyphs} but glyph order has {len(glyph_names)} entries"
            )

        for tag in ("hmtx", "vmtx"):
            try:
                metrics = font[tag].metrics
            except TTLibError as err:
                issues.append(f"{tag} table cannot be read: {err}")
                continue
            if len(metrics) != num_glyphs:
                issues.append(
                    f"{tag}.metrics has {len(metrics)} entries for {num_glyphs} glyphs"
                )

        try:
            vhea: Any = font["vhea"]
            number_of_v_metrics = int(vhea.numberOfVMetrics)
            if not 0 < number_of_v_metrics <= num_glyphs:
                issues.append(
                    f"vhea.numberOfVMetrics={number_of_v_metrics} is out of range"
                )
        except TTLibError as err:
            issues.append(f"vhea table cannot be read: {err}")

        cmap = font.getBestCmap() or {}
        missing = sorted(cp for cp, name in cmap.items() if name not in set(glyph_names))
        if missing:
            preview = ", ".join(f"U+{cp:04X}" for cp in missing[:5])
            issues.append(f"{len(missing)} cmap entries point to missing glyphs ({preview})")

        names = {
            record.nameID: record.toUnicode()
            for record in font["name"].names
        }
        for name_id, label in ((1, "family"), (2, "subfamily"), (4, "full name"), (6, "PostScript name")):
            if not names.get(name_id):
                issues.append(f"name ID {name_id} ({label}) is missing")

        coverage_missing = find_missing(font)
        if coverage_missing:
            issues.append(format_coverage(coverage_missing))

        if require_hinting:
            hinted = _hinted_glyph_count(font, glyph_names)
            if "fpgm" not in font or "prep" not in font:
                issues.append("hinting tables (fpgm/prep) are missing")
            if hinted < MIN_HINTED_GLYPHS:
                issues.append(
                    f"only {hinted} glyphs carry hinting (expected at least {MIN_HINTED_GLYPHS})"
                )
    finally:
        font.close()

    return issues


def format_report(font_path: Path, issues: list[str], *, hinted: int | None = None) -> str:
    """Build a short human-readable verification summary."""
    lines = [f"Verification: {font_path}"]
    if hinted is not None:
        lines.append(f"  hinted glyphs: {hinted:,}")
    if issues:
        lines.append(f"  problems: {len(issues)}")
        lines.extend(f"    - {issue}" for issue in issues)
    else:
        lines.append("  no problems found")
    return "\n".join(lines)
