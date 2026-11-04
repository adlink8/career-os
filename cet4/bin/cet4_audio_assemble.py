# -*- coding: utf-8 -*-
"""把逐句 TTS 片段拼成「像真人念」的音频：句间停顿、段落/换人停顿、换气声。

- 解码：ffmpeg（imageio-ffmpeg 自带）→ 24kHz 单声道 PCM
- 停顿：句间 0.40~0.55s，段落/换人 0.75~1.05s（带 ±15% 随机，避免机械感）
- 换气：在段落/换人停顿前 120~220ms 插入低幅带通噪声（吸气感），不是每个停顿都加
- 编码：ffmpeg libmp3lame 64kbps，输出精确到样本的时间轴

用法:
  python cet4/bin/cet4_audio_assemble.py --kind dialog      # Section B 两段对话
  python cet4/bin/cet4_audio_assemble.py --kind reading     # 四篇阅读
  python cet4/bin/cet4_audio_assemble.py --kind questions   # 给听力音频尾部加「问题朗读」
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
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
VAR = ROOT / "var" / "cet4-daily"
SR = 24000
FF = imageio_ffmpeg.get_ffmpeg_exe()
rng = random.Random(20261104)


# ---------------- 音频基础 ----------------
def decode(path: Path) -> np.ndarray:
    """mp3 → float32 单声道 [-1,1]"""
    out = subprocess.run([FF, "-v", "quiet", "-i", str(path), "-f", "s16le",
                          "-acodec", "pcm_s16le", "-ar", str(SR), "-ac", "1", "-"],
                         capture_output=True)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(f"decode failed: {path}")
    return np.frombuffer(out.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def trim_silence(pcm: np.ndarray, thresh: float = 0.010, keep: float = 0.05) -> np.ndarray:
    """去掉片段首尾多余的静音（TTS 自带约 0.4~0.7s），只保留一点余量。"""
    if pcm.size == 0:
        return pcm
    idx = np.where(np.abs(pcm) > thresh)[0]
    if idx.size == 0:
        return pcm[: int(SR * keep)] if pcm.size > int(SR * keep) else pcm
    m = int(SR * keep)
    a = max(0, idx[0] - m)
    b = min(len(pcm), idx[-1] + m)
    return pcm[a:b]


def silence(sec: float) -> np.ndarray:
    return np.zeros(int(round(sec * SR)), dtype=np.float32)


def breath(sec: float = 0.18, level: float = 0.018) -> np.ndarray:
    """合成「吸气」：带限噪声 + 先快后慢的包络。"""
    n = int(round(sec * SR))
    if n <= 8:
        return silence(sec)
    noise = rng_noise(n)
    # 简单带通：一阶差分（去低频）+ 滑动平均（去高频）
    noise = np.diff(noise, prepend=0.0)
    k = max(2, int(SR * 0.004))
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    env = np.concatenate([
        np.linspace(0, 1, max(1, n // 5)) ** 1.6,
        np.linspace(1, 0.0, n - max(1, n // 5)) ** 2.2,
    ])[:n]
    peak = np.max(np.abs(noise)) or 1.0
    return (noise / peak * env * level).astype(np.float32)


def rng_noise(n: int) -> np.ndarray:
    return np.array([rng.uniform(-1, 1) for _ in range(n)], dtype=np.float32)


def encode(pcm: np.ndarray, out: Path) -> None:
    pcm = np.clip(pcm, -1.0, 1.0)
    raw = (pcm * 32767).astype(np.int16).tobytes()
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
        f.write(raw)
        tmp = f.name
    try:
        subprocess.run([FF, "-y", "-v", "quiet", "-f", "s16le", "-ar", str(SR), "-ac", "1",
                        "-i", tmp, "-c:a", "libmp3lame", "-b:a", "64k", "-ar", str(SR), str(out)],
                       check=True)
    finally:
        Path(tmp).unlink(missing_ok=True)


def assemble(items, gaps) -> tuple[np.ndarray, list]:
    """items: [(pcm, role)]；gaps: 函数 (i, role_prev, role_next) -> (gap_sec, breath_sec)"""
    parts, marks, cur = [], [], 0
    for i, (pcm, role) in enumerate(items):
        start = cur
        parts.append(pcm)
        cur += len(pcm)
        marks.append({"role": role, "start": start / SR, "end": cur / SR})
        if i < len(items) - 1:
            g, b = gaps(i, role, items[i + 1][1])
            if b > 0:
                br = breath(b)
                parts.append(br)
                cur += len(br)
            parts.append(silence(g))
            cur += int(round(g * SR))
    return np.concatenate(parts), marks


# ---------------- 三件事 ----------------
def do_dialog(paper_path: Path, only: str) -> None:
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    seg_dir = VAR / "_dialog"
    for sec in paper["listening"]["sections"]:
        if sec["name"] != "B":
            continue
        for piece in sec["pieces"]:
            name = Path(piece.get("audio") or "").name
            stem = Path(name).stem
            if only and stem != only:
                continue
            timing = piece.get("timing") or []
            files = sorted(seg_dir.glob(f"{stem}_*.mp3"))
            if len(files) != len(timing):
                print(f"  ! {stem}: 片段 {len(files)} 与时间轴 {len(timing)} 不一致，跳过")
                continue
            items = [(trim_silence(decode(f)), re.sub(r"^.*_", "", f.stem).strip()) for f in files]
            # 角色：M/W 同名说话换人停顿更长
            def gaps(i, prev, nxt):
                if prev != nxt:                      # 换人
                    g = rng.uniform(0.50, 0.72)
                    return g, (rng.uniform(0.12, 0.20) if rng.random() < 0.55 else 0.0)
                return rng.uniform(0.18, 0.26), 0.0   # 同一人连续句
            pcm, marks = assemble(items, gaps)
            out = VAR / "design" / "samples" / "audio" / name
            encode(pcm, out)
            piece["timing"] = [
                {"en": t.get("en"), "text": t.get("text"),
                 "start": round(m["start"] + 0.03, 3), "end": round(m["end"] + 0.03, 3)}
                for t, m in zip(timing, marks)
            ]
            out.with_suffix(".orig.mp3").write_bytes(out.read_bytes())
            print(f"  {stem}: {len(items)} 句 / {len(pcm) / SR:.1f}s -> {name}")
    paper_path.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    print("paper updated")


def do_reading(paper_path: Path, only: str) -> None:
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    seg_dir = VAR / "reading-audio" / "_seg"
    timing_path = VAR / "reading-timing.json"
    timing = json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.exists() else {}
    counts = {"cloze": 20, "match": 50, "passage1": 22, "passage2": 20}
    for key in ("cloze", "match", "passage1", "passage2"):
        if only and key != only:
            continue
        files = sorted(seg_dir.glob(f"{key}_*.mp3"))
        if not files:
            print(f"  - {key}: 没有片段")
            continue
        old = timing.get(key) or []
        items = [(trim_silence(decode(f)), i) for i, f in enumerate(files)]

        def gaps(i, prev, nxt):
            # 每 4~6 句当作一次「段落换气」
            if (i + 1) % 5 == 0:
                return rng.uniform(0.55, 0.75), (rng.uniform(0.12, 0.18) if rng.random() < 0.6 else 0.0)
            return rng.uniform(0.36, 0.52), 0.0

        pcm, marks = assemble(items, gaps)
        out = VAR / "reading-audio" / f"reading-{key}.mp3"
        encode(pcm, out)
        timing[key] = [
            {"en": (old[i]["en"] if i < len(old) else ""),
             "start": round(m["start"] + 0.02, 3), "end": round(m["end"] + 0.02, 3)}
            for i, m in enumerate(marks)
        ]
        print(f"  {key}: {len(items)} 句 / {len(pcm) / SR:.1f}s -> {out.name}")
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print("timing updated")


def do_questions(paper_path: Path) -> None:
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    q_dir = VAR / "_qaudio"
    for sec in paper["listening"]["sections"]:
        for piece in sec["pieces"]:
            name = Path(piece.get("audio") or "").name
            stem = Path(name).stem
            base_path = VAR / "design" / "samples" / "audio" / f"{stem}.orig.mp3"
            q_path = q_dir / f"{stem}.q.mp3"
            if not base_path.exists() or not q_path.exists():
                print(f"  - {stem}: 缺片段，跳过")
                continue
            base, q = decode(base_path), decode(q_path)
            # 题目开始前留 0.9s（带一次换气）
            pcm = np.concatenate([base, silence(0.9), breath(0.16), q])
            out = VAR / "design" / "samples" / "audio" / name
            encode(pcm, out)
            print(f"  {stem}: {len(pcm) / SR:.1f}s（含问题）")
    print("questions appended")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["dialog", "reading", "questions"])
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    paper_path = (ROOT / args.paper).resolve()
    if args.kind == "dialog":
        do_dialog(paper_path, args.only)
    elif args.kind == "reading":
        do_reading(paper_path, args.only)
    else:
        do_questions(paper_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
