"""隔离验证 interview_agent 插件加载与四方法契约。

脚本只在临时 manifest 目录中运行，不打开也不写入 Career OS 主数据库。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_plugins import PluginManager
from bin.career_os_store import DB_PATH
from bin.jd_assessment_mapper import infer_assessment_profile


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(folder: Path, plugin_id: str, entrypoint: str) -> None:
    target = folder / plugin_id / "plugin.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "id": plugin_id,
                "name": plugin_id,
                "version": "smoke",
                "capabilities": ["interview_agent"],
                "entrypoint": entrypoint,
                "enabled_by_default": False,
                "license": "Apache-2.0",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    before = _digest(DB_PATH)
    previous = os.environ.get("CAREER_OS_PLUGINS")
    previous_db = os.environ.get("CAREER_OS_DB_PATH")
    try:
        with tempfile.TemporaryDirectory(prefix="career-os-interview-plugin-") as temp:
            temp_root = Path(temp)
            plugin_root = temp_root / "plugins"
            temp_db = temp_root / "career_jobs.sqlite"
            shutil.copy2(DB_PATH, temp_db)
            os.environ["CAREER_OS_DB_PATH"] = str(temp_db)
            _manifest(plugin_root, "broken-agent", "plugins.does_not_exist.adapter:create_plugin")
            _manifest(plugin_root, "deepinterview", "plugins.deepinterview.adapter:create_plugin")
            os.environ["CAREER_OS_PLUGINS"] = "broken-agent,deepinterview"

            manager = PluginManager(root=plugin_root)
            adapter = manager.capability("interview_agent")
            assert adapter is not None, "enabled interview_agent capability did not resolve"
            assert all(callable(getattr(adapter, method, None)) for method in ("prepare", "questions", "score", "report"))

            profile = infer_assessment_profile(
                {
                    "id": 42,
                    "company_name": "Smoke Co",
                    "job_title": "C/RTOS 嵌入式工程师",
                    "category": "物联网/嵌入式",
                    "responsibilities": "负责 C、FreeRTOS、MQTT、UART 和固件调试",
                    "requirements": "熟悉嵌入式系统、通信协议和硬件调试",
                    "english_req": "",
                }
            )
            prepared = adapter.prepare(
                job={"id": 42, "company_name": "Smoke Co", "job_title": "运维工程师"},
                guide={"typical_questions": "1. 请介绍一次线上故障排查。\n2. 如何保证变更安全？"},
                profile=profile,
            )
            assert prepared["tracks"][0]["track_id"] == "iot-embedded"
            assert prepared["tracks"][0]["label"] == "物联网 / 嵌入式"
            questions = adapter.questions(prepared, limit=4)
            assert len(questions) == 4, f"expected four questions, got {len(questions)}"
            assert any(
                item["source_plugin"] in {"github-ather-rag-interview", "github-seringhong-embedded-interview"}
                for item in questions
            )
            assert any(item["source"] == "mock_questions" for item in questions)
            connection = sqlite3.connect(f"{temp_db.resolve().as_uri()}?mode=ro", uri=True)
            try:
                for item in questions:
                    for key in ("source_plugin", "source_question_id", "question_type", "category", "family"):
                        assert item.get(key), (item, key)
                    if item["source"] == "mock_questions":
                        assert connection.execute(
                            "SELECT 1 FROM mock_questions WHERE source_plugin=? AND source_question_id=?",
                            (item["source_plugin"], item["source_question_id"]),
                        ).fetchone(), item
            finally:
                connection.close()
            answer = "首先我负责定位 Linux 日志和 Docker 指标，然后复现并测试变更，最后验证回滚和线上延迟，复盘结果。"
            score = adapter.score(prepared, questions[0], answer)
            assert isinstance(score.get("overall"), int)
            assert score["provider"] == "deepinterview-local-compat"
            assert score["scoring_engine"] == "local-rubric" and score["external_service"] is False
            report = adapter.report(prepared, [{"question": questions[0], "answer": answer, "score": score}])
            assert report["turn_count"] == 1 and report["average_score"] is not None
            assert report["provider"] == "deepinterview-local-compat"
            assert report["scoring_engine"] == "local-rubric" and report["external_service"] is False

            ai_manifest = plugin_root / "ai-mock-interviewer" / "plugin.json"
            ai_manifest.parent.mkdir(parents=True)
            ai_manifest.write_text(
                json.dumps(
                    {
                        "id": "ai-mock-interviewer",
                        "name": "ai-mock-interviewer",
                        "version": "smoke",
                        "capabilities": ["interview_agent", "question_bank"],
                        "entrypoint": "plugins.ai_mock_interviewer.adapter:create_plugin",
                        "enabled_by_default": False,
                        "license": "MIT",
                    }
                ),
                encoding="utf-8",
            )
            os.environ["CAREER_OS_PLUGINS"] = "broken-agent,ai-mock-interviewer"
            ai_manager = PluginManager(root=plugin_root)
            ai_adapter = ai_manager.capability("interview_agent", preferred="ai-mock-interviewer")
            assert ai_adapter is not None
            assert ai_manager.capability("question_bank", preferred="ai-mock-interviewer") is not None

            print("PASS interview_agent capability resolves")
            print("PASS broken plugin isolated and valid plugin still resolves")
            print("PASS prepare/questions/score/report contract")
            print("PASS ai-mock-interviewer interview_agent/question_bank capabilities")
            print("PASS temporary execution does not use main database")
    finally:
        if previous is None:
            os.environ.pop("CAREER_OS_PLUGINS", None)
        else:
            os.environ["CAREER_OS_PLUGINS"] = previous
        if previous_db is None:
            os.environ.pop("CAREER_OS_DB_PATH", None)
        else:
            os.environ["CAREER_OS_DB_PATH"] = previous_db
    after = _digest(DB_PATH)
    if before != after:
        print("FAIL main database changed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
