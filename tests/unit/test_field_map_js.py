import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "tests" / "js" / "field-map.test.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node")
def test_field_map_js_vm():
    proc = subprocess.run(
        ["node", str(JS)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[OK]" in proc.stdout
