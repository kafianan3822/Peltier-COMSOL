"""Compile the Java drivers against the stub API (no COMSOL needed)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac not installed")
def test_java_drivers_compile(tmp_path):
    stubs = sorted(str(p) for p in (ROOT / "tests" / "java_stubs").rglob("*.java"))
    srcs = [str(ROOT / "comsol" / "java" / f) for f in ("BuildPinPeltier.java", "RunVariants.java")]
    r = subprocess.run(["javac", "--release", "8", "-Xlint:-options", "-d", str(tmp_path), *stubs, *srcs],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_java_generated_blocks_in_sync():
    import sys
    sys.path.insert(0, str(ROOT / "comsol" / "python"))
    import sync_java_api_names as s
    for path, text in s.rendered().items():
        assert path.read_text(encoding="utf-8") == text, f"{path.name}: run sync_java_api_names.py"
