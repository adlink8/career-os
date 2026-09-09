#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Career OS 单岗投递编排器 CLI。阶段门禁在此，不在聊天里。"""

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
from services.apply_run import (  # noqa: E402
    ApplyRunError,
    arbitrate,
    ingest,
    next_action,
    release,
    run_ats,
    start_run,
    status,
    suggest_gap_triage,
    write_pack,
)


def _print(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Career OS apply-run orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="从 JobContext 开一场投岗")
    p_start.add_argument("--job-context", help="JobContext JSON 路径")
    p_start.add_argument("--job-id", type=int, help="可选，关联 jobs.id")
    p_start.add_argument("--latest", action="store_true", help="使用库中最近一条 JobContext")

    p_next = sub.add_parser("next", help="计算下一动作并按需写 pack")
    p_next.add_argument("run_id", type=int)

    p_pack = sub.add_parser("pack", help="写出指定角色的纯净上下文包")
    p_pack.add_argument("run_id", type=int)
    p_pack.add_argument("role")

    p_ingest = sub.add_parser("ingest", help="入库子 Agent 产物并跃迁阶段")
    p_ingest.add_argument("run_id", type=int)
    p_ingest.add_argument("--role", required=True)
    p_ingest.add_argument("--file", required=True)

    p_ats = sub.add_parser("ats", help="跑 ats_matcher，分数以脚本为准")
    p_ats.add_argument("run_id", type=int)
    p_ats.add_argument("--resume", required=True)

    p_arb = sub.add_parser("arbitrate", help="三份会审 JSON 加权，不用模型再打分")
    p_arb.add_argument("run_id", type=int)

    p_rel = sub.add_parser("release", help="仅 review_passed：登记投递 + 出 autofill.json")
    p_rel.add_argument("run_id", type=int)
    p_rel.add_argument("--allow-test-profile", action="store_true", help="冒烟用，真实投递禁止")

    p_st = sub.add_parser("status", help="查看 run 状态与事件")
    p_st.add_argument("run_id", type=int)

    p_gap = sub.add_parser("triage-gaps", help="ATS 缺词分诊：改简历 / 开分支 / 放弃")
    p_gap.add_argument("run_id", type=int)
    p_gap.add_argument("--ingest", action="store_true", help="直接写入 gap-triage 并跃迁")

    args = parser.parse_args()
    conn = get_db()
    try:
        if args.cmd == "start":
            run = start_run(
                conn,
                context_path=args.job_context,
                job_id=args.job_id,
                latest=bool(args.latest),
            )
            _print({"ok": True, "run_id": run["id"], "stage": run["stage"], "job_ad_id": run["job_ad_id"]})
            return 0
        if args.cmd == "next":
            _print(next_action(conn, args.run_id))
            return 0
        if args.cmd == "pack":
            _print(write_pack(conn, args.run_id, args.role))
            return 0
        if args.cmd == "ingest":
            run = ingest(conn, args.run_id, args.role, args.file)
            _print({"ok": True, "run_id": run["id"], "stage": run["stage"], "iteration": run["iteration"]})
            return 0
        if args.cmd == "ats":
            run = run_ats(conn, args.run_id, args.resume)
            _print(
                {
                    "ok": True,
                    "run_id": run["id"],
                    "stage": run["stage"],
                    "ats_score": run["ats_score"],
                    "ats_verdict": run["ats_verdict"],
                }
            )
            return 0 if run["stage"] == "ats_passed" else 1
        if args.cmd == "arbitrate":
            run = arbitrate(conn, args.run_id)
            _print(
                {
                    "ok": True,
                    "run_id": run["id"],
                    "stage": run["stage"],
                    "review_score": run["review_score"],
                    "review_verdict": run["review_verdict"],
                    "arbitration": run.get("arbitration"),
                }
            )
            return 0 if run["stage"] == "review_passed" else 1
        if args.cmd == "release":
            run = release(conn, args.run_id, allow_test_profile=bool(args.allow_test_profile))
            _print(
                {
                    "ok": True,
                    "run_id": run["id"],
                    "stage": run["stage"],
                    "autofill_json_path": run.get("autofill_json_path"),
                    "application_id": run.get("application_id"),
                    "note": "已登记投递并生成填写载荷，不会自动点网页提交",
                }
            )
            return 0
        if args.cmd == "status":
            _print(status(conn, args.run_id))
            return 0
        if args.cmd == "triage-gaps":
            suggested = suggest_gap_triage(args.run_id)
            out = Path("data/job_discovery/runs") / str(args.run_id) / "artifacts" / "gap-triage.suggested.json"
            from services.apply_run import run_dir

            out = run_dir(args.run_id) / "artifacts" / "gap-triage.suggested.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(suggested, ensure_ascii=False, indent=2), encoding="utf-8")
            if args.ingest:
                run = ingest(conn, args.run_id, "gap-triage", str(out))
                _print(
                    {
                        "ok": True,
                        "run_id": run["id"],
                        "stage": run["stage"],
                        "triage": suggested,
                    }
                )
                return 0
            _print({"ok": True, "suggested": suggested, "path": str(out)})
            return 0
        parser.error("unknown command")
        return 2
    except ApplyRunError as exc:
        _print({"ok": False, "error": str(exc)})
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
