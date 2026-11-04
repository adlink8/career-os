# -*- coding: utf-8 -*-
"""听力音频转写（faster-whisper，CPU int8 兜底），输出可直接当听力原文。

用法: python cet4/bin/cet4_asr.py <audio> [--out xx.json] [--model small] [--device cpu|cuda]
说明：本机 av/PyAV 与 faster-whisper 的 metadata_errors 不兼容，脚本内做了兼容补丁；
      GPU 缺 cuBLAS 时自动回退 CPU int8。
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
import time
from pathlib import Path

import faster_whisper.audio as A

_orig_open = A.av.open


def _open(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _orig_open(*args, **kwargs)


A.av.open = _open

from faster_whisper import WhisperModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", default="")
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = ap.parse_args()
    src = Path(args.audio)
    out = Path(args.out) if args.out else src.with_suffix(".asr.json")
    t0 = time.time()
    try:
        m = WhisperModel(args.model, device=args.device,
                         compute_type="float16" if args.device == "cuda" else "int8")
        segs, info = m.transcribe(str(src), language="en", vad_filter=True)
    except Exception as e:  # noqa: BLE001
        print("fallback cpu:", str(e)[:100])
        m = WhisperModel(args.model, device="cpu", compute_type="int8")
        segs, info = m.transcribe(str(src), language="en", vad_filter=True)
    data = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"segments={len(data)} elapsed={round(time.time() - t0, 1)}s -> {out}")


if __name__ == "__main__":
    main()
