"""把既有标准库冒烟脚本挂进回归套件。runtime-smoke 依赖本机题库，缺库则跳过。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

ROOT = Path(__file__).resolve().parents[2]


def _run_script(rel: str, extra_env: dict | None = None, timeout: int = 90) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("CAREER_OS_DB_PATH", None)
    env.pop("CAREER_OS_APPLY_RUNS", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(ROOT / rel)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def test_ats_engine_smoke():
    proc = _run_script("scripts/ats-engine-smoke.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[OK]" in proc.stdout or "[PASS]" in proc.stdout


def test_job_context_smoke():
    proc = _run_script("scripts/job-context-smoke.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_apply_run_smoke(tmp_path):
    env = {
        "CAREER_OS_DB_PATH": str(tmp_path / "ignored.sqlite"),
        "CAREER_OS_APPLY_RUNS": str(tmp_path / "runs"),
    }
    proc = _run_script("scripts/apply-run-smoke.py", extra_env=env, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[OK] apply-run-smoke" in proc.stdout


def test_runtime_smoke_optional():
    db = ROOT / "data" / "career_jobs.sqlite"
    if not db.is_file():
        pytest.skip("本机没有 data/career_jobs.sqlite")
    proc = _run_script("scripts/runtime-smoke.py", timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
