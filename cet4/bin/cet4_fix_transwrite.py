# -*- coding: utf-8 -*-
"""按真题口径重做「翻译 + 写作」两块（不动选词/匹配/阅读/听力）。

依据 2026-11-05 整卷档案评测（模拟 3.5 vs 真题 4.83）诊断出的三条硬伤：
1. 翻译撞题：一批里两套写茶，首句几乎逐字相同 → 本脚本给每套锁定**互不重复**的文化领域
2. 写作框架错位：真题是「Suppose + 校园决策场景 + You are now to write an essay to express your view.」，
   且要求只是短短几十词 → 强制套用真题骨架，禁止叠加多条指令
3. 翻译要「X 是……的……」定义句开头、专名后带英文括注、结尾一句现代回响、140-160 字

用法: python cet4/bin/cet4_fix_transwrite.py --papers 81,82,... [--workers 3]
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

# 每套锁定一个互不重复的文化领域（真题风格：历法/建筑/礼俗/工艺/教育/医药/戏曲/书画/园林/饮食器物）
DOMAINS = {
    "81": "二十四节气与农历（历法）",
    "82": "四合院与中国传统住宅建筑",
    "83": "中式婚礼礼俗",
    "84": "景德镇瓷器工艺",
    "85": "书院与中国古代教育",
    "86": "中医与针灸",
    "87": "京剧与脸谱",
    "97": "中国书法",
    "98": "苏州园林",
    "99": "中国茶文化",
}

PROMPT = """你在出一份大学英语四级试卷的 **Part IV 翻译** 与 **Part I 写作**，必须严格照真题写法。

## Part IV 翻译（本题领域：{domain}）
- 一段 **140-160 个汉字**的中文，写 {domain}
- 首句用定义式：「X 是……的……」
- 文中出现的专有名词后面**用括号补英文**，例如「二十四节气(the 24 solar terms)」「四合院(Siheyuan)」
- 分 4-6 句，句式错落；结尾写一句现代回响（「如今……仍然……」）
- 不要写成宣传语、不要升华；只要客观说明
- 给参考译文（地道英文，不逐字死译）与 4-5 个踩分点（中文短语 + 对应英文）

## Part I 写作
- 只用**一个**真题骨架，不超过三句：
  「Suppose your university is seeking students' opinions on whether {topic_hint}. You are now to write an essay to express your view. You should write at least 120 words but no more than 180 words.」
- **不许**再附加「至少两个理由」「处理一个反方观点」「自拟标题」等额外指令
- 配一篇 140-170 词范文 + 2-3 条扣分点
- 场景要具体到校园决策（图书馆/体育场馆/自习室/课程/宿舍/考试形式等），与 {domain} 不重复

只输出 JSON：
{{"translation":{{"zh":"...","reference":"...","points":["..."]}},
 "writing":{{"directions":"...","model_essay":"...","deductions":["..."]}}}}"""


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


def one(pid: str) -> str:
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    domain = DOMAINS.get(pid, "中国传统工艺")
    hint = {
        "81": "the university library should stay open around the clock during exam weeks",
        "82": "university sports facilities should be open to the public",
        "83": "students should be required to take at least one art course",
        "84": "the university should provide more part-time jobs on campus",
        "85": "final exams should be replaced by course papers",
        "86": "students should live off campus after the second year",
        "87": "the university canteen should stop using disposable tableware",
        "97": "every student should do one term of community service",
        "98": "the university should set up a 24-hour study room in each dormitory",
        "99": "students should be allowed to choose their own roommates",
    }.get(pid, "the university should improve campus facilities")
    res = jp(cb(PROMPT.replace("{domain}", domain).replace("{topic_hint}", hint)))
    if not res.get("translation") or not res.get("writing"):
        return f"paper-{pid}: 生成失败"
    d["translation"] = res["translation"]
    d["writing"] = res["writing"]
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    zh = str(res["translation"].get("zh") or "")
    return f"paper-{pid}: 翻译 {len(zh)} 字（{domain}）/ 写作 {len(str(res['writing'].get('directions') or '').split())} 词"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default=",".join(DOMAINS))
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, pids):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
