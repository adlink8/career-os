#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chrome/Edge Native Messaging host：把 JobContext 写进项目 captures 目录。不走 HTTP，不受系统代理影响。"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(ROOT / "bin"))

CAPTURE_DIR = ROOT / "data" / "job_discovery" / "captures"
LOG_DIR = ROOT / "data" / "job_discovery" / "logs"
PROFILE_JSON = ROOT / "extensions" / "ats-autofill" / "profile.json"
FIELD_RULES_JSON = ROOT / "extensions" / "ats-autofill" / "field-map-rules.json"

if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def read_message() -> dict | None:
    raw_len = sys.stdin.buffer.read(4)
    if not raw_len or len(raw_len) < 4:
        return None
    n = struct.unpack("<I", raw_len)[0]
    body = sys.stdin.buffer.read(n)
    return json.loads(body.decode("utf-8"))


def send_message(payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(blob)))
    sys.stdout.buffer.write(blob)
    sys.stdout.buffer.flush()


def filename_for(ctx: dict) -> str:
    host = re.sub(r"[^a-zA-Z0-9.-]", "_", str(ctx.get("host") or "job"))
    stamp = (
        str(ctx.get("captured_at") or "")
        .replace(":", "-")
        .replace(".", "-")
        .replace("Z", "")[:19]
        or "now"
    )
    return f"job-context-{host}-{stamp}.json"


def append_log(event: dict) -> str:
    from datetime import datetime, timezone

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = LOG_DIR / f"runtime-{day}.jsonl"
    if "ts" not in event:
        event["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    latest = LOG_DIR / "runtime-latest.json"
    latest.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def save(ctx: dict) -> str:
    from services.job_context import latest_context, save_context, write_capture_file
    from career_os_store import get_db

    conn = get_db()
    try:
        save_context(conn, ctx)
        merged = latest_context(conn) or ctx
    finally:
        conn.close()
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    stamp_path = CAPTURE_DIR / filename_for(merged)
    stamp_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    canonical = write_capture_file(merged, CAPTURE_DIR)
    return str(canonical)


def main() -> int:
    msg = read_message()
    if not msg:
        send_message({"ok": False, "error": "empty native message"})
        return 1
    action = str(msg.get("action") or "save")
    try:
        if action == "get_profile":
            if not PROFILE_JSON.exists():
                send_message({"ok": False, "error": f"missing {PROFILE_JSON}"})
                return 1
            data = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
            rules = []
            if FIELD_RULES_JSON.exists():
                rules = json.loads(FIELD_RULES_JSON.read_text(encoding="utf-8"))
            send_message({
                "ok": True,
                "data": data,
                "field_rules": rules,
                "path": str(PROFILE_JSON),
            })
            return 0
        if action in ("log", "append_log"):
            event = msg.get("event")
            if not isinstance(event, dict):
                send_message({"ok": False, "error": "missing event"})
                return 1
            path = append_log(event)
            send_message({"ok": True, "path": path})
            return 0
        ctx = msg.get("context")
        if not isinstance(ctx, dict):
            send_message({"ok": False, "error": "missing context"})
            return 1
        path = save(ctx)
        send_message({"ok": True, "path": path})
        return 0
    except Exception as exc:
        send_message({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
