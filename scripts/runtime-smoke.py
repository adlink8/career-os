"""Career OS P0/P1 运行时契约冒烟测试（仅标准库）。"""

from __future__ import annotations

import os
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_plugins import get_plugin_manager
from bin.code_runner import TrustedLocalRunner
from bin.job_source_adapter import JobSourceAdapter
from bin.mock_interview_agent import score_answer
from bin.mock_oa_sandbox import _job_question_tracks
from bin.personality_assessment import score_personality
from bin.question_bank_adapter import QuestionBankAdapter
from bin.jd_assessment_mapper import infer_assessment_profile
from bin.career_os_store import DB_PATH, SCHEMA_VERSION, get_db


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def main() -> int:
    conn = get_db()
    check(
        "latest schema migration recorded",
        conn.execute("select max(version) from career_os_schema_migrations").fetchone()[0]
        == SCHEMA_VERSION,
    )
    for table in ("mock_exam_answers", "interview_turns", "github_project_candidates", "resume_project_proposals", "job_page_contexts", "job_apply_runs", "job_apply_run_events"):
        check(f"table {table} exists", conn.execute("select 1 from sqlite_master where type='table' and name=?", (table,)).fetchone() is not None)
    for table, column in (("mock_exam_records", "provider"), ("mock_interview_reports", "rubric_version"), ("mock_questions", "source_plugin"), ("mock_questions", "assessment_kind"), ("mock_questions", "dimension"), ("jobs", "source_plugin"), ("github_project_candidates", "license_spdx"), ("github_project_candidates", "matched_terms_json"), ("resume_project_proposals", "evidence_text")):
        check(f"column {table}.{column} exists", column in {r[1] for r in conn.execute(f"pragma table_info({table})")})
    check(
        "active personality bank is GitHub/IPIP sourced",
        conn.execute(
            "select count(*) from mock_questions where question_type='personality' and source_plugin='github-deep-personality-oss'"
        ).fetchone()[0] > 0,
    )
    check(
        "original personality bank is absent",
        conn.execute(
            "select count(*) from mock_questions where question_type='personality' and source_plugin='career-os'"
        ).fetchone()[0] == 0,
    )
    check(
        "project question bank is present",
        conn.execute("select count(*) from mock_questions where source_plugin='career-os-project'").fetchone()[0] > 0,
    )
    openquiz_count = conn.execute(
        "select count(*) from mock_questions where source_plugin='github-open-quiz-commons'"
    ).fetchone()[0]
    check("expanded GitHub technical question bank is present", openquiz_count >= 703)
    check(
        "expanded GitHub source IDs are unique",
        conn.execute(
            "select count(*) from mock_questions where source_plugin='github-open-quiz-commons'"
        ).fetchone()[0]
        == conn.execute(
            "select count(distinct source_question_id) from mock_questions where source_plugin='github-open-quiz-commons'"
        ).fetchone()[0],
    )
    snapshot_files = sorted((ROOT / "data").glob("question-bank.github-openquiz*.json"))
    snapshot_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in snapshot_files]
    expanded_files = [path for path in snapshot_files if path.name != "question-bank.github-openquiz.json"]
    check("Open Quiz expanded snapshots are present", len(expanded_files) >= 10)
    check(
        "Open Quiz snapshots declare upstream license",
        all(payload.get("source", {}).get("license") == "CC-BY-SA-4.0" for payload in snapshot_payloads),
    )
    check(
        "Open Quiz snapshots retain license evidence URL",
        all(
            payload.get("source", {}).get("license_evidence", "").startswith(
                "https://github.com/prahladyeri/open-quiz-commons/blob/"
            )
            for payload in snapshot_payloads
        ),
    )
    check(
        "Open Quiz expanded snapshots cover JD gap rows",
        sum(len(payload.get("questions", [])) for payload in snapshot_payloads if payload.get("name", "").endswith(("python-core", "python-data", "python-ops-network", "ai-js", "devops", "embedded-data-infra", "testing-ops", "data-api", "ai", "next-foundations"))) >= 678,
    )
    curated_new = [
        payload for payload in snapshot_payloads
        if payload.get("name", "").endswith(("testing-ops", "data-api", "ai", "next-foundations"))
    ]
    check(
        "new JD snapshots retain source trace and explanations",
        all(
            question.get("source_file")
            and question.get("source_module")
            and question.get("source_text")
            and question.get("explanation")
            for payload in curated_new
            for question in payload.get("questions", [])
        ),
    )
    expansion_snapshots = {
        "question-bank.github-exam-questions-aptitude.json": ("MIT", 175, "choice"),
        "personality-bank.github-bigfive-web-ipip-neo-120.json": ("MIT", 120, "personality"),
        "question-bank.github-embedded-interview-prep.json": ("MIT", 120, "interview"),
    }
    for filename, (license_name, expected_count, expected_type) in expansion_snapshots.items():
        path = ROOT / "data" / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("questions", [])
        check(f"GitHub expansion snapshot {filename} exists", path.exists())
        check(f"GitHub expansion snapshot {filename} license is declared", payload.get("source", {}).get("license") == license_name)
        check(f"GitHub expansion snapshot {filename} has expected count", len(rows) == expected_count)
        check(f"GitHub expansion snapshot {filename} has expected type", all(row.get("question_type") == expected_type for row in rows))
        check(
            f"GitHub expansion snapshot {filename} retains trace fields",
            all(row.get("source_file") and row.get("source_module") and row.get("source_text") for row in rows),
        )
    for source_plugin, expected_count, expected_type in (
        ("github-embedded-interview-prep", 120, "interview"),
        ("github-exam-questions-aptitude", 175, "choice"),
        ("github-bigfive-web-ipip-neo-120", 120, "personality"),
    ):
        check(
            f"imported GitHub source {source_plugin} has expected count",
            conn.execute(
                "select count(*) from mock_questions where source_plugin=? and question_type=?",
                (source_plugin, expected_type),
            ).fetchone()[0] == expected_count,
        )
        check(
            f"imported GitHub source {source_plugin} IDs are unique",
            conn.execute(
                "select count(*) from mock_questions where source_plugin=? and question_type=?",
                (source_plugin, expected_type),
            ).fetchone()[0]
            == conn.execute(
                "select count(distinct source_question_id) from mock_questions where source_plugin=? and question_type=?",
                (source_plugin, expected_type),
            ).fetchone()[0],
        )
    check(
        "personality quick/full modes are separated",
        conn.execute("select count(*) from mock_questions where question_type='personality' and assessment_kind='career-personality-v1'").fetchone()[0] == 15
        and conn.execute("select count(*) from mock_questions where question_type='personality' and assessment_kind='career-personality-ipip-neo-120'").fetchone()[0] == 120,
    )
    jd_sample = conn.execute(
        "select id, company_name, job_title, category, responsibilities, requirements, english_req from jobs where id=42"
    ).fetchone()
    check(
        "JD mapper selects software-testing track",
        jd_sample is not None and infer_assessment_profile(jd_sample)["tracks"][0]["track_id"] == "software-testing-ops",
    )
    targeted_tracks = _job_question_tracks(conn, 42)
    targeted_count = conn.execute(
        "select count(*) from mock_questions where question_type='choice' and company_tags like ?",
        ("%software-testing-ops%",),
    ).fetchone()[0]
    all_choice_count = conn.execute("select count(*) from mock_questions where question_type='choice'").fetchone()[0]
    check(
        "JD-targeted exam scope is available",
        targeted_tracks == ["software-testing-ops"] and 0 < targeted_count < all_choice_count,
    )
    conn.close()

    manager = get_plugin_manager()
    manifests = manager.discover()
    check("plugin manifests discoverable", {m.plugin_id for m in manifests} >= {"judge0", "exameow", "open-quiz-commons", "careerdesk", "careersail", "career-ops", "deepinterview", "openai-compatible-interview", "github-project-scout"})
    old = os.environ.get("CAREER_OS_PLUGINS")
    os.environ["CAREER_OS_PLUGINS"] = "exameow,careerdesk"
    try:
        check("question_bank capability resolves", manager.capability("question_bank").__class__.__name__ == "QuestionBankAdapter")
        check("job_source capability resolves", manager.capability("job_source").__class__.__name__ == "JobSourceAdapter")
    finally:
        if old is None:
            os.environ.pop("CAREER_OS_PLUGINS", None)
        else:
            os.environ["CAREER_OS_PLUGINS"] = old

    runner = TrustedLocalRunner()
    result = runner.run("def answer(value):\n    return value + 1", [{"input": 1, "expected": 2}])
    check("trusted local runner executes in subprocess", result.passed)
    strong = score_answer("项目", "首先我负责项目实现，使用 Python Linux SQLite MQTT，做了测试、监控、回滚和指标验证。")
    weak = score_answer("项目", "不知道")
    check("interview score is answer-dependent", strong["overall"] > weak["overall"])
    personality = score_personality(
        [
            {"id": 1, "dimension": "执行与可靠性", "scale_min": 1, "scale_max": 5, "reverse_scored": 0},
            {"id": 2, "dimension": "执行与可靠性", "scale_min": 1, "scale_max": 5, "reverse_scored": 1},
            {"id": 3, "dimension": "协作与沟通", "scale_min": 1, "scale_max": 5, "reverse_scored": 0},
        ],
        [5, 1, 3],
    )
    check("personality scoring handles reverse items", personality["dimensions"]["执行与可靠性"]["score"] == 100)
    check("personality scoring returns safe disclaimer", "不是心理疾病筛查" in personality["disclaimer"])
    check("question adapter normalizes single choice", QuestionBankAdapter._normalize({"id": "x", "type": "single", "title": "题目", "answer": "A"}, 1)["question_type"] == "choice")
    check("question adapter normalizes personality scale", QuestionBankAdapter._normalize({"id": "p", "type": "likert", "title": "工作题", "dimension": "协作与沟通", "reverse": True}, 1)["question_type"] == "personality")
    check("job adapter requires company and title", JobSourceAdapter._normalize({"company": "示例", "title": "运维"}, 1)["company_name"] == "示例")

    header = "日期\t公司名称\t目标岗位\t目标城市\t薪资范围\t企业官网\t校招网申直达链接\t当前状态\t战略定位与项目匹配备注"
    check("tracker has canonical-v2 header", header in (ROOT / "data" / "tracker.tsv").read_text(encoding="utf-8"))
    check("database path is inside project", ROOT in DB_PATH.parents)
    print("Runtime smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
