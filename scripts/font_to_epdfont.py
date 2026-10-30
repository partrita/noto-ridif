"""Convert TTF/OTF fonts to .epdfont binary format for E-Paper displays.
"""
import math
import struct
import sys
from collections import namedtuple
from collections.abc import Sequence
from pathlib import Path

import click
import freetype

EPDFONT_MAGIC = 0x46445045  # "EPDF"
EPDFONT_VERSION = 1

GlyphProps = namedtuple(
    "GlyphProps",
    [
        "width",
        "height",
        "advance_x",
        "left",
        "top",
        "data_length",
        "data_offset",
        "code_point",
    ],
)


def norm_floor(val: int) -> int:
    """Normalize 26.6 fixed-point FreeType value to integer using floor."""
    return math.floor(val / 64.0)


def norm_ceil(val: int) -> int:
    """Normalize 26.6 fixed-point FreeType value to integer using ceil."""
    return math.ceil(val / 64.0)


def load_glyph(font_stack: Sequence[freetype.Face], code_point: int) -> freetype.Face | None:
    """Find and render glyph for code_point from fallback font stack."""
    for face in font_stack:
        glyph_index = face.get_char_index(code_point)
        if glyph_index > 0:
            face.load_glyph(glyph_index, getattr(freetype, "FT_LOAD_RENDER", 4))
            return face
    return None


def convert_bitmap_to_1bit(bitmap: freetype.Bitmap) -> bytes:
    """Pack grayscale FreeType bitmap buffer into 1-bit monochrome bytes."""
    width = bitmap.width
    rows = bitmap.rows
    buffer = bitmap.buffer

    if width == 0 or rows == 0 or not buffer:
        return b""

    # FreeType render buffer is 8-bit grayscale (0..255)
    # Pack each 8 pixels into 1 byte (MSB first)
    pixels = bytearray()
    curr_byte = 0
    bits_filled = 0

    for val in buffer:
        bit = 1 if val >= 128 else 0
        curr_byte = (curr_byte << 1) | bit
        bits_filled += 1
        if bits_filled == 8:
            pixels.append(curr_byte)
            curr_byte = 0
            bits_filled = 0

    if bits_filled > 0:
        curr_byte <<= (8 - bits_filled)
        pixels.append(curr_byte)

    return bytes(pixels)


def convert_bitmap_to_2bit(bitmap: freetype.Bitmap, gamma: float = 1.0) -> bytes:
    """Pack grayscale FreeType bitmap buffer into 2-bit grayscale bytes (4 pixels per byte).

    ``gamma`` < 1 darkens midtones (useful on e-paper), ``gamma`` > 1 lightens them.
    """
    width = bitmap.width
    rows = bitmap.rows
    buffer = bitmap.buffer

    if width == 0 or rows == 0 or not buffer:
        return b""

    # Quantize 0..255 into 0..3 (2 bits)
    # 0..63: 0, 64..127: 1, 128..191: 2, 192..255: 3
    pixels = bytearray()
    curr_byte = 0
    pixels_filled = 0

    for val in buffer:
        if gamma != 1.0:
            val = int(255.0 * ((val / 255.0) ** gamma))
        two_bit = min(3, val >> 6)
        curr_byte = (curr_byte << 2) | two_bit
        pixels_filled += 1
        if pixels_filled == 4:
            pixels.append(curr_byte)
            curr_byte = 0
            pixels_filled = 0

    if pixels_filled > 0:
        curr_byte <<= (4 - pixels_filled) * 2
        pixels.append(curr_byte)

    return bytes(pixels)


