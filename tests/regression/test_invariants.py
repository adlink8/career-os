"""契约回归：不自动提交、测试画像、权重、schema、插件放行模式。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from career_os_store import SCHEMA_VERSION
from services.apply_run import (
    ATS_MIN_SCORE,
    FILL_READY_STAGES,
    REVIEW_PASS_EACH,
    REVIEW_PASS_TOTAL,
    WEIGHT_ATS,
    WEIGHT_HR,
    WEIGHT_TECH,
)

pytestmark = pytest.mark.regression

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "extensions" / "ats-autofill"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_schema_v22_and_fill_ready_stages(isolated_db):
    assert SCHEMA_VERSION == 22
    cols = {r[1] for r in isolated_db.execute("PRAGMA table_info(job_apply_runs)")}
    assert "apply_mode" in cols
    tables = {
        r[0]
        for r in isolated_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "job_apply_runs" in tables
    assert "job_apply_run_events" in tables
    assert FILL_READY_STAGES == ("released", "volume_ready")


def test_review_formula_is_fixed():
    assert WEIGHT_ATS == 0.35 and WEIGHT_HR == 0.30 and WEIGHT_TECH == 0.35
    assert ATS_MIN_SCORE == 70
    assert REVIEW_PASS_TOTAL == 85 and REVIEW_PASS_EACH == 80
    # 88*0.35 + 90*0.30 + 88*0.35 = 88.6 → PASS 线
    total = round(88 * WEIGHT_ATS + 90 * WEIGHT_HR + 88 * WEIGHT_TECH, 2)
    assert total >= REVIEW_PASS_TOTAL


def test_plugin_declares_no_auto_submit():
    manifest = json.loads(_read(EXT / "manifest.json"))
    assert "不自动提交" in manifest.get("description", "")
    options = _read(EXT / "options.html")
    assert "不自动点网申提交" in options


def test_plugin_js_never_submits_forms():
    forbidden = re.compile(
        r"form\.submit\s*\(|\.type\s*===\s*['\"]submit['\"]|querySelector\([^)]*type=['\"]submit['\"]",
        re.I,
    )
    hits = []
    for path in EXT.glob("*.js"):
        text = _read(path)
        if forbidden.search(text):
            hits.append(path.name)
        if re.search(r"click\(\).*提交|提交.*click\(\)", text):
            hits.append(path.name + ":click-submit")
    assert hits == []


def test_content_js_fill_modes_are_explicit():
    text = _read(EXT / "content.js")
    assert "fillCtx.mode !== 'released'" in text
    assert "fillCtx.mode !== 'volume'" in text
    assert "fillCtx.mode !== 'overlay'" in text
    assert "fillCtx.mode !== 'test'" in text
    assert "allow_fill" in text


def test_release_notes_never_auto_submit():
    text = _read(ROOT / "bin" / "services" / "apply_run.py")
    assert "不自动提交网页" in text
    assert "非自动点提交" in text
    assert "测试画像不得用于真实投递" in text
    assert "测试画像不得用于海投真表" in text


def test_pack_and_gitignore_keep_profile_local():
    gitignore = _read(ROOT / ".gitignore")
    assert "extensions/ats-autofill/profile.json" in gitignore
    assert "config/profile.yml" in gitignore
    assert "data/*.sqlite" in gitignore or "data/*.sqlite*" in gitignore
    pack = _read(ROOT / "scripts" / "pack_autofill_extension.py")
    assert '"profile.json"' in pack
    assert '"native"' in pack


def test_readme_cross_links_gitee_plugin():
    readme = _read(ROOT / "README.md")
    assert "https://gitee.com/li-shuoya/career-os-autofill" in readme
    assert "https://gitee.com/li-shuoya/career-os" in readme
    assert "volume" in readme and "precision" in readme
