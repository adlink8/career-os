# -*- coding: utf-8 -*-
"""给听力难词表里的【词组】补释义（这些不是单词，走词组提示词）。"""
# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
WORDS = ROOT / "var" / "cet4-daily" / "words.json"

PROMPT = """你是英语词典编辑。下面是英语【词组/短语】，逐个给出便于记忆的解析，只输出 JSON 数组。
[{{"word":"","phonetic":"连读提示或'—'","pos":"phr.","cn":"整体释义（<=14 字）",
  "root":"词组构成逻辑，如 turn(转)+down(下)=调低/拒绝；无则'—'",
  "affix":"拆解，如 lent(借出)+out(向外)；无则'—'",
  "family":"同族/近义表达 1-2 个",
  "collocation":"常见搭配或变体 1 个",
  "example":"英文例句（<=12 词，用到该词组）",
  "example_cn":"例句中文",
  "tip":"一句话记忆点（<=20 字）"}}]
规则：word 字段照抄给定词组；只处理给定项，不增减。
词组：
{words}
"""


def main() -> int:
    data = json.loads(WORDS.read_text(encoding="utf-8"))
    have = {w["word"].lower() for w in data}
    # 从页面难词表里取多词条目
    html = (ROOT / "var" / "cet4-daily" / "paper-demo" / "explain" / "index.html").read_text(encoding="utf-8")
    multi = sorted({m for m in re.findall(r'data-w="([a-z][a-z\' -]{2,}?)"', html) if " " in m})
    todo = [w for w in multi if w not in have]
    print("phrases:", len(multi), "todo:", len(todo), todo)
    if not todo:
        return 0
    prompt = PROMPT.format(words="\n".join(todo))
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    txt = (proc.stdout or "").strip()
    i, j = txt.find("["), txt.rfind("]")
    got = json.loads(txt[i:j + 1]) if i >= 0 and j > i else []
    got = [g for g in got if g.get("word")]
    print("annotated:", len(got))
    data.extend(got)
    WORDS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    still = [w for w in todo if w not in {g["word"].lower() for g in got}]
    print("still missing:", still)
    return 0


if __name__ == "__main__":
    sys.exit(main())
