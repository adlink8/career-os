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


_JOB_AD_RE = re.compile(r"jobAdId=([0-9a-fA-F-]{8,})", re.I)
_MOKA_JOB_RE = re.compile(r"[#/]job/([0-9a-fA-F-]{8,})", re.I)
_JD_MARKERS = re.compile(r"工作职责|任职资格|任职要求|岗位职责|职位描述")
_FORM_MARKERS = re.compile(r"你正在投递职位|预览并提交|上传简历|职位申请|Career OS 填表")


def extract_job_ad_id(url: str) -> str:
    m = _JOB_AD_RE.search(url or "")
    if m:
        return m.group(1).lower()
    m = _MOKA_JOB_RE.search(url or "")
    return m.group(1).lower() if m else ""


def looks_like_jd(text: str) -> bool:
    return bool(_JD_MARKERS.search(text or ""))


def looks_like_form_page(text: str) -> bool:
    return bool(_FORM_MARKERS.search(text or ""))


def refine_title(ctx: Dict[str, Any]) -> str:
    jd = ctx.get("jd_text") or ""
    blob = f"{ctx.get('title') or ''}\n{jd}"
    m = re.search(r"【优先】\s*([^\n]+)", blob)
    if m:
        return m.group(1).strip()[:160]
    m = re.search(r"你正在投递职位[:：]\s*([^\n]+)", jd)
    if m:
        return m.group(1).strip()[:160]
    first = jd.strip().split("\n")[0].strip() if jd.strip() else ""
    if (
        first
        and "有限公司" not in first
        and first not in ("首页", "校园招聘")
        and len(first) < 80
        and not re.match(r"负责|具备|熟悉|参与|协助|基于|岗位职责|任职要求|任职资格|职位描述|工作职责", first)
        and re.search(r"工程师|实习|管培|专员|经理|开发|运维|支持|助理", first)
    ):
        return first
    return str(ctx.get("title") or "").strip()


def pick_jd_text(a: str, b: str) -> str:
    a = a or ""
    b = b or ""
    qa, qb = looks_like_jd(a), looks_like_jd(b)
    fa, fb = looks_like_form_page(a), looks_like_form_page(b)
    if qb and not qa:
        return b
    if qa and not qb:
        return a
    if qa and qb:
        return b if len(b) >= len(a) else a
    if fa and not fb:
        return b or a
    if fb and not fa:
        return a or b
    return b if len(b) >= len(a) else a


