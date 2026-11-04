# -*- coding: utf-8 -*-
"""把听力样卷的转写稿合成音频（每篇一个 mp3 + 句级时间轴）。"""
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
from pathlib import Path

import edge_tts


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 2]


async def synth(text: str, out: Path, voice: str, rate: str, sents: list[str]):
    c = edge_tts.Communicate(text, voice, rate=rate)
    bounds = []
    with open(out, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "SentenceBoundary":
                bounds.append({"en": ch.get("text", ""),
                               "start": round(ch["offset"] / 1e7, 3),
                               "end": round((ch["offset"] + ch["duration"]) / 1e7, 3)})
    for i, b in enumerate(bounds):
        if i < len(sents):
            b["text"] = sents[i]
    return bounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("--voice", default="en-US-GuyNeural")
    ap.add_argument("--rate", default="-5%")
    args = ap.parse_args()
    src = Path(args.sample)
    data = json.loads(src.read_text(encoding="utf-8"))
    outdir = src.parent / "audio"
    outdir.mkdir(parents=True, exist_ok=True)
    n = 0
    for sec in data.get("sections", []):
        for idx, piece in enumerate(sec.get("pieces", []), 1):
            script = piece.get("script") or ""
            if not script.strip():
                continue
            name = f"{sec['name']}-{idx:02d}"
            mp3 = outdir / f"{name}.mp3"
            timing = asyncio.run(synth(script, mp3, args.voice, args.rate, sentences(script)))
            piece["audio"] = f"audio/{name}.mp3"
            piece["timing"] = timing
            n += 1
            print(f"wrote {mp3} ({mp3.stat().st_size} bytes, {len(timing)} lines)")
    src.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("pieces", n)


if __name__ == "__main__":
    main()
