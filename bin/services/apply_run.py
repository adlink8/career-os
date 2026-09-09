"""Single-job apply orchestrator: SQLite state machine + isolated context packs.

LLM conversations are not the source of truth. Stages, scores, and artifacts
live in job_apply_runs / job_apply_run_events. ATS scores come only from
ATSEngine. Review totals are weighted in this module, not by a chat model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MAX_ITERATION = 3
ATS_MIN_SCORE = 70
REVIEW_PASS_TOTAL = 85
REVIEW_PASS_EACH = 80
REVIEW_WARN_TOTAL = 70
WEIGHT_ATS = 0.35
WEIGHT_HR = 0.30
WEIGHT_TECH = 0.35

STAGES = (
    "captured",
    "decomposed",
    "mapped",
    "resume_draft",
    "ats_failed",
    "gap_open",
    "ats_passed",
    "review_failed",
    "review_passed",
    "released",
    "abandoned",
)

ROLE_ALIASES = {
    "decompose": "decompose",
    "map": "map",
    "optimize": "optimize",
    "hr": "hr",
    "campus-hr": "hr",
    "tech": "tech",
    "tech-lead": "tech",
    "ats-llm": "ats-llm",
    "ats-scanner": "ats-llm",
    "review": "review",
    "gap-triage": "gap-triage",
    "gap-done": "gap-done",
}

INGEST_ROLES = (
    "decompose",
    "map",
    "optimize",
    "hr",
    "tech",
    "ats-llm",
    "gap-triage",
    "gap-done",
)

REVIEW_FORBIDDEN_KEYS = {
    "bounce_facts",
    "clause_map",
    "breakdown",
    "evidence_index",
    "hr_impressions",
    "optimize_notes",
    "interview_script",
}

OPTIMIZE_FORBIDDEN_KEYS = {
    "hr_impressions",
    "tech_verdict_rationale",
    "ats_recommendation",
    "review_prose",
}


class ApplyRunError(ValueError):
    """Illegal stage transition or missing artifact."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def runs_root() -> Path:
    override = os.environ.get("CAREER_OS_APPLY_RUNS")
    if override:
        return Path(override)
    return ROOT / "data" / "job_discovery" / "runs"


def run_dir(run_id: int) -> Path:
    path = runs_root() / str(int(run_id))
    path.mkdir(parents=True, exist_ok=True)
    (path / "packs").mkdir(exist_ok=True)
    (path / "artifacts").mkdir(exist_ok=True)
    return path


