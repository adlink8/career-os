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
JOB_PROFILES_MAP_JSON = ROOT / "extensions" / "ats-autofill" / "job-profiles-map.json"

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


def match_job_profile_py(test_url: str, jobs: dict) -> dict | None:
    if not test_url or not jobs:
        return None
    from urllib.parse import urlparse

    target = str(test_url).lower()
    parsed = urlparse(test_url)
    netloc = parsed.netloc.lower()

    # 1. UUID / jobAdId match
    uuids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", target)
    if uuids:
        u = uuids[0]
        for item in jobs.values():
            if u in (item.get("url") or "").lower():
                return item

    # 1.2 moseeker pid match
    pids = re.findall(r"pid/(\d+)", test_url)
    if pids:
        p = pids[0]
        for item in jobs.values():
            if f"pid/{p}" in (item.get("url") or ""):
                return item

    # 1.3 html id match
    html_ids = re.findall(r"/(\d+/\d+\.html)", test_url)
    if html_ids:
        h = html_ids[0]
        for item in jobs.values():
            if h in (item.get("url") or ""):
                return item

    # 2. Exact or substring match
    for item in jobs.values():
        jurl = (item.get("url") or "").lower()
        if jurl and (jurl in target or target in jurl):
            return item

    # 3. Host / Domain match with keyword refinement
    if netloc:
        if "maxscend.zhiye.com" in netloc:
            if any(k in target for k in ["network", "网络", "网工"]):
                if "maxscend-network-eng" in jobs:
                    return jobs["maxscend-network-eng"]
            if any(k in target for k in ["系统应用", "系统", "sae"]):
                if "maxscend-system-app" in jobs:
                    return jobs["maxscend-system-app"]
            if bool(re.search(r"\bai\b", target)) or any(k in target for k in ["ai应用", "智能", "算法"]):
                if "maxscend-ai-app" in jobs:
                    return jobs["maxscend-ai-app"]

        if "focus" in netloc or "apply/focus" in target:
            if "7c34fb13" in target or any(k in target for k in ["数据应用", "数据开发", "大数据"]):
                if "focus-data-app" in jobs:
                    return jobs["focus-data-app"]
            if "aae64c70" in target or bool(re.search(r"\bai\b", target)) or any(k in target for k in ["ai算法", "算法"]):
                if "focus-ai-rnd" in jobs:
                    return jobs["focus-ai-rnd"]
            if any(k in target for k in ["ops", "运维", "linux"]):
                if "focus-linux-ops" in jobs:
                    return jobs["focus-linux-ops"]

        for item in jobs.values():
            jparsed = urlparse(item.get("url") or "")
            jhost = jparsed.netloc.lower()
            if jhost and (jhost == netloc or netloc.endswith("." + jhost) or jhost.endswith("." + netloc)):
                return item

    return None


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
        if action == "get_fill_payload":
            from career_os_store import get_db
            from services.apply_run import lookup_fill_payload

            rules = []
            if FIELD_RULES_JSON.exists():
                rules = json.loads(FIELD_RULES_JSON.read_text(encoding="utf-8"))
            profile = None
            if PROFILE_JSON.exists():
                profile = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
            conn = get_db()
            try:
                payload = lookup_fill_payload(
                    conn,
                    url=str(msg.get("url") or ""),
                    job_ad_id=str(msg.get("job_ad_id") or ""),
                )
            finally:
                conn.close()

            # 优先检查是否命中 27 岗位定制底稿
            if payload.get("mode") == "blocked" and JOB_PROFILES_MAP_JSON.exists():
                try:
                    job_map = json.loads(JOB_PROFILES_MAP_JSON.read_text(encoding="utf-8"))
                    matched = match_job_profile_py(str(msg.get("url") or ""), job_map)
                    if matched:
                        import copy
                        base_prof = profile or {}
                        custom_prof = copy.deepcopy(base_prof)
                        if "universal" not in custom_prof:
                            custom_prof["universal"] = {}
                        if "application" not in custom_prof:
                            custom_prof["application"] = {}
                        custom_prof["application"]["target_position"] = matched.get("target_position")
                        custom_prof["application"]["target_company"] = matched.get("company")
                        custom_prof["application"]["track"] = matched.get("track")
                        custom_prof["application"]["self_evaluation"] = matched.get("self_evaluation")
                        custom_prof["application"]["skills_summary"] = matched.get("skills_summary")
                        custom_prof["application"]["projects"] = matched.get("projects") or []

                        payload = {
                            "mode": "job_custom",
                            "custom_company": matched.get("company"),
                            "custom_title": matched.get("title"),
                            "custom_track": matched.get("track"),
                            "allow_fill": True,
                            "reason": f"已自动识别匹配校招岗位：{matched.get('company')} - {matched.get('title')}",
                            "autofill": {
                                "target_position": matched.get("target_position"),
                                "company": matched.get("company"),
                                "track": matched.get("track"),
                                "resume_path": matched.get("resume_path"),
                                "job_id": matched.get("job_id"),
                                "open_answers": [
                                    {"label": "自我评价", "value": matched.get("self_evaluation")},
                                    {"label": "专业技能", "value": matched.get("skills_summary")},
                                    {
                                        "label": "项目经验(综合)",
                                        "value": "\n\n".join([
                                            p.get("full_text") or p.get("description") or ""
                                            for p in matched.get("projects") or []
                                        ]),
                                    },
                                ],
                            },
                            "profile": custom_prof,
                            "run_id": matched.get("job_id"),
                        }
                except Exception:
                    pass

            if payload.get("mode") == "test" and profile is not None:
                payload["profile"] = profile
            elif profile is not None and "profile" not in payload:
                payload["profile"] = profile
            payload["ok"] = True
            payload["field_rules"] = rules
            send_message(payload)
            return 0
        if action == "mark_applied":
            from career_os_store import get_db
            from services.apply_run import mark_applied

            run_id = int(msg.get("run_id") or 0)
            if run_id <= 0:
                send_message({"ok": False, "error": "missing run_id"})
                return 1
            coverage = msg.get("coverage") if isinstance(msg.get("coverage"), dict) else {}
            conn = get_db()
            try:
                run = mark_applied(conn, run_id, coverage=coverage)
            finally:
                conn.close()
            send_message({"ok": True, "run_id": run["id"], "fill_coverage": run.get("fill_coverage")})
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
