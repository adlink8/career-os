#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排器契约冒烟：阶段门禁、pack 隔离、ATS/会审未过不能 release。"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(label: str, cond: bool) -> None:
    if not cond:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _fake_ats(score: int, verdict: str):
    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        def run_full_diagnosis(self):
            return {
                "total_score": score,
                "verdict": verdict,
                "status_text": verdict,
                "sub_scores": {
                    "knockout": {"score": 5, "max": 5, "warnings": [], "critical": []},
                    "keywords_grounding": {
                        "score": 10,
                        "missing": ["Kubernetes"],
                        "grounded": ["Linux"],
                        "skill_only": [],
                    },
                    "project_alignment": {"score": 10, "notes": ["第一项目错位"]},
                    "star_and_evidence": {"score": 5, "notes": []},
                    "parsability": {"score": 8, "notes": []},
                },
            }

    return FakeEngine


def _review(role: str, score: int, verdict: str, extra=None) -> dict:
    payload = {"agent_role": role, "score": score, "verdict": verdict}
    if extra:
        payload.update(extra)
    return payload


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="apply-run-smoke-"))
    db_path = tmp / "career.sqlite"
    real_db = ROOT / "data" / "career_jobs.sqlite"
    if real_db.is_file():
        shutil.copy(real_db, db_path)
    else:
        db_path.touch()
    os.environ["CAREER_OS_DB_PATH"] = str(db_path)
    os.environ["CAREER_OS_APPLY_RUNS"] = str(tmp / "runs")
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "bin"))

    from career_os_store import SCHEMA_VERSION, get_db
    from services import ats_engine
    from services.apply_run import (
        ApplyRunError,
        arbitrate,
        ingest,
        lookup_fill_payload,
        mark_applied,
        next_action,
        pick_volume_track,
        release,
        run_ats,
        start_run,
    )

    conn = get_db()
    check("schema v23", SCHEMA_VERSION == 23)
    check(
        "apply_mode column",
        "apply_mode" in {r[1] for r in conn.execute("PRAGMA table_info(job_apply_runs)")},
    )
    check(
        "job_apply_runs exists",
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_apply_runs'"
        ).fetchone()
        is not None,
    )

    ctx_path = _write(
        tmp / "job-context.json",
        {
            "version": "1.0",
            "url": "https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "host": "example.zhiye.com",
            "company": "示例公司",
            "title": "运维工程师",
            "jd_text": "岗位职责：负责 Linux Docker Kubernetes 运维。任职要求：本科 2027届。",
            "form_schema": [
                {"label": "姓名", "required": True},
                {"label": "求职意向", "required": True},
                {"label": "为什么选择本公司", "required": True, "type": "textarea"},
                {"label": "请选择", "required": False},
            ],
        },
    )
    run = start_run(conn, context_path=str(ctx_path))
    run_id = int(run["id"])
    check("start captured", run["stage"] == "captured")

    nxt = next_action(conn, run_id)
    check("next spawn decompose", nxt["action"] == "spawn" and nxt["role"] == "decompose")
    pack = json.loads(Path(nxt["packs"]["decompose"]).read_text(encoding="utf-8"))
    check("decompose pack keys", set(pack) <= {
        "pack_role", "run_id", "iteration", "title", "company", "jd_text", "hard_filters"
    })
    check("decompose pack has jd", "Linux" in pack["jd_text"])

    try:
        run_ats(conn, run_id, str(ctx_path))
        check("ats blocked before resume_draft", False)
    except ApplyRunError:
        check("ats blocked before resume_draft", True)

    breakdown = _write(
        tmp / "breakdown.json",
        {
            "role": "decompose",
            "one_liner": "Linux 运维",
            "hard_gates": [{"item": "本科", "pass": True}],
            "must_keywords": ["Linux", "Docker"],
            "abandon": False,
        },
    )
    ingest(conn, run_id, "decompose", str(breakdown))
    ingest(
        conn,
        run_id,
        "map",
        str(
            _write(
                tmp / "map.json",
                {"role": "map", "clauses": [{"jd": "Linux", "evidence": "项目A", "status": "corroborated"}]},
            )
        ),
    )
    resume_md = "# 求职意向 运维工程师\n\n## 教育\n本科 2027\n\n## 技能\nLinux\n\n## 项目\n负责 Linux Docker 排障，故障恢复 2 秒。\n"
    ingest(
        conn,
        run_id,
        "optimize",
        str(_write(tmp / "opt.json", {"role": "optimize", "resume_md": resume_md})),
    )
    check("after optimize resume_draft", conn.execute("SELECT stage FROM job_apply_runs WHERE id=?", (run_id,)).fetchone()[0] == "resume_draft")

    resume_file = tmp / "resume.md"
    resume_file.write_text(resume_md, encoding="utf-8")
    ats_engine.ATSEngine = _fake_ats(50, "FAIL")
    ats_run = run_ats(conn, run_id, str(resume_file))
    check("low ATS -> ats_failed", ats_run["stage"] == "ats_failed")
    try:
        release(conn, run_id, allow_test_profile=True)
        check("cannot release after ats_failed", False)
    except ApplyRunError as exc:
        check("cannot release after ats_failed", "review_passed" in str(exc))

    nxt = next_action(conn, run_id)
    check("ats fail first routes to gap-triage", nxt["action"] == "spawn" and nxt["role"] == "gap-triage")
    ingest(
        conn,
        run_id,
        "gap-triage",
        str(_write(tmp / "gap.json", nxt["suggested"])),
    )
    nxt = next_action(conn, run_id)
    check("after skip-only triage spawn optimize", nxt["action"] == "spawn" and nxt["role"] == "optimize")
    opt_pack = json.loads(Path(nxt["packs"]["optimize"]).read_text(encoding="utf-8"))
    check("optimize has bounce_facts", bool(opt_pack.get("bounce_facts")))
    check("optimize bounce missing", "Kubernetes" in (opt_pack["bounce_facts"]["ats"]["missing"]))
    check(
        "optimize pack has no hr prose",
        "hr_impressions" not in opt_pack and "review_prose" not in opt_pack,
    )

    ingest(
        conn,
        run_id,
        "optimize",
        str(
            _write(
                tmp / "opt2.json",
                {
                    "role": "optimize",
                    "resume_md": resume_md,
                    "open_answers": [
                        {"key": "why_us", "value": "因为 Linux 运维与岗位职责对口。"}
                    ],
                },
            )
        ),
    )
    ats_engine.ATSEngine = _fake_ats(88, "PASS")
    ats_run = run_ats(conn, run_id, str(resume_file))
    check("high ATS -> ats_passed", ats_run["stage"] == "ats_passed")

    nxt = next_action(conn, run_id)
    check("review parallel", nxt["action"] == "spawn_review_parallel")
    packs = nxt["packs"]
    hr_pack = json.loads(Path(packs["review-hr"]).read_text(encoding="utf-8"))
    tech_pack = json.loads(Path(packs["review-tech"]).read_text(encoding="utf-8"))
    ats_pack = json.loads(Path(packs["review-ats"]).read_text(encoding="utf-8"))
    for name, packed in (("hr", hr_pack), ("tech", tech_pack), ("ats", ats_pack)):
        leak = {"bounce_facts", "clause_map", "breakdown", "evidence_index", "hr_impressions"} & set(packed)
        check(f"{name} review pack isolated", not leak)
    check("hr pack has resume not matcher", "matcher" not in hr_pack and "resume_text" in hr_pack)
    check("ats-llm pack has matcher", "matcher" in ats_pack)

    try:
        arbitrate(conn, run_id)
        check("arbitrate blocked until 3 json", False)
    except ApplyRunError:
        check("arbitrate blocked until 3 json", True)

    ingest(conn, run_id, "hr", str(_write(tmp / "hr.json", _review("campus-hr", 90, "PASS", {
        "hr_impressions": {"mass_apply_risk_level": "LOW"}
    }))))
    ingest(conn, run_id, "tech", str(_write(tmp / "tech.json", _review("tech-lead", 88, "PASS"))))
    ingest(conn, run_id, "ats-llm", str(_write(tmp / "ats-llm.json", _review("ats-scanner", 40, "WARN", {
        "knockout_check": {"has_composite_intent_violation": False}
    }))))
    arb = arbitrate(conn, run_id)
    check("matcher score used not ats-llm 40", arb["arbitration"]["ats_matcher_score"] == 88)
    check("review passed", arb["stage"] == "review_passed" and arb["review_verdict"] == "PASS")

    released = release(conn, run_id, allow_test_profile=True)
    check("released", released["stage"] == "released")
    autofill = json.loads(Path(released["autofill_json_path"]).read_text(encoding="utf-8"))
    check("autofill has fields", len(autofill.get("fields") or []) >= 2)
    by_label = {str(f.get("label")): f for f in (autofill.get("fields") or [])}
    check("target_position equals context title", bool(autofill.get("target_position")) and autofill.get("target_position") == autofill.get("title"))
    check("求职意向用官网标题", (by_label.get("求职意向") or {}).get("value") == autofill.get("target_position"))
    check("开放题写入 why_us", (by_label.get("为什么选择本公司") or {}).get("value", "").find("Linux") >= 0)
    check("请选择记为 noise", (by_label.get("请选择") or {}).get("kind") == "noise")
    check("coverage 含 required_empty", "required_empty" in (autofill.get("coverage") or {}))

    looked = lookup_fill_payload(
        conn,
        url="https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )
    check("lookup released by jobAdId", looked.get("mode") == "released" and looked.get("run_id") == run_id)

    try:
        mark_applied(conn, run_id, coverage={"required_empty": ["手机号"], "widget_fail": []})
        check("mark-applied blocked when required empty", False)
    except ApplyRunError:
        check("mark-applied blocked when required empty", True)
    marked = mark_applied(conn, run_id, coverage={"required_empty": [], "widget_fail": []})
    check("mark-applied ok when coverage ready", bool((marked.get("fill_coverage") or {}).get("ready")))

    # fail review cannot release
    run2 = start_run(conn, context_path=str(ctx_path))
    rid2 = int(run2["id"])
    ingest(conn, rid2, "decompose", str(breakdown))
    ingest(conn, rid2, "map", str(tmp / "map.json"))
    ingest(conn, rid2, "optimize", str(tmp / "opt.json"))
    ats_engine.ATSEngine = _fake_ats(80, "WARN")
    run_ats(conn, rid2, str(resume_file))
    ingest(conn, rid2, "hr", str(_write(tmp / "hr-fail.json", _review("campus-hr", 50, "FAIL", {
        "hr_impressions": {"mass_apply_risk_level": "HIGH"}
    }))))
    ingest(conn, rid2, "tech", str(_write(tmp / "tech2.json", _review("tech-lead", 90, "PASS"))))
    ingest(conn, rid2, "ats-llm", str(_write(tmp / "ats-llm2.json", _review("ats-scanner", 90, "PASS", {
        "knockout_check": {"has_composite_intent_violation": False}
    }))))
    arb2 = arbitrate(conn, rid2)
    vol = start_run(conn, context_path=str(ctx_path), mode="volume", allow_test_profile=True)
    check("volume skips decompose", vol["stage"] == "volume_ready")
    check("volume apply_mode", vol.get("apply_mode") == "volume")
    vol_af = json.loads(Path(vol["autofill_json_path"]).read_text(encoding="utf-8"))
    check("volume 意向=官网标题", bool(vol_af.get("target_position")) and vol_af.get("target_position") == vol_af.get("title"))
    check("volume 选了分轨", vol_af.get("track") in {"ops", "ai", "iot"})
    check("ops 轨命中运维", pick_volume_track("运维工程师", "Linux Docker")["track"] == "ops")
    nxt_vol = next_action(conn, int(vol["id"]))
    check("volume next is done", nxt_vol.get("done") is True)
    looked_vol = lookup_fill_payload(
        conn,
        url="https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )
    check("lookup prefers released over volume", looked_vol.get("run_id") == run_id and looked_vol.get("mode") == "released")

    check("hr veto -> review_failed", arb2["stage"] == "review_failed")
    try:
        release(conn, rid2, allow_test_profile=True)
        check("cannot release review_failed", False)
    except ApplyRunError:
        check("cannot release review_failed", True)

    print("[OK] apply-run-smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
