# -*- coding: utf-8 -*-
"""整卷渲染：写作 + 听力 + 阅读(选词/匹配/仔细) + 翻译，A4 试卷版式。

用法: python bin/cet4_build_paper.py <whole-paper.json> [--outdir dir]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

CSS = """
:root{--fs:10.5pt;--fsan:9pt}
*{box-sizing:border-box}
body{margin:0;overflow-x:hidden;background:#e9e9e9;font-family:"Times New Roman","SimSun",serif;color:#000;font-size:var(--fs);line-height:1.5}
.paper{width:595.32pt;margin:16pt auto;background:#fff;padding:38pt 36pt 30pt;box-shadow:0 2px 16px rgba(0,0,0,.18)}
.part{font-weight:bold;margin:14pt 0 6pt;font-size:1.05em}
.sec{font-weight:bold;margin:8pt 0 4pt}
.dir{font-style:italic;color:#333;margin:4pt 0 8pt}
p.body{text-indent:2em;margin:0 0 5pt;text-align:justify}
.q{margin:7pt 0}
.opts{display:grid;grid-template-columns:1fr 1fr;column-gap:14pt;padding-left:12pt}
.opt{display:block;cursor:pointer;padding:1pt 2px;border-radius:2px}
.opt input{display:none}
.opt.sel{background:#e3f0ff}
.opt.correct{background:#d9f2df;outline:1px solid #2e7d32}
.opt.wrong{background:#fde0e0;outline:1px solid #c62828}
input.blank{width:110pt;border:none;border-bottom:1px solid #666;font-family:inherit;font-size:1em;text-align:center}
select.stmt{font-family:inherit;font-size:.95em}
.bank{display:grid;grid-template-columns:repeat(4,1fr);gap:2pt 10pt;margin:6pt 0 10pt;font-size:.95em}
.bank div{border-bottom:1px dotted #ddd}
textarea{width:100%;min-height:90pt;font-family:inherit;font-size:1em;border:1px solid #ccc;border-radius:4pt;padding:6pt}
.qa{display:none;margin:4pt 0 0;padding:5pt 8pt;border-left:2pt solid #c9a227;background:#fbf9f1;font-size:.86em;line-height:1.6;font-family:-apple-system,"Microsoft YaHei",sans-serif}
.qa.show{display:block}
.bar{position:fixed;top:0;left:0;right:0;background:#111;color:#fff;padding:5px 10px;font:13px/1.35 -apple-system,"Microsoft YaHei",sans-serif;display:flex;gap:9px;align-items:center;flex-wrap:nowrap;overflow-x:auto;z-index:20;white-space:nowrap}
.bar .ttl{max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar input[type=range]{width:96px;vertical-align:middle}
.bar button{border:1px solid #666;background:#222;color:#fff;border-radius:4px;padding:3px 7px;cursor:pointer;white-space:nowrap;font:12px/1.35 -apple-system,"Microsoft YaHei",sans-serif}
.bar .grp{display:flex;gap:5px;align-items:center;border-left:1px solid #444;padding-left:9px;flex:none}
.bar .fsv{min-width:44px;text-align:center;color:#ffd479;font-variant-numeric:tabular-nums}
.bar .lbl{color:#9a9a9a;font-size:12px;margin-right:-2px}
.bar button.on{background:#2f6fb0;border-color:#8dbdea}
.bar select{background:#222;color:#fff;border:1px solid #666;border-radius:4px;font:12px/1.2 inherit;padding:2px 0;margin:0}
#ink{position:fixed;top:0;left:0;z-index:15;pointer-events:none;touch-action:none}
#ink.on{pointer-events:auto;cursor:crosshair}
mark.hl-yellow{background:#fff3a8}
mark.hl-green{background:#c8e6c9}
mark.hl-red{background:#ffd6d6}
mark.hl-orange{background:#ffe0b2}
mark.hl-purple{background:#e1bee7}
span.redline{text-decoration:underline;text-decoration-color:#e53935;text-decoration-thickness:2px}
span.noted{background:#fff8e1;border-bottom:1px dotted #c9a227;cursor:help}
#radial{position:fixed;z-index:60;width:208px;height:208px;display:none;pointer-events:none;user-select:none;-webkit-user-select:none}
#radial.on{display:block}
#radial .bg{position:absolute;inset:0;border-radius:50%;background:rgba(17,17,17,.78);border:1px solid #4b4b4b;box-shadow:0 12px 34px rgba(0,0,0,.42)}
#radial .hub{position:absolute;left:50%;top:50%;width:78px;height:78px;margin:-39px 0 0 -39px;border-radius:50%;background:#1b1b1b;border:1px solid #5a5a5a;color:#ffd479;display:flex;align-items:center;justify-content:center;text-align:center;font:12px/1.25 -apple-system,"Microsoft YaHei",sans-serif;padding:4px}
#radial .ri{position:absolute;width:50px;height:50px;margin:-25px 0 0 -25px;border-radius:50%;background:#262626;border:1px solid #6a6a6a;color:#fff;display:flex;align-items:center;justify-content:center;font:12px/1.15 -apple-system,"Microsoft YaHei",sans-serif;letter-spacing:.5px;transition:background .06s ease,transform .06s ease,border-color .06s ease,color .06s ease}
#radial .ri.t-y{background:#fff3a8;color:#4a4000;border-color:#d3c25c}
#radial .ri.t-g{background:#c8e6c9;color:#1b5e20;border-color:#8fc796}
#radial .ri.t-r{background:#ffd6d6;color:#a01b1b;border-color:#e59a9a}
#radial .ri.t-n{background:#fff8e1;color:#6b5410;border-color:#dcc98d}
#radial .ri.hot{background:#2f6fb0;border-color:#a9cfef;color:#fff;transform:scale(1.14);box-shadow:0 6px 18px rgba(0,0,0,.45)}
.spacer{height:52px}
.audio{width:100%;margin:4pt 0 6pt}
#report{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:30;align-items:center;justify-content:center}
#report.show{display:flex}
#reportBox{background:#fff;padding:16pt;border-radius:10pt;width:340pt;font:12pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.w{cursor:context-menu}
.w:hover{background:#eef4ff}
#wdict{display:none;position:fixed;z-index:50;width:216px;background:#fff;border:1px solid #999;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.22);padding:6px 8px;font:12px/1.5 -apple-system,"Microsoft YaHei",sans-serif;color:#111}
#wdict.show{display:block}
#wdict .hd{font-weight:700;font-size:14px;line-height:1.3}
#wdict .ipa{color:#555;margin-left:4px;font-size:11.5px;font-weight:400}
#wdict .pos{color:#7a5c00;margin-right:3px}
#wdict .btn{margin-top:5px;display:flex;gap:4px}
#wdict button{border:1px solid #ccc;background:#fafafa;border-radius:4px;padding:1px 6px;cursor:pointer;margin:0;font-size:11.5px;line-height:1.5}
#wdict .cn{font-size:13px;margin:1px 0 2px}
#wdict .dr{margin-top:1px;line-height:1.45;font-size:11.5px}
#wdict .dk{display:inline-block;min-width:2.6em;color:#7a5c00;font-weight:600;font-size:11px}
#wdict .dcn{color:#666}
#wdict .ex{color:#333}
#wdict .ex{-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden}
#vocab{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:45;align-items:center;justify-content:center}
#vocab.show{display:flex}
#vocab .vbox{background:#fff;width:min(760pt,94vw);max-height:84vh;overflow:auto;border-radius:10pt;padding:14pt 16pt;font:11pt/1.7 -apple-system,"Microsoft YaHei",sans-serif}
#vocab h3{margin:0 0 8pt}
#vocab table{width:100%;border-collapse:collapse}
#vocab td,#vocab th{border-bottom:1px solid #eee;padding:3px 6px;text-align:left;vertical-align:top}
#vocab .del{color:#c01c28;cursor:pointer;border:none;background:none;font-size:1em}
#vocab .vbar{display:flex;gap:8px;flex-wrap:wrap;margin:8pt 0}
#vocab .vbar button{border:1px solid #ccc;background:#fafafa;border-radius:6pt;padding:3pt 10pt;cursor:pointer}
.pan,.qax{display:none;margin:2pt 0 8pt;padding:6pt 8pt;border-left:2pt solid #c9a227;background:#fbf9f1;font-size:calc(var(--fsan) * 1.0);line-height:1.7;font-family:-apple-system,"Microsoft YaHei","SimSun",sans-serif}
.pan.show,.qax.show{display:block}
.pan .cn{margin-bottom:3pt}
.tr{margin:4pt 0 8pt;border-left:2pt solid #e0e0e0;padding-left:8pt;font-size:.9em;line-height:1.7;font-family:-apple-system,"Microsoft YaHei",sans-serif}
.tr .line{cursor:pointer;padding:1pt 3px;border-radius:2px}
.tr .line:hover{background:#eef4ff}
.tr .line.on{background:#fff3cd}
.tr .line .en{color:#111}
.tr .line .cn{color:#5a5a5a}
.sum{margin:4pt 0;padding:5pt 8pt;background:#f6f6f6;font-size:.9em;line-height:1.7;font-family:-apple-system,"Microsoft YaHei",sans-serif}
.vt{width:100%;border-collapse:collapse;margin:4pt 0 8pt;font-size:.86em;line-height:1.6;font-family:-apple-system,"Microsoft YaHei",sans-serif}
.vt td{border-bottom:1px dotted #ddd;padding:1pt 4px;vertical-align:top}
.vt td:first-child{font-weight:600;width:24%}
.vt td:nth-child(2){color:#555;width:24%}
.trs{border-collapse:collapse;width:100%;font-size:.86em;line-height:1.6;font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:4pt 0}
.trs td,.trs th{border:1px solid #e2e2e2;padding:2pt 5px;vertical-align:top;text-align:left}
.bands{margin:4pt 0 8pt;font-size:.9em;line-height:1.7;font-family:-apple-system,"Microsoft YaHei",sans-serif}
.bands div{border-bottom:1px dotted #ddd;padding:1pt 0}
/* —— 解析配色：标签chip + 成分色 —— */
.lb{display:inline-block;min-width:4.2em;margin-right:4px;padding:0 4px;border-radius:3px;font-weight:600;font-size:.86em;line-height:1.5;color:#fff;background:#8a8a8a;text-align:center;vertical-align:1px}
.lb-main{background:#1a5fb4}.lb-role{background:#813d9c}.lb-map{background:#0f6674}
.lb-loc{background:#b8860b}.lb-para{background:#26a269}.lb-trap{background:#c01c28}
.lb-why{background:#26a269}.lb-opt{background:#c01c28}.lb-chunk{background:#1a5fb4}
.lb-mean{background:#5a5a5a}.lb-tip{background:#b35c00}.lb-band{background:#3d6b35}
.r-subj{color:#1a5fb4;font-weight:600}
.r-pred{color:#c01c28;font-weight:600}
.r-obj{color:#26a269;font-weight:600}
.r-adv{color:#813d9c;font-weight:600}
.r-attr{color:#0f6674;font-weight:600}
.r-comp{color:#8f5d00;font-weight:600}
.r-other{color:#444}
.loc{background:#fff3cd;padding:0 2px;border-radius:2px}
.an{border-top:1px dotted #e2dcc8;margin-top:4px;padding-top:3px}
.an .row{display:flex;gap:5px;align-items:flex-start;padding:1px 0}
.an .lt{flex:0 0 auto;display:inline-block;min-width:2.4em;text-align:center;border-radius:3px;font-weight:700;font-size:.9em;color:#fff;background:#8a8a8a}
.an .lt.ok{background:#26a269}
.an .lt.bad{background:#c01c28}
.an .tx{flex:1 1 auto}
.an .tx b{color:#a01a26;font-weight:600}
.sent{margin-top:6px;padding-left:4px;border-left:2px solid #f0f0f0}
.sent .chk{line-height:2.1}
.sent .scn{color:#3f3f3f;margin-top:1px}
.sent.clickable{cursor:pointer;border-radius:3px}
.sent.clickable:hover{background:#fbfbf4}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#222;color:#fff;padding:7px 14px;border-radius:6px;font:12px/1.6 -apple-system,"Microsoft YaHei",sans-serif;opacity:0;transition:opacity .2s;z-index:60;pointer-events:none}
#toast.show{opacity:.94}
.side{float:right;width:380px;margin:2pt -440px 12pt 0;position:static;background:#fff;border:1px solid #ddd;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.10);padding:9px 11px;z-index:1;font:12.5px/1.65 -apple-system,"Microsoft YaHei",sans-serif;word-break:break-word;overflow-wrap:anywhere;max-height:calc(100vh - 76px);overflow:auto}
.side table{width:100%!important;table-layout:fixed}
.side .trs td,.side .trs th{overflow-wrap:anywhere;padding:2px 5px;font-size:11.5px}
.side .sk{overflow-wrap:anywhere}
.shd{font-weight:700;color:#111}
.band{margin:4px 0;padding:4px 6px;background:#fafafa;border-left:2px solid #e3e3e3;border-radius:3px}
.band .musts{color:#444;margin:2px 0}
.band .sk{font-family:"Times New Roman",serif;color:#1a4f8a;background:#f2f7ff;padding:1px 4px;border-radius:3px;margin:2px 0}
.side.off{display:none}
.stabs{display:flex;gap:6px;margin-bottom:6px;align-items:center;position:sticky;top:-10px;background:#fff;padding:2px 0 6px}
.stab{border:1px solid #ddd;background:#f7f7f7;border-radius:6px;padding:2px 10px;cursor:pointer;font:12.5px/1.7 -apple-system,"Microsoft YaHei",sans-serif}
.stab.on{background:#111;color:#fff;border-color:#111}
.stab.close{margin-left:auto;background:transparent;border:none;font-size:15px;line-height:1}
.spane{display:none}
.spane.on{display:block}
.fold{margin:6pt 0;font-size:.95em;border-left:2px solid #e6e6e6;padding-left:8pt}
.fold summary{cursor:pointer;color:#1a5fb4}
@media (max-width:1660px){.side{float:none;width:auto;margin:8pt 0}}
.par{color:#1a6b3c;background:#e8f6ec;padding:0 2px;border-radius:2px}
.trap{color:#a01a26;background:#fdeaea;padding:0 2px;border-radius:2px}
.anno-en{font-weight:600;color:#111}
.anno-cn{color:#3f3f3f}
.anno-tip{color:#8a5200}
.dim{color:#7a7a7a}
@media print{.bar,.qa,.pan,.qax,#wdict,#ink,#radial{display:none!important}.paper{box-shadow:none;margin:0}@page{size:A4;margin:38pt 36pt 30pt}}
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
    if(!host) continue;
    // 只有字典弹窗/生词表面板/输入框内部不包词，其余全部可查（含解析区、字幕、作文、翻译）
    if(host.closest('#wdict,#vocab,#toast,textarea,script,style,option')) continue;
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
  const row = (k, v) => (v && v !== '—') ? `<div class="dr"><span class="dk">${k}</span>${v}</div>` : '';
  const ex = info.example
    ? `<div class="dr"><span class="dk">例句</span><span class="ex">${info.example}</span>`
      + (info.example_cn ? `<br><span class="dcn">${info.example_cn}</span>` : '') + `</div>`
    : '';
  box.innerHTML =
    `<div class="hd">${info.word || w}<span class="ipa">${info.phonetic || ''}</span></div>`
    + `<div><span class="pos">${info.pos || ''}</span></div>`
    + `<div class="cn">${info.cn || '暂无释义'}</div>`
    + row('词根', info.root) + row('拆解', info.affix) + row('同族', info.family)
    + row('搭配', info.collocation) + ex + row('记忆', info.tip)
    + `<div class="btn"><button onclick="speakWord('${w}')">🔊 朗读</button>`
    + `<button onclick="toggleVocab('${w}',this)">${vocabHas(w) ? '✓ 已在生词表' : '＋ 加入生词表'}</button></div>`;
  box.style.left = Math.min(x + 12, innerWidth - 240) + 'px';
  box.style.top = Math.min(y + 12, innerHeight - 200) + 'px';
  box.classList.add('show');
}
function speakWord(w){ if(!window.speechSynthesis) return; const u=new SpeechSynthesisUtterance(w); u.lang='en-US'; speechSynthesis.cancel(); speechSynthesis.speak(u); }
/* —— 我的生词表（用户自己挑，不用 AI 预选） —— */
function vocabLoad(){ try{ return JSON.parse(localStorage.getItem('cet4_vocab') || '[]'); }catch(e){ return []; } }
function vocabHas(w){ return vocabLoad().indexOf(w) >= 0; }
function vocabSave(a){ try{ localStorage.setItem('cet4_vocab', JSON.stringify(a)); }catch(e){} updateVocabCount(); }
function updateVocabCount(){
  const b = document.getElementById('vcount');
  if(b) b.textContent = '生词表 ' + vocabLoad().length;
  const n = document.getElementById('vn');
  if(n) n.textContent = vocabLoad().length;
}
function toggleVocab(w, btn){
  const a = vocabLoad();
  const i = a.indexOf(w);
  if(i >= 0) a.splice(i, 1); else a.push(w);
  vocabSave(a);
  if(btn) btn.textContent = vocabHas(w) ? '✓ 已在生词表' : '＋ 加入生词表';
  renderVocab();
}
function renderVocab(){
  const box = document.getElementById('vbox');
  if(!box) return;
  const a = vocabLoad();
  updateVocabCount();
  if(!a.length){
    box.innerHTML = '<p style="color:#666">还没有生词。右键正文里任意单词 → 点「＋ 加入生词表」。</p>';
    return;
  }
  const rows = a.map(w=>{
    const i = WORDS[w] || {};
    return `<tr><td><b>${i.word || w}</b><br><span style="color:#666">${i.phonetic || ''}</span></td>`
      + `<td>${i.pos || ''} ${i.cn || '<span style="color:#c01c28">缺释义</span>'}</td>`
      + `<td>${i.root && i.root !== '—' ? '词根 ' + i.root : ''}${i.affix && i.affix !== '—' ? '<br>拆解 ' + i.affix : ''}</td>`
      + `<td>${i.collocation || ''}${i.tip ? '<br><span style="color:#8a5200">' + i.tip + '</span>' : ''}</td>`
      + `<td><button class="del" title="移出" onclick="toggleVocab('${w}')">✕</button></td></tr>`;
  }).join('');
  box.innerHTML = `<table><tr><th style="width:18%">词</th><th style="width:26%">释义</th>`
    + `<th style="width:24%">词根/拆解</th><th style="width:26%">搭配/记忆</th><th></th></tr>${rows}</table>`;
}
function openVocab(){ renderVocab(); document.getElementById('vocab').classList.add('show'); }
function closeVocab(){ document.getElementById('vocab').classList.remove('show'); }
function exportVocab(){
  const a = vocabLoad();
  if(!a.length){ hint('生词表还是空的：右键正文里的单词即可加入'); return; }
  const lines = a.map(w=>{
    const i = WORDS[w] || {};
    return `- **${i.word || w}** ${i.phonetic || ''} ${i.pos || ''} ${i.cn || ''}\\n`
      + `  - 词根：${i.root || '—'}｜拆解：${i.affix || '—'}｜同族：${i.family || '—'}\\n`
      + `  - 搭配：${i.collocation || '—'}\\n`
      + `  - 例句：${i.example || '—'} ${i.example_cn || ''}\\n`
      + `  - 记忆：${i.tip || '—'}`;
  });
  const blob = new Blob([`# 我的生词表（${a.length} 词）\\n\\n` + lines.join('\\n')], {type:'text/markdown'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = 'cet4-我的生词表.md'; link.click();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}
function clearVocab(){
  if(!vocabLoad().length) return;
  if(confirm('清空生词表？此操作不可撤销。')){ vocabSave([]); renderVocab(); }
}
document.addEventListener('contextmenu', e=>{
  const t = e.target;
  if(t && t.classList && t.classList.contains('w')){ e.preventDefault(); showDict(t, e.clientX, e.clientY); }
  else { const b=document.getElementById('wdict'); if(b) b.classList.remove('show'); }
});
document.addEventListener('click', ()=>{ const b=document.getElementById('wdict'); if(b) b.classList.remove('show'); });
function toggleAll(){
  const els = [...document.querySelectorAll('.pan, .qax')];
  if(!els.length) return;
  const anyOpen = els.some(e=>e.classList.contains('show'));
  els.forEach(e=>e.classList.toggle('show', !anyOpen));
  const b = document.getElementById('btnAll');
  if(b) b.textContent = anyOpen ? '展开解析' : '收起解析';
}
function toggleSide(el){
  const list = el ? [el.closest('.side')] : [...document.querySelectorAll('.side')];
  list.forEach(s=>{ if(s) s.classList.toggle('off'); });
}
function sideTab(i){
  document.querySelectorAll('.stab[data-tab]').forEach(b=>b.classList.toggle('on', b.dataset.tab === ('t'+i)));
  document.querySelectorAll('.spane').forEach(p=>p.classList.toggle('on', p.id === ('t'+i)));
}
(function(){
  const list = [...document.querySelectorAll('.side')];
  list.forEach(s=>s.classList.remove('off'));
})();

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
function seek(aid, t, end, el){
  const a=document.getElementById(aid); if(!a) return;
  document.querySelectorAll('audio').forEach(b=>{ if(b!==a && !b.paused) b.pause(); });
  a.dataset.stop = (document.getElementById('cont') && document.getElementById('cont').checked) ? '' : (end || '');
  document.querySelectorAll('.tr .line.on').forEach(e=>e.classList.remove('on'));
  if(el) el.classList.add('on');
  try{ a.currentTime=t; }catch(e){}
  a.play().catch(()=>{});
  // 某些 HTTP 服务不支持 Range，会导致跳转静默失效 → 稍后重试一次
  setTimeout(()=>{
    if(Math.abs(a.currentTime - t) > 0.8 && a.readyState >= 1){
      try{ a.currentTime = t; }catch(e){}
      setTimeout(()=>{
        if(Math.abs(a.currentTime - t) > 1.2) hint('音频跳句失败：当前打开方式不支持定位，请改用本地浏览器直接打开该 HTML 文件');
      }, 500);
    }
  }, 350);
}
let _toastTimer = null;
function hint(msg){
  const t = document.getElementById('toast'); if(!t) return;
  t.textContent = msg; t.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(()=>t.classList.remove('show'), 3600);
}
/* 单句模式：到下一句起点自动停；勾选「连播」则一直播下去 */
function bindSentenceStop(){
  document.querySelectorAll('audio').forEach(a=>{
    if(a.dataset.bound) return;
    a.dataset.bound = '1';
    a.addEventListener('play', ()=>{
      document.querySelectorAll('audio').forEach(b=>{ if(b!==a && !b.paused) b.pause(); });
    });
    a.addEventListener('timeupdate', ()=>{
      const stop = parseFloat(a.dataset.stop || '0');
      if(stop && a.currentTime >= stop - 0.06 && !a.paused){ a.pause(); a.dataset.stop = ''; }
    });
  });
}
/* 音频先抓成 Blob：Blob 支持随机访问，HTTP 不支持 Range 时也能精确跳句 */
async function upgradeAudio(){
  const list = [...document.querySelectorAll('audio[data-src]')];
  for(const a of list){
    if(a.dataset.blobbed) continue;
    try{
      const r = await fetch(a.dataset.src, {cache:'force-cache'});
      if(!r.ok) continue;
      const buf = await r.arrayBuffer();
      if(!buf.byteLength) continue;
      const url = URL.createObjectURL(new Blob([buf], {type:'audio/mpeg'}));
      const was = a.currentTime, playing = !a.paused;
      a.dataset.blobbed = '1';
      a.src = url;
      a.addEventListener('loadedmetadata', ()=>{
        try{ if(was) a.currentTime = was; }catch(e){}
        if(playing) a.play().catch(()=>{});
      }, {once:true});
      a.load();
    }catch(e){ /* file:// 下 fetch 被拦，保留原生 src：本地文件本身支持跳转 */ }
  }
}
function speakW(w){ speak(w); }
function setFont(pt){
  pt = Math.max(7, Math.min(22, Math.round(pt*2)/2));
  const an = Math.max(6, Math.round(pt*0.86*2)/2);
  document.documentElement.style.setProperty('--fs', pt+'pt');
  document.documentElement.style.setProperty('--fsan', an+'pt');
  const v=document.getElementById('fsv'); if(v) v.textContent = pt.toFixed(1);
  const r=document.getElementById('fsr'); if(r && Math.abs(parseFloat(r.value)-pt)>0.01) r.value = pt;
  try{ localStorage.setItem('cet4_fs', pt); }catch(e){}
}
function stepFont(d){
  let cur = 10.5;
  try{ cur = parseFloat(localStorage.getItem('cet4_fs')) || 10.5; }catch(e){}
  setFont(cur + d);
}
function resetFont(){ setFont(10.5); }
(function(){
  let v = 10.5;
  try{ v = parseFloat(localStorage.getItem('cet4_fs')) || 10.5; }catch(e){}
  setFont(v);
})();
"""


INK = r"""
/* ==================== 画笔 / 标注：笔迹锚在文字上，改字号/展开解析后跟着走 ==================== */
const INK_SLUG = (((PAPER.meta || {}).name) || 'paper').replace(/[^A-Za-z0-9\u4e00-\u9fa5]+/g, '_').slice(0, 60);
const INK_KEY = 'ink_' + INK_SLUG;
const MARK_KEY = 'mk_' + INK_SLUG;
const inkCvs = document.getElementById('ink');
const inkCtx = inkCvs ? inkCvs.getContext('2d') : null;
let inkOn = false, eraseOn = false, strokes = [], curStroke = null, inkRaf = 0, inkMap = null;

function inkPaperEl(){ return document.querySelector('.paper'); }
function inkElById(a){
  if(!a) return null;
  if(!inkMap) inkMap = new Map();
  if(inkMap.has(a)) return inkMap.get(a);
  const e = document.querySelector('[data-ink="' + a + '"]');
  inkMap.set(a, e);
  return e;
}
function inkTextOffset(host, node, off){
  let total = 0, n;
  const w = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
  while((n = w.nextNode())){
    if(n === node) return total + off;
    total += n.textContent.length;
  }
  return null;
}
function inkRangeAt(host, off){
  let total = 0, n;
  const w = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
  while((n = w.nextNode())){
    const L = n.textContent.length;
    if(off < total + L && L > 0){
      const s = Math.max(0, Math.min(L - 1, off - total));
      const r = document.createRange();
      r.setStart(n, s); r.setEnd(n, s + 1);
      return r;
    }
    total += L;
  }
  return null;
}
function inkRangeSpan(host, s, e){
  let total = 0, n, startN = null, startO = 0, endN = null, endO = 0;
  const w = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
  while((n = w.nextNode())){
    const L = n.textContent.length, a = total, b = total + L;
    if(startN === null && s < b){ startN = n; startO = Math.max(0, Math.min(L, s - a)); }
    if(startN !== null && e <= b){ endN = n; endO = Math.max(0, Math.min(L, e - a)); break; }
    total = b;
  }
  if(!startN) return null;
  if(!endN){ endN = startN; endO = startN.textContent.length; }
  try{
    const r = document.createRange();
    r.setStart(startN, startO); r.setEnd(endN, endO);
    return r;
  }catch(err){ return null; }
}
function inkCaret(x, y){
  if(!inkCvs) return null;
  const prev = inkCvs.style.pointerEvents;
  inkCvs.style.pointerEvents = 'none';
  let out = null;
  try{
    if(document.caretPositionFromPoint){
      const cp = document.caretPositionFromPoint(x, y);
      if(cp) out = { node: cp.offsetNode, off: cp.offset };
    }
    if(!out && document.caretRangeFromPoint){
      const r = document.caretRangeFromPoint(x, y);
      if(r) out = { node: r.startContainer, off: r.startOffset };
    }
  }catch(err){}
  inkCvs.style.pointerEvents = prev;
  return out;
}
function inkPoint(x, y){
  const paper = inkPaperEl();
  const hit = inkCaret(x, y);
  let host = null, off = null;
  if(hit && hit.node && hit.node.nodeType === 3){
    let h = hit.node.parentElement;
    while(h && h !== paper && !h.dataset.ink) h = h.parentElement;
    if(h && h.dataset && h.dataset.ink){
      const t = inkTextOffset(h, hit.node, hit.off);
      if(t != null){ host = h; off = t; }
    }
  }
  if(!host){
    const prev = inkCvs.style.pointerEvents;
    inkCvs.style.pointerEvents = 'none';
    const list = document.elementsFromPoint(x, y) || [];
    inkCvs.style.pointerEvents = prev;
    for(const e of list){
      const a = (e.closest ? e.closest('[data-ink]') : null);
      if(a){ host = a; break; }
    }
  }
  if(!host) return null;
  let rect = null;
  if(off != null){
    const r = inkRangeAt(host, off);
    if(r){ const q = r.getBoundingClientRect(); if(q.width || q.height) rect = q; }
  }
  if(!rect) rect = host.getBoundingClientRect();
  return { a: host.dataset.ink, off: off, dx: x - rect.left, dy: y - rect.top };
}
function inkRedraw(){
  if(!inkCtx) return;
  const W = innerWidth, H = innerHeight;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const pw = Math.round(W * dpr), ph = Math.round(H * dpr);
  if(inkCvs.width !== pw || inkCvs.height !== ph){
    inkCvs.width = pw; inkCvs.height = ph;
    inkCvs.style.width = W + 'px'; inkCvs.style.height = H + 'px';
  }
  inkCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  inkCtx.clearRect(0, 0, W, H);
  inkCtx.lineCap = 'round'; inkCtx.lineJoin = 'round';
  let lastKey = '', lastLeft = 0, lastTop = 0;
  function posOf(p){
    const key = (p.a || '') + '|' + (p.off == null ? 'x' : p.off);
    if(key === lastKey) return { x: lastLeft + p.dx, y: lastTop + p.dy };
    const el = inkElById(p.a);
    if(!el) return null;
    let r = null;
    if(p.off != null){
      const rg = inkRangeAt(el, p.off);
      if(rg){ const q = rg.getBoundingClientRect(); if(q.width || q.height) r = q; }
    }
    if(!r) r = el.getBoundingClientRect();
    lastKey = key; lastLeft = r.left; lastTop = r.top;
    return { x: r.left + p.dx, y: r.top + p.dy };
  }
  for(const st of strokes){
    const col = st.color || '#e53935', lw = st.width || 2.8;
    const pts = [];
    for(const p of (st.pts || [])){ const a = posOf(p); if(a) pts.push(a); }
    if(!pts.length) continue;
    inkCtx.strokeStyle = col; inkCtx.fillStyle = col; inkCtx.lineWidth = lw;
    if(pts.length === 1){
      inkCtx.beginPath(); inkCtx.arc(pts[0].x, pts[0].y, Math.max(1, lw / 2), 0, 6.284); inkCtx.fill();
      continue;
    }
    inkCtx.beginPath(); inkCtx.moveTo(pts[0].x, pts[0].y);
    for(let i = 1; i < pts.length; i++) inkCtx.lineTo(pts[i].x, pts[i].y);
    inkCtx.stroke();
  }
}
function inkRedrawSoon(){
  if(inkRaf) return;
  inkRaf = requestAnimationFrame(function(){ inkRaf = 0; inkRedraw(); });
}
function inkSave(){
  try{
    const slim = strokes.map(function(st){
      return { color: st.color, width: st.width, pts: (st.pts || []).map(function(p){
        return { a: p.a, off: p.off, dx: Math.round(p.dx * 10) / 10, dy: Math.round(p.dy * 10) / 10 };
      }) };
    });
    localStorage.setItem(INK_KEY, JSON.stringify(slim));
  }catch(e){ hint('笔迹存不进本地存储（写满了）：点「清笔」清掉一些再写'); }
}
function inkSyncUI(silent){
  if(!inkCvs) return;
  const active = inkOn || eraseOn;
  inkCvs.classList.toggle('on', active);
  const p = document.getElementById('tbPen'), q = document.getElementById('tbErase');
  if(p) p.classList.toggle('on', inkOn && !eraseOn);
  if(q) q.classList.toggle('on', eraseOn);
  inkCvs.style.cursor = eraseOn ? 'cell' : 'crosshair';
  if(silent) return;
  if(!active) hint('画笔已关：现在可以正常选文字、点选项了');
  else if(eraseOn) hint('橡皮已开：点一下或划过笔迹就擦掉；再点🧽关掉');
  else hint('画笔已开：直接在卷面上写画（关掉后才能选文字/点选项）');
}
function toggleInk(){ inkOn = !inkOn; if(inkOn) eraseOn = false; else eraseOn = false; inkSyncUI(false); }
function toggleErase(){ eraseOn = !eraseOn; if(eraseOn) inkOn = true; inkSyncUI(false); }
function clearInk(){
  if(!strokes.length){ hint('现在没有笔迹'); return; }
  strokes = []; curStroke = null;
  inkRedraw(); inkSave(); hint('笔迹已清除');
}
function inkErase(x, y){
  const before = strokes.length;
  strokes = strokes.filter(function(st){
    return !(st.pts || []).some(function(p){
      const el = inkElById(p.a);
      if(!el) return false;
      let r = null;
      if(p.off != null){ const rg = inkRangeAt(el, p.off); if(rg){ const q = rg.getBoundingClientRect(); if(q.width || q.height) r = q; } }
      if(!r) r = el.getBoundingClientRect();
      return Math.hypot(r.left + p.dx - x, r.top + p.dy - y) < 15;
    });
  });
  if(strokes.length !== before){ inkRedraw(); inkSave(); }
}
function assignInkAnchors(paper){
  const SKIP = '.w,mark,span.redline,span.noted,#vocab,#wdict,script,style,textarea,button,select,option,input,audio';
  let seq = 0, n;
  const w = document.createTreeWalker(paper, NodeFilter.SHOW_TEXT);
  while((n = w.nextNode())){
    if(!/[A-Za-z0-9\u4e00-\u9fa5]/.test(n.textContent)) continue;
    let h = n.parentElement;
    while(h && h !== paper && h.matches && h.matches(SKIP)) h = h.parentElement;
    if(!h || h === paper) continue;
    if(!h.dataset.ink) h.dataset.ink = 'a' + (++seq);
  }
  inkMap = null;
}
function inkMarkRange(cls, tag, note){
  const sel = getSelection();
  if(!sel || !sel.rangeCount || sel.isCollapsed){ hint('先用鼠标选中要标注的文字，再点按钮'); return; }
  const r = sel.getRangeAt(0);
  const paper = inkPaperEl();
  if(!paper || !paper.contains(r.commonAncestorContainer)){ hint('只能在试卷正文上标注'); return; }
  const el = document.createElement(tag);
  el.className = cls;
  if(note){ el.dataset.note = note; el.title = note; }
  try{ r.surroundContents(el); }
  catch(e){
    try{ el.appendChild(r.extractContents()); r.insertNode(el); }
    catch(e2){ hint('这段跨了多个排版块，换个短一点的选段'); return; }
  }
  sel.removeAllRanges();
  inkMarkSave();
  hint(cls === 'noted' ? '批注已加' : '标注已加');
  inkRedrawSoon();
}
function markSel(cls){ inkMarkRange(cls, cls === 'redline' ? 'span' : 'mark', ''); }
function noteSel(){
  const sel = getSelection();
  if(!sel || !sel.rangeCount || sel.isCollapsed){ hint('先选中要批注的文字'); return; }
  const t = prompt('批注内容：');
  if(!t) return;
  inkMarkRange('noted', 'span', t);
}
function inkElOffsets(host, el){
  let total = 0, s = null, e = 0, n;
  const w = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
  while((n = w.nextNode())){
    const L = n.textContent.length;
    if(el.contains(n)){ if(s === null) s = total; e = total + L; }
    total += L;
  }
  return (s === null) ? null : { s: s, e: e };
}
function inkMarkSave(){
  const paper = inkPaperEl();
  if(!paper) return;
  const out = [];
  paper.querySelectorAll('mark, span.redline, span.noted').forEach(function(el){
    const host = el.parentElement ? el.parentElement.closest('[data-ink]') : null;
    if(!host) return;
    const sp = inkElOffsets(host, el);
    if(!sp) return;
    out.push({ a: host.dataset.ink, s: sp.s, e: sp.e, cls: el.className, note: el.dataset.note || '' });
  });
  try{ localStorage.setItem(MARK_KEY, JSON.stringify(out)); }catch(e){}
}
function inkMarkApply(){
  let data = [];
  try{ data = JSON.parse(localStorage.getItem(MARK_KEY) || '[]') || []; }catch(e){ return; }
  if(!data.length) return;
  const jobs = [];
  data.forEach(function(m){
    if(!m || !m.a || !m.cls) return;
    const host = inkElById(m.a);
    if(!host) return;
    const r = inkRangeSpan(host, m.s, m.e);
    if(r) jobs.push({ r: r, m: m });
  });
  jobs.forEach(function(j){
    const tag = (j.m.cls === 'redline' || j.m.cls === 'noted') ? 'span' : 'mark';
    const el = document.createElement(tag);
    el.className = j.m.cls;
    if(j.m.note){ el.dataset.note = j.m.note; el.title = j.m.note; }
    try{ j.r.surroundContents(el); }
    catch(e){ try{ el.appendChild(j.r.extractContents()); j.r.insertNode(el); }catch(e2){} }
  });
}
function clearMarks(){
  const paper = inkPaperEl();
  if(!paper) return;
  const els = paper.querySelectorAll('mark, span.redline, span.noted');
  if(!els.length){ hint('当前没有高亮/红线/批注'); return; }
  els.forEach(function(el){
    const p = el.parentNode;
    if(!p) return;
    while(el.firstChild) p.insertBefore(el.firstChild, el);
    p.removeChild(el);
  });
  try{ localStorage.removeItem(MARK_KEY); }catch(e){}
  inkRedrawSoon();
  hint('已清除全部高亮 / 红线 / 批注');
}
if(inkCvs){
  inkCvs.addEventListener('pointerdown', function(e){
    if(!inkOn) return;
    if(e.pointerType === 'mouse' && e.button !== 0) return;
    try{ inkCvs.setPointerCapture(e.pointerId); }catch(err){}
    if(eraseOn){ inkErase(e.clientX, e.clientY); e.preventDefault(); return; }
    const p = inkPoint(e.clientX, e.clientY);
    if(!p) return;
    const c = document.getElementById('penColor'), wd = document.getElementById('penWidth');
    curStroke = { color: c ? c.value : '#e53935', width: wd ? parseFloat(wd.value) : 2.8, pts: [p] };
    strokes.push(curStroke);
    inkRedraw();
    e.preventDefault();
  });
  inkCvs.addEventListener('pointermove', function(e){
    if(!inkOn) return;
    if(eraseOn){
      if(e.pointerType === 'mouse' && !(e.buttons & 1)) return;
      inkErase(e.clientX, e.clientY);
      return;
    }
    if(!curStroke) return;
    const p = inkPoint(e.clientX, e.clientY);
    if(!p) return;
    const last = curStroke.pts[curStroke.pts.length - 1];
    if(last && last.a === p.a && Math.abs(last.dx - p.dx) < 1.2 && Math.abs(last.dy - p.dy) < 1.2) return;
    if(curStroke.pts.length > 1500) return;
    curStroke.pts.push(p);
    inkRedraw();
    e.preventDefault();
  });
  function inkEndStroke(){ if(curStroke){ curStroke = null; inkSave(); } }
  inkCvs.addEventListener('pointerup', inkEndStroke);
  inkCvs.addEventListener('pointercancel', inkEndStroke);
}
document.addEventListener('click', function(e){
  const t = e.target && e.target.closest ? e.target.closest('span.noted') : null;
  if(t && t.dataset.note) hint('批注：' + t.dataset.note);
});
function inkInit2(){
  if(!inkCvs || !inkCtx) return;
  const paper = inkPaperEl();
  if(!paper) return;
  assignInkAnchors(paper);
  try{
    const raw = localStorage.getItem(INK_KEY);
    const d = raw ? JSON.parse(raw) : null;
    if(Array.isArray(d)) strokes = d;
  }catch(e){}
  inkMarkApply();
  inkRedraw();
  window.addEventListener('scroll', inkRedrawSoon, { passive: true });
  window.addEventListener('resize', inkRedrawSoon);
  document.querySelectorAll('.side').forEach(function(s){ s.addEventListener('scroll', inkRedrawSoon, { passive: true }); });
  if(window.MutationObserver){
    new MutationObserver(inkRedrawSoon).observe(document.documentElement, { attributes: true, attributeFilter: ['style', 'class'] });
  }
  document.addEventListener('click', function(){ if(strokes.length) inkRedrawSoon(); }, true);
  try{
    if(!localStorage.getItem('cet4_radial_tip')){
      localStorage.setItem('cet4_radial_tip', '1');
      setTimeout(function(){ hint('💡 按住鼠标中键 → 圆形工具盘，移动选工具，松开即用'); }, 1600);
    }
  }catch(e){}
}

/* ==================== 中键圆形工具盘（按住→移动→松开） ==================== */
const RAD_ITEMS = [
  { lb: '画笔', t: '', run: function(){ toggleInk(); } },
  { lb: '橡皮', t: '', run: function(){ toggleErase(); } },
  { lb: '清笔', t: '', run: function(){ clearInk(); } },
  { lb: '荧光', t: 't-y', run: function(){ markSel('hl-yellow'); } },
  { lb: '答案句', t: 't-g', run: function(){ markSel('hl-green'); } },
  { lb: '红线', t: 't-r', run: function(){ markSel('redline'); } },
  { lb: '批注', t: 't-n', run: function(){ noteSel(); } },
  { lb: '清标', t: '', run: function(){ clearMarks(); } }
];
const RAD_SIZE = 208, RAD_R = 78, RAD_DEAD = 32;
let radEl = null, radHub = null, radOpen = false, radHot = -1, radCx = 0, radCy = 0;

function radBuild(){
  if(radEl) return radEl;
  radEl = document.createElement('div');
  radEl.id = 'radial';
  radEl.innerHTML = '<div class="bg"></div><div class="hub" id="radHub">工具盘</div>';
  const step = 360 / RAD_ITEMS.length;
  RAD_ITEMS.forEach(function(it, i){
    const a = (-90 + i * step) * Math.PI / 180;
    const b = document.createElement('div');
    b.className = 'ri' + (it.t ? ' ' + it.t : '');
    b.dataset.i = i;
    b.style.left = (RAD_SIZE / 2 + Math.cos(a) * RAD_R) + 'px';
    b.style.top = (RAD_SIZE / 2 + Math.sin(a) * RAD_R) + 'px';
    b.textContent = it.lb;
    radEl.appendChild(b);
  });
  document.body.appendChild(radEl);
  radHub = document.getElementById('radHub');
  return radEl;
}
function radOpenAt(x, y){
  radBuild();
  const half = RAD_SIZE / 2;
  radCx = Math.max(half + 6, Math.min(window.innerWidth - half - 6, x));
  radCy = Math.max(half + 6, Math.min(window.innerHeight - half - 6, y));
  radEl.style.left = (radCx - half) + 'px';
  radEl.style.top = (radCy - half) + 'px';
  radEl.classList.add('on');
  radOpen = true; radHot = -1;
  radPaint();
}
function radPaint(){
  const kids = radEl.querySelectorAll('.ri');
  kids.forEach(function(b, i){ b.classList.toggle('hot', i === radHot); });
  if(radHub) radHub.textContent = radHot >= 0 ? RAD_ITEMS[radHot].lb : '松开取消';
}
function radUpdate(x, y){
  const dx = x - radCx, dy = y - radCy;
  let idx = -1;
  if(Math.hypot(dx, dy) >= RAD_DEAD){
    const step = 360 / RAD_ITEMS.length;
    const deg = (Math.atan2(dy, dx) * 180 / Math.PI + 90 + 720) % 360;
    idx = Math.round(deg / step) % RAD_ITEMS.length;
  }
  if(idx !== radHot){ radHot = idx; radPaint(); }
}
function radClose(){
  if(!radEl) return;
  radEl.classList.remove('on');
  radOpen = false; radHot = -1;
}
function radCommit(){
  const idx = radHot;
  radClose();
  if(idx >= 0) setTimeout(function(){ RAD_ITEMS[idx].run(); }, 0);
}
document.addEventListener('mousedown', function(e){
  if(e.button !== 1) return;
  e.preventDefault();
  radOpenAt(e.clientX, e.clientY);
}, true);
/* 兜底：菜单开着时左键/滚轮 = 取消，避免卡住 */
document.addEventListener('mousedown', function(e){ if(radOpen && e.button === 0) radClose(); }, true);
window.addEventListener('wheel', function(){ if(radOpen) radClose(); }, { capture: true, passive: true });
document.addEventListener('mousemove', function(e){
  if(!radOpen) return;
  radUpdate(e.clientX, e.clientY);
}, true);
/* 中键松开：Chromium 只发 auxclick（不发 mouseup），两个都接，谁先到谁提交 */
function radRelease(e){
  if(!radOpen || e.button !== 1) return;
  e.preventDefault();
  radUpdate(e.clientX, e.clientY);
  radCommit();
}
document.addEventListener('mouseup', radRelease, true);
document.addEventListener('auxclick', radRelease, true);
document.addEventListener('pointercancel', function(){ if(radOpen) radClose(); }, true);
document.addEventListener('keydown', function(e){ if(radOpen && e.key === 'Escape') radClose(); });
window.addEventListener('blur', radClose);
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ROLE_MAP = (("主", "r-subj"), ("谓", "r-pred"), ("宾", "r-obj"),
            ("状", "r-adv"), ("定", "r-attr"), ("补", "r-comp"))


def role_cls(role: str) -> str:
    """成分 → 颜色类（主语蓝/谓语红/宾语绿/状语紫/定语青/补语棕）。"""
    for k, c in ROLE_MAP:
        if k in (role or ""):
            return c
    return "r-other"


def lb(text: str, cls: str = "lb-mean") -> str:
    """解析小标签 chip，颜色区分字段类别。"""
    return f'<span class="lb {cls}">{esc(text)}</span>'


def split_options(text: str) -> list[tuple[str, str]]:
    """把 "A) 无中生有… B) 偷换概念…" 这类长串拆成 [(字母, 说明), …]。"""
    if not text:
        return []
    t = text.replace("A）", "A)").replace("B）", "B)").replace("C）", "C)").replace("D）", "D)")
    parts = re.split(r"(?=(?:^|[\s；;。、，,])([ABCD])[)）、．.]\s*)", t)
    out, cur_l, buf = [], "", ""
    for seg in parts:
        if seg in ("A", "B", "C", "D"):
            if cur_l:
                out.append((cur_l, buf.strip(" ；;。、")))
            cur_l, buf = seg, ""
        else:
            buf += seg
    if cur_l:
        out.append((cur_l, buf.strip(" ；;。、")))
    out = [(k, v) for k, v in out if v]
    return out if len(out) >= 2 else []


def option_rows(q: dict, an: dict) -> str:
    """答案 + 逐选项一行（每行一句）。"""
    ans = (q.get("answer") or "").strip().upper()
    rows = []
    why = (an.get("why") or "").strip()
    if why:
        rows.append(f'<div class="row"><span class="lt ok">{esc(ans)}</span>'
                    f'<span class="tx"><b>对：</b>{esc(why)}</span></div>')
    opts = an.get("options") or []
    if opts:
        for o in opts:
            lt = (o.get("letter") or "").strip().upper()
            if lt == ans:
                continue
            ok = bool(o.get("ok"))
            rows.append(f'<div class="row"><span class="lt {"ok" if ok else "bad"}">{esc(lt)}</span>'
                        f'<span class="tx">{esc((o.get("why") or "").strip())}</span></div>')
    else:
        for lt, why_txt in split_options(an.get("trap") or ""):
            if lt == ans:
                continue
            rows.append(f'<div class="row"><span class="lt bad">{esc(lt)}</span>'
                        f'<span class="tx">{esc(why_txt)}</span></div>')
    return '<div class="an">' + "".join(rows) + "</div>" if rows else ""


def sentence_html(s: dict, aid: str = "", start: float = 0.0, end: float = 0.0) -> str:
    """统一逐句块：意群（带成分配色）+ 整句中文；有音频时可点句播放。"""
    parts = []
    for c in (s.get("chunks") or []):
        if not isinstance(c, dict):
            continue
        inspan = f'<span class="{role_cls(c.get("role"))}">{esc(c.get("en",""))}</span>'
        if c.get("role"):
            inspan += f'<span class="dim">〔{esc(c.get("role"))}·{esc(c.get("cn",""))}〕</span>'
        elif c.get("cn"):
            inspan += f'<span class="dim">（{esc(c.get("cn",""))}）</span>'
        parts.append(inspan)
    body = f'<div class="chk">{" ".join(parts) or esc(s.get("en",""))}</div>'
    if s.get("cn"):
        body += f'<div class="scn">{esc(s.get("cn"))}</div>'
    if s.get("note"):
        body += f'<div>{lb("路标","lb-tip")}<span class="anno-tip">{esc(s.get("note"))}</span></div>'
    if aid:
        return (f'<div class="sent clickable" onclick="seek(\'{aid}\',{start:.3f},{end:.3f},this)">'
                f'{body}</div>')
    return f'<div class="sent">{body}</div>'


def think_writing(tc: dict) -> str:
    """写作思维链：拆题 → 立场 → 框架 → 填充 → 避坑。"""
    if not tc:
        return '<p class="dim">思维链未生成，运行 bin/cet4_thinkchain.py</p>'
    out = []
    if tc.get("breakdown"):
        out.append(lb("① 拆题", "lb-map"))
        out.append('<table class="trs"><tr><th>要素</th><th>这道题要什么</th></tr>' + "".join(
            f'<tr><td>{esc(x.get("item",""))}</td><td>{esc(x.get("value",""))}</td></tr>'
            for x in tc["breakdown"]) + '</table>')
    if tc.get("stance"):
        out.append(lb("② 立场", "lb-main") + f'<div class="anno-en">{esc(tc["stance"])}</div>')
    if tc.get("framework"):
        out.append(lb("③ 框架", "lb-role"))
        for f in tc["framework"]:
            must = "".join(f'<div>· {esc(x)}</div>' for x in (f.get("must") or []))
            out.append(f'<div class="band"><b>第 {esc(str(f.get("para")))} 段</b>　{esc(f.get("goal",""))}'
                       + (f'<div class="musts">{must}</div>' if must else "")
                       + (f'<div class="sk">{esc(f.get("skeleton",""))}</div>' if f.get("skeleton") else "")
                       + "</div>")
    if tc.get("fill"):
        out.append(lb("④ 填充", "lb-chunk"))
        for f in tc["fill"]:
            rows = ""
            for k, lbl in (("openers", "开头"), ("supports", "展开"), ("closers", "收尾"), ("connectors", "衔接")):
                if f.get(k):
                    rows += f'<div class="dim">{lbl}</div>' + "".join(
                        f'<div class="sk">{esc(x)}</div>' for x in f[k])
            out.append(f'<div class="band"><b>第 {esc(str(f.get("para")))} 段</b>{rows}</div>')
    if tc.get("pitfalls"):
        out.append(lb("⑤ 避坑", "lb-trap") + "".join(
            f'<div class="bands"><div>· {esc(x)}</div></div>' for x in tc["pitfalls"]))
    return "".join(out)


def think_translation(tc: dict) -> str:
    """翻译思维链：步骤 → 逐句拆解（小句/主干/难点/成句）→ 文化词。"""
    if not tc:
        return '<p class="dim">思维链未生成，运行 bin/cet4_thinkchain.py</p>'
    out = []
    if tc.get("steps"):
        out.append(lb("① 步骤", "lb-map") + "".join(
            f'<div class="bands"><div>{i}. {esc(x)}</div></div>'
            for i, x in enumerate(tc["steps"], 1)))
    for s in tc.get("sentences") or []:
        clauses = "｜".join(esc(x) for x in (s.get("clauses") or []))
        out.append('<div class="sent">'
                   + f'<div class="dim">中文：{esc(s.get("cn",""))}</div>'
                   + (f'<div>拆句：{clauses}</div>' if clauses else "")
                   + (f'<div>{lb("主干", "lb-main")}{esc(s.get("spine",""))}</div>' if s.get("spine") else "")
                   + (f'<div>{lb("难点", "lb-trap")}{esc(s.get("trap",""))}</div>' if s.get("trap") else "")
                   + (f'<div class="anno-en">{esc(s.get("en",""))}</div>' if s.get("en") else "")
                   + "</div>")
    if tc.get("phrases"):
        out.append(lb("③ 文化词", "lb-band") + "".join(
            f'<div class="bands"><div>{esc(x.get("cn",""))} → <b>{esc(x.get("en",""))}</b>'
            f'　<span class="dim">{esc(x.get("why",""))}</span></div></div>'
            for x in tc["phrases"]))
    return "".join(out)


def build_timing_index(timing: list) -> dict:
    """句子文本 → (start, 下一句 start)。"""
    norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
    idx = {}
    for i, t in enumerate(timing or []):
        key = norm(t.get("en", ""))
        if not key:
            continue
        nxt = timing[i + 1].get("start") if i + 1 < len(timing) else 0
        idx[key] = (float(t.get("start") or 0), float(nxt or 0))
    return idx


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
    ap.add_argument("--sentence-dir", default="var/cet4-daily")
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
    sdir = Path(args.sentence_dir)

    def load_sent(kind: str) -> dict:
        p = sdir / f"sent-explain-{kind}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    sen = {k: load_sent(k) for k in ("cloze", "match", "writing", "translation", "listening")}
    chain_path = sdir / "thinkchain.json"
    chain = json.loads(chain_path.read_text(encoding="utf-8")) if chain_path.exists() else {}
    sectiming = {}
    for k in ("writing", "translation"):
        p = sdir / "audio" / f"{k}.timing.json"
        sectiming[k] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    words_path = Path(args.words)
    words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.exists() else []
    wdict = {x["word"].lower(): x for x in words if x.get("word")}
    wjs = "window.__WORDS__ = " + json.dumps(wdict, ensure_ascii=False) + ";"
    outdir = Path(args.outdir) / args.mode
    outdir.mkdir(parents=True, exist_ok=True)

    parts = []
    parts.append(f'<div class="part">Part I &nbsp; Writing &nbsp;(30 minutes)</div>')
    if MODE == "explain":
        parts.append('<aside class="side"><div class="stabs"><b class="shd">写作思维链</b>'
                     '<button class="stab close" title="收起" onclick="toggleSide(this)">×</button></div>'
                     '<div class="spane on">' + think_writing(chain.get("writing") or {}) + '</div></aside>')
    parts.append(f'<div class="dir">Directions: {esc(data["writing"]["directions"].replace("Directions:","").strip())}</div>')
    parts.append('<textarea placeholder="Write your essay here (120-180 words)"></textarea>')
    if MODE == "explain":
        wdir = sen["writing"].get("writing-directions") or []
        if wdir:
            parts.append('<div class="pan"><div>' + lb("题目逐句", "lb-chunk") + '</div>'
                         + "".join(sentence_html(s) for s in wdir) + '</div>')
    if MODE == "explain":
        w = data["writing"]
        # 音频
        src_mp3 = sdir / "audio" / "writing.mp3"
        if src_mp3.exists():
            shutil.copy(src_mp3, outdir / "writing.mp3")
            parts.append('<audio class="audio" id="au-writing" controls preload="metadata" '
                         'data-src="writing.mp3" src="writing.mp3"></audio>')
        # 范文（可折叠，避免大段占用正文）
        essay = "".join(f'<p class="body">{esc(p.strip())}</p>'
                        for p in (w.get("model_essay") or "").split("\n\n") if p.strip())
        parts.append(f'<details class="fold"><summary>范文（{len((w.get("model_essay") or "").split())} 词）</summary>{essay}</details>')

        wblk = [lb("范文解构", "lb-main")]
        if wexp.get("structure"):
            rows = "".join(f'<tr><td>第 {x.get("para")} 段</td><td>{esc(x.get("role",""))}</td>'
                           f'<td>{esc(x.get("cn",""))}</td></tr>' for x in wexp["structure"])
            wblk.append(f'<table class="trs"><tr><th>段</th><th>作用</th><th>内容</th></tr>{rows}</table>')
        wsent = sen["writing"].get("writing") or []
        wtim = build_timing_index(sectiming["writing"])
        norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        for s in wsent:
            t = wtim.get(norm(s.get("en", "")))
            wblk.append(sentence_html(s, "au-writing", t[0], t[1]) if t else sentence_html(s))
        if wexp.get("expressions"):
            wblk.append(lb("可复用表达", "lb-map") + "".join(
                f'<div class="bands"><div>{esc(x.get("phrase",""))}　{esc(x.get("cn",""))}'
                f'　<span class="dim">{esc(x.get("use",""))}</span></div></div>'
                for x in wexp["expressions"]))
        if wexp.get("bands"):
            wblk.append(lb("评分档", "lb-band") + "".join(
                f'<div class="bands"><div><b>{esc(x.get("score",""))}</b>　{esc(x.get("desc",""))}</div></div>'
                for x in wexp["bands"]))
        if w.get("deductions"):
            wblk.append(lb("扣分点", "lb-trap") + "".join(
                f'<div class="bands"><div>· {esc(x)}</div></div>' for x in w["deductions"]))
        parts.append('<div class="pan">' + "".join(wblk) + "</div>")

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
                parts.append(f'<audio class="audio" id="{aid}" controls preload="metadata" '
                             f'data-src="{audio.name}" src="{audio.name}"></audio>')
            lx = lexp.get(f"{sec['name']}-{Path(piece.get('audio') or 'x').stem}") or {}
            if MODE == "explain":
                if piece.get("summary"):
                    parts.append(f'<div class="sum"><b>大意</b>　{esc(piece["summary"])}</div>')
                cn_map = {x.get("i"): x.get("cn") for x in (lx.get("sentences") or [])}
                timing = piece.get("timing") or []
                starts = [(float(s.get("start") or 0),
                           float(timing[i + 1].get("start") or 0) if i + 1 < len(timing) else 0)
                          for i, s in enumerate(timing)]
                lsent = sen["listening"].get(f"{sec['name']}-{Path(piece.get('audio') or 'x').stem}") or []
                norm_txt = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
                tmap = {}
                for i, s in enumerate(timing):
                    k2 = norm_txt(s.get("en") or s.get("text") or "")
                    if k2:
                        tmap[k2] = starts[i]
                if lsent:
                    blocks = []
                    for i, s in enumerate(lsent):
                        t = tmap.get(norm_txt(s.get("en", ""))) or (starts[i] if i < len(starts) else None)
                        blocks.append(sentence_html(s, aid, t[0], t[1]) if t else sentence_html(s))
                    parts.append('<div class="tr">' + "".join(blocks) + "</div>")
                else:
                    lines = []
                    for i, s in enumerate(timing, 1):
                        en = s.get("en") or s.get("text") or ""
                        st, nxt = starts[i - 1]
                        lines.append(f'<div class="line" onclick="seek(\'{aid}\',{st:.3f},{nxt:.3f},this)">'
                                     f'<div class="en">{i}. {esc(en)}</div>'
                                     f'<div class="cn">{esc(cn_map.get(i) or "")}</div></div>')
                    if lines:
                        parts.append('<div class="tr">' + "".join(lines) + "</div>")
                if lx.get("words"):
                    rows = "".join(
                        f'<tr><td class="w" onclick="speakW(\'{esc(x.get("w",""))}\')">{esc(x.get("w",""))}</td>'
                        f'<td>{esc(x.get("ipa",""))}</td><td>{esc(x.get("pos",""))}</td>'
                        f'<td>{esc(x.get("cn",""))}</td></tr>' for x in lx["words"])
                    parts.append('<table class="vt"><tr><th>本段难词（AI 预选·参考）</th><th>音标</th><th>词性</th><th>释义</th></tr>'
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
                    parts.append('<div class="qax">' + option_rows(q, an) + '</div>')

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
        cl_sents = sen["cloze"].get("cloze") or []
        if cl_sents:
            blk.append(f'<div style="margin-top:6pt">{lb("逐句拆解", "lb-chunk")}</div>'
                       + "".join(sentence_html(s) for s in cl_sents))
        elif cexp.get("passage_cn"):
            blk.append(lb("全文顺流直译", "lb-mean") + "".join(
                f'<div class="bands"><div><span class="dim">{i}.</span> {esc(x)}</div></div>'
                for i, x in enumerate(cexp["passage_cn"], 1)))
        if blk:
            parts.append('<div class="pan">' + "".join(blk) + "</div>")

    parts.append('<div class="sec">Section B</div>')
    parts.append('<div class="dir">Directions: Match each statement with the paragraph it is derived from.</div>')
    for k, v in r["match"]["paragraphs"].items():
        parts.append(f'<p class="body"><b>{k})</b> {esc(v)}</p>')
        mx = mexp.get(k) or {}
        msent = sen["match"].get(f"match-{k}") or []
        if MODE == "explain" and (mx or msent):
            sent = "".join(sentence_html(s) for s in msent)
            parts.append(f'<div class="pan"><div class="anno-cn">{lb("主旨", "lb-main")}{esc(mx.get("main",""))}</div>'
                         f'<div>{lb("作用", "lb-role")}{esc(mx.get("role",""))}</div>'
                         f'<div>{lb("对应题", "lb-map")}{esc("、".join(mx.get("answers") or []) or "无")}</div>'
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
                    sent = "".join(sentence_html(s) for s in (para.get("sentences") or []))
                    extra = ""
                    for key, label in (("meaning", "意思"), ("modifier", "谁修饰谁"),
                                       ("why", "为啥"), ("collocation", "搭配")):
                        if para.get(key):
                            extra += f'<div>{lb(label, "lb-mean")}<span class="anno-cn">{esc(para.get(key))}</span></div>'
                    parts.append(f'<div class="pan"><div class="anno-cn">{lb("段落中文", "lb-mean")}{esc(para.get("cn",""))}</div>'
                                 f'<div>{lb("主旨", "lb-main")}{esc(para.get("main",""))}</div>'
                                 f'<div>{lb("作用", "lb-role")}{esc(para.get("structure",""))}</div>{sent}{extra}</div>')
        else:
            parts.append(f'<p class="body">{esc(pg.get("passage", ""))}</p>')
        for q in pg["questions"]:
            opts = "".join(
                f'<label class="opt" data-q="{q["no"]}" data-l="{o[0]}" onclick="pick({q["no"]},\'{o[0]}\',this)">'
                f'<input type="radio" name="q{q["no"]}">{esc(o)}</label>' for o in q["options"])
            parts.append(f'<div class="q" data-no="{q["no"]}" data-ans="{q["answer"]}"><b>{q["no"]}.</b> '
                         f'{esc(q["stem"])}<div class="opts">{opts}</div></div>')
            if MODE == "explain":
                ans = (q.get("answer") or "").strip().upper()
                rows = []
                for x in (q.get("option_analysis") or []):
                    if not isinstance(x, dict):
                        continue
                    lt = (x.get("letter") or "").strip().upper()
                    ok = lt == ans
                    rows.append(f'<div class="row"><span class="lt {"ok" if ok else "bad"}">{esc(lt)}</span>'
                                f'<span class="tx">{esc((x.get("why") or "").strip())}</span></div>')
                oa = '<div class="an">' + "".join(rows) + "</div>" if rows else ""
                para = q.get("paraphrase") or {}
                parts.append(f'<div class="qax"><div>{lb("答案", "lb-para")}<b>{esc(ans)}</b></div>'
                             + (f'<div>{lb("定位", "lb-loc")}<span class="loc">{esc(q.get("evidence",""))}</span></div>' if q.get("evidence") else "")
                             + (f'<div>{lb("同义替换", "lb-map")}<span class="par">{esc(para.get("original",""))} → {esc(para.get("option",""))}</span></div>' if para else "")
                             + (f'<div>{lb("陷阱", "lb-trap")}<span class="trap">{esc(q.get("trap",""))}</span></div>' if q.get("trap") else "")
                             + oa + '</div>')

    parts.append('<div class="part">Part IV &nbsp; Translation &nbsp;(30 minutes)</div>')
    if MODE == "explain":
        parts.append('<aside class="side"><div class="stabs"><b class="shd">翻译思维链</b>'
                     '<button class="stab close" title="收起" onclick="toggleSide(this)">×</button></div>'
                     '<div class="spane on">' + think_translation(chain.get("translation") or {}) + '</div></aside>')
    parts.append(f'<div class="dir">Directions: Translate the following passage into English.</div>')
    parts.append(f'<p class="body">{esc(data["translation"]["zh"])}</p>')
    parts.append('<textarea placeholder="Write your translation here"></textarea>')
    if MODE == "explain":
        tr = data["translation"]
        src_mp3 = sdir / "audio" / "translation.mp3"
        if src_mp3.exists():
            shutil.copy(src_mp3, outdir / "translation.mp3")
            parts.append('<audio class="audio" id="au-translation" controls preload="metadata" '
                         'data-src="translation.mp3" src="translation.mp3"></audio>')
        if tr.get("reference"):
            parts.append(f'<details class="fold"><summary>参考译文（{len(tr["reference"].split())} 词）</summary>'
                         f'<p class="body">{esc(tr["reference"])}</p></details>')
        tblk = []
        if tr.get("points"):
            tblk.append(lb("踩分点与译法", "lb-map") + "".join(
                f'<div class="bands"><div>· {esc(x)}</div></div>' for x in tr["points"]))
        tsent = sen["translation"].get("translation") or []
        ttim = build_timing_index(sectiming["translation"])
        norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        if tsent:
            tblk.append(lb("逐句拆解", "lb-chunk"))
        for s in tsent:
            t = ttim.get(norm(s.get("en", "")))
            tblk.append(sentence_html(s, "au-translation", t[0], t[1]) if t else sentence_html(s))
        parts.append('<div class="pan">' + "".join(tblk) + "</div>")
        pass

    # 纯题目版只嵌判分必需字段，避免学生查看源码就能读到解析与答案理由
    if MODE == "plain":
        r_ = data["reading"]
        embed = {
            "meta": data.get("meta"),
            "listening": {"questions": [{"no": q["no"], "answer": q["answer"]}
                                        for q in data["listening"]["questions"]]},
            "reading": {
                "cloze": {"answers": r_["cloze"]["answers"]},
                "match": {"answers": r_["match"]["answers"]},
                "passage1": {"questions": [{"no": q["no"], "answer": q["answer"]}
                                           for q in r_["passage1"]["questions"]]},
                "passage2": {"questions": [{"no": q["no"], "answer": q["answer"]}
                                           for q in r_["passage2"]["questions"]]},
            },
        }
    else:
        embed = data

    mode_btns = ('<button id="btnAll" onclick="toggleAll()">展开解析</button>'
                 '<button onclick="toggleSide()">思维链</button>') if MODE == "explain" else ""

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</title><style>{CSS}</style></head><body>
<div class="bar"><b class="ttl">{esc(data.get('meta',{}).get('name','CET-4 模拟卷'))}</b>
<span class="grp">字号
<button onclick="stepFont(-1)" title="缩小">A−</button>
<input id="fsr" type="range" min="7" max="22" step="0.5" value="10.5" oninput="setFont(parseFloat(this.value))">
<button onclick="stepFont(1)" title="放大">A+</button>
<span class="fsv" id="fsv">10.5</span>
<button onclick="resetFont()">默认</button></span>
<span class="grp">
<button id="tbPen" onclick="toggleInk()" title="开/关自由画笔：可在卷面任意书写圈画，笔迹跟着文字走">✒️ 画笔</button>
<select id="penColor" title="笔色"><option value="#e53935">红</option><option value="#111111">黑</option><option value="#1565c0">蓝</option><option value="#2e7d32">绿</option></select>
<select id="penWidth" title="笔粗"><option value="1.6">细</option><option value="2.8" selected>中</option><option value="5">粗</option></select>
<button id="tbErase" onclick="toggleErase()" title="橡皮：点或划过笔迹即可擦除">🧽 橡皮</button>
<button onclick="clearInk()" title="清除全部笔迹">清笔</button></span>
<span class="grp"><span class="lbl">标注</span>
<button onclick="markSel('hl-yellow')" title="荧光笔：先选中文字再点">荧光</button>
<button onclick="markSel('hl-green')" title="答案句：先选中文字再点">答案句</button>
<button onclick="markSel('redline')" title="红线：先选中文字再点">红线</button>
<button onclick="noteSel()" title="批注：先选中文字再点">批注</button>
<button onclick="clearMarks()" title="清除全部高亮/红线/批注">清标</button></span>
<span class="grp"><label style="cursor:pointer;user-select:none"><input type="checkbox" id="cont"> 连播</label>
<button onclick="openVocab()" id="vcount">生词表 0</button>
<span id="score">客观题 --</span>
<button onclick="check()">对答案</button><button onclick="showQA()">显示答案</button>
{mode_btns}
<button onclick="window.print()">打印</button></span></div>
<div class="spacer"></div>
<div class="paper">{''.join(parts)}</div>
<div id="report"><div id="reportBox"><h3 style="margin:0 0 10pt">得分</h3><div id="reportBody"></div>
<button onclick="closeReport()" style="width:100%;margin-top:10pt;padding:6pt">关闭</button></div></div>
<div id="wdict"></div>
<div id="vocab"><div class="vbox"><h3>我的生词表（<span id="vn">0</span> 词）</h3>
<div class="vbar"><button onclick="exportVocab()">导出 Markdown</button>
<button onclick="clearVocab()">清空</button>
<button onclick="closeVocab()" style="margin-left:auto">关闭</button></div>
<div id="vbox"></div></div></div>
<div id="toast"></div>
<canvas id="ink"></canvas>
<script>{wjs}const PAPER = {json.dumps(embed, ensure_ascii=False)};{JS}{INK}
wrapWords(document.querySelector(".paper"));
inkInit2();
upgradeAudio();
setTimeout(bindSentenceStop, 0);
updateVocabCount();</script></body></html>"""
    out = outdir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes, mode={args.mode})")


if __name__ == "__main__":
    main()
