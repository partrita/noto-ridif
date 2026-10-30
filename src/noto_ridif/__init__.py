"""noto-ridif: Merge NotoSerifKR-Regular and RIDIBatang fonts."""

import argparse
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

# Noto fallbacks used to fill codepoints that neither the CJK base nor
# RIDIBatang provides (rare Latin/Cyrillic, combining marks, symbols, currency).
DEFAULT_FALLBACK_FONTS = (
    Path("fonts/NotoSerif-Regular.ttf"),
    Path("fonts/NotoSansMath-Regular.ttf"),
    Path("fonts/NotoSansSymbols2-Regular.ttf"),
)


def _default_font_version() -> str:
    try:
        return package_version("noto-ridif")
    except PackageNotFoundError:
        return "0.0.0"


def update_font_names(
    font: TTFont,
    family_name: str = "noto-ridif",
    subfamily_name: str = "Regular",
    font_version: str | None = None,
) -> None:
    """Update name records in the font's 'name' table."""
    full_name = f"{family_name} {subfamily_name}".strip()
    postscript_name = f"{family_name}-{subfamily_name}".replace(" ", "")
    font_version = font_version or _default_font_version()

    name_table = font["name"]

    # Typical name IDs to update:
    # 1: Font Family name
    # 2: Font Subfamily name
    # 3: Unique font identifier
    # 4: Full font name
    # 6: PostScript name
    # 16: Typographic Family name (if present)
    # 17: Typographic Subfamily name (if present)
    for record in list(name_table.names):
        nid = record.nameID
        if nid == 1:
            name_table.setName(family_name, 1, record.platformID, record.platEncID, record.langID)
        elif nid == 2:
            name_table.setName(subfamily_name, 2, record.platformID, record.platEncID, record.langID)
        elif nid == 3:
            unique_id = f"noto-ridif;{postscript_name}"
            name_table.setName(unique_id, 3, record.platformID, record.platEncID, record.langID)
        elif nid == 4:
            name_table.setName(full_name, 4, record.platformID, record.platEncID, record.langID)
        elif nid == 5:
            name_table.setName(
                f"Version {font_version}", 5, record.platformID, record.platEncID, record.langID
            )
        elif nid == 6:
            name_table.setName(postscript_name, 6, record.platformID, record.platEncID, record.langID)
        elif nid == 16:
            name_table.setName(family_name, 16, record.platformID, record.platEncID, record.langID)
        elif nid == 17:
            name_table.setName(subfamily_name, 17, record.platformID, record.platEncID, record.langID)

    head: Any = font["head"]
    head.fontRevision = float(".".join(font_version.split(".")[:2]))


def _glyph_y_max(font: TTFont, glyph_name: str) -> int:
    """Return the yMax of a glyph, treating empty glyphs as zero height."""
    glyph = font["glyf"][glyph_name]
    if glyph.numberOfContours == 0:
        return 0
    glyph.recalcBounds(font["glyf"])
    return getattr(glyph, "yMax", 0)


def sync_vertical_metrics(font: TTFont, glyph_names: set[str]) -> None:
    """Ensure vmtx has an entry for every glyph and refresh replaced glyphs.

    The merge step replaces outlines (and adds glyphs) without touching vmtx,
    which leaves the table shorter than maxp.numGlyphs.  That makes the font
    invalid and breaks vertical layout.  Vertical origin follows the Noto
    convention (OS/2.sTypoAscender).
    """
    vmtx = font["vmtx"]
    os2: Any = font["OS/2"]
    head: Any = font["head"]
    vhea: Any = font["vhea"]
    origin_y = int(os2.sTypoAscender)
    default_advance = int(head.unitsPerEm)

    for glyph_name in glyph_names:
        advance, _ = vmtx.metrics.get(glyph_name, (default_advance, 0))
        vmtx.metrics[glyph_name] = (advance, origin_y - _glyph_y_max(font, glyph_name))

    vhea.numberOfVMetrics = len(vmtx.metrics)


def _add_cmap_entry(font: TTFont, cp: int, glyph_name: str) -> bool:
    """Add *cp* to every cmap subtable that can represent it."""
    added = False
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        if table.format == 4 and cp > 0xFFFF:
            continue
        table.cmap[cp] = glyph_name
        added = True
    return added


def _decompose_glyph(glyph_set: Any, glyph_name: str) -> Any:
    """Copy a glyph outline (decomposing components) into a TTGlyph."""
    recorder = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(recorder)
    pen = TTGlyphPen(None)
    recorder.replay(pen)
    return pen.glyph()


