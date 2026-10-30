#!/usr/bin/env python3
"""
Render demo images using the noto-ridif font formatted as an A5 book page.
"""

from pathlib import Path

import click
from PIL import Image, ImageDraw, ImageFont

# ISO 216 A5 paper: 148 x 210 mm
# At standard display resolution (150 DPI): 874 x 1240 px
# At high resolution (300 DPI): 1748 x 2480 px
A5_WIDTH_150DPI = 874
A5_HEIGHT_150DPI = 1240

DEFAULT_SAMPLE_TEXT = r"""noto-ridif Font Demo

1. 서체 소개
'noto-ridif'은 Google의 Noto Serif CJK KR 서체를 베이스로, 리디(RIDI)의 대표 전자책 본문용 서체인 '리디바탕(RIDIBatang)'의 글리프를 자연스럽게 융합한 오픈소스 폰트입니다.

2. 한글 글리프 테스트
다람쥐 헌 쳇바퀴에 타고파.
동해 물과 백두산이 마르고 닳도록 하느님이 보우하사 우리나라 만세.
무궁화 삼천리 화려 강산 대한 사람 대한으로 길이 보전하세.
가나다라마바사아자차카타파하 거너더러머버서어저처커터퍼허

3. 영문 및 특수기호
The quick brown fox jumps over the lazy dog.
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789 ()[]{}<> +-*/= %$#@! &*~`^|\:;"',.?/

4. 가독성 및 조판 안내
A5 용지 비율(148mm × 210mm)과 여백 규격에 맞춰 자동 줄바꿈(Word wrap)되어 렌더링됩니다. 전자종이(E-Paper) 단말기와 전자책 뷰어 환경에서 뛰어난 가독성을 제공합니다."""


def wrap_text(text: str, max_width: int, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont) -> list[str]:
    """Wrap text to fit within max_width, breaking by word and falling back to char break."""
    wrapped_lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            wrapped_lines.append("")
            continue

        words = paragraph.split(" ")
        current_line = ""

        for word in words:
            candidate = f"{current_line} {word}".strip() if current_line else word
            bbox = draw.textbbox((0, 0), candidate, font=font)
            w = bbox[2] - bbox[0]

            if w <= max_width:
                current_line = candidate
            else:
                if current_line:
                    wrapped_lines.append(current_line)
                    current_line = ""

                # If the single word itself exceeds max_width, break character by character
                bbox_word = draw.textbbox((0, 0), word, font=font)
                if bbox_word[2] - bbox_word[0] > max_width:
                    for ch in word:
                        test_ch = current_line + ch
                        bbox_ch = draw.textbbox((0, 0), test_ch, font=font)
                        if bbox_ch[2] - bbox_ch[0] <= max_width:
                            current_line = test_ch
                        else:
                            if current_line:
                                wrapped_lines.append(current_line)
                            current_line = ch
                else:
                    current_line = word

        if current_line:
            wrapped_lines.append(current_line)

    return wrapped_lines


def render_font_sample(
    font_path: Path,
    output_path: Path,
    text: str = DEFAULT_SAMPLE_TEXT,
    font_size: int = 24,
    width: int = A5_WIDTH_150DPI,
    height: int = A5_HEIGHT_150DPI,
    margin_x: int = 70,
    margin_y: int = 80,
    line_spacing: int = 14,
    bg_color: str = "#FAF8F5",  # Warm book paper tone
    fg_color: str = "#1E1E1E",  # Soft reading black
    auto_height: bool = False,
) -> None:
    """Render sample text onto an A5 proportion document image."""
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")

    font = ImageFont.truetype(str(font_path), font_size)

    # Printable text area width
    max_text_width = width - (margin_x * 2)

    # Measure and wrap text
    dummy_img = Image.new("RGB", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)

    lines = wrap_text(text, max_text_width, draw_dummy, font)

    # Calculate line heights
    _, _, _, sample_h = draw_dummy.textbbox((0, 0), "A가y", font=font)
    line_height = sample_h

    total_content_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
    final_height = int(max(height, total_content_height + (margin_y * 2))) if auto_height else height

    img = Image.new("RGB", (width, final_height), color=bg_color)
    draw = ImageDraw.Draw(img)

    curr_y = margin_y
    for line in lines:
        if line:
            draw.text((margin_x, curr_y), line, font=font, fill=fg_color)
        curr_y += line_height + line_spacing

        # Prevent overflow if not auto-height
        if not auto_height and curr_y + line_height > height - margin_y:
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), quality=95)
    click.echo(
        click.style("✓ ", fg="green", bold=True)
        + f"Rendered A5 document image to: {click.style(str(output_path), bold=True)} ({width}x{final_height}px)"
    )


@click.command(help="Render demo images using noto-ridif font (A5 document layout).")
@click.option(
    "--font",
    type=click.Path(path_type=Path),
    default=Path("noto-ridif.ttf"),
    show_default=True,
    help="Path to font file.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=Path("demo.png"),
    show_default=True,
    help="Output image path.",
)
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to text file containing sample text (e.g. demo.txt).",
)
@click.option(
    "--text",
    type=str,
    default=None,
    help="Custom sample text string (optional).",
)
@click.option(
    "--size",
    type=int,
    default=22,
    show_default=True,
    help="Font size in pt (for A5 book layout).",
)
@click.option(
    "--width",
    type=int,
    default=A5_WIDTH_150DPI,
    show_default=True,
    help="Page width in px (A5 @ 150DPI).",
)
@click.option(
    "--height",
    type=int,
    default=A5_HEIGHT_150DPI,
    show_default=True,
    help="Page height in px (A5 @ 150DPI).",
)
@click.option(
    "--auto-height",
    is_flag=True,
    default=False,
    help="Extend page height dynamically if content exceeds standard A5 height.",
)
def main(
    font: Path,
    output: Path,
    file_path: Path | None,
    text: str | None,
    size: int,
    width: int,
    height: int,
    auto_height: bool,
) -> None:
    # Friendly font resolution
    effective_font = font
    if not effective_font.exists():
        fallback_candidates = [
            Path("fonts/noto-ridif.ttf"),
            Path("fonts/NotoSerifKR-Regular.ttf"),
        ]
        for candidate in fallback_candidates:
            if candidate.exists():
                click.echo(
                    click.style("ℹ Note: ", fg="cyan", bold=True)
                    + f"'{font}' not found. Using fallback font '{candidate}'."
                )
                effective_font = candidate
                break

    if file_path:
        sample_text = file_path.read_text(encoding="utf-8")
    elif text:
        sample_text = text
    elif Path("demo.txt").exists():
        sample_text = Path("demo.txt").read_text(encoding="utf-8")
    else:
        sample_text = DEFAULT_SAMPLE_TEXT

    try:
        render_font_sample(
            font_path=effective_font,
            output_path=output,
            text=sample_text,
            font_size=size,
            width=width,
            height=height,
            auto_height=auto_height,
        )
    except FileNotFoundError as err:
        click.echo(click.style(f"✗ Error: {err}", fg="red", bold=True), err=True)
        raise SystemExit(1) from err


if __name__ == "__main__":
    main()
