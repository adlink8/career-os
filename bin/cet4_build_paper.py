# -*- coding: utf-8 -*-
"""整卷渲染：写作 + 听力 + 阅读(选词/匹配/仔细) + 翻译，A4 试卷版式。

用法: python bin/cet4_build_paper.py <whole-paper.json> [--outdir dir]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#e9e9e9;font-family:"Times New Roman","SimSun",serif;color:#000;font-size:10.5pt;line-height:1.5}
.paper{width:595.32pt;margin:16pt auto;background:#fff;padding:38pt 36pt 30pt;box-shadow:0 2px 16px rgba(0,0,0,.18)}
.part{font-weight:bold;margin:14pt 0 6pt;font-size:11pt}
.sec{font-weight:bold;margin:8pt 0 4pt}
.dir{font-style:italic;color:#333;margin:4pt 0 8pt}
p.body{text-indent:2em;margin:0 0 5pt;text-align:justify}
.q{margin:7pt 0}
.opts{display:grid;grid-template-columns:1fr 1fr;column-gap:14pt;padding-left:12pt}
.opt{display:block;cursor:pointer;padding:1pt 2pt;border-radius:2px}
.opt input{display:none}
.opt.sel{background:#e3f0ff}
.opt.correct{background:#d9f2df;outline:1px solid #2e7d32}
.opt.wrong{background:#fde0e0;outline:1px solid #c62828}
input.blank{width:110pt;border:none;border-bottom:1px solid #666;font-family:inherit;font-size:10.5pt;text-align:center}
select.stmt{font-family:inherit;font-size:10pt}
.bank{display:grid;grid-template-columns:repeat(4,1fr);gap:2pt 10pt;margin:6pt 0 10pt;font-size:10pt}
.bank div{border-bottom:1px dotted #ddd}
textarea{width:100%;min-height:90pt;font-family:inherit;font-size:10.5pt;border:1px solid #ccc;border-radius:4pt;padding:6pt}
.qa{display:none;margin:4pt 0 0;padding:5pt 8pt;border-left:2pt solid #c9a227;background:#fbf9f1;font:9pt/1.6 -apple-system,"Microsoft YaHei",sans-serif}
.qa.show{display:block}
.bar{position:fixed;top:0;left:0;right:0;background:#111;color:#fff;padding:6px 12px;font:13px/1.4 -apple-system,"Microsoft YaHei",sans-serif;display:flex;gap:14px;align-items:center;z-index:20}
.bar input[type=range]{width:120px}
.bar button{border:1px solid #666;background:#222;color:#fff;border-radius:4px;padding:3px 8px;cursor:pointer}
.spacer{height:44px}
.audio{width:100%;margin:4pt 0 6pt}
#report{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:30;align-items:center;justify-content:center}
#report.show{display:flex}
#reportBox{background:#fff;padding:16pt;border-radius:10pt;width:340pt;font:12pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
@media print{.bar,.qa{display:none!important}.paper{box-shadow:none;margin:0}@page{size:A4;margin:38pt 36pt 30pt}}
"""

