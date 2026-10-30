"""noto-ridif: Merge NotoSerifKR-Regular and RIDIBatang fonts."""

import argparse
from pathlib import Path

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def update_font_names(
    font: TTFont,
    family_name: str = "noto-ridif",
    subfamily_name: str = "Regular",
) -> None:
    """Update name records in the font's 'name' table."""
    full_name = f"{family_name} {subfamily_name}".strip()
    postscript_name = f"{family_name}-{subfamily_name}".replace(" ", "")

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
        elif nid == 6:
            name_table.setName(postscript_name, 6, record.platformID, record.platEncID, record.langID)
        elif nid == 16:
            name_table.setName(family_name, 16, record.platformID, record.platEncID, record.langID)
        elif nid == 17:
            name_table.setName(subfamily_name, 17, record.platformID, record.platEncID, record.langID)


def merge_fonts(
    base_font_path: Path,
    overlay_font_path: Path,
    output_font_path: Path,
    font_name: str = "noto-ridif",
    max_err: float = 1.0,
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
            overridden_count += 1
        else:
            new_gname = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:06X}"
            if new_gname not in existing_glyph_names:
                existing_glyph_names.add(new_gname)
                new_glyph_order.append(new_gname)

            base_font["glyf"][new_gname] = glyph
            base_font["hmtx"][new_gname] = metrics

            for table in base_font["cmap"].tables:
                if table.isUnicode():
                    table.cmap[cp] = new_gname
            new_count += 1

    base_font.setGlyphOrder(new_glyph_order)

    print(f"Overridden glyphs: {overridden_count}")
    print(f"Newly added glyphs: {new_count}")

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

    args = parser.parse_args()
    merge_fonts(
        base_font_path=args.base,
        overlay_font_path=args.overlay,
        output_font_path=args.output,
        font_name=args.name,
        max_err=args.max_err,
    )


if __name__ == "__main__":
    main()
