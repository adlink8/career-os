import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node")
@pytest.mark.parametrize(
    "name",
    ["fill-policy.test.js", "overlay-store.test.js", "fill-runtime.test.js", "fill-dropdown.test.js"],
)
def test_js_contract(name):
    js = ROOT / "tests" / "js" / name
    proc = subprocess.run(
        ["node", str(js)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[OK]" in proc.stdout


def _npm() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


@pytest.mark.skipif(shutil.which("node") is None or _npm() is None, reason="需要 node/npm")
def test_simulated_campus_forms():
    js_dir = ROOT / "tests" / "js"
    if not (js_dir / "node_modules" / "jsdom").exists():
        install = subprocess.run(
            [_npm(), "install", "--prefix", str(js_dir), "--no-fund", "--no-audit"],
            cwd=str(js_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert install.returncode == 0, install.stdout + install.stderr
    proc = subprocess.run(
        [shutil.which("node") or "node", str(js_dir / "form-mocks.test.js")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[OK]" in proc.stdout
