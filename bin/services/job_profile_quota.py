"""按画像匹配动态定每家名额，再按 recommendation_weight 排序。

名额 = 过门禁且背景匹配达到阈值的岗位数，不写死每家 3 个。
匹配不上就 0 个，不拿弱岗凑数。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
FIT_KEEP = 50
FIT_BAND = 12  # 同一公司只留最贴近背景的一档，不拿弱岗凑数

_PRIMARY = ("运维", "技术支持", "fae", "现场应用", "交付", "linux", "devops", "sre")
_SECONDARY = ("应用工程师", "系统应用", "技术销售", "销售实习", "测试", "验证", "it工程师")
_DROP_TITLE = ("数字ic", "模拟ic", "版图", "rtl", "数字设计", "模拟设计", "固件", "嵌入式软件", "嵌入式电控")
_KEEP_WITH_DROP = ("支持", "fae", "运维", "交付", "应用")
_JS = ("南京", "苏州", "无锡", "常州", "昆山", "江苏")
_MASTER = ("硕士及以上", "硕士以上", "硕士学历", "硕博")
_YEARS = ("3年以上", "3年及以上", "5年以上", "2年以上相关")


def load_profile(path: Optional[Path] = None) -> Dict[str, Any]:
    import yaml

    p = path or (ROOT / "config" / "profile.yml")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _cities(profile: Dict[str, Any]) -> List[str]:
    ct = profile.get("career_target") or {}
    cities = [str(x) for x in (ct.get("cities") or [])]
    school = str((profile.get("education") or {}).get("school") or "")
    if "常州" in school and not any("常州" in c for c in cities):
        cities.append("常州")
    return cities


def _skills(profile: Dict[str, Any]) -> List[str]:
    sk = profile.get("skills") or {}
    out: List[str] = []
    for key in ("proficient", "familiar"):
        out.extend(str(x) for x in (sk.get(key) or []))
    return out


def _hard_master(req: str) -> bool:
    blob = req or ""
    if "本科" in blob or "本硕" in blob:
        return False
    if any(k in blob for k in _MASTER):
        return True
    return bool(re.search(r"硕士", blob) and "本科" not in blob)


def background_fit(profile: Dict[str, Any], job: Dict[str, Any]) -> Optional[int]:
    """过硬门禁后给 0-100；None 表示直接淘汰。"""
    try:
        from services.job_ingest_gate import ingest_gate_ok
    except ImportError:
        from bin.services.job_ingest_gate import ingest_gate_ok

    title = str(job.get("job_title") or job.get("title") or "")
    city = str(job.get("city") or "")
    req = str(job.get("requirements") or job.get("req") or "")
    duty = str(job.get("responsibilities") or job.get("duty") or "")
    edu = str(job.get("education_req") or "")
    blob = f"{title}\n{city}\n{edu}\n{duty}\n{req}"

    if not ingest_gate_ok(title, duty, req):
        return None
    if _hard_master(edu) or _hard_master(req):
        return None
    if any(y in (edu + req + title) for y in _YEARS):
        return None
    low_title = title.lower().replace(" ", "")
    if any(k in low_title for k in _DROP_TITLE):
        if not any(k in title for k in _KEEP_WITH_DROP):
            return None

    primary_hit = any(k.lower() in title.lower() for k in _PRIMARY)
    secondary_hit = any(k.lower() in title.lower() for k in _SECONDARY)
    if not primary_hit and not secondary_hit:
        return None

    score = 0
    if primary_hit:
        score += 30
    elif secondary_hit:
        score += 16
    if "实习" in title or "校招" in title or "2027" in title:
        score += 6
    if any(k in city for k in ("深圳", "南山", "杭州", "北京", "海淀")) and not any(
        k in city for k in _JS
    ) and "上海" not in city:
        return None
    cities = _cities(profile)
    js_hit = any(c in city or c in title for c in _JS)
    sh_hit = "上海" in city or "上海" in title
    if cities:
        if (not city.strip()) or "全国" in city:
            score += 6
        elif js_hit:
            score += 18
        elif sh_hit:
            score += 8
        elif any(c in city or c in title for c in cities):
            score += 10
        else:
            return None
    if js_hit:
        score += 4
    if "本科" in (edu + req) or not edu:
        score += 10
    major = str((profile.get("education") or {}).get("major") or "")
    if "计算机" in major and ("计算机" in blob or "软件" in req):
        score += 8
    hits = 0
    low_blob = blob.lower()
    for sk in _skills(profile):
        token = sk.split("/")[0].strip()
        if len(token) >= 2 and token.lower() in low_blob:
            hits += 1
        if hits >= 3:
            break
    score += min(hits, 3) * 4
    if "协助" in duty or "导师" in duty:
        score += 6
    return min(score, 100)


def allocate_company_slots(
    jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    *,
    keep_min: int = FIT_KEEP,
) -> List[Dict[str, Any]]:
    """名额=过阈值的岗位数；按 recommendation_weight 降序。"""
    scored: List[Dict[str, Any]] = []
    for job in jobs:
        fit = background_fit(profile, job)
        if fit is None or fit < keep_min:
            continue
        item = dict(job)
        item["fit_score"] = fit
        scored.append(item)
    if scored:
        best = max(int(j["fit_score"]) for j in scored)
        scored = [j for j in scored if int(j["fit_score"]) >= best - FIT_BAND]
    scored.sort(
        key=lambda j: (
            -float(j.get("recommendation_weight") or 0),
            -int(j.get("fit_score") or 0),
            int(j.get("id") or 0),
        )
    )
    for i, item in enumerate(scored, start=1):
        item["recommendation_rank"] = i
    return scored
