#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JobContext：网申页快照契约。扩展产出 JSON，本模块解析、补关键词、入库。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

CONTEXT_VERSION = "1.0"

_CITIES = (
    "上海", "苏州", "无锡", "南京", "杭州", "深圳", "北京", "常州",
    "宁波", "合肥", "武汉", "成都", "广州", "天津", "青岛", "厦门",
)

try:
    from .tech_lexicon import extract_keywords_from_jd
except (ImportError, ValueError):
    from services.tech_lexicon import extract_keywords_from_jd


def extract_hard_filters(title: str, jd_text: str) -> Dict[str, Any]:
    blob = f"{title or ''}\n{jd_text or ''}"
    cohorts = list(dict.fromkeys(re.findall(r"20\d{2}届", blob)))
    education = [k for k in ("博士", "硕士", "本科", "大专") if k in blob]
    cities = [c for c in _CITIES if c in blob]
    intern_m = re.search(r"实习\s*(\d+)\s*(?:个)?月", blob)
    english = []
    if re.search(r"CET-?6|英语六级|六级", blob, re.I):
        english.append("CET-6")
    elif re.search(r"CET-?4|英语四级|四级", blob, re.I):
        english.append("CET-4")
    if re.search(r"雅思|IELTS", blob, re.I):
        english.append("IELTS")
    if re.search(r"托福|TOEFL", blob, re.I):
        english.append("TOEFL")
    return {
        "graduation_cohorts": cohorts,
        "education": education,
        "cities": cities,
        "internship_months_min": int(intern_m.group(1)) if intern_m else None,
        "english": english,
        "mentions_intern": bool(re.search(r"实习", title or "") or re.search(r"实习生", blob[:400])),
        "mentions_full_time": "全职" in blob or "校招" in blob,
    }


def normalize_context(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = str(raw.get("title") or "").strip()
    jd_text = str(raw.get("jd_text") or "").strip()
    filters = raw.get("hard_filters") if isinstance(raw.get("hard_filters"), dict) else {}
    merged_filters = extract_hard_filters(title, jd_text)
    merged_filters.update({k: v for k, v in filters.items() if v not in (None, [], "")})
    keywords = raw.get("keywords") if isinstance(raw.get("keywords"), list) else []
    if jd_text:
        keywords = sorted(extract_keywords_from_jd(jd_text))
    form_schema = raw.get("form_schema") if isinstance(raw.get("form_schema"), list) else []
    return {
        "version": CONTEXT_VERSION,
        "captured_at": str(raw.get("captured_at") or ""),
        "url": str(raw.get("url") or "").strip(),
        "host": str(raw.get("host") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "title": title,
        "jd_text": jd_text,
        "hard_filters": merged_filters,
        "keywords": keywords,
        "form_schema": form_schema,
        "stats": {
            "jd_chars": len(re.sub(r"\s+", "", jd_text)),
            "form_fields": len(form_schema),
            "required_fields": sum(1 for f in form_schema if f.get("required")),
            "mapped_fields": sum(1 for f in form_schema if f.get("slot")),
        },
    }


def load_context_file(path: str | Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JobContext 必须是 JSON 对象")
    ctx = normalize_context(data)
    if not ctx["url"] and not ctx["title"] and not ctx["jd_text"]:
        raise ValueError("JobContext 缺少 url/title/jd_text")
    return ctx


def to_jd_info(ctx: Dict[str, Any]) -> Dict[str, str]:
    title = ctx.get("title") or "页面捕获岗位"
    jd = ctx.get("jd_text") or ""
    company = ctx.get("company") or ""
    return {
        "company": company,
        "title": title,
        "full_text": f"{title}\n{company}\n{jd}".strip(),
    }


def save_context(conn, ctx: Dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO job_page_contexts (
            captured_at, url, host, company, title, jd_text,
            hard_filters_json, keywords_json, form_schema_json, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ctx.get("captured_at") or "",
            ctx.get("url") or "",
            ctx.get("host") or "",
            ctx.get("company") or "",
            ctx.get("title") or "",
            ctx.get("jd_text") or "",
            json.dumps(ctx.get("hard_filters") or {}, ensure_ascii=False),
            json.dumps(ctx.get("keywords") or [], ensure_ascii=False),
            json.dumps(ctx.get("form_schema") or [], ensure_ascii=False),
            json.dumps(ctx, ensure_ascii=False),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def latest_context(conn) -> Dict[str, Any] | None:
    row = conn.execute(
        "SELECT raw_json FROM job_page_contexts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    raw = row["raw_json"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
    return json.loads(raw)
