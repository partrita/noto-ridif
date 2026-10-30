"""Post-merge optimizations for noto-ridif.

Currently this module adds TrueType hinting instructions to the Latin,
Greek, Cyrillic, punctuation, currency, and number glyphs without touching
the CJK outlines.  Hinting is produced by ``ttfautohint`` on a temporary
"donor" subset, then copied back into the merged font by codepoint.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fontTools import subset
from fontTools.ttLib import TTFont

# Character ranges that receive TrueType hinting.
# Basic Latin, Latin supplements and extended ranges, Greek, Cyrillic,
# general punctuation, currency symbols, and number forms.
HINT_RANGES: tuple[tuple[int, int], ...] = (
    (0x0020, 0x052F),
    (0x2000, 0x206F),
    (0x20A0, 0x20CF),
    (0x2150, 0x218F),
)

# Tables produced by ttfautohint that must be copied into the merged font.
_HINT_TABLES = ("fpgm", "prep", "cvt ", "gasp")

# maxp fields that describe the instruction program.
_MAXP_INSTRUCTION_FIELDS = (
    "maxStackElements",
    "maxFunctionDefs",
    "maxInstructionDefs",
    "maxStorage",
    "maxTwilightPoints",
    "maxZones",
    "maxSizeOfInstructions",
)


def hint_codepoints() -> list[int]:
    """Return every codepoint that should receive hinting."""
    return [cp for start, end in HINT_RANGES for cp in range(start, end + 1)]


def _build_hint_donor(source: Path, target: Path) -> None:
    """Subset *source* to the hint ranges so ttfautohint stays fast."""
    options = subset.Options()
    options.glyph_names = True
    options.notdef_outline = True
    options.drop_tables = ["GSUB", "GPOS", "GDEF", "BASE", "STAT", "DSIG"]

    font = subset.load_font(str(source), options)
    try:
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=hint_codepoints())
        subsetter.subset(font)
        subset.save_font(font, str(target), options)
    finally:
        font.close()


def _run_ttfautohint(source: Path, target: Path) -> None:
    # Imported lazily so the base build does not require the dev dependency.
    from ttfautohint import ttfautohint

    ttfautohint(
        in_file=str(source),
        out_file=str(target),
        no_info=True,
        increase_x_height=0,
        hinting_range_min=8,
        hinting_range_max=50,
    )


def _copy_hinting(main: TTFont, donor: TTFont) -> int:
    """Copy hinted glyph programs and global hint tables into *main*."""
    donor_cmap = donor.getBestCmap() or {}
    main_cmap = main.getBestCmap() or {}
    donor_glyf = donor["glyf"]
    main_glyf = main["glyf"]

    copied = 0
    for cp, donor_name in donor_cmap.items():
        main_name = main_cmap.get(cp)
        if main_name is None:
            continue

        program = getattr(donor_glyf[donor_name], "program", None)
        if program is None or not program.getBytecode():
            continue

        main_glyf[main_name].program = program
        copied += 1

    for tag in _HINT_TABLES:
        if tag in donor:
            main[tag] = donor[tag]

    main_head: Any = main["head"]
    donor_head: Any = donor["head"]
    main_head.flags = donor_head.flags
    for field in _MAXP_INSTRUCTION_FIELDS:
        setattr(main["maxp"], field, getattr(donor["maxp"], field))

    return copied


def hint_font(font_path: Path) -> int:
    """Add TrueType hinting to *font_path* in place.

    Returns the number of glyphs that received hinting instructions.
    """
    font_path = Path(font_path)

    with tempfile.TemporaryDirectory(prefix="noto-ridif-hint-") as tmp:
        tmp_dir = Path(tmp)
        donor_path = tmp_dir / "donor.ttf"
        hinted_path = tmp_dir / "donor-hinted.ttf"

        _build_hint_donor(font_path, donor_path)
        _run_ttfautohint(donor_path, hinted_path)

        hinted_font = TTFont(str(hinted_path))
        try:
            hinted_font["glyf"]  # ensure the table is decompiled before copying
            main_font = TTFont(str(font_path))
            try:
                copied = _copy_hinting(main_font, hinted_font)
                main_font.save(str(font_path))
            finally:
                main_font.close()
        finally:
            hinted_font.close()

    return copied
