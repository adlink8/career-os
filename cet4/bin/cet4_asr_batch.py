# -*- coding: utf-8 -*-
"""批量转写 08-真题配套资源 下所有听力音频（可断点续跑）。"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
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

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "knowledge" / "cet4-bank" / "08-真题配套资源"
OUT = ROOT / "var" / "cet4-daily" / "asr"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = [p for p in SRC.rglob("*") if p.suffix.lower() in (".mp3", ".m4a", ".mp4")]
    model = WhisperModel("small", device="cpu", compute_type="int8")
    for p in sorted(files):
        dst = OUT / (p.stem + ".json")
        if dst.exists() and dst.stat().st_size > 1000:
            print("skip", p.name)
            continue
        t0 = time.time()
        try:
            segs, info = model.transcribe(str(p), language="en", vad_filter=True)
            data = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
            dst.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"ok {p.name} segs={len(data)} {round(time.time()-t0,1)}s", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"fail {p.name}: {str(e)[:120]}", flush=True)


if __name__ == "__main__":
    main()
