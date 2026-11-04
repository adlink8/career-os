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
.w{cursor:context-menu}
.w:hover{background:#eef4ff}
#wdict{display:none;position:fixed;z-index:50;max-width:260pt;background:#fff;border:1px solid #999;border-radius:8pt;box-shadow:0 6px 20px rgba(0,0,0,.25);padding:8pt 10pt;font:11pt/1.6 -apple-system,"Microsoft YaHei",sans-serif}
#wdict.show{display:block}
#wdict .hd{font-weight:700;font-size:13pt}
#wdict .ipa{color:#555;margin-left:6pt}
#wdict .pos{color:#7a5c00;margin-right:6pt}
#wdict .btn{margin-top:6pt}
#wdict button{border:1px solid #ccc;background:#fafafa;border-radius:6pt;padding:2pt 8pt;cursor:pointer}
.pan,.qax{display:none;margin:2pt 0 8pt;padding:6pt 8pt;border-left:2pt solid #c9a227;background:#fbf9f1;font:9pt/1.7 -apple-system,"Microsoft YaHei","SimSun",sans-serif}
.pan.show,.qax.show{display:block}
.pan .cn{margin-bottom:3pt}
.tr{margin:4pt 0 8pt;border-left:2pt solid #e0e0e0;padding-left:8pt;font:9.5pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.tr .line{cursor:pointer;padding:1pt 3pt;border-radius:2pt}
.tr .line:hover{background:#eef4ff}
.tr .line.on{background:#fff3cd}
.tr .line .en{color:#111}
.tr .line .cn{color:#5a5a5a}
.sum{margin:4pt 0;padding:5pt 8pt;background:#f6f6f6;font:9.5pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.vt{width:100%;border-collapse:collapse;margin:4pt 0 8pt;font:9pt/1.6 -apple-system,"Microsoft YaHei",sans-serif}
.vt td{border-bottom:1px dotted #ddd;padding:1pt 4pt;vertical-align:top}
.vt td:first-child{font-weight:600;width:24%}
.vt td:nth-child(2){color:#555;width:24%}
.trs{border-collapse:collapse;width:100%;font:9pt/1.6 -apple-system,"Microsoft YaHei",sans-serif;margin:4pt 0}
.trs td,.trs th{border:1px solid #e2e2e2;padding:2pt 5pt;vertical-align:top;text-align:left}
.bands{margin:4pt 0 8pt;font:9.5pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.bands div{border-bottom:1px dotted #ddd;padding:1pt 0}
@media print{.bar,.qa,.pan,.qax,#wdict{display:none!important}.paper{box-shadow:none;margin:0}@page{size:A4;margin:38pt 36pt 30pt}}
"""

JS = """
const P = PAPER;
const WORDS = window.__WORDS__ || {};
function wrapWords(root){
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let n;
  while((n = w.nextNode())){
    const host = n.parentElement;
    if(!host || host.closest('.pan,.qax,.qa,#wdict')) continue;
    if(/[A-Za-z]{2}/.test(n.textContent)) nodes.push(n);
  }
  nodes.forEach(node=>{
    const frag = document.createDocumentFragment();
    node.textContent.split(/([A-Za-z][A-Za-z'-]+)/).forEach((part, i)=>{
      if(i % 2 === 1){
        const sp = document.createElement('span');
        sp.className = 'w'; sp.dataset.w = part.toLowerCase(); sp.textContent = part;
        frag.appendChild(sp);
      } else if(part){ frag.appendChild(document.createTextNode(part)); }
    });
    node.parentNode.replaceChild(frag, node);
  });
}
function showDict(el, x, y){
  const w = el.dataset.w;
  const info = WORDS[w] || {};
  const box = document.getElementById('wdict');
  box.innerHTML = `<div class="hd">${w}<span class="ipa">${info.phonetic||''}</span></div>`+
    `<div><span class="pos">${info.pos||''}</span>${info.cn||'暂无释义'}</div>`+
    `<div class="btn"><button onclick="speakWord('${w}')">🔊 朗读</button></div>`;
  box.style.left = Math.min(x + 12, innerWidth - 280) + 'px';
  box.style.top = Math.min(y + 12, innerHeight - 160) + 'px';
  box.classList.add('show');
}
function speakWord(w){ if(!window.speechSynthesis) return; const u=new SpeechSynthesisUtterance(w); u.lang='en-US'; speechSynthesis.cancel(); speechSynthesis.speak(u); }
document.addEventListener('contextmenu', e=>{
  const t = e.target;
  if(t && t.classList && t.classList.contains('w')){ e.preventDefault(); showDict(t, e.clientX, e.clientY); }
  else { const b=document.getElementById('wdict'); if(b) b.classList.remove('show'); }
});
document.addEventListener('click', ()=>{ const b=document.getElementById('wdict'); if(b) b.classList.remove('show'); });
function toggleAnalysis(){ document.querySelectorAll('.pan').forEach(e=>e.classList.toggle('show')); }
function toggleAnswers(){ document.querySelectorAll('.qax').forEach(e=>e.classList.toggle('show')); }

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
function seek(aid, t, el){
  const a=document.getElementById(aid); if(!a) return;
  a.currentTime=t; a.play().catch(()=>{});
  document.querySelectorAll('.tr .line.on').forEach(e=>e.classList.remove('on'));
  if(el) el.classList.add('on');
}
function speakW(w){ speak(w); }
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
    ap.add_argument("--mode", default="explain", choices=["plain", "explain"])
    ap.add_argument("--words", default="var/cet4-daily/words.json")
    ap.add_argument("--lexplain", default="var/cet4-daily/listening-explain.json")
    ap.add_argument("--wexplain", default="var/cet4-daily/writing-explain.json")
    ap.add_argument("--cexplain", default="var/cet4-daily/cloze-explain.json")
    ap.add_argument("--mexplain", default="var/cet4-daily/match-explain.json")
    args = ap.parse_args()
    global MODE
    MODE = args.mode
    src = Path(args.paper)
    data = json.loads(src.read_text(encoding="utf-8"))
    lexp_path = Path(args.lexplain)
    lexp = json.loads(lexp_path.read_text(encoding="utf-8")) if lexp_path.exists() else {}
    wexp_path = Path(args.wexplain)
    wexp = json.loads(wexp_path.read_text(encoding="utf-8")) if wexp_path.exists() else {}
    cexp_path = Path(args.cexplain)
    cexp = json.loads(cexp_path.read_text(encoding="utf-8")) if cexp_path.exists() else {}
    mexp_path = Path(args.mexplain)
    mexp = json.loads(mexp_path.read_text(encoding="utf-8")) if mexp_path.exists() else {}
    words_path = Path(args.words)
    words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.exists() else []
    wdict = {x["word"].lower(): x for x in words if x.get("word")}
    wjs = "window.__WORDS__ = " + json.dumps(wdict, ensure_ascii=False) + ";"
    outdir = Path(args.outdir) / args.mode
    outdir.mkdir(parents=True, exist_ok=True)

    parts = []
    parts.append(f'<div class="part">Part I &nbsp; Writing &nbsp;(30 minutes)</div>')
    parts.append(f'<div class="dir">Directions: {esc(data["writing"]["directions"].replace("Directions:","").strip())}</div>')
    parts.append('<textarea placeholder="Write your essay here (120-180 words)"></textarea>')
    if MODE == "explain":
        w = data["writing"]
        blk = ['<div class="sum"><b>范文（165 词，4 段）</b>']
        for para in [x for x in (w.get("model_essay") or "").split("\n\n") if x.strip()]:
            blk.append(f'<p class="body">{esc(para.strip())}</p>')
        blk.append("</div>")
        if wexp.get("structure"):
            rows = "".join(f'<tr><td>第 {x.get("para")} 段</td><td>{esc(x.get("role",""))}</td>'
                           f'<td>{esc(x.get("cn",""))}</td></tr>' for x in wexp["structure"])
            blk.append(f'<div class="vt" style="display:block"><table class="trs">'
                       f'<tr><th>段落</th><th>作用</th><th>内容</th></tr>{rows}</table></div>')
        for i, s in enumerate(wexp.get("sentences") or [], 1):
            blk.append(f'<div class="tr"><div class="line"><div class="en">{i}. {esc(s.get("en",""))}</div>'
                       f'<div class="cn">意群：{esc(s.get("chunks",""))}</div>'
                       f'<div class="cn">顺流直译：{esc(s.get("cn",""))}</div>'
                       + (f'<div class="cn">点拨：{esc(s.get("note",""))}</div>' if s.get("note") else "")
                       + "</div></div>")
        if wexp.get("expressions"):
            blk.append("<b>可复用表达</b>" + "".join(
                f'<div class="bands"><div>{esc(x.get("phrase",""))}　{esc(x.get("cn",""))}'
                f'　<span style="color:#888">{esc(x.get("use",""))}</span></div></div>'
                for x in wexp["expressions"]))
        if wexp.get("bands"):
            blk.append("<b>评分档</b>" + "".join(
                f'<div class="bands"><div><b>{esc(x.get("score",""))}</b>　{esc(x.get("desc",""))}</div></div>'
                for x in wexp["bands"]))
        if w.get("deductions"):
            blk.append("<b>判卷扣分点</b>" + "".join(
                f'<div class="bands"><div>· {esc(x)}</div></div>' for x in w["deductions"]))
        parts.append('<div class="sum">' + "".join(blk) + "</div>")

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
            aid = f"au-{Path(piece.get('audio') or 'x').stem}"
            if audio and audio.exists():
                shutil.copy(audio, outdir / audio.name)
                parts.append(f'<audio class="audio" id="{aid}" controls src="{audio.name}"></audio>')
            lx = lexp.get(f"{sec['name']}-{Path(piece.get('audio') or 'x').stem}") or {}
            if MODE == "explain":
                if piece.get("summary"):
                    parts.append(f'<div class="sum"><b>大意</b>　{esc(piece["summary"])}</div>')
                cn_map = {x.get("i"): x.get("cn") for x in (lx.get("sentences") or [])}
                lines = []
                for i, s in enumerate(piece.get("timing") or [], 1):
                    en = s.get("en") or s.get("text") or ""
                    st = float(s.get("start") or 0)
                    lines.append(f'<div class="line" onclick="seek(\'{aid}\',{st:.3f},this)">'
                                 f'<div class="en">{i}. {esc(en)}</div>'
                                 f'<div class="cn">{esc(cn_map.get(i) or "")}</div></div>')
                if lines:
                    parts.append('<div class="tr">' + "".join(lines) + "</div>")
                if lx.get("words"):
                    rows = "".join(
                        f'<tr><td class="w" onclick="speakW(\'{esc(x.get("w",""))}\')">{esc(x.get("w",""))}</td>'
                        f'<td>{esc(x.get("ipa",""))}</td><td>{esc(x.get("pos",""))}</td>'
                        f'<td>{esc(x.get("cn",""))}</td></tr>' for x in lx["words"])
                    parts.append('<table class="vt"><tr><th>生词</th><th>音标</th><th>词性</th><th>释义</th></tr>'
                                 + rows + "</table>")
            qan = {x.get("no"): x for x in (lx.get("qanalysis") or []) if x.get("no")}
            for q in piece["questions"]:
                opts = "".join(
                    f'<label class="opt" data-q="{q["no"]}" data-l="{o[0]}" onclick="pick({q["no"]},\'{o[0]}\',this)">'
                    f'<input type="radio" name="q{q["no"]}">{esc(o)}</label>' for o in q["options"])
                parts.append(f'<div class="q" data-no="{q["no"]}" data-ans="{q["answer"]}"><b>{q["no"]}.</b> '
                             f'<span class="opts">{opts}</span></div>')
                an = qan.get(q["no"])
                if MODE == "explain" and an:
                    parts.append(f'<div class="qax"><div><b>答案 {esc(q["answer"])}</b></div>'
                                 f'<div>为什么对：{esc(an.get("why",""))}</div>'
                                 f'<div>干扰项：{esc(an.get("trap",""))}</div></div>')

    r = data["reading"]
    parts.append('<div class="part">Part III &nbsp; Reading Comprehension &nbsp;(40 minutes)</div>')
    parts.append('<div class="sec">Section A</div>')
    parts.append('<div class="dir">Directions: Read the passage and choose one word for each blank from the word bank.</div>')
    parts.append(cloze_html(r["cloze"]["passage"]))
    bank = "".join(f'<div>{k}) {esc(v)}</div>' for k, v in r["cloze"]["bank"].items())
    parts.append(f'<div class="bank">{bank}</div>')
    ans_a = " ".join(f'{k}:{v}' for k, v in r["cloze"]["answers"].items())
    parts.append(f'<div class="qa">答案：{ans_a}</div>')
    if MODE == "explain":
        blk = []
        if cexp.get("blanks"):
            rows = "".join(
                f'<tr><td><b>{esc(str(b.get("no")))}</b></td><td>{esc(b.get("answer",""))}) '
                f'{esc(b.get("word",""))}</td><td>{esc(b.get("slot",""))}</td>'
                f'<td>{esc(b.get("why",""))}</td><td>{esc(b.get("reject",""))}</td>'
                f'<td>{esc(b.get("cn",""))}</td></tr>' for b in cexp["blanks"])
            blk.append('<table class="trs"><tr><th>题</th><th>答案</th><th>空位语法槽</th>'
                       '<th>为什么是它</th><th>其它候选为什么不行</th><th>顺流中文</th></tr>'
                       + rows + "</table>")
        if cexp.get("passage_cn"):
            blk.append("<b>全文顺流直译</b>" + "".join(
                f'<div class="bands"><div>{i}. {esc(x)}</div></div>'
                for i, x in enumerate(cexp["passage_cn"], 1)))
        if blk:
            parts.append('<div class="pan show">' + "".join(blk) + "</div>")

    parts.append('<div class="sec">Section B</div>')
    parts.append('<div class="dir">Directions: Match each statement with the paragraph it is derived from.</div>')
    for k, v in r["match"]["paragraphs"].items():
        parts.append(f'<p class="body"><b>{k})</b> {esc(v)}</p>')
        mx = mexp.get(k) or {}
        if MODE == "explain" and mx:
            sent = "".join(
                f'<div style="margin-top:3pt"><b>{esc(s.get("en",""))}</b><br>'
                f'<span style="color:#555">{esc(s.get("chunks",""))}</span><br>'
                f'<span style="color:#666">{esc(s.get("cn",""))}</span>'
                + (f'<div style="color:#7a5c00">↳ {esc(s.get("note",""))}</div>' if s.get("note") else "")
                + "</div>" for s in (mx.get("sentences") or []))
            parts.append(f'<div class="pan"><div class="cn">{esc(mx.get("main",""))}</div>'
                         f'<div style="color:#555">作用：{esc(mx.get("role",""))}</div>'
                         f'<div style="color:#555">对应题号：{esc("、".join(mx.get("answers") or []) or "无")}</div>'
                         f'{sent}</div>')
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
                if MODE == "explain":
                    sent = "".join(
                        f'<div style="margin-top:3pt"><b>{esc(s.get("en",""))}</b><br>' +
                        " ".join(f'{esc(c.get("en",""))}<span style="color:#888">[{esc(c.get("role",""))}：{esc(c.get("cn",""))}]</span>' for c in (s.get("chunks") or [])) +
                        (f'<div style="color:#555">意思：{esc(s.get("meaning",""))}</div>' if s.get("meaning") else "") +
                        (f'<div style="color:#555">谁修饰谁：{esc(s.get("modifier",""))}</div>' if s.get("modifier") else "") +
                        (f'<div style="color:#555">为啥：{esc(s.get("why",""))}</div>' if s.get("why") else "") +
                        (f'<div style="color:#555">搭配：{esc(s.get("collocation",""))}</div>' if s.get("collocation") else "") +
                        "</div>" for s in (para.get("sentences") or []))
                    parts.append(f'<div class="pan"><div class="cn">{esc(para.get("cn",""))}</div>'
                                 f'<div style="color:#555">主旨：{esc(para.get("main",""))}</div>'
                                 f'<div style="color:#555">作用：{esc(para.get("structure",""))}</div>{sent}</div>')
        else:
            parts.append(f'<p class="body">{esc(pg.get("passage", ""))}</p>')
        for q in pg["questions"]:
            opts = "".join(
                f'<label class="opt" data-q="{q["no"]}" data-l="{o[0]}" onclick="pick({q["no"]},\'{o[0]}\',this)">'
                f'<input type="radio" name="q{q["no"]}">{esc(o)}</label>' for o in q["options"])
            parts.append(f'<div class="q" data-no="{q["no"]}" data-ans="{q["answer"]}"><b>{q["no"]}.</b> '
                         f'{esc(q["stem"])}<div class="opts">{opts}</div></div>')
            if MODE == "explain":
                oa_parts = []
                for x in (q.get("option_analysis") or []):
                    if isinstance(x, dict):
                        oa_parts.append(f'<div>{esc(x.get("letter",""))}) {"✓" if x.get("correct") else "✗"} {esc(x.get("why",""))}</div>')
                    else:
                        oa_parts.append(f'<div>{esc(str(x))}</div>')
                oa = "".join(oa_parts)
                parts.append(f'<div class="qax"><div><b>答案 {esc(q["answer"])}</b></div>'
                             + (f'<div>定位：{esc(q.get("evidence",""))}</div>' if q.get("evidence") else "")
                             + (f'<div>同义替换：{esc((q.get("paraphrase") or {}).get("original",""))} → {esc((q.get("paraphrase") or {}).get("option",""))}</div>' if q.get("paraphrase") else "")
                             + (f'<div>陷阱：{esc(q.get("trap",""))}</div>' if q.get("trap") else "")
                             + oa + '</div>')

    parts.append('<div class="part">Part IV &nbsp; Translation &nbsp;(30 minutes)</div>')
    parts.append(f'<div class="dir">Directions: Translate the following passage into English.</div>')
    parts.append(f'<p class="body">{esc(data["translation"]["zh"])}</p>')
    parts.append('<textarea placeholder="Write your translation here"></textarea>')
    if MODE == "explain":
        tr = data["translation"]
        blk = []
        if tr.get("reference"):
            blk.append(f'<div class="sum"><b>参考译文</b><p class="body">{esc(tr["reference"])}</p></div>')
        if tr.get("points"):
            blk.append("<b>踩分点与译法</b>" + "".join(
                f'<div class="bands"><div>· {esc(x)}</div></div>' for x in tr["points"]))
        if blk:
            parts.append('<div class="sum">' + "".join(blk) + "</div>")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</title><style>{CSS}</style></head><body>
<div class="bar"><b>{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</b>
<span id="score">客观题 --</span>
<button onclick="check()">对答案</button><button onclick="showQA()">显示答案</button>
<button onclick="toggleAnalysis()">段落解析</button><button onclick="toggleAnswers()">题目解析</button><button onclick="window.print()">打印</button></div>
<div class="spacer"></div>
<div class="paper">{''.join(parts)}</div>
<div id="report"><div id="reportBox"><h3 style="margin:0 0 10pt">得分</h3><div id="reportBody"></div>
<button onclick="closeReport()" style="width:100%;margin-top:10pt;padding:6pt">关闭</button></div></div>
<div id="wdict"></div>
<script>{wjs}const PAPER = {json.dumps(data, ensure_ascii=False)};{JS}
wrapWords(document.querySelector(".paper"));</script></body></html>"""
    out = outdir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes, mode={args.mode})")


if __name__ == "__main__":
    main()
