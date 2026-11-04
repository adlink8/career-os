# -*- coding: utf-8 -*-
"""批量：候选文章 → CodeBuddy 改写 → 校验 → 生成 HTML。

用法:
  python cet4/bin/cet4_batch_adapt.py --candidates var/cet4-daily/candidates-YYYY-MM-DD.json --limit 30 [--workers 2]

产物:
  var/cet4-daily/out/YYYY-MM-DD-NN.json / .html
  var/cet4-daily/batch-log.jsonl
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
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cet4_validate import check  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是大学英语四级命题组的阅读选材编辑。输入是一篇英文文章（标题+正文）。
只输出一个 JSON 对象，不要 markdown 代码块，不要解释。

JSON 结构：
{{
 "title": "改写后的英文标题（<=12 词）",
 "title_cn": "中文标题",
 "topic": "教育/职场/心理/健康/环境/科技/消费 之一",
 "passage": "改写后的正文，350±60 词，5-7 段，每段 2-4 句；散文体，不要小标题",
 "paragraphs": [
  {{"en":"第 1 段英文（与 passage 完全一致）",
    "cn":"第 1 段整段中文翻译",
    "main":"本段主旨（一句话中文）",
    "structure":"本段作用（提出反常识/给证据/转折/结论 之一）",
    "sentences":[{{"en":"本段一句原文","chunks":[{{"en":"片段（5-10 词）","role":"主|谓|宾|状|定|补|表","cn":"该片段中文"}}],"meaning":"整句中文","modifier":"谁修饰谁（如 for 短语说明范围）","why":"为什么这样切（先抓主谓宾）","collocation":"固定搭配"}}]}}
 ],
 "questions": [
  {{"no":1,"stem":"题干英文 <=20 词","stem_cn":"题干中文（顺流直译）","options":["A) ...","B) ...","C) ...","D) ..."],"options_cn":["A 项中文","B 项中文","C 项中文","D 项中文"],
    "answer":"A","evidence":"passage 中逐字出现的定位句",
    "paraphrase":{{"original":"原文词句","option":"选项换皮词"}},
    "trap":"无中生有|偷换概念|因果倒置|范围扩大|原词拼接",
    "option_analysis":[
      {{"letter":"A","correct":false,"why":"具体错因，必须引用原文或指出缺席信息"}},
      {{"letter":"B","correct":true,"why":"正确项为什么对（同义替换关系）"}},
      {{"letter":"C","correct":false,"why":"具体错因"}},
      {{"letter":"D","correct":false,"why":"具体错因"}}]}}
 ],
 "difficulty": {{"words":350,"avg_sentence":19,"long10_pct":7,"cefr":"B2"}}
}}

硬约束：
1) 保留原文「反常识结论+研究证据+转折」；删掉生僻人名机构名。
2) 词汇不超四级大纲（专有名词除外）；>=10 字母词占 5%-9%；平均句长 16-22，单句 <=35 词。
3) 5 题：细节 2、推断 1、态度/观点 1、词义/指代 1；至少 1 题落在转折处。
4) 每题 4 选项，长度接近；正确项必须同义替换，不得照抄原文。
5) evidence 必须逐字出现在 passage 里。
6) paragraphs 的 en 按顺序拼接后必须与 passage 完全一致；每段都要有 cn/main/structure；每段的 sentences 必须覆盖该段的每一句（顺序一致），chunks 的 en 拼接要等于该句英文（标点空格可差）。
7) 参考真题风格（不要照抄）：{anchors}
8) 5 题答案必须覆盖至少 3 个不同字母（例如 B/A/C/D/B），禁止 5 题同答案。\n8b) 每题必须给 option_analysis：4 个选项逐个写 why，正确项标 correct=true，错误项写具体错因（引用原文或指出缺席/偷换/夸大）。\n8c) 所有中文必须按英文语序顺流直译：前一块中文紧接后一块，禁止为通顺倒装、合并或改写语序；meaning 也用顺流中文。\n8d) 成分只标最小单位：主语只圈名词短语核心（the brain / a new study），谓语只圈动词（is / suggests），其余标 状/定/补/表；禁止把整句或从句标成 [主]；连词不标成分。\n8e) 每段给 vocab：[{{"word":"生词","phonetic":"音标","cn":"文中释义"}}]，只收超出四级基础的词，3-6 个。
9) 题材红线：毒品/自杀/自残/暴力/具体药物疗效一律改写或回避；保持四级通用社会、教育、健康、职场话题。

文章标题：{title}
文章正文：
{text}
"""


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(path: Path, **kw):
    kw["ts"] = now()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def parse_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    start = t.find("{")
    end = t.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


