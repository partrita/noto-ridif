import shutil
import subprocess
import sys


def test_ruff_check() -> None:
    """Verify that ruff check passes across the entire project."""
    cmd = [sys.executable, "-m", "ruff", "check", "."]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert res.returncode == 0, f"ruff check failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


def test_ty_check() -> None:
    """Verify that ty check passes across the entire project."""
    ty_bin = shutil.which("ty")
    if not ty_bin:
        ty_bin = "/Users/fkt/.local/bin/ty"

    cmd = [ty_bin, "check", "."]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert res.returncode == 0, f"ty check failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