def get_default_unicode_intervals() -> list[tuple[int, int]]:
    """Return standard comprehensive Unicode ranges."""
    return [
        # Basic Latin & Extensions
        (0x0000, 0x007F),  # Basic Latin (ASCII)
        (0x0080, 0x00FF),  # Latin-1 Supplement
        (0x0100, 0x017F),  # Latin Extended-A
        (0x0180, 0x024F),  # Latin Extended-B
        (0x0250, 0x02AF),  # IPA Extensions
        (0x02B0, 0x02FF),  # Spacing Modifier Letters
        (0x0300, 0x036F),  # Combining Diacritical Marks
        (0x0370, 0x03FF),  # Greek and Coptic
        (0x0400, 0x04FF),  # Cyrillic
        (0x0500, 0x052F),  # Cyrillic Supplement
        # Korean (Hangul)
        (0x1100, 0x11FF),  # Hangul Jamo
        (0x3130, 0x318F),  # Hangul Compatibility Jamo
        (0xA960, 0xA97F),  # Hangul Jamo Extended-A
        (0xAC00, 0xD7AF),  # Hangul Syllables (11,172)
        (0xD7B0, 0xD7FF),  # Hangul Jamo Extended-B
        # CJK
        (0x3000, 0x303F),  # CJK Symbols and Punctuation
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0x3100, 0x312F),  # Bopomofo
        (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
        (0x3200, 0x32FF),  # Enclosed CJK Letters and Months
        (0x3300, 0x33FF),  # CJK Compatibility
        (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
        (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
        # Punctuation & Symbols
        (0x2000, 0x206F),  # General Punctuation
        (0x2070, 0x209F),  # Superscripts and Subscripts
        (0x20A0, 0x20CF),  # Currency Symbols
        (0x20D0, 0x20FF),  # Combining Diacritical Marks for Symbols
        (0x2100, 0x214F),  # Letterlike Symbols
        (0x2150, 0x218F),  # Number Forms
        (0x2190, 0x21FF),  # Arrows
        (0x2200, 0x22FF),  # Mathematical Operators
        (0x2300, 0x23FF),  # Miscellaneous Technical
        (0x2400, 0x243F),  # Control Pictures
        (0x2440, 0x245F),  # Optical Character Recognition
        (0x2460, 0x24FF),  # Enclosed Alphanumerics
        (0x2500, 0x257F),  # Box Drawing
        (0x2580, 0x259F),  # Block Elements
        (0x25A0, 0x25FF),  # Geometric Shapes
        (0x2600, 0x26FF),  # Miscellaneous Symbols
        (0x2700, 0x27BF),  # Dingbats
        (0x27C0, 0x27EF),  # Misc Math Symbols-A
        (0x27F0, 0x27FF),  # Supplemental Arrows-A
        (0x2800, 0x28FF),  # Braille Patterns
        (0x2900, 0x297F),  # Supplemental Arrows-B
        (0x2980, 0x29FF),  # Misc Math Symbols-B
        (0x2A00, 0x2AFF),  # Supplemental Math Operators
        (0x2B00, 0x2BFF),  # Misc Symbols and Arrows
        (0xFFF0, 0xFFFF),  # Specials
        # Emoji & Pictographs
        (0x1F300, 0x1F5FF),
        (0x1F600, 0x1F64F),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA00, 0x1FA6F),
        (0x1FA70, 0x1FAFF),
    ]


def convert_font_to_epdfont(
    font_files: Sequence[str],
    font_name: str,
    size: int,
    output_path: str,
    additional_intervals: Sequence[str] | None = None,
    is_2bit: bool = True,
    line_height: float = 1.2,
    letter_spacing: int = 0,
    width_scale: float = 1.0,
    baseline_offset: int = 0,
    gamma: float = 1.0,
) -> bool:
    """Convert TTF font(s) to .epdfont binary format."""
    font_stack = [freetype.Face(str(f)) for f in font_files]

    for face in font_stack:
        face.set_pixel_sizes(0, size)

    intervals = get_default_unicode_intervals()

    if additional_intervals:
        for interval in additional_intervals:
            parts = interval.split(",")
            if len(parts) == 2:
                intervals.append((int(parts[0], 0), int(parts[1], 0)))

    # Sort and merge intervals
    sorted_intervals = sorted(intervals)
    merged_intervals: list[tuple[int, int]] = []
    for i_start, i_end in sorted_intervals:
        if merged_intervals and i_start <= merged_intervals[-1][1] + 1:
            merged_intervals[-1] = (merged_intervals[-1][0], max(merged_intervals[-1][1], i_end))
        else:
            merged_intervals.append((i_start, i_end))

    # Validate intervals against fonts in stack
    validated_intervals: list[tuple[int, int]] = []
    for i_start, i_end in merged_intervals:
        start = i_start
        for cp in range(i_start, i_end + 1):
            face = load_glyph(font_stack, cp)
            if face is None:
                if start < cp:
                    validated_intervals.append((start, cp - 1))
                start = cp + 1
        if start <= i_end:
            validated_intervals.append((start, i_end))

    total_size = 0
    all_glyphs = []

    with click.progressbar(
        validated_intervals,
        label=click.style("Rendering glyphs", fg="cyan"),
        show_pos=True,
        show_percent=True,
        item_show_func=lambda item: f"U+{item[0]:04X}..U+{item[1]:04X}" if item else "",
    ) as bar:
        for i_start, i_end in bar:
            for code_point in range(i_start, i_end + 1):
                face = load_glyph(font_stack, code_point)
                if face is None:
                    continue

                bitmap = face.glyph.bitmap
                packed = (
                    convert_bitmap_to_2bit(bitmap, gamma=gamma)
                    if is_2bit
                    else convert_bitmap_to_1bit(bitmap)
                )

                original_advance_x = norm_floor(face.glyph.advance.x)
                adjusted_advance_x = int(original_advance_x * width_scale) + letter_spacing
                adjusted_top = face.glyph.bitmap_top + baseline_offset

                glyph = GlyphProps(
                    width=bitmap.width,
                    height=bitmap.rows,
                    advance_x=adjusted_advance_x,
                    left=face.glyph.bitmap_left,
                    top=adjusted_top,
                    data_length=len(packed),
                    data_offset=total_size,
                    code_point=code_point,
                )
                total_size += len(packed)
                all_glyphs.append((glyph, packed))

    # Determine vertical font metrics
    face = load_glyph(font_stack, ord("|")) or font_stack[0]
    original_advance_y = norm_ceil(face.size.height)
    advance_y = int(original_advance_y * line_height)
    ascender = norm_ceil(face.size.ascender)
    descender = norm_floor(face.size.descender)

    click.echo(
        f"  Total glyphs extracted: {click.style(str(len(all_glyphs)), bold=True)} across {len(validated_intervals)} intervals"
    )
    click.echo(
        f"  Font metrics: advanceY={advance_y} (line-height: {line_height*100:.0f}%), "
        f"ascender={ascender}, descender={descender}"
    )
    if letter_spacing != 0:
        click.echo(f"  Letter spacing: {letter_spacing:+d}px")
    if width_scale != 1.0:
        click.echo(f"  Width scale (장평): {width_scale*100:.0f}%")
    if baseline_offset != 0:
        click.echo(f"  Baseline offset: {baseline_offset:+d}px")
    if gamma != 1.0:
        click.echo(f"  Gamma: {gamma:.2f} (2-bit grayscale only)")

    write_epdfont(
        output_path=output_path,
        intervals=validated_intervals,
        all_glyphs=all_glyphs,
        advance_y=advance_y,
        ascender=ascender,
        descender=descender,
        is_2bit=is_2bit,
    )

    return True


def write_epdfont(
    output_path: str,
    intervals: Sequence[tuple[int, int]],
    all_glyphs: Sequence[tuple[GlyphProps, bytes]],
    advance_y: int,
    ascender: int,
    descender: int,
    is_2bit: bool,
) -> None:
    """Write binary .epdfont structure to disk."""
    header_size = 32
    intervals_size = len(intervals) * 12
    glyphs_size = len(all_glyphs) * 16

    intervals_offset = header_size
    glyphs_offset = intervals_offset + intervals_size
    bitmap_offset = glyphs_offset + glyphs_size

    bitmap_data = b"".join([packed for _, packed in all_glyphs])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        # Header (32 bytes)
        header = struct.pack(
            "<IHBBBBBB5I",
            EPDFONT_MAGIC,
            EPDFONT_VERSION,
            1 if is_2bit else 0,
            0,
            advance_y & 0xFF,
            ascender & 0xFF,
            descender & 0xFF,
            0,
            len(intervals),
            len(all_glyphs),
            intervals_offset,
            glyphs_offset,
            bitmap_offset,
        )
        f.write(header)

        # Intervals table
        offset = 0
        for i_start, i_end in intervals:
            f.write(struct.pack("<3I", i_start, i_end, offset))
            offset += i_end - i_start + 1

        # Glyphs table
        f.writelines(struct.pack(
                    "<4B2h2I",
                    glyph.width,
                    glyph.height,
                    glyph.advance_x,
                    0,
                    glyph.left,
                    glyph.top,
                    glyph.data_length,
                    glyph.data_offset,
                ) for glyph, _ in all_glyphs)

        # Raw bitmap data
        f.write(bitmap_data)

    total_size = bitmap_offset + len(bitmap_data)
    click.echo()
    click.echo(click.style("✓ Output file generated:", fg="green", bold=True) + f" {click.style(str(output_path), bold=True)}")
    click.echo(f"  • Unicode intervals: {len(intervals):,}")
    click.echo(f"  • Glyphs included: {len(all_glyphs):,}")
    click.echo(f"  • Raw bitmap data: {len(bitmap_data):,} bytes")
    click.echo(f"  • Total binary size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")


@click.command(help="Convert TTF or OTF fonts to .epdfont binary format for E-Paper displays.")
@click.argument("name", type=str)
@click.argument("size", type=int)
@click.argument("fontfiles", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--2bit/--1bit",
    "is_2bit",
    default=True,
    show_default=True,
    help="Generate 2-bit grayscale bitmap (default) or 1-bit monochrome bitmap.",
)
@click.option(
    "--additional-intervals",
    "additional_intervals",
    multiple=True,
    help="Additional Unicode intervals as MIN,MAX (hex or decimal). Can be repeated.",
)
@click.option("-o", "--output", "output", type=click.Path(), default=None, help="Output .epdfont file path.")
@click.option(
    "--line-height",
    type=float,
    default=1.2,
    show_default=True,
    help="Line height multiplier (e.g. 1.2 = 120%).",
)
@click.option(
    "--letter-spacing",
    type=int,
    default=0,
    show_default=True,
    help="Additional spacing between characters in pixels.",
)
@click.option(
    "--width-scale",
    type=float,
    default=1.0,
    show_default=True,
    help="Horizontal width scale factor, 장평 (e.g. 1.0 = 100%).",
)
@click.option(
    "--baseline-offset",
    type=int,
    default=0,
    show_default=True,
    help="Baseline vertical offset in pixels (positive = up).",
)
@click.option(
    "--gamma",
    type=float,
    default=1.0,
    show_default=True,
    help="Gamma for 2-bit grayscale quantization (<1 darkens midtones, >1 lightens).",
)
def main(
    name: str,
    size: int,
    fontfiles: tuple[str, ...],
    is_2bit: bool,
    additional_intervals: tuple[str, ...],
    output: str | None,
    line_height: float,
    letter_spacing: int,
    width_scale: float,
    baseline_offset: int,
    gamma: float,
) -> None:
    output_path = output if output else f"{name}_{size}.epdfont"

    click.echo(click.style("▶ E-Paper Font Conversion", fg="blue", bold=True))
    click.echo(f"  • Font Name: {click.style(name, bold=True)} ({size}px)")
    click.echo(f"  • Source(s): {', '.join(fontfiles)}")
    click.echo(f"  • Mode: {click.style('2-bit Grayscale' if is_2bit else '1-bit Monochrome', bold=True)}")
    click.echo(f"  • Layout: line-height={line_height*100:.0f}%, spacing={letter_spacing}px, width-scale={width_scale*100:.0f}%, offset={baseline_offset}px")
    click.echo()

    success = convert_font_to_epdfont(
        font_files=fontfiles,
        font_name=name,
        size=size,
        output_path=output_path,
        additional_intervals=list(additional_intervals) if additional_intervals else None,
        is_2bit=is_2bit,
        line_height=line_height,
        letter_spacing=letter_spacing,
        width_scale=width_scale,
        baseline_offset=baseline_offset,
        gamma=gamma,
    )

    if success:
        click.echo(click.style("✨ Conversion completed successfully!", fg="green", bold=True))
    else:
        click.echo(click.style("✗ Conversion failed!", fg="red", bold=True), err=True)
        sys.exit(1)
if __name__ == "__main__":
    main()

# Backwards compatibility alias
convert_ttf_to_epdfont = convert_font_to_epdfont
