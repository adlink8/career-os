#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把扩展捕获的 JobContext JSON 写入 data/career_jobs.sqlite。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(ROOT / "bin"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from career_os_store import get_db  # noqa: E402
from services.job_context import load_context_file, save_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest JobContext JSON from the autofill extension")
    parser.add_argument("json_path", help="扩展导出的 job-context JSON 路径")
    args = parser.parse_args()
    ctx = load_context_file(args.json_path)
    conn = get_db()
    try:
        row_id = save_context(conn, ctx)
    finally:
        conn.close()
    stats = ctx.get("stats") or {}
    print("[OK] 已入库 job_page_contexts id={}".format(row_id))
    print("  岗位: {} · {}".format(ctx.get("company") or "—", ctx.get("title") or "—"))
    print("  URL: {}".format(ctx.get("url") or "—"))
    print("  JD 字数: {} | 表单字段: {} | 已映射: {}".format(
        stats.get("jd_chars", 0), stats.get("form_fields", 0), stats.get("mapped_fields", 0)
    ))
    print("  硬门槛: {}".format(json.dumps(ctx.get("hard_filters") or {}, ensure_ascii=False)))
    print("  关键词: {}".format("、".join(ctx.get("keywords") or []) or "（词典未命中）"))
    print("ATS: python bin/ats_matcher.py --resume <简历> --job-context \"{}\"".format(args.json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
