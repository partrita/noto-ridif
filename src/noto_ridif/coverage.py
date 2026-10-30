"""Guaranteed character coverage for noto-ridif."""

from __future__ import annotations

import unicodedata

from fontTools.ttLib import TTFont

# Ranges that the released font must cover.  Codepoints that Unicode marks as
# unassigned, control, format, surrogate, or private-use are skipped.
REQUIRED_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0020, 0x021F, "Latin letters, digits, punctuation, Latin Extended"),
    (0x0300, 0x036F, "combining diacritical marks"),
    (0x0400, 0x04FF, "Cyrillic"),
    (0x1EA0, 0x1EF9, "Vietnamese Latin Extended Additional"),
    (0x2000, 0x2060, "general punctuation"),
    (0x2070, 0x20BF, "super/subscripts and currency symbols"),
    (0x2190, 0x21EA, "arrows"),
    (0x2200, 0x22EF, "mathematical operators"),
    (0x3000, 0x301F, "CJK symbols and punctuation"),
    (0x3131, 0x318E, "Hangul compatibility jamo"),
    (0xAC00, 0xD7A3, "Hangul syllables"),
)

# CJK Unified Ideographs are counted instead of enumerated: the font ships a
# working Korean hanja set, not the whole 20,992-codepoint block.
CJK_IDEOGRAPHS = (0x4E00, 0x9FFF)
MIN_CJK_IDEOGRAPHS = 4620

_SKIP_CATEGORIES = ("Cn", "Cc", "Cf", "Cs", "Co")


def is_required(cp: int) -> bool:
    """Return True when *cp* is a printable character that needs a glyph."""
    return unicodedata.category(chr(cp)) not in _SKIP_CATEGORIES


def required_codepoints() -> set[int]:
    """Return every codepoint that must be present (CJK counted separately)."""
    return {
        cp
        for start, end, _label in REQUIRED_RANGES
        for cp in range(start, end + 1)
        if is_required(cp)
    }


def find_missing(font: TTFont) -> list[tuple[int, str]]:
    """Return ``(codepoint, range label)`` pairs missing from *font*."""
    cmap = font.getBestCmap() or {}
    missing: list[tuple[int, str]] = []

    for start, end, label in REQUIRED_RANGES:
        for cp in range(start, end + 1):
            if is_required(cp) and cp not in cmap:
                missing.append((cp, label))

    start, end = CJK_IDEOGRAPHS
    present = sum(1 for cp in range(start, end + 1) if cp in cmap)
    if present < MIN_CJK_IDEOGRAPHS:
        label = (
            f"CJK Unified Ideographs: only {present:,} present "
            f"(need at least {MIN_CJK_IDEOGRAPHS:,})"
        )
        missing.append((start, label))

    return missing


def format_coverage(missing: list[tuple[int, str]]) -> str:
    """Summarize missing coverage for CLI output."""
    if not missing:
        return "coverage: all required ranges are present"

    lines = [f"coverage: {len(missing)} required characters are missing"]
    for cp, label in missing[:20]:
        lines.append(f"  - U+{cp:04X} ({label})")
    if len(missing) > 20:
        lines.append(f"  ... and {len(missing) - 20} more")
    return "\n".join(lines)
