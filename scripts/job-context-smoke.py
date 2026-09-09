#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JobContext 契约冒烟：硬门槛抽取、归一化、ATS --job-context 读入。"""
from __future__ import annotations

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from services.job_context import extract_hard_filters, load_context_file, to_jd_info  # noqa: E402


def check(label: str, cond: bool) -> None:
    if not cond:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def main() -> int:
    filters = extract_hard_filters(
        "运维工程师（苏州）2027届",
        "本科及以上，可实习6个月，英语四级，工作地点苏州、上海。熟悉 Linux Docker。",
    )
    check("抽出 2027届", "2027届" in filters["graduation_cohorts"])
    check("抽出本科", "本科" in filters["education"])
    check("抽出苏州", "苏州" in filters["cities"])
    check("抽出实习月数", filters["internship_months_min"] == 6)
    check("抽出英语四级", "CET-4" in filters["english"])

    payload = {
        "version": "1.0",
        "captured_at": "2026-09-09T00:00:00Z",
        "url": "https://example.zhiye.com/job/1",
        "host": "example.zhiye.com",
        "company": "示例公司",
        "title": "运维工程师",
        "jd_text": "负责 Linux Docker Nginx 运维与排障。本科 2027届。",
        "form_schema": [
            {"label": "姓名", "required": True, "slot": "universal.personal.name"},
            {"label": "自我评价", "required": False, "slot": "application.self_evaluation"},
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        path = fh.name
    ctx = load_context_file(path)
    os.remove(path)
    check("归一化后有 Linux 关键词", "Linux" in ctx["keywords"])
    jd = to_jd_info(ctx)
    check("to_jd_info 含岗位名", jd["title"] == "运维工程师")
    check("to_jd_info 含 JD 正文", "Docker" in jd["full_text"])
    print("[OK] job-context-smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