JS = """
const P = PAPER;
let answers = {};
function pick(no, letter, el){
  answers[no] = letter;
  document.querySelectorAll(`.opt[data-q="${no}"]`).forEach(e=>e.classList.toggle('sel', e===el));
}
function check(){
  let right=0, total=0;
  document.querySelectorAll('.q[data-ans]').forEach(q=>{
    const no = q.dataset.no, ans = q.dataset.ans;
    const sel = answers[no];
    total++;
    if(sel === ans) right++;
    q.querySelectorAll('.opt').forEach(o=>{
      o.classList.remove('correct','wrong');
      if(o.dataset.l === ans) o.classList.add('correct');
      if(sel && o.dataset.l === sel && sel !== ans) o.classList.add('wrong');
    });
  });
  document.querySelectorAll('input.blank').forEach(inp=>{
    total++;
    const want = (P.reading.cloze.answers[inp.dataset.no]||'').toString().toUpperCase();
    const got = (inp.value||'').trim().toUpperCase();
    const ok = got === want;
    if(ok) right++;
    inp.style.background = ok ? '#d9f2df' : (got ? '#fde0e0' : '');
  });
  document.querySelectorAll('select.stmt').forEach(sel=>{
    total++;
    const want = P.reading.match.answers[sel.dataset.no];
    const ok = sel.value === want;
    if(ok) right++;
    sel.style.background = ok ? '#d9f2df' : (sel.value ? '#fde0e0' : '');
  });
  document.getElementById('score').textContent = `客观题 ${right}/${total}`;
  document.getElementById('report').classList.add('show');
  document.getElementById('reportBody').innerHTML = `<div>听力 + 阅读客观题：<b>${right}/${total}</b></div><div style="margin-top:8pt;color:#666">写作与翻译为主观题，未计入。</div>`;
}
function closeReport(){document.getElementById('report').classList.remove('show')}
function speak(t){ if(!window.speechSynthesis) return; const u=new SpeechSynthesisUtterance(t); u.lang='en-US'; speechSynthesis.cancel(); speechSynthesis.speak(u); }
function showQA(){document.querySelectorAll('.qa').forEach(e=>e.classList.toggle('show'))}
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cloze_html(passage: str) -> str:
    import re
    t = esc(passage)
    t = re.sub(r"__(\d+)__", lambda m: f'<input class="blank" data-no="{m.group(1)}" placeholder="{m.group(1)}">', t)
    return f'<p class="body">{t}</p>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--outdir", default="var/cet4-daily/paper-demo")
    args = ap.parse_args()
    src = Path(args.paper)
    data = json.loads(src.read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    parts = []
    parts.append(f'<div class="part">Part I &nbsp; Writing &nbsp;(30 minutes)</div>')
    parts.append(f'<div class="dir">Directions: {esc(data["writing"]["directions"].replace("Directions:","").strip())}</div>')
    parts.append('<textarea placeholder="Write your essay here (120-180 words)"></textarea>')

    parts.append('<div class="part">Part II &nbsp; Listening Comprehension &nbsp;(25 minutes)</div>')
    lq = data["listening"]["questions"]
    for sec in data["listening"]["sections"]:
        parts.append(f'<div class="sec">Section {sec["name"]}</div>')
        for piece in sec["pieces"]:
            audio = None
            if piece.get("audio"):
                for base in (src.parent, src.parent / "design" / "samples"):
                    cand = (base / piece["audio"]).resolve()
                    if cand.exists():
                        audio = cand
                        break
            if audio and audio.exists():
                shutil.copy(audio, outdir / audio.name)
                parts.append(f'<audio class="audio" controls src="{audio.name}"></audio>')
            for q in piece["questions"]:
                opts = "".join(
                    f'<label class="opt" data-q="{q["no"]}" data-l="{o[0]}" onclick="pick({q["no"]},\'{o[0]}\',this)">'
                    f'<input type="radio" name="q{q["no"]}">{esc(o)}</label>' for o in q["options"])
                parts.append(f'<div class="q" data-no="{q["no"]}" data-ans="{q["answer"]}"><b>{q["no"]}.</b> '
                             f'<span class="opts">{opts}</span></div>')

    r = data["reading"]
    parts.append('<div class="part">Part III &nbsp; Reading Comprehension &nbsp;(40 minutes)</div>')
    parts.append('<div class="sec">Section A</div>')
    parts.append('<div class="dir">Directions: Read the passage and choose one word for each blank from the word bank.</div>')
    parts.append(cloze_html(r["cloze"]["passage"]))
    bank = "".join(f'<div>{k}) {esc(v)}</div>' for k, v in r["cloze"]["bank"].items())
    parts.append(f'<div class="bank">{bank}</div>')
    ans_a = " ".join(f'{k}:{v}' for k, v in r["cloze"]["answers"].items())
    parts.append(f'<div class="qa">答案：{ans_a}</div>')

    parts.append('<div class="sec">Section B</div>')
    parts.append('<div class="dir">Directions: Match each statement with the paragraph it is derived from.</div>')
    for k, v in r["match"]["paragraphs"].items():
        parts.append(f'<p class="body"><b>{k})</b> {esc(v)}</p>')
    letters = "".join(f'<option>{c}</option>' for c in r["match"]["paragraphs"].keys())
    for st in r["match"]["statements"]:
        parts.append(f'<div class="q"><b>{st["no"]}.</b> {esc(st["text"])} '
                     f'<select class="stmt" data-no="{st["no"]}"><option value="">--</option>{letters}</select></div>')
    ans_b = " ".join(f'{k}:{v}' for k, v in r["match"]["answers"].items())
    parts.append(f'<div class="qa">答案：{ans_b}</div>')

    for key, label in (("passage1", "Passage One"), ("passage2", "Passage Two")):
        pg = r[key]
        parts.append(f'<div class="sec">Section C &nbsp; {label}</div>')
        start = 46 if key == "passage1" else 51
        parts.append(f'<div class="dir">Questions {start} to {start + 4} are based on the following passage.</div>')
        if pg.get("paragraphs"):
            for para in pg["paragraphs"]:
                parts.append(f'<p class="body">{esc(para.get("en", ""))}</p>')
        else:
            parts.append(f'<p class="body">{esc(pg.get("passage", ""))}</p>')
        for q in pg["questions"]:
            opts = "".join(
                f'<label class="opt" data-q="{q["no"]}" data-l="{o[0]}" onclick="pick({q["no"]},\'{o[0]}\',this)">'
                f'<input type="radio" name="q{q["no"]}">{esc(o)}</label>' for o in q["options"])
            parts.append(f'<div class="q" data-no="{q["no"]}" data-ans="{q["answer"]}"><b>{q["no"]}.</b> '
                         f'{esc(q["stem"])}<div class="opts">{opts}</div></div>')

    parts.append('<div class="part">Part IV &nbsp; Translation &nbsp;(30 minutes)</div>')
    parts.append(f'<div class="dir">Directions: Translate the following passage into English.</div>')
    parts.append(f'<p class="body">{esc(data["translation"]["zh"])}</p>')
    parts.append('<textarea placeholder="Write your translation here"></textarea>')

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</title><style>{CSS}</style></head><body>
<div class="bar"><b>{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</b>
<span id="score">客观题 --</span>
<button onclick="check()">对答案</button><button onclick="showQA()">显示答案</button>
<button onclick="window.print()">打印</button></div>
<div class="spacer"></div>
<div class="paper">{''.join(parts)}</div>
<div id="report"><div id="reportBox"><h3 style="margin:0 0 10pt">得分</h3><div id="reportBody"></div>
<button onclick="closeReport()" style="width:100%;margin-top:10pt;padding:6pt">关闭</button></div></div>
<script>const PAPER = {json.dumps(data, ensure_ascii=False)};{JS}</script></body></html>"""
    out = outdir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
