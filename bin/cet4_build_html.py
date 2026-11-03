# -*- coding: utf-8 -*-
"""「仔细阅读」JSON -> 与四级真题卷面一致的 A4 试卷 HTML（含句级成分解析）。

卷面参数取自真题 PDF（2024-06 第 1 套）实测：
- A4 595.32 × 841.92 pt；左右边距 36pt、上 38pt
- Times New Roman 10.5pt，行距 15.6pt（≈1.5）
- 正文首行缩进 2 字符（57-36=21pt）
- 选项两栏：A)/C) 同行，B)/D) 下一行

段落解析（默认隐藏）：每段英文后跟该段中文、主旨、作用，以及逐句「主谓宾/状定补」成分标注。

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
*{box-sizing:border-box}
html,body{margin:0;background:#e9e9e9}
body{font-family:"Times New Roman","SimSun",serif;color:#000;font-size:10.5pt;line-height:1.5}
.paper{width:595.32pt;min-height:841.92pt;margin:16pt auto;background:#fff;padding:38pt 36pt 30pt;box-shadow:0 2px 16px rgba(0,0,0,.18)}
.partrow{display:flex;align-items:baseline;font-weight:bold;margin:6pt 0}
.partrow .c{flex:1;text-align:center}
.partrow .r{text-align:right}
.sec{font-weight:bold;margin:6pt 0 4pt}
.dir{margin:4pt 0 6pt}
.dir i{font-style:italic}
.ptitle{font-weight:bold;margin:8pt 0 2pt}
.passage p{text-indent:2em;margin:0 0 5pt;text-align:justify}
.q{margin:9pt 0 0}
.opts{display:grid;grid-template-columns:1fr 1fr;column-gap:14pt;padding-left:12pt}
.opt{display:block;padding:0 2pt;border-radius:2px;cursor:pointer}
.opt input{display:none}
.opt:hover{background:#f2f2f2}
.opt.correct{background:#d9f2df;outline:1px solid #2e7d32}
.opt.wrong{background:#fde0e0;outline:1px solid #c62828}
.tools{position:fixed;top:12px;right:12px;display:flex;gap:8px;font:13px/1.4 -apple-system,"Microsoft YaHei",sans-serif;z-index:9}
.tools button,.tools .score{border:1px solid #999;background:#fff;border-radius:6px;padding:6px 10px;cursor:pointer}
.sheet{position:fixed;left:12px;top:12px;display:grid;grid-template-columns:repeat(5,24px);gap:4px;font:11px/1.5 -apple-system,sans-serif}
.sheet .cell{border:1px solid #999;background:#fff;text-align:center;border-radius:3px;cursor:pointer}
.sheet .cell.done{background:#eee}
.sheet .cell.ok{background:#c8e6c9}
.sheet .cell.bad{background:#ffcdd2}
.para-ans{display:none;margin:2pt 0 8pt;padding:8pt 10pt;border-left:2pt solid #c9a227;background:#fbf9f1;font:9.5pt/1.7 -apple-system,"Microsoft YaHei","SimSun",sans-serif}
.para-ans.show{display:block}
.para-ans .cn{margin-bottom:5pt}
.sent{margin:6pt 0;padding-top:4pt;border-top:1px dashed #ddd}
.sent .en{font-weight:600}
.role{font-weight:600}
.r-主{color:#1565c0}.r-谓{color:#c62828}.r-宾{color:#2e7d32}.r-状{color:#ef6c00}.r-定{color:#6a1b9a}.r-补{color:#00838f}.r-表{color:#5d4037}.r-连{color:#777;font-style:italic;font-weight:400}
.small{color:#555;font-size:8.5pt}
.chip{display:inline-block;border:1px solid #ddd;border-radius:8px;padding:0 5px;margin:1px 3px 1px 0;font-size:8.5pt;color:#444}
.qans{display:none;margin:4pt 0 0;padding:6pt 8pt;border-left:2pt solid #c9a227;background:#fbf9f1;font:9pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.qans.show{display:block}
.footer{margin-top:14pt;padding-top:4pt;border-top:1px solid #ddd;font-size:9pt;color:#555;display:flex;justify-content:space-between}
.notice{width:595.32pt;margin:0 auto 4pt;font:12px/1.5 -apple-system,"Microsoft YaHei";color:#555}
@media (max-width:640px){.paper{width:auto;min-height:auto;margin:8px;padding:16px}.small{font-size:11pt}body{font-size:12pt}.sheet{display:none}.tools{top:6px;right:6px}}
@media print{
  html,body{background:#fff}
  .tools,.sheet,.notice,.para-ans{display:none !important}
  .paper{box-shadow:none;margin:0;width:auto;min-height:auto;padding:0}
  @page{size:A4;margin:38pt 36pt 30pt}
}
</style></head><body>
<div class="notice">CET-4 阅读模拟卷（非官方真题） · __META__ · 生成于 __DATE__ · 来源 __SOURCE__</div>
<div class="sheet" id="sheet"></div>
<div class="tools">
  <span class="score" id="answered">已答 0/5</span><span class="score" id="score">得分 —</span>
  <span class="score" id="timer">40:00</span>
  <button onclick="toggleAnalysis()">段落解析</button>
  <button onclick="check()">对答案</button>
</div>

<div class="paper">
  <div class="partrow"><span>Part III</span><span class="c">Reading Comprehension</span><span class="r">(40 minutes)</span></div>
  <div class="sec">Section C</div>
  <div class="dir"><i>Directions: Read the following passage carefully. For each question, choose the best answer from the four choices marked A), B), C) and D).</i></div>
  <div class="ptitle">Passage One</div>
  <div class="dir">Questions 46 to 50 are based on the following passage.</div>
  <div class="passage" id="passage"></div>
  <div id="qs"></div>
  <div class="footer"><span>CET-4 模拟阅读</span><span>1</span></div>
</div>

<script>
const PAPER = __PAPER__;
const OFF = 45;
const KEY = 'cet4-sim-' + PAPER.date;
let left = 40*60, tick = null, analysisOn = false;

function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function tickTimer(){ if(left<=0){clearInterval(tick); const t=document.getElementById('timer'); t.textContent='时间到'; t.style.color='#c62828'; return;} left--; document.getElementById('timer').textContent=fmt(left); }

function roleSpan(chunk){
  const role = chunk.role || '成';
  return `<span class="role r-${role}">${chunk.en} <span class="small">[${role}：${chunk.cn||''}]</span></span>`;
}

function paraBlock(para){
  const sents = (para.sentences||[]).map(s => `
    <div class="sent">
      <div class="en">${(s.chunks&&s.chunks.length) ? s.chunks.map(roleSpan).join(' ') : (s.en||'')}</div>
      ${s.meaning?`<div class="small">意思：${s.meaning}</div>`:''}
      ${s.modifier?`<div class="small">谁修饰谁：${s.modifier}</div>`:''}
      ${s.why?`<div class="small">为啥：${s.why}</div>`:''}
      ${s.collocation?`<div class="small">搭配/固定短语：${s.collocation}</div>`:''}
    </div>`).join('');
  return `<div class="para">
    <p>${(para.en||'').trim()}</p>
    <div class="para-ans">
      <div class="cn">${(para.cn||'').trim()}</div>
      ${para.main?`<div class="small">本段主旨：${para.main}</div>`:''}
      ${para.structure?`<div class="small">段落作用：${para.structure}</div>`:''}
      ${sents}
    </div>
  </div>`;
}

function renderPassage(){
  const el = document.getElementById('passage');
  el.innerHTML = (PAPER.paragraphs && PAPER.paragraphs.length)
    ? PAPER.paragraphs.map(paraBlock).join('')
    : `<p>${PAPER.passage}</p>`;
}

function renderQuestions(){
  const order = [0,2,1,3];
  document.getElementById('qs').innerHTML = PAPER.questions.map(q => {
    const opts = order.map(i => q.options[i]).map(o => {
      const letter = o[0];
      return `<label class="opt" data-q="${q.no}" data-l="${letter}"><input type="radio" name="q${q.no}" value="${letter}" onchange="pick(${q.no})">${o}</label>`;
    }).join('');
    return `<div class="q" id="q${q.no}"><div class="stem">${q.no+OFF}. ${q.stem}</div><div class="opts">${opts}</div>
      <div class="qans" id="qa${q.no}"></div></div>`;
  }).join('');
  document.getElementById('sheet').innerHTML = PAPER.questions.map(q => `<div class="cell" id="c${q.no}" onclick="jump(${q.no})">${q.no+OFF}</div>`).join('');
}

function pick(n){
  document.getElementById('c'+n).classList.toggle('done', !!document.querySelector(`input[name=q${n}]:checked`));
  document.getElementById('answered').textContent = '已答 '+answered()+'/5';
  save();
}
function answered(){ return PAPER.questions.filter(q=>document.querySelector(`input[name=q${q.no}]:checked`)).length; }
function jump(n){ document.getElementById('q'+n).scrollIntoView({behavior:'smooth',block:'center'}); }

function check(){
  let right=0;
  PAPER.questions.forEach(q => {
    const v = document.querySelector(`input[name=q${q.no}]:checked`);
    document.querySelectorAll(`.opt[data-q="${q.no}"]`).forEach(el => {
      el.classList.remove('correct','wrong');
      if(el.dataset.l === q.answer) el.classList.add('correct');
      if(v && v.value === el.dataset.l && v.value !== q.answer) el.classList.add('wrong');
    });
    const ok = v && v.value === q.answer; if(ok) right++;
    const cell = document.getElementById('c'+q.no); cell.classList.remove('ok','bad'); cell.classList.add(ok?'ok':'bad');
    const qa = document.getElementById('qa'+q.no);
    if (qa) {
      const oa = (q.option_analysis||[]).map(x => `<div class="small">${x.letter}) ${x.correct?'✓':'✗'} ${x.why||''}</div>`).join('');
      qa.innerHTML = `<div><b>答案 ${q.answer}</b></div>` +
        (q.evidence?`<div class="small">定位：${q.evidence}</div>`:'') +
        (q.paraphrase?`<div class="small">同义替换：${q.paraphrase.original} → ${q.paraphrase.option}</div>`:'') +
        (q.trap?`<div class="small">陷阱：${q.trap}</div>`:'') + oa;
      qa.classList.add('show');
    }
  });
  document.getElementById('score').textContent = '得分 '+right+'/5';
  save();
}
function toggleAnalysis(){ analysisOn=!analysisOn; document.querySelectorAll('.para-ans').forEach(e=>e.classList.toggle('show',analysisOn)); }
function save(){ try{ const ans={}; PAPER.questions.forEach(q=>{const v=document.querySelector(`input[name=q${q.no}]:checked`); if(v) ans[q.no]=v.value;}); localStorage.setItem(KEY, JSON.stringify({ans,left})); }catch(e){} }
function load(){ try{ const raw=localStorage.getItem(KEY); if(!raw) return; const d=JSON.parse(raw); if(d.left){left=d.left;document.getElementById('timer').textContent=fmt(left);} Object.entries(d.ans||{}).forEach(([n,v])=>{const el=document.querySelector(`input[name=q${n}][value="${v}"]`); if(el){el.checked=true;document.getElementById('c'+n).classList.add('done');}}); document.getElementById('score').textContent=answered()+'/5'; }catch(e){} }

renderPassage(); renderQuestions(); load(); tick=setInterval(tickTimer,1000);
</script></body></html>"""


def main():
    src = Path(sys.argv[1])
    paper = json.loads(src.read_text(encoding="utf-8"))
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    meta = f"{paper.get('topic','')} · {len(paper.get('passage','').split())} 词 · CEFR {paper.get('difficulty',{}).get('cefr','')}"
    html = (TEMPLATE
            .replace("__TITLE__", paper.get("title", ""))
            .replace("__META__", meta)
            .replace("__DATE__", paper.get("date", ""))
            .replace("__SOURCE__", paper.get("source", ""))
            .replace("__PAPER__", json.dumps(paper, ensure_ascii=False)))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
