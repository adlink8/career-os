from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def _load_pack_module():
    path = ROOT / "scripts" / "pack_autofill_extension.py"
    spec = importlib.util.spec_from_file_location("pack_autofill_extension", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_pack_excludes_profile_and_native(tmp_path, monkeypatch):
    pack = _load_pack_module()

    src = tmp_path / "src"
    dist = tmp_path / "dist"
    src.mkdir()
    (src / "manifest.json").write_text(
        json.dumps({"version": "9.9.9", "name": "test"}, ensure_ascii=False), encoding="utf-8"
    )
    (src / "content.js").write_text("console.log('ok');", encoding="utf-8")
    (src / "profile.json").write_text('{"name":"SECRET"}', encoding="utf-8")
    (src / "profile.test.json").write_text("{}", encoding="utf-8")
    native = src / "native"
    native.mkdir()
    (native / "host.py").write_text("print(1)", encoding="utf-8")

    monkeypatch.setattr(pack, "SRC", src)
    monkeypatch.setattr(pack, "DIST", dist)
    assert pack.main() == 0

    zip_path = dist / "career-os-autofill-9.9.9.zip"
    assert zip_path.is_file()
    names = zipfile.ZipFile(zip_path).namelist()
    joined = "\n".join(names)
    assert any(n.endswith("manifest.json") for n in names)
    assert any(n.endswith("content.js") for n in names)
    assert any("安装说明.txt" in n for n in names)
    assert "profile.json" not in joined
    assert "profile.test.json" not in joined
    assert "native/" not in joined.replace("\\", "/")
    assert "SECRET" not in zip_path.read_bytes().decode("utf-8", errors="ignore")


def test_pack_skip_constants():
    pack = _load_pack_module()
    assert "profile.json" in pack.SKIP_NAMES
    assert "native" in pack.SKIP_DIRS
