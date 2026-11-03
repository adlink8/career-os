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

#ink{position:absolute;left:0;top:0;width:100%;pointer-events:none;z-index:5}
#ink.on{pointer-events:auto;cursor:crosshair}
#floatTool{position:fixed;right:18px;bottom:18px;z-index:20;font:13px/1.5 -apple-system,"Microsoft YaHei",sans-serif}
#floatTool .bubble{background:#111;color:#fff;border-radius:22px;padding:10px 14px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3)}
#tbPanel{display:none;width:240px;background:#fff;border:1px solid #bbb;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.25);padding:10px;margin-bottom:8px}
#tbPanel.show{display:block}
#tbPanel .head{display:flex;justify-content:space-between;align-items:center;font-weight:700;margin-bottom:6px}
#tbPanel .grp{border-top:1px dashed #ddd;padding-top:6px;margin-top:6px}
#tbPanel .lbl{color:#666;font-size:11px;margin-bottom:4px}
#tbPanel button{font-size:12px;margin:2px 2px 0 0;padding:4px 7px;border:1px solid #ccc;background:#fafafa;border-radius:6px;cursor:pointer}
#tbPanel button.active{background:#111;color:#fff;border-color:#111}
#tbPanel .span2{display:block;width:100%;text-align:left}
#tbPanel select{font-size:12px;margin:2px 2px 0 0;padding:3px 4px;border:1px solid #ccc;border-radius:6px;background:#fafafa}
.audioBar{width:595.32pt;margin:0 auto 6pt;display:flex;gap:10px;align-items:center;font:12px/1.5 -apple-system,"Microsoft YaHei";position:sticky;top:0;z-index:25;background:#fff;padding:6pt 0 4pt;box-shadow:0 4px 10px -6px rgba(0,0,0,.35)}
.audioBar audio{width:320px;height:32px}
.audioBar{flex-wrap:wrap}
#subs{flex:1 1 100%;max-height:58px;overflow:auto;border:1px solid #ddd;border-radius:6px;padding:4px 6px;background:#fcfcf8}
#subs div{padding:1px 2px;border-radius:3px;cursor:pointer;color:#444}
#subs div.on{background:#fff3a8;color:#000}
#subs .s-en{font-weight:600}
#subs .s-cn{color:#666;font-size:8.5pt}
#vocab{display:none;margin:10pt 0 4pt;padding:8pt 10pt;border:1px solid #ddd;border-radius:6pt;background:#fcfcf8}
#vocab.show{display:block}
#vocab table{border-collapse:collapse;width:100%;font-size:9.5pt}
#vocab td,#vocab th{border-bottom:1px dashed #ddd;padding:2pt 4pt;text-align:left}
#vocab th{color:#666;font-weight:600}
#srsModal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:30;align-items:center;justify-content:center}
#srsModal.show{display:flex}
#srsBox{background:#fff;border-radius:12px;padding:16px;width:360px;font:14px/1.6 -apple-system,"Microsoft YaHei"}
#srsBox h3{margin:0 0 10px;font-size:15px}
#srsBox .card{border:1px solid #ddd;border-radius:8px;padding:10px;margin-bottom:8px}
#srsBox .word{font-weight:700;font-size:16px}
#srsBox .btns{display:flex;gap:8px;margin-top:8px}
#srsBox button{flex:1;padding:6px;border:1px solid #ccc;border-radius:8px;background:#fafafa;cursor:pointer}
#srsBox .close{width:100%;margin-top:6px}
@media print{.audioBar,#vocab,#srsModal{display:none !important}}
mark.hl-yellow{background:#fff3a8}mark.hl-red{background:#ffd6d6}mark.hl-orange{background:#ffe0b2}
mark.hl-green{background:#c8e6c9}mark.hl-purple{background:#e1bee7}
span.redline{text-decoration:underline;text-decoration-color:#e53935;text-decoration-thickness:2px}
span.noted{background:#fff8e1;border-bottom:1px dotted #c9a227;cursor:help}
@media print{#floatTool,#ink{display:none !important}}
</style></head><body>
<div class="audioBar" id="audioBar" style="display:none"><audio id="pAudio" controls preload="none"></audio><span class="small">朗读：文章 + 题干 + 选项</span><div id="subs"></div></div>
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
  <div id="vocab"></div>
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

function paraBlock(para, idx){
  const sents = (para.sentences||[]).map(s => `
    <div class="sent">
      <div class="en">${(s.chunks&&s.chunks.length) ? s.chunks.map(roleSpan).join(' ') : (s.en||'')}</div>
      ${s.meaning?`<div class="small">意思：${s.meaning}</div>`:''}
      ${s.modifier?`<div class="small">谁修饰谁：${s.modifier}</div>`:''}
      ${s.why?`<div class="small">为啥：${s.why}</div>`:''}
      ${s.collocation?`<div class="small">搭配/固定短语：${s.collocation}</div>`:''}
    </div>`).join('');
  return `<div class="para" data-ink="p${idx}">
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
    ? PAPER.paragraphs.map((p,i)=>paraBlock(p,i)).join('')
    : `<p>${PAPER.passage}</p>`;
}

function renderQuestions(){
  const order = [0,2,1,3];
  document.getElementById('qs').innerHTML = PAPER.questions.map(q => {
    const opts = order.map(i => q.options[i]).map(o => {
      const letter = o[0];
      return `<label class="opt" data-q="${q.no}" data-l="${letter}"><input type="radio" name="q${q.no}" value="${letter}" onchange="pick(${q.no})">${o}</label>`;
    }).join('');
    return `<div class="q" id="q${q.no}" data-ink="q${q.no}"><div class="stem">${q.no+OFF}. ${q.stem}</div><div class="opts">${opts}</div>
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
</script>
<canvas id="ink"></canvas>
<div id="floatTool" style="left:auto;right:18px;bottom:18px">
  <div id="tbPanel">
    <div class="head"><span>✏️ 工具</span><button onclick="tbToggle()">收起 ✕</button></div>
    <div class="grp"><div class="lbl">选文字</div>
      <button onclick="wrapSel('span','redline')">🔴 红线</button>
      <button onclick="wrapSel('mark','hl-yellow')">🟡 荧光笔</button>
      <button onclick="wrapSel('mark','hl-green')">🟢 答案句</button>
    </div>
    <div class="grp"><div class="lbl">标记</div>
      <button onclick="wrapSel('mark','hl-red')">🔴 不会翻译</button>
      <button onclick="wrapSel('mark','hl-orange')">🟠 不认识单词</button>
      <button onclick="wrapSel('mark','hl-purple')">🟣 重点</button>
      <button onclick="clearMarks()">清除标记</button>
    </div>
    <div class="grp"><div class="lbl">批注与画笔</div>
      <button class="span2" onclick="addNote()">💬 给选中文字加批注</button>
      <button id="tbPen" onclick="toggleInk()">✒️ 画笔</button>
      <button id="tbErase" onclick="toggleErase()">🧽 橡皮</button>
      <button onclick="clearInk()">清除画画</button>
      <select id="penColor"><option value="#e53935">红笔</option><option value="#111111">黑笔</option><option value="#1565c0">蓝笔</option></select>
      <select id="penWidth"><option value="2">细</option><option value="3" selected>中</option><option value="6">粗</option></select>
    </div>
    <div class="grp"><div class="lbl">生词与复习</div>
      <button class="span2" onclick="toggleVocab()">📖 生词表</button>
      <button class="span2" onclick="openSrs()">⏰ 今日复习 <span id="srsDue"></span></button>
    </div>
    <div class="grp"><div class="lbl">保存与导出</div>
      <button onclick="saveAll()">💾 保存</button>
      <button onclick="exportNotes()">⬇️ 导出笔记</button>
    </div>
  </div>
  <div class="bubble" id="tbBubble">✏️ 工具</div>
</div>
<script>
let tbOpen=false, inkOn=false, eraseOn=false, strokes=[], cur=null, drag=null;
const float=document.getElementById('floatTool'), cvs=document.getElementById('ink'), ctx=cvs.getContext('2d');

/* ---------- 工具栏拖动 ---------- */
function restorePos(){try{const p=JSON.parse(localStorage.getItem('cet4-tool-pos')||'null');if(!p)return;float.style.left=p.left+'px';float.style.top=p.top+'px';float.style.right='auto';float.style.bottom='auto';}catch(e){}}
function startDrag(e){ if(e.target.closest('#tbPanel')) return; const r=float.getBoundingClientRect();
  drag={x:e.clientX,y:e.clientY,left:r.left,top:r.top,moved:false};
  float.setPointerCapture&&e.target.setPointerCapture&&e.target.setPointerCapture(e.pointerId);
  e.preventDefault(); }
document.addEventListener('pointermove', e=>{ if(!drag) return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
  if(Math.abs(dx)>4||Math.abs(dy)>4) drag.moved=true;
  const w=float.offsetWidth,h=float.offsetHeight;
  let L=Math.min(Math.max(0,drag.left+dx), innerWidth-w), T=Math.min(Math.max(0,drag.top+dy), innerHeight-40);
  float.style.left=L+'px'; float.style.top=T+'px'; float.style.right='auto'; float.style.bottom='auto'; });
document.addEventListener('pointerup', ()=>{ if(!drag) return; const d=drag; drag=null;
  if(d.moved){ try{localStorage.setItem('cet4-tool-pos',JSON.stringify({left:parseInt(float.style.left),top:parseInt(float.style.top)}));}catch(e){} }
  else { tbToggle(); } });
document.getElementById('tbBubble').addEventListener('pointerdown', startDrag);

/* ---------- 画笔：词级锚定 ---------- */
function caretAt(x,y){ const d=cvs.style.display; cvs.style.display='none';
  const cp=document.caretPositionFromPoint?document.caretPositionFromPoint(x,y):null;
  cvs.style.display=d; return cp; }
function anchorAt(x,y){ const els=document.elementsFromPoint(x,y); for(const el of els){ const a=el.closest&&el.closest('[data-ink]'); if(a) return a; } return document.querySelector('.passage'); }
function textOffset(el, node, off){ let total=0; const w=document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
  while((n=w.nextNode())){ if(n===node) return total+off; total+=n.textContent.length; } return null; }
function rangeAt(el, off){ let total=0; const w=document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
  while((n=w.nextNode())){ const L=n.textContent.length;
    if(off<=total+L){ const r=document.createRange(); r.setStart(n, Math.max(0,off-total)); r.setEnd(n, Math.min(L, Math.max(0,off-total)+1)); return r; }
    total+=L; } return null; }
function absPoint(st, pt){ const el=document.querySelector(`[data-ink="${st.anchor}"]`);
  if(!el) return null;
  if(pt.off!=null){ const r=rangeAt(el, pt.off);
    if(r){ const b=r.getBoundingClientRect();
      if(b.width||b.height) return {x:b.left+scrollX+pt.dx, y:b.top+scrollY+pt.dy}; } }
  const b=el.getBoundingClientRect(); return {x:b.left+scrollX+pt.dx, y:b.top+scrollY+pt.dy}; }
function redraw(){ ctx.clearRect(0,0,cvs.width,cvs.height); ctx.lineCap='round'; ctx.lineJoin='round';
  strokes.forEach(st=>{ ctx.strokeStyle=st.color||'#e53935'; ctx.lineWidth=st.width||3; ctx.beginPath(); let started=false;
    st.pts.forEach(pt=>{ const a=absPoint(st,pt); if(!a) return; started?ctx.lineTo(a.x,a.y):(ctx.moveTo(a.x,a.y),started=true); });
    if(started) ctx.stroke(); }); }
function sizeInk(){ cvs.width=Math.max(document.documentElement.scrollWidth,innerWidth);
  cvs.height=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight,innerHeight); redraw(); }
function toggleInk(){ inkOn=!inkOn; eraseOn=false; cvs.classList.toggle('on',inkOn);
  document.getElementById('tbPen').classList.toggle('active',inkOn); document.getElementById('tbErase').classList.remove('active'); }
function toggleErase(){ eraseOn=!eraseOn; inkOn=eraseOn; cvs.classList.toggle('on',inkOn);
  document.getElementById('tbErase').classList.toggle('active',eraseOn); document.getElementById('tbPen').classList.remove('active'); }
function clearInk(){ strokes=[]; redraw(); saveAll(); }
cvs.addEventListener('pointerdown', e=>{ if(!inkOn) return;
  const px=e.clientX+scrollX, py=e.clientY+scrollY;
  if(eraseOn){ strokes=strokes.filter(st=>!st.pts.some(pt=>{const a=absPoint(st,pt); return a && Math.hypot(a.x-px,a.y-py)<14;})); redraw(); saveAll(); return; }
  const el=anchorAt(e.clientX,e.clientY);
  const cp=caretAt(e.clientX,e.clientY);
  let off=null; if(cp && el.contains(cp.offsetNode)) off=textOffset(el, cp.offsetNode, cp.offset);
  const r = (cp && off!=null && rangeAt(el,off)) ? rangeAt(el,off).getBoundingClientRect() : el.getBoundingClientRect();
  const color=document.getElementById('penColor')?.value||'#e53935';
  const width=parseInt(document.getElementById('penWidth')?.value||'3',10);
  cur={anchor:el.dataset.ink, color, width, pts:[{off, dx:px-(r.left+scrollX), dy:py-(r.top+scrollY)}]};
  strokes.push(cur); });
cvs.addEventListener('pointermove', e=>{ if(!cur) return; const el=document.querySelector(`[data-ink="${cur.anchor}"]`); if(!el) return;
  const cp=caretAt(e.clientX,e.clientY);
  let off=null; if(cp && el.contains(cp.offsetNode)) off=textOffset(el, cp.offsetNode, cp.offset);
  const r=(cp && off!=null && rangeAt(el,off))?rangeAt(el,off).getBoundingClientRect():el.getBoundingClientRect();
  cur.pts.push({off, dx:e.clientX+scrollX-(r.left+scrollX), dy:e.clientY+scrollY-(r.top+scrollY)}); redraw(); });
cvs.addEventListener('pointerup', ()=>{ if(cur){cur=null; saveAll();} });
window.addEventListener('resize', sizeInk);
if(window.ResizeObserver){ new ResizeObserver(()=>sizeInk()).observe(document.querySelector('.paper')); }

/* ---------- 标记 / 批注 ---------- */
function wrapSel(tag,cls){const sel=getSelection();if(!sel.rangeCount||sel.isCollapsed){alert('先选中文字');return;}
  const r=sel.getRangeAt(0);const el=document.createElement(tag);el.className=cls;
  try{r.surroundContents(el);}catch(e){el.appendChild(r.extractContents());r.insertNode(el);}
  sel.removeAllRanges();saveAll();}
function addNote(){const sel=getSelection();if(!sel.rangeCount||sel.isCollapsed){alert('先选中文字');return;}
  const note=prompt('批注内容：');if(!note)return;
  const r=sel.getRangeAt(0);const el=document.createElement('span');el.className='noted';el.title=note;el.dataset.note=note;
  try{r.surroundContents(el);}catch(e){el.appendChild(r.extractContents());r.insertNode(el);}
  sel.removeAllRanges();saveAll();}
function clearMarks(){document.querySelectorAll('.paper mark,.paper span.redline').forEach(el=>{const p=el.parentNode;while(el.firstChild)p.insertBefore(el.firstChild,el);p.removeChild(el);});saveAll();}
function exportNotes(){const notes=[...document.querySelectorAll('.paper span.noted')].map(el=>({text:el.textContent,note:el.dataset.note||''}));
  let txt='批注导出\n\n'+notes.map((n,i)=>`#${i+1} 原文：${n.text}\n批注：${n.note}\n`).join('\n');
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([txt],{type:'text/plain;charset=utf-8'}));a.download='阅读批注.txt';a.click();}

/* ---------- 保存 / 载入 ---------- */
function saveAll(){try{const paper=document.querySelector('.paper');localStorage.setItem('cet4-tool-'+(PAPER.date||''),JSON.stringify({html:paper.innerHTML,strokes:strokes.map(s=>({anchor:s.anchor,color:s.color,width:s.width,pts:s.pts}))}));}catch(e){}}
function loadAll(){try{const raw=localStorage.getItem('cet4-tool-'+(PAPER.date||''));if(!raw)return;const d=JSON.parse(raw);
  if(d.html){document.querySelector('.paper').innerHTML=d.html;}
  if(d.strokes){strokes=d.strokes;redraw();}}catch(e){}}
function tbToggle(){tbOpen=!tbOpen;document.getElementById('tbPanel').classList.toggle('show',tbOpen);}
function snapshotHooks(){}
document.addEventListener('change',e=>{const t=e.target;if(t&&t.name&&t.name.startsWith('q')){const n=+t.name.slice(1);
  const c=document.getElementById('c'+n); c&&c.classList.add('done');
  const a=document.getElementById('answered'); if(a) a.textContent='已答 '+PAPER.questions.filter(q=>document.querySelector(`input[name=q${q.no}]:checked`)).length+'/5';
  saveAll();}});

/* ---------- 生词表 ---------- */
function allVocab(){ const out=[]; (PAPER.paragraphs||[]).forEach(p=>(p.vocab||[]).forEach(v=>out.push(v))); return out; }
function toggleVocab(){ const v=document.getElementById('vocab'); v.classList.toggle('show'); }
function speak(w){ if(!window.speechSynthesis) return; const u=new SpeechSynthesisUtterance(w); u.lang='en-US'; speechSynthesis.cancel(); speechSynthesis.speak(u); }
function renderVocab(){ const rows=allVocab(); const box=document.getElementById('vocab'); if(!rows.length){ box.innerHTML='<div class="small">本篇暂无生词表（需用新版契约重新生成）</div>'; return; }
  box.innerHTML='<div class="small" style="margin-bottom:4pt">生词表（点单词朗读）</div><table><tr><th>单词</th><th>音标</th><th>释义</th></tr>'+
    rows.map(v=>`<tr><td><a href="javascript:speak('${(v.word||'').replace(/'/g,"")}')">${v.word||''}</a></td><td>${v.phonetic||''}</td><td>${v.cn||''}</td></tr>`).join('')+'</table>'; }
/* ---------- 遗忘曲线复习 ---------- */
function todayKey(){ const d=new Date(); return d.toISOString().slice(0,10); }
function addDays(n){ const d=new Date(); d.setDate(d.getDate()+n); return d.toISOString().slice(0,10); }
function srsLoad(){ try{ return JSON.parse(localStorage.getItem('cet4-srs')||'{}'); }catch(e){ return {}; } }
function srsSave(o){ localStorage.setItem('cet4-srs', JSON.stringify(o)); }
function initSrs(){ const st=srsLoad(); const t=todayKey();
  allVocab().forEach(v=>{ const k=(v.word||'').toLowerCase(); if(!k) return;
    if(!st[k]) st[k]={word:v.word, phonetic:v.phonetic||'', cn:v.cn||'', due:t, interval:1, reps:0};
    else { st[k].cn=v.cn||st[k].cn; st[k].phonetic=v.phonetic||st[k].phonetic; } });
  srsSave(st); const due=Object.values(st).filter(c=>c.due<=t).length;
  const el=document.getElementById('srsDue'); if(el) el.textContent=due?`(${due})`:''; }
function openSrs(){ document.getElementById('srsModal').classList.add('show'); renderSrs(); }
function closeSrs(){ document.getElementById('srsModal').classList.remove('show'); }
function rate(k, how){ const st=srsLoad(); const c=st[k]; if(!c) return;
  c.reps=(c.reps||0)+1;
  if(how==='forget'){ c.interval=1; }
  else if(how==='fuzzy'){ c.interval=Math.max(2, Math.round((c.interval||1)*1.6)); }
  else { c.interval=Math.max(4, Math.round((c.interval||1)*2.3)); }
  c.interval=Math.min(60,c.interval); c.due=addDays(c.interval);
  srsSave(st); renderSrs(); initSrs(); }
function renderSrs(){ const st=srsLoad(); const t=todayKey(); const due=Object.values(st).filter(c=>c.due<=t);
  const box=document.getElementById('srsToday');
  if(!due.length){ box.innerHTML='<div class="small">今天没有到期生词。</div>'; return; }
  box.innerHTML=due.slice(0,3).map(c=>`<div class="card"><div class="word">${c.word}</div><div class="small">${c.phonetic||''} ${c.cn||''}</div>
    <div class="btns"><button onclick="rate('${c.word.toLowerCase()}','forget')">忘记</button>
    <button onclick="rate('${c.word.toLowerCase()}','fuzzy')">模糊</button>
    <button onclick="rate('${c.word.toLowerCase()}','know')">记得</button></div></div>`).join('')+
    `<div class="small">剩余 ${due.length} 个 · 下次到期自动按 1/2/4/7/15/30 天递进</div>`; }

/* ---------- 音频字幕 ---------- */
function renderSubs(){ if(!PAPER.timing || !PAPER.timing.length) return; const box=document.getElementById('subs');
  box.innerHTML=PAPER.timing.map(x=>`<div data-t="${x.start}" onclick="seekTo(${x.start})"><div class="s-en">${x.en||x.text||''}</div><div class="s-cn">${x.cn||''}</div></div>`).join(''); }
function seekTo(t){ const a=document.getElementById('pAudio'); if(!a) return; a.currentTime=t; a.play&&a.play(); }
function syncSubs(){ const a=document.getElementById('pAudio'); if(!a||!PAPER.timing) return; const t=a.currentTime;
  const lines=document.querySelectorAll('#subs div'); let cur=null;
  for(const el of lines){ const st=parseFloat(el.dataset.t); if(st<=t+0.05) cur=el; else break; }
  lines.forEach(el=>el.classList.toggle('on', el===cur));
  if(cur && !cur.dataset.scrolled){ cur.scrollIntoView({block:'nearest'}); }
}

/* ---------- 音频 ---------- */
function initAudio(){ if(!PAPER.audio) return; const bar=document.getElementById('audioBar'); const a=document.getElementById('pAudio');
  a.src=PAPER.audio; bar.style.display='flex'; renderSubs(); a.addEventListener('timeupdate', syncSubs); }

restorePos(); sizeInk(); loadAll(); renderVocab(); initSrs(); initAudio();
if(PAPER.audio){ const b=document.getElementById('pAudio'); if(b) b.load(); }
</script>
<div id="srsModal"><div id="srsBox">
  <h3>生词复习（遗忘曲线）</h3>
  <div id="srsToday"></div>
  <button class="close" onclick="closeSrs()">关闭</button>
</div></div>
</body></html>"""


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
            .replace("__PAPER__", json.dumps({**paper,
                "audio": (out.with_suffix(".mp3").name if out.with_suffix(".mp3").exists() else ""),
                "timing": (json.loads(out.with_suffix(".timing.json").read_text(encoding="utf-8")) if out.with_suffix(".timing.json").exists() else [])}, ensure_ascii=False)))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
