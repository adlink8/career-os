# -*- coding: utf-8 -*-
"""独立双角色流水线：writer / reviewer / repair 永远是彼此独立的 CB 会话，禁止自审。

关键：reviewer 的 must_fix 必须回灌给 repair，否则后续轮次只是同一篇文章重掷骰子。

用法:
  python bin/cet4_pipeline.py --type reading --input paper.json [--rounds 3] [--start-round 4]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = {"reading": ("questions",), "cloze": ("passage", "bank", "answers", "translate"),
        "match": ("title", "paragraphs", "statements", "answers")}


def run(role: str, typ: str, inp: Path, out: Path, prev: Path | None = None,
        mustfix: Path | None = None) -> dict:
    cmd = [sys.executable, str(ROOT / "bin" / "cet4_roles.py"),
           "--type", typ, "--role", role, "--input", str(inp), "--out", str(out)]
    if prev:
        cmd += ["--prev", str(prev)]
    if mustfix:
        cmd += ["--mustfix", str(mustfix)]
    subprocess.run(cmd, check=False, capture_output=True, text=True,
                   encoding="utf-8", timeout=1500)
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}


def merge(paper: dict, typ: str, art: dict) -> dict:
    """把 writer/repair 产物并回候选卷，空字段不覆盖旧值。"""
    for k in KEYS[typ]:
        if art.get(k):
            paper[k] = art[k]
    return paper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--start-round", type=int, default=1)
    ap.add_argument("--resume", action="store_true",
                    help="从目录里已有的最大轮次接着跑 repair（不重掷）")
    args = ap.parse_args()

    typ = args.type
    cur = Path(args.input)
    stem = cur.with_suffix("")
    results = []
    prev_art: Path | None = None

    if args.resume:
        best = 0
        for p in cur.parent.glob(f"{stem.name}.{typ}.*.r*.json"):
            tail = p.stem.rsplit(".r", 1)
            if len(tail) == 2 and tail[1].isdigit():
                best = max(best, int(tail[1]))
        if best:
            args.start_round = best + 1
            for cand in (f"{stem.name}.{typ}.repair.r{best}.json",
                         f"{stem.name}.{typ}.writer.r{best}.json"):
                p = cur.parent / cand
                if p.exists():
                    prev_art = p
                    break
            rv = cur.parent / f"{stem.name}.{typ}.reviewer.r{best}.json"
            if prev_art and rv.exists():
                prev_rev = rv
            elif prev_art:
                print("resume: 缺上一轮 reviewer 报告，退回重写")
                prev_art = None
        print(f"resume from round {args.start_round}, seed={prev_art}")

    for r in range(args.start_round, args.start_round + args.rounds):
        paper = json.loads(cur.read_text(encoding="utf-8"))
        if prev_art is None:
            w_out = Path(f"{stem}.{typ}.writer.r{r}.json")
            art = run("writer", typ, cur, w_out)
        else:
            # 只有拿到上一轮 must_fix 才能定向修复
            w_out = Path(f"{stem}.{typ}.repair.r{r}.json")
            art = run("repair", typ, cur, w_out, prev=prev_art, mustfix=prev_rev)
        if not art:
            print(f"round {r}: {'repair' if prev_art else 'writer'} parse failed, stop")
            break
        if typ == "reading":
            for q in art.get("questions") or []:
                for oa in q.get("option_analysis") or []:
                    oa["correct"] = (oa.get("letter") == q.get("answer"))
        paper = merge(paper, typ, art)
        cur.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")

        rv_out = Path(f"{stem}.{typ}.reviewer.r{r}.json")
        rv = run("reviewer", typ, cur, rv_out)  # 全新独立会话，看不到 writer 的推理
        if not rv:
            print(f"round {r}: reviewer parse failed, stop")
            break
        results.append({"round": r, "verdict": rv.get("verdict"), "score": rv.get("score"),
                        "fixes": [(f.get("problem") if isinstance(f, dict) else str(f))
                                  for f in (rv.get("must_fix") or [])]})
        print(f"round {r}: verdict={rv.get('verdict')} score={rv.get('score')} "
              f"fixes={len(rv.get('must_fix') or [])}", flush=True)
        Path(cur.with_suffix(".pipeline.json")).write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        if rv.get("verdict") == "pass":
            break
        prev_art, prev_rev = w_out, rv_out

    Path(cur.with_suffix(".pipeline.json")).write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done:", cur)


if __name__ == "__main__":
    main()
