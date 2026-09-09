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

from services.job_context import (  # noqa: E402
    extract_hard_filters,
    extract_job_ad_id,
    load_context_file,
    merge_contexts,
    to_jd_info,
)


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

    detail = {
        "url": "https://leadchina.zhiye.com/campus/detail?jobAdId=ec6ce6c4-501d-476f-a63c-e23285b7b5ce",
        "title": "无锡先导智能装备股份有限公司",
        "jd_text": "集团战略管培生-项目运营（2027届校招）\n工作职责\n参与项目全周期管理\n任职资格\n硕士及以上学历，26、27年毕业",
        "form_schema": [{"label": "搜索职位关键词", "type": "text", "slot": ""}],
    }
    form = {
        "url": "https://leadchina.zhiye.com/form?fromPage=job&jobAdId=ec6ce6c4-501d-476f-a63c-e23285b7b5ce",
        "title": "无锡先导智能装备股份有限公司",
        "jd_text": "你正在投递职位: 集团战略管培生-项目运营（2027届校招）\n姓名\n预览并提交\nCareer OS 填表",
        "form_schema": [
            {"label": "请输入 姓名", "type": "text", "slot": ""},
            {"label": "请输入 项目名称", "type": "text", "slot": "application.projects.name"},
        ],
    }
    merged = merge_contexts(form, detail)
    check("合流保留详情页职责", "工作职责" in merged["jd_text"])
    check("合流不把报名页当 JD", "预览并提交" not in merged["jd_text"])
    check("合流保留报名表格子", any(f.get("label") == "请输入 姓名" for f in merged["form_schema"]))
    check("合流抽出硕士门槛", "硕士" in merged["hard_filters"]["education"])
    check("合流 title 用岗位名", "管培生" in merged["title"])
    check(
        "moka hash 抽出 job id",
        extract_job_ad_id(
            "https://app.mokahr.com/apply/focus/148405#/job/d96fd833-7473-49fa-a959-171412a34bee/apply"
        )
        == "d96fd833-7473-49fa-a959-171412a34bee",
    )
    print("[OK] job-context-smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
