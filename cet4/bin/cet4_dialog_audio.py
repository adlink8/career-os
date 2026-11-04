# -*- coding: utf-8 -*-
"""重做 Section B 男女对话音频：按角色换音色，不再把 "M:"/"W:" 念出来。

- 逐句合成：男声 en-US-GuyNeural / 女声 en-US-AriaNeural
- MP3 按帧拼接（不依赖 ffmpeg），并解析帧数得到精确时长
- 重算 piece["timing"] 的 start/end，保留原 en/text 文案

用法: python cet4/bin/cet4_dialog_audio.py [--paper var/cet4-daily/demo-whole-paper.json] [--dry-run] [--only B-01]
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
VOICE = {"M": "en-US-GuyNeural", "W": "en-US-AriaNeural", "N": "en-US-ChristopherNeural"}

# --- MPEG 音频帧解析（只算时长，不解码）---
BR_MPEG2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
SR_MPEG1 = [44100, 48000, 32000, 0]
SR_MPEG2 = [22050, 24000, 16000, 0]
SR_MPEG25 = [11025, 12000, 8000, 0]


def strip_id3(data: bytes) -> bytes:
    if data[:3] == b"ID3":
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        return data[10 + size:]
    return data


def trim_tail(data: bytes) -> bytes:
    return data[:-128] if data[-128:-125] == b"TAG" else data


def mp3_duration(data: bytes) -> float:
    """按帧统计时长（秒）。"""
    i, total, n = 0, 0.0, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        h = data[i:i + 4]
        ver = (h[1] >> 3) & 0x03       # 3=MPEG1, 2=MPEG2, 0=MPEG2.5
        layer = (h[1] >> 1) & 0x03     # 1 = Layer III
        br_i = (h[2] >> 4) & 0x0F
        sr_i = (h[2] >> 2) & 0x03
        pad = (h[2] >> 1) & 0x01
        if layer != 1 or br_i in (0, 15) or sr_i == 3:
            i += 1
            continue
        if ver == 3:
            sr, br = SR_MPEG1[sr_i], [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0][br_i]
            flen = (144 * br * 1000) // sr + pad
            samples = 1152
        else:
            sr = (SR_MPEG2 if ver == 2 else SR_MPEG25)[sr_i]
            br = BR_MPEG2_L3[br_i] * 1000
            flen = (72 * br) // sr + pad
            samples = 576
        if flen <= 4:
            i += 1
            continue
        total += samples / sr
        i += flen
    return total


async def speak(text: str, voice: str, out: Path) -> None:
    await edge_tts.Communicate(text, voice, rate="+0%").save(str(out))


def split_speaker(en: str):
    m = re.match(r"^\s*([MW])\s*:\s*(.+)$", en or "")
    if m:
        return m.group(1), m.group(2).strip()
    return "N", (en or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="只处理某一段，如 B-01")
    args = ap.parse_args()

    paper = ROOT / args.paper
    data = json.loads(paper.read_text(encoding="utf-8"))
    tmp = VAR / "_dialog"
    tmp.mkdir(parents=True, exist_ok=True)

    for sec in data["listening"]["sections"]:
        if sec["name"] != "B":
            continue
        for piece in sec["pieces"]:
            name = Path(piece.get("audio") or "").name
            stem = Path(name).stem
            if args.only and stem != args.only:
                continue
            src = None
            for d in AUDIO_DIRS:
                if (d / name).exists():
                    src = d / name
                    break
            if not src:
                print(f"  ! 找不到 {name}")
                continue
            timing = piece.get("timing") or []
            if not timing:
                print(f"  - {name}: 没有 timing，跳过")
                continue
            audio_parts, new_timing, cur = [], [], 0.0
            last_spk = "N"
            for idx, item in enumerate(timing):
                spk, text = split_speaker(item.get("en") or item.get("text") or "")
                if spk == "N" and last_spk in ("M", "W"):
                    spk = last_spk          # 同一人连续说话的后续句沿用上一个说话人
                elif spk in ("M", "W"):
                    last_spk = spk
                seg_path = tmp / f"{stem}_{idx:03d}_{spk}.mp3"
                if not seg_path.exists():
                    if args.dry_run:
                        seg_path = None
                    else:
                        asyncio.run(speak(text, VOICE.get(spk, VOICE["N"]), seg_path))
                if seg_path is None:
                    continue
                raw = trim_tail(strip_id3(seg_path.read_bytes()))
                dur = mp3_duration(raw)
                audio_parts.append(raw)
                new_timing.append({"en": item.get("en"), "text": item.get("text"),
                                   "start": round(cur, 3), "end": round(cur + dur, 3)})
                cur += dur
            if args.dry_run:
                print(f"  [dry] {name}: 句数 {len(new_timing)} 预计 {cur:.1f}s")
                continue
            out_bytes = b"".join(audio_parts)
            orig = src.with_suffix(".orig.mp3")
            orig.write_bytes(out_bytes)          # 原始（无问题）基线
            src.write_bytes(out_bytes)
            piece["timing"] = new_timing
            print(f"  {name}: {len(new_timing)} 句 / {cur:.1f}s -> {src.name}")
    if not args.dry_run:
        paper.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("paper updated:", paper)
    return 0


if __name__ == "__main__":
    sys.exit(main())
