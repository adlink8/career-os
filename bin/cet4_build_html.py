# -*- coding: utf-8 -*-
"""把一道「仔细阅读」JSON 渲染成单文件 HTML（可直接双击做题）。

用法: python bin/cet4_build_html.py <paper.json> [out.html]
"""
import json
import sys
from pathlib import Path

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · CET-4 模拟阅读</title>
<style>
:root{--bg:#fff;--fg:#111;--muted:#666;--line:#ddd;--ok:#0a7d32;--bad:#c62828;--hl:#fff3bf}
[data-theme=dark]{--bg:#121212;--fg:#e8e8e8;--muted:#9aa;--line:#333;--ok:#4caf50;--bad:#ef5350;--hl:#4a3f00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:24px 20px 80px}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--line);padding-bottom:10px;margin-bottom:18px}
h1{font-size:20px;margin:0}
.bar{display:flex;gap:14px;align-items:center;font-size:14px;color:var(--muted)}
#timer{font-weight:700;color:var(--fg);font-variant-numeric:tabular-nums}
button{cursor:pointer;border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:8px;padding:6px 12px;font-size:14px}
button:hover{background:rgba(127,127,127,.12)}
.p{white-space:pre-wrap;margin:0 0 16px}
.q{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:14px 0}
.q b{color:var(--muted)}
.opt{display:block;padding:6px 8px;border-radius:6px;margin:2px 0;cursor:pointer}
.opt:hover{background:rgba(127,127,127,.10)}
.opt.correct{background:rgba(10,125,50,.16);outline:1px solid var(--ok)}
.opt.wrong{background:rgba(198,40,40,.16);outline:1px solid var(--bad)}
.ans{display:none;margin-top:8px;padding-top:8px;border-top:1px dashed var(--line);font-size:14px}
.ans.show{display:block}
.ans .tag{display:inline-block;background:var(--muted);color:#fff;border-radius:4px;padding:0 6px;margin-right:6px;font-size:12px}
.sheet{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:18px 0}
.cell{border:1px solid var(--line);border-radius:8px;text-align:center;padding:6px 0;font-size:13px;cursor:pointer}
.cell.done{background:rgba(127,127,127,.15)}
.cell.ok{background:rgba(10,125,50,.2)}
.cell.bad{background:rgba(198,40,40,.2)}
.bi{margin:10px 0;padding:10px;border-left:3px solid var(--hl);background:rgba(255,243,191,.18);display:none}
.bi.show{display:block}
.bi .en{font-weight:600}
.bi .cn{color:var(--muted);font-size:14px}
.chip{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:10px;padding:0 8px;margin:2px 4px 2px 0;color:var(--muted)}
#score{font-weight:700}
.small{font-size:13px;color:var(--muted)}
footer{margin-top:40px;font-size:12px;color:var(--muted)}
</style></head><body><div class="wrap">
<header><h1>__TITLE__</h1><div class="bar"><span id="timer">40:00</span><span id="progress">0/5</span><button onclick="toggleBi()">双语逐句</button><button onclick="toggleTheme()">深色</button></div></header>
<div class="small">__META__</div>
<div id="passage" class="p"></div>
<div id="qs"></div>
<div class="sheet" id="sheet"></div>
<p><button onclick="check()">对答案</button> <span id="score"></span> <button onclick="resetAll()">清空重做</button></p>
<div id="bis"></div>
<div class="ans" id="explain"><span class="tag">解析</span><div id="explainBody"></div></div>
<footer>生成于 __DATE__ · 题目为外刊改写模拟题，非官方真题 · 数据来源：__SOURCE__</footer>
</div>
<script>
const PAPER = __PAPER__;
const ANSWERS = {};
PAPER.questions.forEach(q => ANSWERS[q.no] = q.answer);
const KEY = 'cet4-sim-' + PAPER.date;
let left = 40*60, tick = null, biOn = false;

function fmt(s){const m=String(Math.floor(s/60)).padStart(2,'0');const x=String(s%60).padStart(2,'0');return m+':'+x;}
function tickTimer(){ if(left<=0){clearInterval(tick); document.getElementById('score').textContent='时间到'; return;} left--; document.getElementById('timer').textContent=fmt(left); }

function render(){
  document.getElementById('passage').textContent = PAPER.passage;
  const qs = document.getElementById('qs');
  qs.innerHTML = PAPER.questions.map(q => {
    const opts = q.options.map(o => {
      const letter = o[0];
      return `<label class="opt" data-q="${q.no}" data-l="${letter}"><input type="radio" name="q${q.no}" value="${letter}" onchange="pick(${q.no})"> ${o}</label>`;
    }).join('');
    return `<div class="q" id="q${q.no}"><b>Q${q.no}</b> ${q.stem}<div>${opts}</div>
      <div class="ans" id="a${q.no}"><span class="tag">答案 ${q.answer}</span>${q.evidence ? '<div class="small">定位：'+q.evidence+'</div>' : ''}
      ${q.paraphrase ? '<div class="small">同义替换：'+q.paraphrase.original+' → '+q.paraphrase.option+'</div>' : ''}
      ${q.trap ? '<div class="small">陷阱：'+q.trap+'</div>' : ''}</div></div>`;
  }).join('');
  const sheet = document.getElementById('sheet');
  sheet.innerHTML = PAPER.questions.map(q => `<div class="cell" id="c${q.no}" onclick="jump(${q.no})">${q.no}</div>`).join('');
  const bis = document.getElementById('bis');
  bis.innerHTML = PAPER.sentences.map(s => `<div class="bi"><div class="en">${s.en}</div><div class="cn">${s.cn}</div>${(s.chunks||[]).map(c=>`<span class="chip">${c.en} → ${c.cn}</span>`).join('')}</div>`).join('');
}
function pick(n){
  const v = document.querySelector(`input[name=q${n}]:checked`);
  document.getElementById('c'+n).classList.toggle('done', !!v);
  document.getElementById('progress').textContent = answered()+'/5';
  save();
}
function answered(){ return PAPER.questions.filter(q => document.querySelector(`input[name=q${q.no}]:checked`)).length; }
function jump(n){ document.getElementById('q'+n).scrollIntoView({behavior:'smooth',block:'center'}); }
function check(){
  let right=0;
  PAPER.questions.forEach(q => {
    const v = document.querySelector(`input[name=q${q.no}]:checked`);
    const cell = document.getElementById('c'+q.no);
    document.querySelectorAll(`.opt[data-q="${q.no}"]`).forEach(el => {
      el.classList.remove('correct','wrong');
      if(el.dataset.l === q.answer) el.classList.add('correct');
      if(v && v.value === el.dataset.l && v.value !== q.answer) el.classList.add('wrong');
    });
    const ok = v && v.value === q.answer; if(ok) right++;
    cell.classList.remove('ok','bad'); cell.classList.add(ok?'ok':'bad');
    document.getElementById('a'+q.no).classList.add('show');
  });
  document.getElementById('score').textContent = '得分 '+right+'/5（已答 '+answered()+'）';
  document.getElementById('explain').classList.add('show');
  document.getElementById('explainBody').innerHTML = PAPER.questions.map(q =>
    `<div class="small"><b>Q${q.no}</b> 正确答案 ${q.answer}；${q.paraphrase?('同义替换：'+q.paraphrase.original+' → '+q.paraphrase.option):''}${q.trap?('；陷阱：'+q.trap):''}</div>`).join('');
  save();
}
function resetAll(){ if(!confirm('清空作答？')) return; localStorage.removeItem(KEY); location.reload(); }
function toggleBi(){ biOn=!biOn; document.querySelectorAll('.bi').forEach(e=>e.classList.toggle('show',biOn)); }
function toggleTheme(){ const d=document.documentElement; const n=d.getAttribute('data-theme')==='dark'?'light':'dark'; d.setAttribute('data-theme',n); localStorage.setItem('cet4-sim-theme',n); }
function save(){ try{ const ans={}; PAPER.questions.forEach(q=>{const v=document.querySelector(`input[name=q${q.no}]:checked`); if(v) ans[q.no]=v.value;}); localStorage.setItem(KEY, JSON.stringify({ans,left})); }catch(e){} }
function load(){ try{ const raw=localStorage.getItem(KEY); if(!raw) return; const d=JSON.parse(raw); if(d.left) {left=d.left; document.getElementById('timer').textContent=fmt(left);} Object.entries(d.ans||{}).forEach(([n,v])=>{const el=document.querySelector(`input[name=q${n}][value="${v}"]`); if(el){el.checked=true; document.getElementById('c'+n).classList.add('done');}}); document.getElementById('progress').textContent=answered()+'/5'; }catch(e){} }
document.addEventListener('keydown', e => { if(e.key>='1'&&e.key<='4'){ const n=window.__cur||1; const el=document.querySelector(`input[name=q${n}][value="${'ABCD'[+e.key-1]}"]`); if(el){el.checked=true;pick(n);} } });
render(); load(); tick=setInterval(tickTimer,1000);
</script></body></html>"""


def main():
    src = Path(sys.argv[1])
    paper = json.loads(src.read_text(encoding="utf-8"))
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    meta = f"{paper.get('topic','')} · {paper.get('difficulty',{}).get('words','')} 词 · CEFR {paper.get('difficulty',{}).get('cefr','')}"
    html = (TEMPLATE
            .replace("__TITLE__", f"{paper.get('title','')} · {paper.get('title_cn','')}")
            .replace("__META__", meta)
            .replace("__DATE__", paper.get("date", ""))
            .replace("__SOURCE__", paper.get("source", ""))
            .replace("__PAPER__", json.dumps(paper, ensure_ascii=False)))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