REJECT = ["blood", "lizard", "spider", "shark", "dinosaur", "galaxy", "black hole",
          "quantum", "particle", "asteroid", "volcano", "fossil", "dna", "gene ",
          "cancer cell", "tumor", "virus", "bacteria"]


def usable(cand: dict) -> bool:
    low = (cand.get("title", "") + " " + cand.get("text", "")[:400]).lower()
    if any(w in low for w in REJECT):
        return False
    human = ["people", "study", "researchers", "participants", "students", "workers",
             "employees", "adults", "children", "health", "brain", "sleep", "work",
             "school", "consumers", "families"]
    return sum(1 for w in human if w in low) >= 2


def adapt(cand: dict, idx: int, outdir: Path, logpath: Path, anchors: str, two_stage=False, review=False):
    prompt = PROMPT.format(anchors=anchors, title=cand["title"], text=cand["text"][:7000])
    t0 = time.time()
    try:
        proc = subprocess.run([str(CB), "-p", "--output-format", "text"],
                              input=prompt,
                              capture_output=True, text=True, encoding="utf-8", timeout=900,
                              cwd=str(ROOT))
        raw = proc.stdout or ""
        if not raw.strip():
            log(logpath, idx=idx, status="cb_empty", stderr=(proc.stderr or "")[:300])
            return None
        data = parse_json(raw)
        if not data:
            log(logpath, idx=idx, status="parse_fail", head=raw[:300])
            return None
        data["date"] = datetime.now().strftime("%Y-%m-%d")
        data["source"] = cand.get("source", "")
        data["source_url"] = cand.get("url", "")
        result = check(data)
        log(logpath, idx=idx, status="ok" if result["ok"] else "validate_fail",
            title=cand["title"], words=result["words"], errors=result["errors"],
            latency_s=round(time.time() - t0, 1))
        if not result["ok"]:
            return None
        stem = f"{datetime.now().strftime('%Y-%m-%d')}-{idx:02d}"
        jp = outdir / f"{stem}.json"
        jp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        # 先出音频+时间轴，再渲染 HTML（HTML 会嵌入 audio/timing）
        subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_tts.py"), str(jp)], check=False,
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
        if two_stage:
            subprocess.run([sys.executable, str(ROOT / 'bin' / 'cet4_make_questions.py'), str(jp),
                            '--out', str(jp)], check=False, timeout=900)
        if review:
            subprocess.run([sys.executable, str(ROOT / 'bin' / 'cet4_review.py'), str(jp)], check=False, timeout=900)
        subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_build_html.py"), str(jp),
                        str(outdir / f"{stem}.html")], check=False)
        return jp
    except subprocess.TimeoutExpired:
        log(logpath, idx=idx, status="timeout")
        return None
    except Exception as e:  # noqa: BLE001
        log(logpath, idx=idx, status="error", err=str(e)[:300])
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--two-stage", action="store_true")
    ap.add_argument("--review", action="store_true")
    args = ap.parse_args()

    raw = json.loads(Path(args.candidates).read_text(encoding="utf-8"))["picked"]
    seen = set()
    filtered = []
    for c in raw:
        key = c.get("title", "").strip().lower()
        if key in seen or not usable(c):
            continue
        seen.add(key)
        filtered.append(c)
    filtered.sort(key=lambda c: (-c.get("score", 0), -c.get("words", 0)))
    cands = filtered[: args.limit]
    Path(ROOT / "var" / "cet4-daily" / "batch-log.jsonl").parent.mkdir(parents=True, exist_ok=True)
    print(f"pool={len(raw)} usable={len(filtered)} take={len(cands)}", flush=True)
    outdir = ROOT / "var" / "cet4-daily" / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    logpath = ROOT / "var" / "cet4-daily" / "batch-log.jsonl"
    anchors = "The Battle Over Bike Lanes Needs a Mindset Shift; Why Do Americans Work So Much?; Is juicing actually good for you?"
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(adapt, c, i + 1, outdir, logpath, anchors, args.two_stage, args.review): c for i, c in enumerate(cands)}
        for f in as_completed(futs):
            if f.result():
                ok += 1
            else:
                fail += 1
            print(f"progress ok={ok} fail={fail}", flush=True)
    print(f"done ok={ok} fail={fail} out={outdir}")


if __name__ == "__main__":
    main()