def _dump(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm_role(role: str) -> str:
    key = (role or "").strip().lower()
    if key not in ROLE_ALIASES:
        raise ApplyRunError(f"未知角色: {role}")
    return ROLE_ALIASES[key]


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def get_run(conn: sqlite3.Connection, run_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM job_apply_runs WHERE id=?", (int(run_id),)).fetchone()
    if not row:
        raise ApplyRunError(f"找不到 run_id={run_id}")
    return _row_to_dict(row)


def _add_event(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    stage: str,
    actor: str,
    artifact_path: str = "",
    input_sha256: str = "",
    notes: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO job_apply_run_events
            (run_id, stage, actor, artifact_path, input_sha256, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (int(run_id), stage, actor, artifact_path, input_sha256, notes, _utc_now()),
    )


def _update_run(conn: sqlite3.Connection, run_id: int, **fields: Any) -> Dict[str, Any]:
    if not fields:
        return get_run(conn, run_id)
    fields["updated_at"] = _utc_now()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE job_apply_runs SET {cols} WHERE id=?",
        [*fields.values(), int(run_id)],
    )
    return get_run(conn, run_id)


def load_context_for_run(conn: sqlite3.Connection, run: Dict[str, Any]) -> Dict[str, Any]:
    path = run.get("context_json_path") or ""
    if path and Path(path).is_file():
        try:
            from services.job_context import load_context_file
        except ImportError:
            from bin.services.job_context import load_context_file
        return load_context_file(path)
    context_id = run.get("context_id")
    if context_id:
        row = conn.execute(
            "SELECT raw_json FROM job_page_contexts WHERE id=?", (int(context_id),)
        ).fetchone()
        if row:
            return json.loads(row["raw_json"])
    raise ApplyRunError("缺少 JobContext：context_json_path / context_id 都不可用")


def start_run(
    conn: sqlite3.Connection,
    *,
    context_path: Optional[str] = None,
    job_id: Optional[int] = None,
    latest: bool = False,
) -> Dict[str, Any]:
    try:
        from services.job_context import latest_context, load_context_file, save_context
    except ImportError:
        from bin.services.job_context import latest_context, load_context_file, save_context

    if context_path:
        ctx = load_context_file(context_path)
        context_id = save_context(conn, ctx)
    elif latest:
        ctx = latest_context(conn)
        if not ctx:
            raise ApplyRunError("库中没有 job_page_contexts")
        row = conn.execute(
            "SELECT id FROM job_page_contexts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        context_id = int(row["id"]) if row else None
    else:
        raise ApplyRunError("必须提供 --job-context 或 --latest")
    if not context_id:
        raise ApplyRunError("JobContext 入库失败")
    saved = conn.execute(
        "SELECT raw_json FROM job_page_contexts WHERE id=?", (int(context_id),)
    ).fetchone()
    if saved:
        ctx = json.loads(saved["raw_json"])

    if job_id is not None:
        row = conn.execute("SELECT id FROM jobs WHERE id=?", (int(job_id),)).fetchone()
        if not row:
            raise ApplyRunError(f"找不到 job_id={job_id}")

    now = _utc_now()
    cur = conn.execute(
        """
        INSERT INTO job_apply_runs (
            job_id, context_id, job_ad_id, stage, iteration,
            created_at, updated_at
        ) VALUES (?, ?, ?, 'captured', 1, ?, ?)
        """,
        (
            int(job_id) if job_id is not None else None,
            context_id,
            str(ctx.get("job_ad_id") or ""),
            now,
            now,
        ),
    )
    run_id = int(cur.lastrowid)
    dest = run_dir(run_id) / "job-context.json"
    _dump(dest, ctx)
    run = _update_run(conn, run_id, context_json_path=str(dest))
    _add_event(conn, run_id, stage="captured", actor="orchestrator", artifact_path=str(dest))
    conn.commit()
    return run


def _evidence_index(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='resume_evidence_projects'"
    ).fetchone() is None:
        return []
    rows = conn.execute(
        """
        SELECT p.display_name, p.positioning,
               COALESCE(p.priority, 'normal') AS priority,
               b.sort_order, b.bullet_text, b.evidence_status
        FROM resume_evidence_projects p
        LEFT JOIN resume_evidence_bullets b ON b.project_id = p.id
        ORDER BY p.id, b.sort_order
        """
    ).fetchall()
    grouped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in rows:
        name = row["display_name"]
        if name not in grouped:
            grouped[name] = {
                "display_name": name,
                "positioning": row["positioning"] or "",
                "priority": row["priority"] or "normal",
                "bullets": [],
            }
            order.append(name)
        if row["bullet_text"]:
            grouped[name]["bullets"].append(
                {
                    "sort_order": row["sort_order"],
                    "text": row["bullet_text"],
                    "evidence_status": row["evidence_status"],
                }
            )
    return [grouped[name] for name in order]


def _resume_text(run: Dict[str, Any]) -> str:
    artifact = run_dir(int(run["id"])) / "artifacts" / "resume.md"
    if artifact.is_file():
        return artifact.read_text(encoding="utf-8")
    path = run.get("resume_path") or ""
    if path and Path(path).is_file():
        try:
            from services.resume_parser import extract_text_from_file
        except ImportError:
            from bin.services.resume_parser import extract_text_from_file
        return extract_text_from_file(path)
    return ""


def _breakdown(run_id: int) -> Dict[str, Any]:
    path = run_dir(run_id) / "artifacts" / "breakdown.json"
    return _load(path) if path.is_file() else {}


def _clause_map(run_id: int) -> Dict[str, Any]:
    path = run_dir(run_id) / "artifacts" / "clause-map.json"
    return _load(path) if path.is_file() else {}


def _identity_excerpt() -> Dict[str, str]:
    """姓名/学历等身份字段，不含求职方向，避免优化 Agent 写成运维海投稿。"""
    path = ROOT / "config" / "profile.yml"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")

    def grab(key: str) -> str:
        m = re.search(rf'(?m)^\s*{re.escape(key)}:\s*"([^"]+)"', text)
        return m.group(1).strip() if m else ""

    return {
        "name": grab("name"),
        "school": grab("school"),
        "major": grab("major"),
        "degree": grab("degree"),
        "graduation": grab("graduation"),
        "education_current": grab("current"),
    }


def _bounce(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    path = run.get("bounce_json_path") or ""
    if path and Path(path).is_file():
        return _load(Path(path))
    return None


def _gap_triage(run_id: int) -> Dict[str, Any]:
    path = run_dir(run_id) / "artifacts" / "gap-triage.json"
    return _load(path) if path.is_file() else {}


def suggest_gap_triage(run_id: int) -> Dict[str, Any]:
    """Deterministic triage so ATS 打回先分流，而不是无脑改简历。"""
    run_path = run_dir(run_id)
    bounce_files = sorted((run_path / "artifacts").glob("bounce-iter*.json"))
    bounce = _load(bounce_files[-1]) if bounce_files else {}
    missing = list(((bounce.get("ats") or {}).get("missing")) or [])
    clauses = (_clause_map(run_id).get("clauses") or [])
    status_by: Dict[str, str] = {}
    for row in clauses:
        jd = str(row.get("jd") or "")
        status_by[jd] = str(row.get("status") or "")
        for token in re.split(r"[/、，,（）()]", jd):
            token = token.strip()
            if token:
                status_by.setdefault(token, str(row.get("status") or ""))

    items = []
    for term in missing:
        clause_status = status_by.get(term, "")
        if clause_status == "corroborated" or term in {"多模态"}:
            items.append(
                {
                    "term": term,
                    "decision": "rewrite",
                    "reason": "能力已在宿主项目，属简历漏写",
                }
            )
        elif term in {"LangChain"}:
            items.append(
                {
                    "term": term,
                    "decision": "skip",
                    "reason": "JD 为加分项非硬门槛，原生 RAG 已覆盖同一能力",
                }
            )
        elif term in {"Kafka"}:
            items.append(
                {
                    "term": term,
                    "decision": "skip",
                    "reason": "消息中间件时间盒>1天且无现成 Kafka 宿主",
                }
            )
        elif term in {"微服务"}:
            items.append(
                {
                    "term": term,
                    "decision": "skip",
                    "reason": "JD 要 Java Spring Cloud；Python/FastAPI 宿主装不下，禁止硬塞",
                }
            )
        elif term in {"Milvus"}:
            items.append(
                {
                    "term": term,
                    "decision": "skip",
                    "reason": "向量库能力已在 ChromaDB 闭环；换品牌名而不跑 Milvus 算造假",
                }
            )
        elif term in {"Redis"}:
            items.append(
                {
                    "term": term,
                    "decision": "branch",
                    "host": "novel-mind",
                    "branch": "feat/jd-redis-focus",
                    "reason": "检索缓存是 RAG 自然延伸，时间盒≤1天",
                }
            )
        else:
            items.append(
                {
                    "term": term,
                    "decision": "skip",
                    "reason": "未通过立项门槛或证据不足",
                }
            )
    return {
        "role": "gap-triage",
        "items": items,
        "rewrite": [i["term"] for i in items if i["decision"] == "rewrite"],
        "branch": [i["term"] for i in items if i["decision"] == "branch"],
        "skip": [i["term"] for i in items if i["decision"] == "skip"],
    }


def write_pack(conn: sqlite3.Connection, run_id: int, role: str) -> Dict[str, Any]:
    role = _norm_role(role)
    run = get_run(conn, run_id)
    ctx = load_context_for_run(conn, run)
    folder = run_dir(run_id) / "packs"
    written: Dict[str, str] = {}

    def dump_pack(name: str, payload: Dict[str, Any]) -> Path:
        path = folder / f"{name}.json"
        _dump(path, payload)
        written[name] = str(path)
        return path

    if role == "decompose":
        payload = {
            "pack_role": "decompose",
            "run_id": int(run_id),
            "iteration": run["iteration"],
            "title": ctx.get("title") or "",
            "company": ctx.get("company") or "",
            "jd_text": ctx.get("jd_text") or "",
            "hard_filters": ctx.get("hard_filters") or {},
        }
        dump_pack("decompose", payload)
    elif role == "map":
        payload = {
            "pack_role": "map",
            "run_id": int(run_id),
            "iteration": run["iteration"],
            "breakdown": _breakdown(run_id),
            "identity": _identity_excerpt(),
            "evidence_index": _evidence_index(conn),
        }
        dump_pack("map", payload)
    elif role == "optimize":
        payload = {
            "pack_role": "optimize",
            "run_id": int(run_id),
            "iteration": run["iteration"],
            "breakdown": _breakdown(run_id),
            "identity": _identity_excerpt(),
            "clause_map": _clause_map(run_id),
            "current_resume": _resume_text(run),
            "bounce_facts": _bounce(run),
        }
        for bad in OPTIMIZE_FORBIDDEN_KEYS:
            payload.pop(bad, None)
        dump_pack("optimize", payload)
    elif role == "gap-triage":
        payload = {
            "pack_role": "gap-triage",
            "run_id": int(run_id),
            "iteration": run["iteration"],
            "bounce_facts": _bounce(run),
            "clause_map": _clause_map(run_id),
            "hosts": ["novel-mind", "local-llm-lab", "career-os"],
            "suggested": suggest_gap_triage(run_id),
        }
        dump_pack("gap-triage", payload)
    elif role in ("hr", "tech", "ats-llm", "review"):
        resume_text = _resume_text(run)
        jd_text = ctx.get("jd_text") or ""
        if role in ("hr", "review"):
            dump_pack(
                "review-hr",
                {
                    "pack_role": "campus-hr",
                    "run_id": int(run_id),
                    "company": ctx.get("company") or "",
                    "title": ctx.get("title") or "",
                    "jd_text": jd_text,
                    "resume_text": resume_text,
                },
            )
        if role in ("tech", "review"):
            dump_pack(
                "review-tech",
                {
                    "pack_role": "tech-lead",
                    "run_id": int(run_id),
                    "title": ctx.get("title") or "",
                    "jd_text": jd_text,
                    "resume_text": resume_text,
                },
            )
        if role in ("ats-llm", "review"):
            matcher = {}
            ats_path = run.get("ats_json_path") or ""
            if ats_path and Path(ats_path).is_file():
                matcher = _load(Path(ats_path))
            dump_pack(
                "review-ats",
                {
                    "pack_role": "ats-scanner",
                    "run_id": int(run_id),
                    "matcher": matcher,
                    "jd_text": jd_text,
                    "resume_text": resume_text,
                },
            )
        for name, path in written.items():
            packed = _load(Path(path))
            leak = REVIEW_FORBIDDEN_KEYS.intersection(packed)
            if leak:
                raise ApplyRunError(f"会审包 {name} 含禁止字段: {sorted(leak)}")
    else:
        raise ApplyRunError(f"不能打包角色 {role}")

    _add_event(
        conn,
        run_id,
        stage=run["stage"],
        actor="pack",
        artifact_path=json.dumps(written, ensure_ascii=False),
        notes=role,
    )
    conn.commit()
    return {"run_id": int(run_id), "role": role, "packs": written}


def next_action(conn: sqlite3.Connection, run_id: int) -> Dict[str, Any]:
    run = get_run(conn, run_id)
    stage = run["stage"]
    iteration = int(run["iteration"] or 1)
    base = {
        "run_id": int(run_id),
        "stage": stage,
        "iteration": iteration,
        "done": False,
    }
    if stage == "released":
        return {**base, "action": "done", "done": True, "autofill_json_path": run.get("autofill_json_path")}
    if stage == "abandoned":
        return {**base, "action": "stop", "done": True, "reason": run.get("notes") or "abandoned"}
    if stage == "captured":
        packs = write_pack(conn, run_id, "decompose")
        return {**base, "action": "spawn", "role": "decompose", "packs": packs["packs"]}
    if stage == "decomposed":
        packs = write_pack(conn, run_id, "map")
        return {**base, "action": "spawn", "role": "map", "packs": packs["packs"]}
    if stage == "mapped":
        packs = write_pack(conn, run_id, "optimize")
        return {**base, "action": "spawn", "role": "optimize", "packs": packs["packs"]}
    if stage == "resume_draft":
        return {
            **base,
            "action": "ats",
            "command": f"python bin/career_apply_run.py ats {run_id} --resume <简历>",
            "resume_path": run.get("resume_path") or "",
        }
    if stage == "gap_open":
        triage = _gap_triage(run_id)
        branches = [i for i in (triage.get("items") or []) if i.get("decision") == "branch"]
        return {
            **base,
            "action": "gap_branch",
            "skill": "career-jd-gap-branch",
            "branches": branches,
            "note": "宿主项目开 feat/jd-* 分支，可运行实现+测试+提交后再 ingest gap-done",
        }
    if stage in ("ats_failed", "review_failed"):
        if iteration >= MAX_ITERATION:
            _update_run(conn, run_id, stage="abandoned", notes=f"{stage} 已达 {MAX_ITERATION} 轮")
            conn.commit()
            return {**base, "action": "stop", "done": True, "stage": "abandoned", "reason": "max_iteration"}
        if not _gap_triage(run_id):
            packs = write_pack(conn, run_id, "gap-triage")
            return {
                **base,
                "action": "spawn",
                "role": "gap-triage",
                "skill": "career-jd-gap-branch",
                "packs": packs["packs"],
                "suggested": suggest_gap_triage(run_id),
            }
        packs = write_pack(conn, run_id, "optimize")
        return {**base, "action": "spawn", "role": "optimize", "packs": packs["packs"]}
    if stage == "ats_passed":
        missing = [
            name
            for name, col in (("hr", "hr_json_path"), ("tech", "tech_json_path"), ("ats-llm", "ats_llm_json_path"))
            if not (run.get(col) or "")
        ]
        if missing:
            packs = write_pack(conn, run_id, "review")
            return {
                **base,
                "action": "spawn_review_parallel",
                "roles": ["hr", "tech", "ats-llm"],
                "missing": missing,
                "packs": packs["packs"],
            }
        return {
            **base,
            "action": "arbitrate",
            "command": f"python bin/career_apply_run.py arbitrate {run_id}",
        }
    if stage == "review_passed":
        return {
            **base,
            "action": "release",
            "command": f"python bin/career_apply_run.py release {run_id}",
        }
    raise ApplyRunError(f"未知阶段 {stage}")


def _require_stage(run: Dict[str, Any], allowed: tuple[str, ...], role: str) -> None:
    if run["stage"] not in allowed:
        raise ApplyRunError(
            f"阶段 {run['stage']} 不能 ingest {role}（允许: {', '.join(allowed)}）"
        )


def ingest(conn: sqlite3.Connection, run_id: int, role: str, file_path: str) -> Dict[str, Any]:
    role = _norm_role(role)
    if role not in INGEST_ROLES:
        raise ApplyRunError(f"不能 ingest {role}")
    src = Path(file_path)
    if not src.is_file():
        raise ApplyRunError(f"产物不存在: {file_path}")
    payload = _load(src)
    if not isinstance(payload, dict):
        raise ApplyRunError("产物必须是 JSON 对象")
    run = get_run(conn, run_id)
    dest = run_dir(run_id) / "artifacts"
    digest = _sha256(src)

    if role == "decompose":
        _require_stage(run, ("captured",), role)
        stored = dest / "breakdown.json"
        _dump(stored, payload)
        if payload.get("abandon"):
            run = _update_run(
                conn,
                run_id,
                stage="abandoned",
                notes=str(payload.get("abandon_reason") or "decompose abandon"),
            )
        else:
            run = _update_run(conn, run_id, stage="decomposed")
        _add_event(conn, run_id, stage=run["stage"], actor="decompose", artifact_path=str(stored), input_sha256=digest)
    elif role == "map":
        _require_stage(run, ("decomposed",), role)
        stored = dest / "clause-map.json"
        _dump(stored, payload)
        run = _update_run(conn, run_id, stage="mapped")
        _add_event(conn, run_id, stage="mapped", actor="map", artifact_path=str(stored), input_sha256=digest)
    elif role == "optimize":
        _require_stage(run, ("mapped", "ats_failed", "review_failed"), role)
        md_text = payload.get("resume_md") or ""
        md_path = payload.get("resume_md_path") or ""
        if md_path and Path(md_path).is_file():
            md_text = Path(md_path).read_text(encoding="utf-8")
        stored = dest / "resume.md"
        if md_text:
            stored.write_text(md_text, encoding="utf-8")
        resume_path = str(payload.get("resume_path") or run.get("resume_path") or "")
        if md_text and not resume_path:
            resume_path = str(stored)
        fields: Dict[str, Any] = {
            "stage": "resume_draft",
            "resume_path": resume_path,
            "ats_score": None,
            "ats_verdict": "",
            "ats_json_path": "",
            "review_score": None,
            "review_verdict": "",
            "hr_json_path": "",
            "tech_json_path": "",
            "ats_llm_json_path": "",
        }
        if run["stage"] in ("ats_failed", "review_failed"):
            fields["iteration"] = int(run["iteration"] or 1) + 1
            if fields["iteration"] > MAX_ITERATION:
                fields["stage"] = "abandoned"
                fields["notes"] = "超过最大优化轮次"
        run = _update_run(conn, run_id, **fields)
        _add_event(conn, run_id, stage=run["stage"], actor="optimize", artifact_path=str(stored), input_sha256=digest)
    elif role == "gap-triage":
        _require_stage(run, ("ats_failed", "review_failed"), role)
        stored = dest / "gap-triage.json"
        _dump(stored, payload)
        branches = [i for i in (payload.get("items") or []) if i.get("decision") == "branch"]
        stage = "gap_open" if branches else run["stage"]
        run = _update_run(conn, run_id, stage=stage)
        _add_event(
            conn,
            run_id,
            stage=stage,
            actor="gap-triage",
            artifact_path=str(stored),
            input_sha256=digest,
        )
    elif role == "gap-done":
        _require_stage(run, ("gap_open",), role)
        stored = dest / "gap-done.json"
        _dump(stored, payload)
        run = _update_run(conn, run_id, stage="ats_failed")
        _add_event(
            conn,
            run_id,
            stage="ats_failed",
            actor="gap-done",
            artifact_path=str(stored),
            input_sha256=digest,
        )
    elif role in ("hr", "tech", "ats-llm"):
        _require_stage(run, ("ats_passed",), role)
        if "score" not in payload:
            raise ApplyRunError(f"{role} 产物缺少 score")
        stored = dest / f"review-{role}.json"
        _dump(stored, payload)
        col = {"hr": "hr_json_path", "tech": "tech_json_path", "ats-llm": "ats_llm_json_path"}[role]
        run = _update_run(conn, run_id, **{col: str(stored)})
        _add_event(conn, run_id, stage="ats_passed", actor=role, artifact_path=str(stored), input_sha256=digest)
    conn.commit()
    return run


def _write_bounce(run_id: int, facts: Dict[str, Any]) -> Path:
    path = run_dir(run_id) / "artifacts" / f"bounce-iter{facts.get('iteration') or 1}.json"
    _dump(path, facts)
    return path


def run_ats(conn: sqlite3.Connection, run_id: int, resume_path: str) -> Dict[str, Any]:
    run = get_run(conn, run_id)
    if run["stage"] != "resume_draft":
        raise ApplyRunError(f"阶段 {run['stage']} 不能跑 ATS（需要 resume_draft）")
    resume = Path(resume_path)
    if not resume.is_file():
        raise ApplyRunError(f"简历不存在: {resume_path}")

    try:
        from services.ats_engine import ATSEngine
        from services.job_context import load_context_file, to_jd_info
        from services.resume_parser import extract_text_from_file
    except ImportError:
        from bin.services.ats_engine import ATSEngine
        from bin.services.job_context import load_context_file, to_jd_info
        from bin.services.resume_parser import extract_text_from_file

    ctx = load_context_file(run["context_json_path"])
    jd_info = to_jd_info(ctx)
    resume_text = extract_text_from_file(str(resume))
    results = ATSEngine(jd_info, resume_text).run_full_diagnosis()
    stored = run_dir(run_id) / "artifacts" / "ats.json"
    _dump(stored, results)

    score = float(results.get("total_score") or 0)
    verdict = str(results.get("verdict") or "")
    knockout = verdict == "FAIL_KNOCKOUT" or bool(
        ((results.get("sub_scores") or {}).get("knockout") or {}).get("critical")
    )
    passed = (not knockout) and score >= ATS_MIN_SCORE
    stage = "ats_passed" if passed else "ats_failed"
    bounce_path = ""
    if not passed:
        kw = ((results.get("sub_scores") or {}).get("keywords_grounding") or {})
        proj = ((results.get("sub_scores") or {}).get("project_alignment") or {})
        bounce = {
            "iteration": run["iteration"],
            "ats": {
                "score": score,
                "verdict": verdict,
                "missing": kw.get("missing") or [],
                "knockout": ((results.get("sub_scores") or {}).get("knockout") or {}).get("critical") or [],
                "first_project_misaligned": any(
                    "第一" in str(n) or "错位" in str(n) for n in (proj.get("notes") or [])
                ),
            },
            "review": None,
        }
        bounce_path = str(_write_bounce(run_id, bounce))

    run = _update_run(
        conn,
        run_id,
        stage=stage,
        resume_path=str(resume),
        ats_score=score,
        ats_verdict=verdict,
        ats_json_path=str(stored),
        bounce_json_path=bounce_path,
        hr_json_path="",
        tech_json_path="",
        ats_llm_json_path="",
        review_score=None,
        review_verdict="",
    )
    _add_event(
        conn,
        run_id,
        stage=stage,
        actor="ats",
        artifact_path=str(stored),
        input_sha256=_sha256(stored),
        notes=f"{verdict} {score}",
    )
    conn.commit()
    return run


def _load_review(path: str) -> Dict[str, Any]:
    if not path or not Path(path).is_file():
        raise ApplyRunError("会审产物不齐，不能仲裁")
    data = _load(Path(path))
    if "score" not in data:
        raise ApplyRunError(f"{path} 缺少 score")
    return data


def _vetoes(hr: Dict[str, Any], tech: Dict[str, Any], ats_llm: Dict[str, Any]) -> List[str]:
    vetoes: List[str] = []
    hr_v = str(hr.get("verdict") or "").upper()
    tech_v = str(tech.get("verdict") or "").upper()
    ats_v = str(ats_llm.get("verdict") or "").upper()
    impressions = hr.get("hr_impressions") or {}
    if hr_v in ("FAIL", "REJECT") or str(impressions.get("mass_apply_risk_level") or "").upper() == "HIGH":
        vetoes.append("HR 海投/FAIL")
    if tech_v in ("FAIL", "REJECT"):
        vetoes.append("技术官判定不对口")
    knockout = ats_llm.get("knockout_check") or {}
    if knockout.get("has_composite_intent_violation") or ats_v in ("FAIL_KNOCKOUT",):
        vetoes.append("ATS-LLM 复合意向")
    return vetoes


def arbitrate(conn: sqlite3.Connection, run_id: int) -> Dict[str, Any]:
    run = get_run(conn, run_id)
    if run["stage"] != "ats_passed":
        raise ApplyRunError(f"阶段 {run['stage']} 不能仲裁（需要 ats_passed 且三份 JSON 已 ingest）")
    if run.get("ats_score") is None:
        raise ApplyRunError("缺少 matcher ATS 分数，不能用 LLM 分替代")
    hr = _load_review(run.get("hr_json_path") or "")
    tech = _load_review(run.get("tech_json_path") or "")
    ats_llm = _load_review(run.get("ats_llm_json_path") or "")

    ats_score = float(run["ats_score"])
    hr_score = float(hr["score"])
    tech_score = float(tech["score"])
    total = round(ats_score * WEIGHT_ATS + hr_score * WEIGHT_HR + tech_score * WEIGHT_TECH, 2)
    vetoes = _vetoes(hr, tech, ats_llm)

    if vetoes:
        verdict = "FAIL"
        stage = "review_failed"
    elif total >= REVIEW_PASS_TOTAL and hr_score >= REVIEW_PASS_EACH and tech_score >= REVIEW_PASS_EACH:
        verdict = "PASS"
        stage = "review_passed"
    elif total >= REVIEW_WARN_TOTAL:
        verdict = "WARN"
        stage = "review_failed"
    else:
        verdict = "FAIL"
        stage = "review_failed"

    summary = {
        "total": total,
        "verdict": verdict,
        "ats_matcher_score": ats_score,
        "hr_score": hr_score,
        "tech_score": tech_score,
        "ats_llm_score": float(ats_llm.get("score") or 0),
        "vetoes": vetoes,
        "note": "加权 ATS 分取自 ats_matcher，不用 ats-llm.score",
    }
    stored = run_dir(run_id) / "artifacts" / "review-arbitration.json"
    _dump(stored, summary)

    bounce_path = run.get("bounce_json_path") or ""
    if stage == "review_failed":
        bounce = {
            "iteration": run["iteration"],
            "ats": {
                "score": ats_score,
                "verdict": run.get("ats_verdict"),
                "missing": (((_load(Path(run["ats_json_path"])) if run.get("ats_json_path") else {}).get("sub_scores") or {}).get("keywords_grounding") or {}).get("missing") or [],
                "knockout": [],
            },
            "review": {
                "verdict": verdict,
                "must_fix": vetoes or (["review_below_pass_line"] if verdict != "PASS" else []),
            },
        }
        bounce_path = str(_write_bounce(run_id, bounce))

    run = _update_run(
        conn,
        run_id,
        stage=stage,
        review_score=total,
        review_verdict=verdict,
        bounce_json_path=bounce_path,
    )
    _add_event(
        conn,
        run_id,
        stage=stage,
        actor="arbitrate",
        artifact_path=str(stored),
        notes=f"{verdict} {total}",
    )
    conn.commit()
    run["arbitration"] = summary
    return run


def _pick(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _is_test_profile(profile: Dict[str, Any]) -> bool:
    version = str(profile.get("version") or "").lower()
    name = str(_pick(profile, "universal.personal.name") or "")
    return "test" in version or name in {"测一填"}


def _load_profile(*, allow_test: bool) -> Dict[str, Any]:
    real = ROOT / "extensions" / "ats-autofill" / "profile.json"
    test = ROOT / "extensions" / "ats-autofill" / "profile.test.json"
    if real.is_file():
        profile = _load(real)
        if _is_test_profile(profile) and not allow_test:
            raise ApplyRunError("当前 profile.json 是测试画像，拒绝 release")
        return profile
    if allow_test and test.is_file():
        return _load(test)
    raise ApplyRunError("缺少 extensions/ats-autofill/profile.json，不能生成填写载荷")


def _compile_rules() -> List[Dict[str, Any]]:
    path = ROOT / "extensions" / "ats-autofill" / "field-map-rules.json"
    if not path.is_file():
        return []
    rules = []
    for item in _load(path):
        if not item or not item.get("slot") or not item.get("re"):
            continue
        try:
            rules.append(
                {
                    "slot": item["slot"],
                    "textarea": item.get("textarea"),
                    "re": re.compile(item["re"], re.I if "i" in str(item.get("flags") or "") else 0),
                }
            )
        except re.error:
            continue
    return rules


def _resolve_slot(label: str, rules: List[Dict[str, Any]], is_textarea: bool = False) -> str:
    text = re.sub(r"请输入\d*位?", " ", label or "")
    text = re.sub(r"请输入|请选择", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if re.search(r"民族", text) and re.search(r"大学|学院", text):
        return ""
    for rule in rules:
        if rule["textarea"] is True and not is_textarea:
            continue
        if rule["textarea"] is False and is_textarea:
            continue
        if rule["re"].search(text):
            return str(rule["slot"])
    return ""


def _value_for_slot(slot: str, profile: Dict[str, Any]) -> str:
    if not slot:
        return ""
    hit = re.match(
        r"^(application\.(?:projects|internships|campus_practices|campus_roles|award_records|certificate_records|languages))\.(.+)$",
        slot,
    )
    if hit:
        item = (_pick(profile, hit.group(1)) or [{}])
        row = item[0] if isinstance(item, list) and item else {}
        raw = row.get(hit.group(2)) if isinstance(row, dict) else None
        return "" if raw is None else str(raw).strip()
    if slot == "application.expected_city":
        city = _pick(profile, "application.expected_city")
        if city:
            return str(city).strip()
        cities = str(_pick(profile, "application.target_cities") or "")
        return cities.split("、")[0].split(",")[0].strip()
    raw = _pick(profile, slot)
    if raw is None:
        return ""
    if isinstance(raw, list):
        return "、".join(str(x) for x in raw)
    return str(raw).strip()


def build_autofill(ctx: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    rules = _compile_rules()
    fields = []
    for item in ctx.get("form_schema") or []:
        label = str(item.get("label") or "")
        is_textarea = bool(item.get("textarea") or item.get("type") == "textarea")
        slot = str(item.get("slot") or "") or _resolve_slot(label, rules, is_textarea)
        value = _value_for_slot(slot, profile)
        fields.append(
            {
                "label": label,
                "slot": slot,
                "value": value,
                "required": bool(item.get("required")),
                "empty": not bool(value),
            }
        )
    return {
        "job_ad_id": ctx.get("job_ad_id") or "",
        "url": ctx.get("url") or "",
        "title": ctx.get("title") or "",
        "fields": fields,
    }


def release(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    allow_test_profile: bool = False,
) -> Dict[str, Any]:
    run = get_run(conn, run_id)
    if run["stage"] != "review_passed":
        raise ApplyRunError(f"阶段 {run['stage']} 不能 release（需要 review_passed）")
    ctx = load_context_for_run(conn, run)
    profile = _load_profile(allow_test=allow_test_profile)
    if _is_test_profile(profile) and not allow_test_profile:
        raise ApplyRunError("测试画像不得用于真实投递")

    autofill = build_autofill(ctx, profile)
    stored = run_dir(run_id) / "artifacts" / "autofill.json"
    _dump(stored, autofill)

    application_id = run.get("application_id")
    job_id = run.get("job_id")
    if job_id:
        cur = conn.execute(
            """
            INSERT INTO applications (job_id, status, notes, submitted_at, channel, created_at, updated_at)
            VALUES (?, '已投递', ?, ?, 'apply-run', ?, ?)
            """,
            (
                int(job_id),
                f"apply-run {run_id} review_passed",
                _utc_now(),
                _utc_now(),
                _utc_now(),
            ),
        )
        application_id = int(cur.lastrowid)
        try:
            from services.job_service import JobService
        except ImportError:
            from bin.services.job_service import JobService
        JobService.transition_job_status(
            int(job_id),
            "已投递",
            resume_path=run.get("resume_path") or None,
            notes=f"apply-run {run_id} 绿灯放行（未自动点网页提交）",
            conn=conn,
        )

    run = _update_run(
        conn,
        run_id,
        stage="released",
        autofill_json_path=str(stored),
        application_id=application_id,
        notes="released: 登记投递 + 填写载荷，不自动提交网页",
    )
    _add_event(conn, run_id, stage="released", actor="release", artifact_path=str(stored))
    conn.commit()
    run["autofill"] = {"path": str(stored), "field_count": len(autofill.get("fields") or [])}
    return run


def status(conn: sqlite3.Connection, run_id: int) -> Dict[str, Any]:
    run = get_run(conn, run_id)
    events = conn.execute(
        """
        SELECT id, stage, actor, artifact_path, notes, created_at
        FROM job_apply_run_events WHERE run_id=? ORDER BY id
        """,
        (int(run_id),),
    ).fetchall()
    run["events"] = [_row_to_dict(e) for e in events]
    return run
