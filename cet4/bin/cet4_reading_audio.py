# -*- coding: utf-8 -*-
"""给四篇阅读（选词填空 / 匹配 / 仔细阅读一 / 仔细阅读二）生成朗读音频。

- 选词填空：先把空按答案填好再念（念带空的句子没有意义）
- 匹配/仔细阅读：逐句念
- 逐句合成后按 MP3 帧拼接，产出精确时间轴 reading-timing.json，页面里点一句读一句

用法: python cet4/bin/cet4_reading_audio.py [--dry-run] [--only passage1]
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
OUT_DIR = VAR / "reading-audio"
VOICE = "en-US-ChristopherNeural"


def strip_id3(data: bytes) -> bytes:
    if data[:3] == b"ID3":
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        return data[10 + size:]
    return data


def trim_tail(data: bytes) -> bytes:
    return data[:-128] if data[-128:-125] == b"TAG" else data


BR_MPEG2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
SR_MPEG1 = [44100, 48000, 32000, 0]
SR_MPEG2 = [22050, 24000, 16000, 0]
SR_MPEG25 = [11025, 12000, 8000, 0]


def mp3_duration(data: bytes) -> float:
    i, total, n = 0, 0.0, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        h = data[i:i + 4]
        ver, layer = (h[1] >> 3) & 0x03, (h[1] >> 1) & 0x03
        br_i, sr_i, pad = (h[2] >> 4) & 0x0F, (h[2] >> 2) & 0x03, (h[2] >> 1) & 0x01
        if layer != 1 or br_i in (0, 15) or sr_i == 3:
            i += 1
            continue
        if ver == 3:
            sr = SR_MPEG1[sr_i]
            br = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0][br_i] * 1000
            flen, samples = (144 * br) // sr + pad, 1152
        else:
            sr = (SR_MPEG2 if ver == 2 else SR_MPEG25)[sr_i]
            br = BR_MPEG2_L3[br_i] * 1000
            flen, samples = (72 * br) // sr + pad, 576
        if flen <= 4:
            i += 1
            continue
        total += samples / sr
        i += flen
    return total


async def speak(text: str, out: Path) -> None:
    await edge_tts.Communicate(text, VOICE, rate="+0%").save(str(out))


def split_sents(text: str):
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def cloze_sentences(paper):
    """选词填空：按答案把空填上再念。"""
    c = paper["reading"]["cloze"]
    bank, ans = c.get("bank") or {}, c.get("answers") or {}
    raw = json.loads((VAR / "sent-explain-cloze.json").read_text(encoding="utf-8")).get("cloze") or []
    pairs = []
    for item in raw:
        en = item.get("en") or ""
        filled = re.sub(r"__(\d+)__",
                        lambda m: (bank.get(ans.get(m.group(1), ""), "") or m.group(0)),
                        en)
        pairs.append((en, filled))
    if not pairs:
        text = c.get("passage") or ""
        filled = re.sub(r"__(\d+)__", lambda m: bank.get(ans.get(m.group(1), ""), "") or m.group(0), text)
        pairs = [(s, s) for s in split_sents(filled)]
    return pairs


def match_sentences(paper):
    exp = json.loads((VAR / "sent-explain-match.json").read_text(encoding="utf-8"))
    out = []
    for k in sorted(paper["reading"]["match"]["paragraphs"]):
        items = exp.get(f"match-{k}") or []
        if items:
            for it in items:
                en = (it.get("en") or "").strip()
                if en:
                    out.append((en, en))
        else:
            for s in split_sents(paper["reading"]["match"]["paragraphs"][k]):
                out.append((s, s))
    return out


def passage_sentences(paper, key):
    out = []
    for para in paper["reading"][key].get("paragraphs") or []:
        sents = para.get("sentences") or []
        if sents:
            for s in sents:
                en = (s.get("en") or "").strip()
                if en:
                    out.append((en, en))
        else:
            for s in split_sents(para.get("en") or ""):
                out.append((s, s))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    paper = json.loads((ROOT / args.paper).read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seg_dir = OUT_DIR / "_seg"
    seg_dir.mkdir(exist_ok=True)

    blocks = {
        "cloze": cloze_sentences(paper),
        "match": match_sentences(paper),
        "passage1": passage_sentences(paper, "passage1"),
        "passage2": passage_sentences(paper, "passage2"),
    }

    timing_all = {}
    for key, pairs in blocks.items():
        if args.only and key != args.only:
            continue
        if not pairs:
            print(f"  - {key}: 无句子，跳过")
            continue
        parts, timeline, cur = [], [], 0.0
        for idx, (match_text, tts_text) in enumerate(pairs):
            seg = seg_dir / f"{key}_{idx:03d}.mp3"
            if not seg.exists():
                if args.dry_run:
                    print(f"  [dry] {key}: {len(pairs)} 句（未合成）")
                    parts = []
                    break
                asyncio.run(speak(tts_text, seg))
            raw = trim_tail(strip_id3(seg.read_bytes()))
            dur = mp3_duration(raw)
            parts.append(raw)
            timeline.append({"en": match_text, "start": round(cur, 3), "end": round(cur + dur, 3)})
            cur += dur
        if not parts:
            continue
        mp3 = OUT_DIR / f"reading-{key}.mp3"
        mp3.write_bytes(b"".join(parts))
        timing_all[key] = timeline
        print(f"  {key}: {len(timeline)} 句 / {cur:.1f}s -> {mp3.name} ({mp3.stat().st_size // 1024}KB)")

    if timing_all and not args.dry_run:
        tp = VAR / "reading-timing.json"
        old = {}
        if tp.exists():
            try:
                old = json.loads(tp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                old = {}
        old.update(timing_all)
        tp.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
        print("timing ->", tp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
