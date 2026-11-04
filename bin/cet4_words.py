# -*- coding: utf-8 -*-
"""批量给词表生成单词解析（音标/词性/中文），分批调用 CB。"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是英语词典编辑。为下列单词逐个给出简明解析，只输出 JSON 数组，不要解释：
[{{"word":"","phonetic":"IPA 音标，带斜杠","pos":"n./v./adj./adv. 等","cn":"最常见中文释义（<=12 字）"}}]
要求：只给这些词，不增不减；音标必须准确；一词多义取最常用一个。
单词：
{words}
"""


def parse(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def main():
    src = Path(ROOT / "var" / "cet4-daily" / "wordlist.json")
    words = json.loads(src.read_text(encoding="utf-8"))
    out_path = ROOT / "var" / "cet4-daily" / "words.json"
    done = {}
    if out_path.exists():
        done = {x["word"]: x for x in json.loads(out_path.read_text(encoding="utf-8"))}
    todo = [w["word"] for w in words if w["word"] not in done]
    print("todo", len(todo), "done", len(done), flush=True)
    batch = 120
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        prompt = PROMPT.format(words=", ".join(chunk))
        proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                              capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
        data = parse(proc.stdout or "")
        if not data:
            print("chunk fail", i, flush=True)
            continue
        for x in data:
            if x.get("word"):
                done[x["word"].lower()] = x
        out_path.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"chunk {i//batch + 1} ok total {len(done)}", flush=True)
    print("finished", len(done))


if __name__ == "__main__":
    main()
