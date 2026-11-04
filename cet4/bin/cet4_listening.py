# -*- coding: utf-8 -*-
"""Part II 听力产线：出脚本 → 合成音轨（含停顿/换气）→ 写入卷子 → 渲染。

阶段：
  script  每题组按 25 题结构生成 8 段（A 3 段新闻 / B 2 段对话 / C 3 段短文）脚本与题目
  tts     逐句合成（男/女声按 M:/W: 切换），拼接时插入停顿与换气，输出到 papers/ 目录
  insert  把 audio / timing / questions 写回 paper JSON
用法:
  python cet4/bin/cet4_listening.py --stage script --papers 81
  python cet4/bin/cet4_listening.py --stage tts    --papers 81
  python cet4/bin/cet4_listening.py --stage insert  --papers 81
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
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

VOICE_M = "en-US-GuyNeural"
VOICE_W = "en-US-AriaNeural"
VOICE_N = "en-US-ChristopherNeural"

PROMPT = """你在出一个大学英语四级听力部分（Part II，25 题，25 分钟）。请按下面结构写 8 段脚本与 25 道题。

## 结构
- **Section A 新闻**（3 段，共 7 题）：每段 110-130 词 的新闻播报；题量 2 / 2 / 3
- **Section B 长对话**（2 段，共 8 题）：每段 210-260 词，两人对话（男 M / 女 W），每句开头标 `M:` 或 `W:`；题量 4 / 4
- **Section C 短文**（3 段，共 10 题）：每段 140-170 词 的说明性短文；题量 3 / 3 / 4

## 硬要求
- 题目只考**听能得到的显性信息或直接推断**，不考需要看原文的细节
- 每题 4 个选项，长度接近；正确项用同义替换表达，不与脚本逐字相同
- 题干用四级听力惯用问法（What / Why / How / According to the speaker / What does the man imply）
- 话题贴近四级真题：校园生活、就业实习、科技与社会、健康、环保、文化习俗
- 脚本必须口播友好：短句为主，少用书面嵌套从句；数字与专有名词控制在少量
- 全文美式发音与拼写

## 输出 JSON
{"sections":[{"name":"A","pieces":[{"title":"<=8 词","speed_wpm":140,"summary":"中文大意 <=60 字","script":"正文（对话用 M:/W: 行首标注；其余段落不加标记）","questions":[{"no":1,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"D"}]}]}]}

