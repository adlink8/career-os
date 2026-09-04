"""Verify the real HTTP path of the opt-in OpenAI-compatible interview plugin.

The test starts a local fake ``/chat/completions`` endpoint, so it proves the
request/response contract without credentials, paid traffic, or internet.
"""

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
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data" / "career_jobs.sqlite"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeLLMHandler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self):  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        request = json.loads(body.decode("utf-8"))
        assert request["messages"] and request["model"]
        type(self).calls += 1
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "technical": 86,
                                "expression": 84,
                                "project": 82,
                                "follow_up": 80,
                                "overall": 84,
                                "focus": "补充量化项目证据",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        return


def _run_interview(db_path: Path, *, endpoint: str | None):
    os.environ["CAREER_OS_DB_PATH"] = str(db_path)
    os.environ["CAREER_OS_PLUGINS"] = "openai-compatible-interview"
    if endpoint is None:
        os.environ.pop("CAREER_OS_LLM_BASE_URL", None)
    else:
        os.environ["CAREER_OS_LLM_BASE_URL"] = endpoint
    os.environ["CAREER_OS_LLM_MODEL"] = "fake-model"
    from bin.mock_interview_agent import run_mock_interview

    conn = sqlite3.connect(db_path)
    company_id = conn.execute("SELECT company_id FROM jobs WHERE id=17").fetchone()[0]
    conn.close()
    answer = "我会先复现，再用日志和测试定位，最后给出指标、取舍、回滚与回归验证。"
    with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()):
        assert run_mock_interview(str(company_id), job_id=17)


def main() -> int:
    previous = {key: os.environ.get(key) for key in ("CAREER_OS_DB_PATH", "CAREER_OS_PLUGINS", "CAREER_OS_LLM_BASE_URL", "CAREER_OS_LLM_MODEL")}
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeLLMHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="career-os-openai-agent-") as tmp:
                db_path = Path(tmp) / "career_jobs.sqlite"
                shutil.copy2(SOURCE_DB, db_path)
                endpoint = f"http://127.0.0.1:{server.server_port}/v1"
                _run_interview(db_path, endpoint=endpoint)
                conn = sqlite3.connect(db_path)
                row = conn.execute(
                    "SELECT provider, rubric_version, qa_transcript_json FROM mock_interview_reports WHERE job_id=17 ORDER BY id DESC LIMIT 1"
                ).fetchone()
                conn.close()
                assert row and row[0] == "openai-compatible", row
                assert json.loads(row[2])["context"]["external_service"] is True
                assert FakeLLMHandler.calls > 0, FakeLLMHandler.calls
                print(f"PASS real HTTP provider path: {FakeLLMHandler.calls} local chat/completions calls")

                _run_interview(db_path, endpoint=None)
                conn = sqlite3.connect(db_path)
                fallback = conn.execute(
                    "SELECT provider, qa_transcript_json FROM mock_interview_reports WHERE job_id=17 ORDER BY id DESC LIMIT 1"
                ).fetchone()
                conn.close()
                context = json.loads(fallback[1])["context"]
                assert fallback[0] == "local-rubric", fallback
                assert "CAREER_OS_LLM_BASE_URL" in context.get("plugin_fallback_reason", ""), context
                print("PASS no-endpoint safety: plugin falls back to local-rubric without network")
                print("PASS temporary DB only; no credentials or paid endpoint used")
        finally:
            server.shutdown()
            server.server_close()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
