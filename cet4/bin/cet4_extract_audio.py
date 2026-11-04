# -*- coding: utf-8 -*-
"""从 mp4/m4a 容器抽出 16k 单声道 wav，供 ASR 使用（无 ffmpeg 依赖）。"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import sys
from pathlib import Path

import av
import numpy as np
import wave


def extract(src: str, dst: str):
    container = av.open(src)
    stream = next(s for s in container.streams if s.type == "audio")
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    frames = []
    for frame in container.decode(stream):
        for out in resampler.resample(frame):
            frames.append(out.to_ndarray().reshape(-1))
    if not frames:
        raise RuntimeError("no audio frames")
    data = np.concatenate(frames).astype(np.int16)
    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(data.tobytes())
    print(f"wrote {dst} ({len(data)/16000:.1f}s)")


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2])