def merge_fonts(
    base_font_path: Path,
    overlay_font_path: Path,
    output_font_path: Path,
    font_name: str = "noto-ridif",
    max_err: float = 1.0,
    fallback_font_paths: Sequence[Path] = (),
) -> None:
    print(f"Loading base font: {base_font_path}")
    base_font = TTFont(str(base_font_path))

    print(f"Loading overlay font: {overlay_font_path}")
    overlay_font = TTFont(str(overlay_font_path))

    base_cmap = base_font.getBestCmap()
    overlay_cmap = overlay_font.getBestCmap()
    overlay_glyphset = overlay_font.getGlyphSet()

    if base_cmap is None or overlay_cmap is None:
        raise ValueError("Font cmap table is missing or could not be loaded.")

    print(f"Base cmap codepoint count: {len(base_cmap)}")
    print(f"Overlay cmap codepoint count: {len(overlay_cmap)}")

    converted_glyphs = {}
    glyph_order = base_font.getGlyphOrder()
    existing_glyph_names = set(glyph_order)

    overridden_count = 0
    new_count = 0
    touched_glyphs: set[str] = set()

    # Ensure glyph order list is modifiable
    new_glyph_order = list(glyph_order)

    for cp, overlay_gname in sorted(overlay_cmap.items()):
        # Skip control codes or .notdef
        if cp < 32 or overlay_gname == ".notdef":
            continue

        if overlay_gname not in converted_glyphs:
            pen = TTGlyphPen(None)
            cu_pen = Cu2QuPen(pen, max_err=max_err)
            overlay_glyphset[overlay_gname].draw(cu_pen)
            converted_glyphs[overlay_gname] = pen.glyph()

        glyph = converted_glyphs[overlay_gname]
        metrics = overlay_font["hmtx"][overlay_gname]

        if cp in base_cmap:
            target_gname = base_cmap[cp]
            base_font["glyf"][target_gname] = glyph
            base_font["hmtx"][target_gname] = metrics
            touched_glyphs.add(target_gname)
            overridden_count += 1
        else:
            new_gname = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:06X}"
            if new_gname not in existing_glyph_names:
                existing_glyph_names.add(new_gname)
                new_glyph_order.append(new_gname)

            base_font["glyf"][new_gname] = glyph
            base_font["hmtx"][new_gname] = metrics
            touched_glyphs.add(new_gname)

            _add_cmap_entry(base_font, cp, new_gname)
            new_count += 1

    covered_codepoints = set(base_cmap)
    covered_codepoints.update(
        cp
        for cp, gname in overlay_cmap.items()
        if cp >= 32 and gname != ".notdef"
    )

    from noto_ridif.coverage import required_codepoints

    wanted_codepoints = required_codepoints()

    fallback_count = 0
    for fallback_path in fallback_font_paths:
        print(f"Loading fallback font: {fallback_path}")
        fallback_font = TTFont(str(fallback_path))
        try:
            fallback_cmap = fallback_font.getBestCmap() or {}
            fallback_glyphset = fallback_font.getGlyphSet()
            fallback_hmtx = fallback_font["hmtx"]

            for cp, fallback_gname in sorted(fallback_cmap.items()):
                if (
                    cp not in wanted_codepoints
                    or fallback_gname == ".notdef"
                    or cp in covered_codepoints
                ):
                    continue

                glyph = _decompose_glyph(fallback_glyphset, fallback_gname)
                metrics = fallback_hmtx[fallback_gname]

                new_gname = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:06X}"
                if new_gname not in existing_glyph_names:
                    existing_glyph_names.add(new_gname)
                    new_glyph_order.append(new_gname)

                base_font["glyf"][new_gname] = glyph
                base_font["hmtx"][new_gname] = metrics
                touched_glyphs.add(new_gname)

                _add_cmap_entry(base_font, cp, new_gname)
                covered_codepoints.add(cp)
                fallback_count += 1
        finally:
            fallback_font.close()

    base_font.setGlyphOrder(new_glyph_order)
    sync_vertical_metrics(base_font, touched_glyphs)

    print(f"Overridden glyphs: {overridden_count}")
    print(f"Newly added glyphs: {new_count}")
    print(f"Fallback glyphs: {fallback_count}")

    print(f"Updating metadata to '{font_name}'...")
    update_font_names(base_font, family_name=font_name, subfamily_name="Regular")

    output_font_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving merged font to: {output_font_path}")
    base_font.save(str(output_font_path))
    print("Done!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge RIDIBatang glyphs into NotoSerifKR-Regular."
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("fonts/NotoSerifKR-Regular.ttf"),
        help="Path to base Noto font (default: fonts/NotoSerifKR-Regular.ttf)",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        default=Path("fonts/RIDIBatang.otf"),
        help="Path to overlay RIDIBatang font (default: fonts/RIDIBatang.otf)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("noto-ridif.ttf"),
        help="Path to output font (default: noto-ridif.ttf)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="noto-ridif",
        help="Font family name (default: noto-ridif)",
    )
    parser.add_argument(
        "--max-err",
        type=float,
        default=1.0,
        help="Maximum approximation error for cubic-to-quadratic curve conversion (default: 1.0)",
    )
    parser.add_argument(
        "--fallback",
        type=Path,
        action="append",
        default=None,
        help="Font used to fill codepoints missing from base and overlay. "
        "May be repeated. Defaults to the bundled Noto Serif/Math/Symbols fonts.",
    )
    parser.add_argument(
        "--hint",
        action="store_true",
        help="Add TrueType hinting to Latin/Greek/Cyrillic, punctuation, and number glyphs "
        "(requires the ttfautohint-py dev dependency).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run font integrity checks after building and fail if problems are found.",
    )

    args = parser.parse_args()

    fallback_paths = (
        [Path(path) for path in args.fallback]
        if args.fallback
        else [path for path in DEFAULT_FALLBACK_FONTS if path.exists()]
    )
    missing_fallbacks = [path for path in fallback_paths if not path.exists()]
    if missing_fallbacks:
        parser.error(f"fallback font not found: {missing_fallbacks[0]}")

    merge_fonts(
        base_font_path=args.base,
        overlay_font_path=args.overlay,
        output_font_path=args.output,
        font_name=args.name,
        max_err=args.max_err,
        fallback_font_paths=fallback_paths,
    )

    from noto_ridif.optimize import hint_font
    from noto_ridif.verify import format_report, verify_font

    if args.hint:
        print("Adding TrueType hinting to Latin and symbol glyphs...")
        hinted = hint_font(args.output)
        print(f"Hinted glyphs: {hinted:,}")

    if args.verify:
        issues = verify_font(args.output, require_hinting=args.hint)
        print(format_report(args.output, issues))
        if issues:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