def merge_form_schema(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[tuple, Dict[str, Any]] = {}
    order: List[tuple] = []
    for src in list(left or []) + list(right or []):
        if not isinstance(src, dict):
            continue
        key = (
            str(src.get("type") or ""),
            str(src.get("label") or "").strip(),
            str(src.get("name") or ""),
            str(src.get("id") or ""),
            str(src.get("frame") or ""),
        )
        if key not in merged:
            merged[key] = dict(src)
            order.append(key)
        elif src.get("slot") and not merged[key].get("slot"):
            merged[key] = dict(src)
    return [merged[k] for k in order]


def merge_contexts(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """同一岗位：详情页贡献 JD，报名页贡献表单格子。"""
    a = dict(base or {})
    b = dict(incoming or {})
    jd_text = pick_jd_text(str(a.get("jd_text") or ""), str(b.get("jd_text") or ""))
    urls = []
    for u in (a.get("url"), b.get("url")):
        if u and u not in urls:
            urls.append(u)
    detail_url = next((u for u in urls if "/detail" in u or "/campus/" in u), "")
    form_url = next((u for u in urls if "/form" in u), "")
    title_src = {
        "title": a.get("title") or b.get("title") or "",
        "jd_text": "\n".join(
            [str(a.get("title") or ""), str(b.get("title") or ""), str(a.get("jd_text") or ""), str(b.get("jd_text") or "")]
        ),
    }
    merged = {
        "version": CONTEXT_VERSION,
        "captured_at": max(str(a.get("captured_at") or ""), str(b.get("captured_at") or "")),
        "url": detail_url or form_url or str(b.get("url") or a.get("url") or ""),
        "form_url": form_url,
        "urls": urls,
        "host": str(b.get("host") or a.get("host") or ""),
        "company": str(a.get("company") or b.get("company") or "").strip(),
        "title": refine_title(title_src),
        "jd_text": jd_text,
        "form_schema": merge_form_schema(a.get("form_schema") or [], b.get("form_schema") or []),
        "job_ad_id": extract_job_ad_id(str(b.get("url") or ""))
        or extract_job_ad_id(str(a.get("url") or "")),
    }
    if not merged["company"] and "有限公司" in str(a.get("title") or b.get("title") or ""):
        merged["company"] = str(a.get("title") or b.get("title") or "").strip()
    return normalize_context(merged)


def extract_hard_filters(title: str, jd_text: str) -> Dict[str, Any]:
    blob = f"{title or ''}\n{jd_text or ''}"
    cohorts = list(dict.fromkeys(re.findall(r"20\d{2}届", blob)))
    for y in re.findall(r"(?<!\d)(2[0-9])(?=届|年毕业)", blob):
        cohorts.append(f"20{y}届")
    pair = re.search(r"(?<!\d)(2[0-9])[、,/](2[0-9])年毕业", blob)
    if pair:
        cohorts.extend([f"20{pair.group(1)}届", f"20{pair.group(2)}届"])
    cohorts = list(dict.fromkeys(cohorts))
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
    jd_text = str(raw.get("jd_text") or "").strip()
    title = refine_title({"title": str(raw.get("title") or "").strip(), "jd_text": jd_text})
    job_ad_id = str(raw.get("job_ad_id") or extract_job_ad_id(str(raw.get("url") or "")))
    # 硬门槛只从最终 JD/标题重算，避免报名页「学历=本科」污染详情页「硕士及以上」
    merged_filters = extract_hard_filters(title, jd_text)
    keywords = sorted(extract_keywords_from_jd(jd_text)) if jd_text else []
    form_schema = raw.get("form_schema") if isinstance(raw.get("form_schema"), list) else []
    return {
        "version": CONTEXT_VERSION,
        "captured_at": str(raw.get("captured_at") or ""),
        "url": str(raw.get("url") or "").strip(),
        "form_url": str(raw.get("form_url") or "").strip(),
        "urls": raw.get("urls") if isinstance(raw.get("urls"), list) else [],
        "job_ad_id": job_ad_id,
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


def _row_payload(ctx: Dict[str, Any]) -> tuple:
    return (
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
        ctx.get("job_ad_id") or "",
    )


def find_context_by_job_ad(conn, job_ad_id: str) -> Dict[str, Any] | None:
    if not job_ad_id:
        return None
    row = conn.execute(
        """
        SELECT id, raw_json FROM job_page_contexts
        WHERE job_ad_id = ? OR url LIKE ? OR raw_json LIKE ?
        ORDER BY id DESC LIMIT 1
        """,
        (job_ad_id, f"%jobAdId={job_ad_id}%", f"%{job_ad_id}%"),
    ).fetchone()
    if not row:
        return None
    raw = row["raw_json"] if hasattr(row, "keys") else row[1]
    data = json.loads(raw)
    data["_row_id"] = int(row["id"] if hasattr(row, "keys") else row[0])
    return data


def save_context(conn, ctx: Dict[str, Any]) -> int:
    ctx = normalize_context(ctx)
    job_ad_id = ctx.get("job_ad_id") or ""
    existing = find_context_by_job_ad(conn, job_ad_id) if job_ad_id else None
    if existing:
        ctx = merge_contexts(existing, ctx)
        row_id = int(existing["_row_id"])
        cols = {r[1] for r in conn.execute("PRAGMA table_info(job_page_contexts)")}
        if "job_ad_id" in cols:
            conn.execute(
                """
                UPDATE job_page_contexts SET
                    captured_at=?, url=?, host=?, company=?, title=?, jd_text=?,
                    hard_filters_json=?, keywords_json=?, form_schema_json=?, raw_json=?,
                    job_ad_id=?
                WHERE id=?
                """,
                _row_payload(ctx) + (row_id,),
            )
        else:
            conn.execute(
                """
                UPDATE job_page_contexts SET
                    captured_at=?, url=?, host=?, company=?, title=?, jd_text=?,
                    hard_filters_json=?, keywords_json=?, form_schema_json=?, raw_json=?
                WHERE id=?
                """,
                _row_payload(ctx)[:-1] + (row_id,),
            )
        conn.commit()
        return row_id

    cols = {r[1] for r in conn.execute("PRAGMA table_info(job_page_contexts)")}
    if "job_ad_id" in cols:
        cur = conn.execute(
            """
            INSERT INTO job_page_contexts (
                captured_at, url, host, company, title, jd_text,
                hard_filters_json, keywords_json, form_schema_json, raw_json, job_ad_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _row_payload(ctx),
        )
    else:
        cur = conn.execute(
            """
            INSERT INTO job_page_contexts (
                captured_at, url, host, company, title, jd_text,
                hard_filters_json, keywords_json, form_schema_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _row_payload(ctx)[:-1],
        )
    conn.commit()
    return int(cur.lastrowid)


def write_capture_file(ctx: Dict[str, Any], dest_dir: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[2]
    folder = dest_dir or (root / "data" / "job_discovery" / "captures")
    folder.mkdir(parents=True, exist_ok=True)
    host = re.sub(r"[^a-zA-Z0-9.-]", "_", str(ctx.get("host") or "job"))
    job_ad = str(ctx.get("job_ad_id") or "unknown")
    path = folder / f"job-context-{host}-{job_ad}.json"
    path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def latest_context(conn) -> Dict[str, Any] | None:
    row = conn.execute(
        "SELECT raw_json FROM job_page_contexts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    raw = row["raw_json"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
    return json.loads(raw)
