"""验证 JD 感知模拟面试的出题、报告上下文和旧调用兼容性。"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data" / "career_jobs.sqlite"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="career-os-interview-jd-") as tmp:
        db_path = Path(tmp) / "career_jobs.sqlite"
        shutil.copy2(SOURCE_DB, db_path)
        env_db = os.environ.get("CAREER_OS_DB_PATH")
        previous_plugins = os.environ.get("CAREER_OS_PLUGINS")
        os.environ["CAREER_OS_DB_PATH"] = str(db_path)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from bin.career_os_store import get_db
        import bin.mock_interview_agent as interview_module
        from bin.jd_assessment_mapper import infer_assessment_profile
        from bin.mock_interview_agent import _interview_category_allowed, _select_jd_questions, run_mock_interview

        answer = "首先我负责项目实现，使用 Python、Linux、SQL、Docker 和 MQTT，做了测试、监控、指标验证和回滚；然后说明取舍，最后复盘结果。"
        outputs: dict[int, str] = {}
        try:
            conn = get_db()
            jobs = {
                1: conn.execute("SELECT company_id FROM jobs WHERE id=1").fetchone()[0],
                7: conn.execute("SELECT company_id FROM jobs WHERE id=7").fetchone()[0],
            }
            # Represent a newly imported open-ended community item.  The row
            # is intentionally created only in the temporary copy so this
            # smoke proves type/provenance handling without touching main DB.
            conn.execute(
                """
                INSERT INTO mock_questions
                    (category, difficulty, company_tags, question_type, title,
                     explanation, source_plugin, source_question_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "RAG 开放题", "中", "smoke-open-source", "interview",
                    "请设计 RAG 召回评测方案并说明验证指标。", "开放式社区题",
                    "smoke-open-source", "smoke-rag-001",
                ),
            )
            conn.commit()
            conn.close()

            for job_id, company_id in jobs.items():
                with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()) as captured:
                    assert run_mock_interview(str(company_id), job_id=job_id), job_id
                outputs[job_id] = captured.getvalue()

            conn = get_db()
            reports = {}
            for job_id in jobs:
                row = conn.execute(
                    "SELECT qa_transcript_json, provider, rubric_version FROM mock_interview_reports WHERE job_id=? ORDER BY id DESC LIMIT 1",
                    (job_id,),
                ).fetchone()
                assert row, job_id
                payload = json.loads(row[0])
                assert isinstance(payload, dict) and "context" in payload and "turns" in payload, job_id
                context = payload["context"]
                for key in ("tracks", "matched_signals", "question_families", "selected_questions", "provider", "rubric_version"):
                    assert context.get(key), (job_id, key)
                for item in context["selected_questions"]:
                    for provenance_key in ("source_plugin", "source_question_id", "question_type"):
                        assert item.get(provenance_key), (job_id, item, provenance_key)
                assert row[1:3] == ("local-rubric", "interview-v1"), row[1:3]
                reports[job_id] = payload
            conn.close()

            # The legacy company-only entry point still writes the old list
            # transcript shape and does not require a JD context object.
            legacy_company = jobs[1]
            with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()):
                assert run_mock_interview(str(legacy_company)), "legacy call"

            conn = get_db()

            legacy = conn.execute(
                "SELECT qa_transcript_json FROM mock_interview_reports WHERE job_id=? ORDER BY id DESC LIMIT 1",
                (legacy_company,),
            ).fetchone()
            legacy_payload = json.loads(legacy[0])
            assert isinstance(legacy_payload, list), type(legacy_payload)
            assert len(legacy_payload) == 4, len(legacy_payload)
            conn.close()

            # Exercise the real deepinterview manifest through PluginManager;
            # this run remains isolated in the temporary database copy.
            os.environ["CAREER_OS_PLUGINS"] = "deepinterview"
            plugin_job_id = 42
            plugin_company = jobs.get(plugin_job_id)
            if plugin_company is None:
                conn = get_db()
                plugin_company = conn.execute("SELECT company_id FROM jobs WHERE id=?", (plugin_job_id,)).fetchone()[0]
                conn.close()
            with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()) as plugin_output:
                assert run_mock_interview(str(plugin_company), job_id=plugin_job_id), "deepinterview run"
            conn = get_db()
            plugin_row = conn.execute(
                "SELECT qa_transcript_json, provider, rubric_version FROM mock_interview_reports WHERE job_id=? ORDER BY id DESC LIMIT 1",
                (plugin_job_id,),
            ).fetchone()
            conn.close()
            assert plugin_row and plugin_row[1] == "deepinterview-local-compat", plugin_row[1:]
            plugin_payload = json.loads(plugin_row[0])
            plugin_context = plugin_payload["context"]
            assert plugin_context.get("plugin_id") == "deepinterview", plugin_context
            assert plugin_context.get("contract_version") == "interview-agent-v1", plugin_context
            assert all(
                item.get(key)
                for item in plugin_context["selected_questions"]
                for key in ("source_plugin", "source_question_id", "question_type")
            ), plugin_context["selected_questions"]
            assert any(
                item.get("source") == "mock_questions"
                and item.get("track") == "software-testing-ops"
                and item.get("source_plugin")
                and item.get("source_question_id")
                and item.get("question_type")
                for item in plugin_context["selected_questions"]
            ), plugin_context["selected_questions"]
            assert "当前引擎: deepinterview-local-compat" in plugin_output.getvalue()

            class BrokenAgent:
                def prepare(self, **_kwargs):
                    raise RuntimeError("smoke prepare failure")

            class BrokenManager:
                def capability(self, _capability):
                    return BrokenAgent()

            previous_manager = interview_module.get_plugin_manager
            try:
                interview_module.get_plugin_manager = lambda: BrokenManager()
                with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()) as fallback_output:
                    assert run_mock_interview(str(plugin_company), job_id=plugin_job_id), "plugin fallback run"
                assert "[plugin-fallback] interview_agent" in fallback_output.getvalue()
                conn = get_db()
                fallback_row = conn.execute(
                    "SELECT provider, rubric_version FROM mock_interview_reports WHERE job_id=? ORDER BY id DESC LIMIT 1",
                    (plugin_job_id,),
                ).fetchone()
                conn.close()
                assert tuple(fallback_row) == ("local-rubric", "interview-v1"), fallback_row
            finally:
                interview_module.get_plugin_manager = previous_manager

            track_a = reports[1]["context"]["tracks"][0]["track_id"]
            track_b = reports[7]["context"]["tracks"][0]["track_id"]
            selected_a = [item["question"] for item in reports[1]["context"]["selected_questions"]]
            selected_b = [item["question"] for item in reports[7]["context"]["selected_questions"]]
            assert track_a != track_b, (track_a, track_b)
            assert selected_a != selected_b, (selected_a, selected_b)
            assert all(
                int(item.get("match_score", "0")) > 0
                for item in reports[1]["context"]["selected_questions"]
                if item.get("source_plugin") == "github-ather-rag-interview"
            ), reports[1]["context"]["selected_questions"]
            assert not any(
                item.get("source_question_id") in {
                    "ather-rag-advanced-rag-q1", "ather-rag-advanced-rag-q2",
                    "ather-rag-advanced-rag-q3", "ather-rag-graph-rag-q1",
                    "ather-rag-graph-rag-q2", "ather-rag-corrective-rag-q1",
                    "ather-rag-corrective-rag-q2",
                }
                for item in reports[1]["context"]["selected_questions"]
            ), reports[1]["context"]["selected_questions"]
            assert all(
                _interview_category_allowed("data-analysis", item.get("family", ""), item.get("category", ""))
                for item in reports[1]["context"]["selected_questions"]
                if item.get("source") == "mock_questions"
            ), reports[1]["context"]["selected_questions"]
            # The curated open-ended GitHub bank is the authoritative source;
            # do not depend on an inserted smoke row's ID/order after imports.
            assert any(
                item.get("source_plugin") == "github-ather-rag-interview"
                and item.get("question_type") == "interview"
                for item in reports[7]["context"]["selected_questions"]
            ), reports[7]["context"]["selected_questions"]

            # The embedded open bank contains a broadly tagged volatile item;
            # it must not leak into a software-testing JD without a matching
            # question-family hit.
            conn = get_db()
            job_42 = conn.execute(
                "SELECT id, company_name, job_title, category, responsibilities, requirements, english_req FROM jobs WHERE id=42"
            ).fetchone()
            guide_42 = conn.execute(
                "SELECT typical_questions FROM company_interview_guides WHERE company_id=?",
                (conn.execute("SELECT company_id FROM jobs WHERE id=42").fetchone()[0],),
            ).fetchone()
            profile_42 = infer_assessment_profile(job_42)
            profile_42["typical_questions"] = guide_42["typical_questions"]
            _unused_questions, selected_42 = _select_jd_questions(conn, profile_42)
            conn.close()
            assert not any(
                item.get("source_plugin") == "github-seringhong-embedded-interview"
                and "volatile" in item.get("question", "").casefold()
                for item in selected_42
            ), selected_42
            assert all(
                _interview_category_allowed("software-testing-ops", item.get("family", ""), item.get("category", ""))
                for item in selected_42
                if item.get("source") == "mock_questions"
            ), selected_42
            assert "岗位专项追问" in outputs[1] and "岗位专项追问" in outputs[7]
            print(f"[PASS] two JD tracks produce different interview contexts: {track_a} vs {track_b}")
            print("[PASS] report context persists tracks/signals/families/provider/rubric")
            print("[PASS] company-only legacy call keeps list transcript and completes")
            print("[PASS] enabled deepinterview plugin runs and supplies track question")
            print("[PASS] broken interview plugin prints reason and falls back to local-rubric")
            print("Mock interview JD smoke: PASS (temporary DB only)")
            return 0
        finally:
            if env_db is None:
                os.environ.pop("CAREER_OS_DB_PATH", None)
            else:
                os.environ["CAREER_OS_DB_PATH"] = env_db
            if previous_plugins is None:
                os.environ.pop("CAREER_OS_PLUGINS", None)
            else:
                os.environ["CAREER_OS_PLUGINS"] = previous_plugins


if __name__ == "__main__":
    raise SystemExit(main())
