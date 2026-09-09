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
from services.job_context import (  # noqa: E402
    latest_context,
    load_context_file,
    save_context,
    write_capture_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest JobContext JSON from the autofill extension")
    parser.add_argument("json_paths", nargs="+", help="一份或多份 JobContext JSON；同一 jobAdId 会合流")
    args = parser.parse_args()
    conn = get_db()
    row_id = None
    last_path = args.json_paths[-1]
    try:
        for path in args.json_paths:
            ctx = load_context_file(path)
            row_id = save_context(conn, ctx)
            last_path = path
        ctx = latest_context(conn) or ctx
        merged_path = write_capture_file(ctx)
    finally:
        conn.close()
    stats = ctx.get("stats") or {}
    print("[OK] 已入库 job_page_contexts id={}".format(row_id))
    print("  岗位: {} · {}".format(ctx.get("company") or "—", ctx.get("title") or "—"))
    print("  jobAdId: {}".format(ctx.get("job_ad_id") or "—"))
    print("  URL: {}".format(ctx.get("url") or "—"))
    print("  合流文件: {}".format(merged_path))
    print("  JD 字数: {} | 表单字段: {} | 已映射: {}".format(
        stats.get("jd_chars", 0), stats.get("form_fields", 0), stats.get("mapped_fields", 0)
    ))
    print("  硬门槛: {}".format(json.dumps(ctx.get("hard_filters") or {}, ensure_ascii=False)))
    print("  关键词: {}".format("、".join(ctx.get("keywords") or []) or "（词典未命中）"))
    print("ATS: python bin/ats_matcher.py --resume <简历> --job-context \"{}\"".format(merged_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