题号从 1 连续到 25。"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    t = re.sub(r"^```(?:json)?\s*", "", (t or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return {}
    frag = t[i:j + 1]
    for a in (frag, re.sub(r",\s*([}\]])", r"\1", frag)):
        try:
            return json.loads(a)
        except json.JSONDecodeError:
            continue
    return {}


def pid_list(spec: str) -> list:
    out = []
    for x in re.split(r"[,\s]+", spec.strip()):
        if x:
            out.append(x)
    return out


def stage_script(pids: list) -> None:
    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        if (d.get("listening") or {}).get("sections"):
            print(f"  paper-{pid}: 已有听力，跳过")
            continue
        data = jp(cb(PROMPT))
        secs = data.get("sections") or []
        nq = sum(len(p.get("questions") or []) for s in secs for p in s.get("pieces") or [])
        if len(secs) != 3 or nq != 25:
            print(f"  paper-{pid}: 结构不合格（sections={len(secs)}, questions={nq}），重试一次")
            data = jp(cb(PROMPT))
            secs = data.get("sections") or []
            nq = sum(len(p.get("questions") or []) for s in secs for p in s.get("pieces") or [])
            if len(secs) != 3 or nq != 25:
                print(f"  paper-{pid}: 仍不合格，跳过")
                continue
        d["listening"] = {"sections": secs,
                          "questions": [{"no": q["no"], "options": q.get("options") or [], "answer": q.get("answer")}
                                        for s in secs for p in s.get("pieces") or [] for q in p.get("questions") or []]}
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        words = sum(len(str(p.get("script") or "").split()) for s in secs for p in s.get("pieces") or [])
        print(f"  paper-{pid}: {len(secs)} 节 / {nq} 题 / 脚本 {words} 词")


def split_lines(script: str) -> list:
    """把脚本拆成 (role, text)：对话按 M:/W: 切，其余整段按句拆给 N。"""
    lines = [x.strip() for x in (script or "").splitlines() if x.strip()]
    out = []
    for ln in lines:
        m = re.match(r"^(M|W)\s*[:：]\s*(.+)$", ln)
        if m:
            role, text = m.group(1), m.group(2)
            for s in re.split(r"(?<=[.!?])\s+", text):
                if s.strip():
                    out.append((role, s.strip()))
        else:
            for s in re.split(r"(?<=[.!?])\s+", ln):
                if s.strip():
                    out.append(("N", s.strip()))
    return out


async def tts_one(text: str, voice: str, out: Path) -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(str(out))


def synth_items(items: list, tmpdir: Path) -> list:
    files = []
    for i, (role, text) in enumerate(items):
        voice = {"M": VOICE_M, "W": VOICE_W}.get(role, VOICE_N)
        f = tmpdir / f"s{i:03d}.mp3"
        asyncio.run(tts_one(text, voice, f))
        files.append(f)
    return files


def stage_tts(pids: list) -> None:
    sys.path.insert(0, str(ROOT / "bin"))
    from cet4_audio_assemble import decode, trim_silence, silence, breath, encode, assemble, SR  # type: ignore
    import numpy as np

    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        secs = (d.get("listening") or {}).get("sections") or []
        if not secs:
            print(f"  paper-{pid}: 无脚本，先跑 --stage script")
            continue
        for sec in secs:
            for k, piece in enumerate(sec.get("pieces") or [], 1):
                name = f"listening-{pid}-{sec['name'].lower()}{k}.mp3"
                target = PAPERS / name
                items = split_lines(piece.get("script") or "")
                if not items:
                    continue
                with tempfile.TemporaryDirectory() as td:
                    tdp = Path(td)
                    files = synth_items(items, tdp)
                    pcm_items = []
                    timing = []
                    for (role, text), mp3 in zip(items, files):
                        pcm = trim_silence(decode(mp3))
                        pcm_items.append((pcm, role))
                        timing.append({"en": text, "role": role})
                    def gaps(i, prev, nxt):
                        if prev != nxt:
                            return (0.62, 0.20)
                        return (0.30, 0.10)
                    pcm, marks = assemble(pcm_items, gaps)
                    # 师范：句间停顿已含在 marks 里
                    for t, m in zip(timing, marks):
                        t["start"] = round(m["start"], 3)
                        t["end"] = round(m["end"], 3)
                    encode(pcm, target)
                piece["audio"] = name
                piece["timing"] = timing
                dur = timing[-1]["end"] if timing else 0
                print(f"  paper-{pid} {sec['name']}{k}: {name} {dur:.1f}s / {len(timing)} 句")
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


DIRECTIONS = {'A': 'Section A. Directions: In this section, you will hear three news reports. At the end of each news report, you will hear two or three questions. Both the news report and the questions will be spoken only once. After you hear a question, you must choose the best answer from the four choices marked A, B, C and D.', 'B': 'Section B. Directions: In this section, you will hear two long conversations. At the end of each conversation, you will hear four questions. Both the conversation and the questions will be spoken only once. After you hear a question, you must choose the best answer from the four choices marked A, B, C and D.', 'C': 'Section C. Directions: In this section, you will hear three passages. At the end of each passage, you will hear three or four questions. Both the passage and the questions will be spoken only once. After you hear a question, you must choose the best answer from the four choices marked A, B, C and D.'}


def stage_extra(pids: list) -> None:
    """写作与翻译音轨：写作=题目要求+范文；翻译=英文参考译文。"""
    sys.path.insert(0, str(ROOT / "bin"))
    from cet4_audio_assemble import decode, trim_silence, silence, breath, assemble, encode, SR  # type: ignore

    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        jobs = []
        w = d.get("writing") or {}
        if w.get("directions"):
            jobs.append(("writing", [w.get("directions"), w.get("model_essay") or ""]))
        t = d.get("translation") or {}
        if t.get("reference"):
            jobs.append(("translation", [t["reference"]]))
        for key, texts in jobs:
            jobs_name = f"{key}-{pid}.mp3"
            target = PAPERS / jobs_name
            items, timing = [], []
            for ti, text in enumerate(texts):
                for sent in re.split(r"(?<=[.!?])\s+", text or ""):
                    sent = sent.strip()
                    if len(sent.split()) < 3:
                        continue
                    items.append(("N", sent))
                    timing.append({"en": sent, "role": "X", "para": ti})
            if not items:
                continue
            with tempfile.TemporaryDirectory() as td:
                files = synth_items(items, Path(td))
                pcm_items = [(trim_silence(decode(mp3)), role) for (role, _), mp3 in zip(items, files)]

                def gaps(i, prev, nxt):
                    if timing[i].get("para") != timing[i + 1].get("para"):
                        return (0.9, 0.16)
                    return (0.26, 0.08)

                pcm, marks = assemble(pcm_items, gaps)
                for tt, m in zip(timing, marks):
                    tt["start"] = round(m["start"], 3)
                    tt["end"] = round(m["end"], 3)
                encode(pcm, target)
            d.setdefault("audio", {})[key] = jobs_name
            print(f"  paper-{pid} {key}: {jobs_name} {timing[-1]['end']:.0f}s / {len(timing)} 句")
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_reading(pids: list) -> None:
    """四个阅读板块的朗读音轨（选词/匹配/双篇），旁白男声，段落间留停顿。"""
    sys.path.insert(0, str(ROOT / "bin"))
    from cet4_audio_assemble import decode, trim_silence, silence, breath, assemble, encode, SR  # type: ignore
    import numpy as np

    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        r = d.get("reading") or {}
        jobs = []
        if (r.get("cloze") or {}).get("passage"):
            jobs.append(("cloze", [r["cloze"]["passage"]]))
        if (r.get("match") or {}).get("paragraphs"):
            jobs.append(("match", [f"{k}. {v}" for k, v in r["match"]["paragraphs"].items()]))
        for key in ("passage1", "passage2"):
            paras = (r.get(key) or {}).get("paragraphs") or []
            if paras:
                jobs.append((key, [x.get("en", "") for x in paras]))
        for key, texts in jobs:
            name = f"reading-{pid}-{key}.mp3"
            target = PAPERS / name
            items, timing, bounds = [], [], []
            for ti, text in enumerate(texts):
                for sent in re.split(r"(?<=[.!?])\s+", text):
                    sent = sent.strip()
                    if len(sent.split()) < 3:
                        continue
                    items.append(("N", sent))
                    timing.append({"en": sent, "role": "R", "para": ti})
            if not items:
                continue
            with tempfile.TemporaryDirectory() as td:
                tdp = Path(td)
                files = synth_items(items, tdp)
                pcm_items = [(trim_silence(decode(mp3)), role) for (role, _), mp3 in zip(items, files)]

                def gaps(i, prev, nxt):
                    a, b = timing[i], timing[i + 1]
                    if a.get("para") != b.get("para"):
                        return (0.72, 0.18)
                    return (0.26, 0.08)

                pcm, marks = assemble(pcm_items, gaps)
                for t, m in zip(timing, marks):
                    t["start"] = round(m["start"], 3)
                    t["end"] = round(m["end"], 3)
                encode(pcm, target)
            d.setdefault("audio", {})[key] = name
            d.setdefault("timing", {})[key] = timing
            print(f"  paper-{pid} {key}: {name} {timing[-1]['end']:.0f}s / {len(timing)} 句")
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_directions(pids: list) -> None:
    """把 Section A/B/C 的标准指令音拼到每节第一段音轨前（真题录音顺序：指令 → 正文 → 题目）。"""
    sys.path.insert(0, str(ROOT / "bin"))
    from cet4_audio_assemble import decode, trim_silence, silence, encode, SR  # type: ignore
    import numpy as np

    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for sec in (d.get("listening") or {}).get("sections") or []:
            pieces = sec.get("pieces") or []
            if not pieces or pieces[0].get("directions"):
                continue
            first = pieces[0]
            if not first.get("audio"):
                continue
            text = DIRECTIONS.get(sec.get("name")) or ""
            if not text:
                continue
            target = PAPERS / first["audio"]
            with tempfile.TemporaryDirectory() as td:
                f_mp3 = Path(td) / "dir.mp3"
                asyncio.run(tts_one(text, VOICE_N, f_mp3))
                dir_pcm = trim_silence(decode(f_mp3))
            body = decode(target)
            gap = silence(1.2)
            pcm = np.concatenate([dir_pcm, gap, body])
            encode(pcm, target)
            shift = (len(dir_pcm) + len(gap)) / SR
            for t in first.get("timing") or []:
                t["start"] = round(float(t.get("start") or 0) + shift, 3)
                t["end"] = round(float(t.get("end") or 0) + shift, 3)
            first["directions"] = True
            print(f"  paper-{pid} Section {sec.get('name')}: 指令音 {len(dir_pcm)/SR:.1f}s 已拼到首段前")
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_qaudio(pids: list, gap: float = 12.0) -> None:
    """把每段的题目逐题念出来追加到音轨末尾，每题后留答题停顿（贴合真题节奏）。"""
    sys.path.insert(0, str(ROOT / "bin"))
    from cet4_audio_assemble import decode, trim_silence, silence, encode, assemble, SR  # type: ignore

    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for sec in (d.get("listening") or {}).get("sections") or []:
            for k, piece in enumerate(sec.get("pieces") or [], 1):
                if not piece.get("audio"):
                    continue
                target = PAPERS / piece["audio"]
                if piece.get("qaudio"):
                    print(f"  paper-{pid} {sec['name']}{k}: 已含题目口播，跳过")
                    continue
                qs = piece.get("questions") or []
                if not qs:
                    continue
                items = []
                for q in qs:
                    items.append(("N", (q.get("stem") or "").strip()))
                with tempfile.TemporaryDirectory() as td:
                    tdp = Path(td)
                    files = synth_items(items, tdp)
                    parts, base_marks = [decode(target)], []
                    cur = len(parts[0])
                    timing = list(piece.get("timing") or [])
                    marks = []
                    for q, mp3 in zip(qs, files):
                        pcm = trim_silence(decode(mp3))
                        silence_before = silence(2.2)
                        silence_after = silence(gap)
                        start = cur + len(silence_before)
                        parts += [silence_before, pcm, silence_after]
                        cur += len(silence_before) + len(pcm) + len(silence_after)
                        timing.append({"en": (q.get("stem") or "").strip(), "role": "Q",
                                       "start": round(start / SR, 3), "end": round((start + len(pcm)) / SR, 3)})
                import numpy as np
                encode(np.concatenate(parts), target)
                piece["timing"] = timing
                piece["qaudio"] = True
                print(f"  paper-{pid} {sec['name']}{k}: 追加 {len(qs)} 题口播 + 答题停顿 {gap:.0f}s"
                      f"，总长 {timing[-1]['end']:.0f}s")
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_insert(pids: list) -> None:
    for pid in pids:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        secs = (d.get("listening") or {}).get("sections") or []
        if not secs:
            print(f"  paper-{pid}: 无听力数据")
            continue
        qs = [{"no": q["no"], "options": q.get("options") or [], "answer": q.get("answer")}
              for s in secs for p in s.get("pieces") or [] for q in p.get("questions") or []]
        d["listening"]["questions"] = qs
        d["meta"]["total"] = 57
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        have_audio = sum(1 for s in secs for p in s.get("pieces") or [] if p.get("audio"))
        print(f"  paper-{pid}: 题 {len(qs)} / 音轨 {have_audio} 段")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["script", "tts", "directions", "qaudio", "reading", "extra", "insert", "all"])
    ap.add_argument("--gap", type=float, default=12.0, help="每题后答题停顿秒数")
    ap.add_argument("--papers", default="81")
    args = ap.parse_args()
    pids = pid_list(args.papers)
    if args.stage in ("script", "all"):
        print("[script]")
        stage_script(pids)
    if args.stage in ("tts", "all"):
        print("[tts]")
        stage_tts(pids)
    if args.stage in ("directions", "all"):
        print("[directions]")
        stage_directions(pids)
    if args.stage in ("qaudio", "all"):
        print("[qaudio]")
        stage_qaudio(pids, args.gap)
    if args.stage in ("reading", "all"):
        print("[reading]")
        stage_reading(pids)
    if args.stage in ("extra", "all"):
        print("[extra]")
        stage_extra(pids)
    if args.stage in ("insert", "all"):
        print("[insert]")
        stage_insert(pids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
