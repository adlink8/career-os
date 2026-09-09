#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本机接收器：扩展把 JobContext POST 到 127.0.0.1:18765，写入项目目录
data/job_discovery/captures/，并入库 job_page_contexts。
"""
from __future__ import annotations

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(ROOT / "bin"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from career_os_store import get_db  # noqa: E402
from services.job_context import normalize_context, save_context  # noqa: E402

PORT = 18765
CAPTURE_DIR = ROOT / "data" / "job_discovery" / "captures"


def _filename(ctx: dict) -> str:
    host = re.sub(r"[^a-zA-Z0-9.-]", "_", str(ctx.get("host") or "job"))
    stamp = (
        str(ctx.get("captured_at") or "")
        .replace(":", "-")
        .replace(".", "-")
        .replace("Z", "")[:19]
        or "now"
    )
    return f"job-context-{host}-{stamp}.json"


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/health":
            self.send_error(404)
            return
        body = json.dumps(
            {"ok": True, "dir": str(CAPTURE_DIR), "project": str(ROOT)},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/job-context":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            ctx = normalize_context(payload)
        except Exception as exc:
            msg = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(400)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return

        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DIR / _filename(ctx)
        path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        row_id = None
        try:
            conn = get_db()
            try:
                row_id = save_context(conn, ctx)
            finally:
                conn.close()
        except Exception as exc:
            print("[warn] 入库失败:", exc)

        result = {
            "ok": True,
            "path": str(path),
            "id": row_id,
            "title": ctx.get("title") or "",
        }
        print("[OK]", result["path"])
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("[job-context] " + (format % args) + "\n")


def main() -> int:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"JobContext 接收器: http://127.0.0.1:{PORT}")
    print(f"写入目录: {CAPTURE_DIR}")
    print("保持本窗口运行。扩展捕获时会自动 POST 到这里。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
