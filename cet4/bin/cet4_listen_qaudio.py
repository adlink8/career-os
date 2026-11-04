# -*- coding: utf-8 -*-
"""给每段听力音频结尾追加「问题朗读」，让卷面可以只印选项（真题样式）。

做法：edge-tts 合成 "Question 1. ...? Question 2. ...?"，去掉 ID3 头后拼到原音频尾部。
原音频的帧完全不动 → 已有的逐句时间轴（timing）继续有效。

用法: python cet4/bin/cet4_listen_qaudio.py [--paper var/cet4-daily/demo-whole-paper.json] [--dry-run]
"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
VAR = ROOT / "var" / "cet4-daily"
AUDIO_DIRS = [VAR / "design" / "samples" / "audio", VAR / "audio"]
VOICE = "en-US-ChristopherNeural"


def strip_id3(data: bytes) -> bytes:
    if data[:3] == b"ID3":
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        return data[10 + size:]
    return data


def trim_id3v1(data: bytes) -> bytes:
    if data[-128:-125] == b"TAG":
        return data[:-128]
    return data


async def speak(text: str, out: Path) -> None:
    await edge_tts.Communicate(text, VOICE, rate="+0%").save(str(out))


def question_text(qs) -> str:
    parts = []
    for q in qs:
        stem = (q.get("stem") or "").strip()
        if not stem:
            continue
        parts.append(f"Question {q['no']}. {stem}")
    return "  ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="已追加过的也重做（用 .orig 备份还原后重拼）")
    args = ap.parse_args()

    paper = ROOT / args.paper
    data = json.loads(paper.read_text(encoding="utf-8"))
    tmp = VAR / "_qaudio"
    tmp.mkdir(parents=True, exist_ok=True)

    done = 0
    for sec in data["listening"]["sections"]:
        for piece in sec["pieces"]:
            name = piece.get("audio")
            if not name:
                continue
            src = None
            bases = [ROOT / args.paper, VAR, VAR / "design" / "samples", ROOT / "var" / "cet4-daily" / "design" / "samples"]
            for b in bases:
                cand = (Path(b).parent / name) if str(b).endswith(".json") else (Path(b) / name)
                if cand.exists():
                    src = cand
                    break
            if not src:
                print(f"  ! 找不到音频 {name}")
                continue
            orig = src.with_suffix(".orig.mp3")
            base = orig if orig.exists() else src
            qs = piece.get("questions") or []
            text = question_text(qs)
            if not text:
                print(f"  - {name}: 没有问句，跳过")
                continue
            if done and args.dry_run:
                continue
            qmp3 = tmp / f"{src.stem}.q.mp3"
            if not qmp3.exists() or args.force:
                asyncio.run(speak(text, qmp3))
            base_bytes = trim_id3v1(strip_id3(base.read_bytes()))
            q_bytes = trim_id3v1(strip_id3(qmp3.read_bytes()))
            out = base_bytes + q_bytes
            print(f"  {name}: {len(base_bytes) // 1024}KB + {len(q_bytes) // 1024}KB -> {len(out) // 1024}KB"
                  f"  ({len(qs)} 问)")
            if not args.dry_run:
                if not orig.exists():
                    orig.write_bytes(src.read_bytes())
                src.write_bytes(out)
            done += 1
    print(f"done {done} pieces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
