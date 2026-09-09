"""Career OS 测试隔离：禁止写入本机 career_jobs.sqlite 与 runs 目录。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))


@pytest.fixture(autouse=True)
def isolate_career_os_paths(tmp_path, monkeypatch):
    db_path = tmp_path / "career.sqlite"
    db_path.touch()
    monkeypatch.setenv("CAREER_OS_DB_PATH", str(db_path))
    monkeypatch.setenv("CAREER_OS_APPLY_RUNS", str(tmp_path / "runs"))
    import career_os_store

    monkeypatch.setattr(career_os_store, "DB_PATH", db_path)
    yield {"db_path": db_path, "runs": tmp_path / "runs", "tmp": tmp_path}


_SCHEMA_SQL = ROOT / "tests" / "fixtures" / "career_os_schema.sql"


@pytest.fixture
def isolated_db(isolate_career_os_paths):
    import sqlite3

    from career_os_store import get_db

    raw = sqlite3.connect(str(isolate_career_os_paths["db_path"]))
    raw.executescript(_SCHEMA_SQL.read_text(encoding="utf-8"))
    raw.close()
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def sample_context_payload():
    return {
        "version": "1.0",
        "url": "https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "host": "example.zhiye.com",
        "company": "示例公司",
        "title": "运维工程师",
        "jd_text": "岗位职责：负责 Linux Docker Kubernetes 运维。任职要求：本科 2027届。",
        "form_schema": [
            {"label": "姓名", "required": True},
            {"label": "求职意向", "required": True},
            {"label": "为什么选择本公司", "required": True, "type": "textarea"},
            {"label": "请选择", "required": False},
        ],
    }


@pytest.fixture
def test_profile():
    return {
        "version": "3.0-test-fixture",
        "universal": {
            "personal": {
                "name": "测一填",
                "phone": "13800138000",
                "email": "filltest@example.com",
            },
            "education": {
                "undergraduate": {
                    "school": "常州大学",
                    "major": "计算机科学与技术",
                    "degree": "本科",
                }
            },
        },
        "application": {
            "target_position": "运维工程师",
            "expected_city": "苏州",
            "projects": [{"name": "网关排障", "full_text": "负责 Linux Docker 排障。"}],
        },
    }
