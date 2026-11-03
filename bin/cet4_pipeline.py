# -*- coding: utf-8 -*-
"""独立双角色流水线：writer 与 reviewer 永远是两个独立 CB 会话，禁止自审。

用法: python bin/cet4_pipeline.py --type reading --input paper.json [--rounds 2]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(role: str, typ: str, inp: Path, out: Path) -> dict:
    subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_roles.py"),
                    "--type", typ, "--role", role, "--input", str(inp), "--out", str(out)],
                   check=False, capture_output=True, text=True, encoding="utf-8", timeout=1200)
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()
    cur = Path(args.input)
    results = []
    for r in range(1, args.rounds + 1):
        w_out = cur.with_name(f"{cur.stem}.{args.type}.writer.r{r}.json")
        w = run("writer", args.type, cur, w_out)
        data = json.loads(cur.read_text(encoding="utf-8"))
        if args.type == "reading" and w.get("questions"):
            data["questions"] = w["questions"]
        elif args.type == "cloze" and w.get("passage"):
            data.update({"passage": w["passage"], "bank": w.get("bank", {}), "answers": w.get("answers", {})})
        elif args.type == "match" and w.get("paragraphs"):
            data.update({"paragraphs": w["paragraphs"], "statements": w.get("statements", []),
                         "answers": w.get("answers", {})})
        cur.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        rv_out = cur.with_name(f"{cur.stem}.{args.type}.reviewer.r{r}.json")
        rv = run("reviewer", args.type, cur, rv_out)  # 独立会话
        results.append({"round": r, "verdict": rv.get("verdict"), "score": rv.get("score"),
                        "fixes": len(rv.get("must_fix") or [])})
        print(f"round {r}: verdict={rv.get('verdict')} score={rv.get('score')} fixes={len(rv.get('must_fix') or [])}")
        if rv.get("verdict") == "pass":
            break
    Path(cur.with_suffix(".pipeline.json")).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
