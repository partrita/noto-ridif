import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from noto_ridif.coverage import find_missing
from noto_ridif.verify import verify_font


def test_font_file_exists() -> None:
    font_path = Path("noto-ridif.ttf")
    assert font_path.exists(), "noto-ridif.ttf must exist"


def test_font_metadata() -> None:
    font_path = Path("noto-ridif.ttf")
    assert font_path.exists()

    font = TTFont(str(font_path))
    name_table = font["name"]

    names_by_id = {}
    for record in name_table.names:
        names_by_id[record.nameID] = record.toUnicode()

    assert names_by_id.get(1) == "noto-ridif"
    assert names_by_id.get(2) == "Regular"
    assert names_by_id.get(3) == "noto-ridif;noto-ridif-Regular"
    assert names_by_id.get(4) == "noto-ridif Regular"
    assert names_by_id.get(6) == "noto-ridif-Regular"


def test_font_integrity() -> None:
    """The generated font must pass cmap/hmtx/vmtx/name integrity checks."""
    assert verify_font(Path("noto-ridif.ttf")) == []


def test_required_coverage() -> None:
    """Every character in the required ranges must be present."""
    font = TTFont("noto-ridif.ttf")
    try:
        assert find_missing(font) == []
    finally:
        font.close()


def test_vertical_metrics_complete() -> None:
    """vmtx must cover every glyph, including overlay-only additions."""
    font = TTFont("noto-ridif.ttf")
    try:
        assert len(font["vmtx"].metrics) == font["maxp"].numGlyphs
    finally:
        font.close()


def test_web_fonts(tmp_path: Path) -> None:
    """WOFF and WOFF2 output must preserve glyph coverage and flavor."""
    cmd = [
        sys.executable,
        "scripts/font_to_woff.py",
        "noto-ridif.ttf",
        "--output-dir",
        str(tmp_path),
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert res.returncode == 0, f"font_to_woff.py failed: {res.stderr}"

    source = TTFont("noto-ridif.ttf")
    try:
        source_cmap = source.getBestCmap()
        assert source_cmap is not None
        expected_cmap = set(source_cmap)
    finally:
        source.close()

    for flavor in ("woff", "woff2"):
        output = tmp_path / f"noto-ridif.{flavor}"
        assert output.exists(), f"{flavor} output is missing"
        font = TTFont(str(output))
        try:
            assert font.flavor == flavor
            cmap = font.getBestCmap()
            assert cmap is not None
            assert set(cmap) == expected_cmap
        finally:
            font.close()


def test_render_demo_runs(tmp_path: Path) -> None:
    out_file = tmp_path / "test_demo.png"
    cmd = [
        sys.executable,
        "scripts/render_demo.py",
        "--font",
        "noto-ridif.ttf",
        "-o",
        str(out_file),
        "--text",
        "Noto-Ridif 테스트 문장입니다.",
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert res.returncode == 0, f"render_demo.py failed: {res.stderr}"
    assert out_file.exists()
