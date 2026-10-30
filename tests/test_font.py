import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont


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
