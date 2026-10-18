#!/usr/bin/env python3
"""CET-4 模拟卷听力 -> MP3 + 双语字幕（SRT + 自带播放器 player.html）。
解析 mock-XX/parts/part2-listening.md 的 tapescript 折叠块，edge-tts 逐句分角色合成，
精确记录每句时间轴；audio/sentences.en.json 为英文逐句骨架，人工/代理回填
audio/subtitles.zh.json（同长度字符串数组）后即出双语字幕。
逐句 PCM 缓存于 audio/.tts-cache，重跑只补缺失句。
用法: python bin/cet4_mock_to_audio.py <mock_dir> [--demo] [--pause 10]"""
import asyncio, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VOICE_M = "en-US-GuyNeural"      # 对话男声
VOICE_W = "en-US-AriaNeural"    # 对话女声
VOICE_N = "en-US-ChristopherNeural"  # 新闻与篇章播报
SR = 24000

BLOCK_QN = {"news": [2, 2, 3], "conv": [4, 4], "passage": [3, 3, 4]}
WORDNUM = {"1": "One", "2": "Two", "3": "Three"}
INTRO = {"news": "News Report", "conv": "Conversation", "passage": "Passage"}


def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    return [s for s in (x.strip() for x in re.split(r"(?<=[.!?])\s+", text)) if s]


def parse_blocks(md: str):
    """按文档顺序产出 (kind, idx, title, [(voice, text), ...])。"""
    counters = {"news": 0, "conv": 0, "passage": 0}
    for m in re.finditer(r"<summary>(.*?)原文（Tapescript）</summary>\n([\s\S]*?)</details>", md):
        title, body = m.group(1).strip(), m.group(2)
        if "News Report" in title:
            kind = "news"
        elif "Conversation" in title:
            kind = "conv"
        elif "Passage" in title:
            kind = "passage"
        else:
            continue
        idx = counters[kind]
        counters[kind] += 1
        lines = []
        for raw in body.splitlines():
            s = raw.strip().rstrip("#").strip()
            if not s or re.match(r"^Q\d+[:.]", s) or s.startswith(("[", "###")):
                continue
            dm = re.match(r"^(M|W)\d?:\s*(.+)", s)
            if dm:
                voice = VOICE_M if dm.group(1) == "M" else VOICE_W
                lines.append((voice, re.sub(r"\*\*(.+?)\*\*", r"\1", dm.group(2))))
            else:
                lines.append((VOICE_N, re.sub(r"\*\*(.+?)\*\*", r"\1", s)))
        yield kind, idx, title, lines


def build_items(blocks, pause):
    """(say, text, voice, pad) / (gap, seconds) 序列。"""
    items = []
    for kind, idx, title, lines in blocks:
        items.append(("say", f"{INTRO[kind]} {WORDNUM[str(idx + 1)]}.", VOICE_N, 0.8))
        if any(v in (VOICE_M, VOICE_W) for v, _ in lines):
            for voice, text in lines:
                v = voice if voice in (VOICE_M, VOICE_W) else VOICE_N
                for s in split_sentences(text):
                    items.append(("say", s, v, 0.35))
        else:
            for s in split_sentences(" ".join(t for _, t in lines)):
                items.append(("say", s, VOICE_N, 0.3))
        items.append(("gap", float(BLOCK_QN[kind][idx]) * pause + 1.5))
    return items


def srt_ts(sec):
    ms = int(round(sec * 1000))
    h, r = divmod(ms, 3600000)
    m, r = divmod(r, 60000)
    s, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues, path):
    out = []
    for i, c in enumerate(cues, 1):
        text = "\n".join(x for x in (c["en"], c["zh"]) if x)
        out.append(f"{i}\n{srt_ts(c['start'])} --> {srt_ts(c['end'])}\n{text}\n")
    path.write_text("\n".join(out), encoding="utf-8")


def apply_annotations(cues, out_dir):
    """读 audio/annotations.json，把逐句重点标注（marks）与板块听法提示（tip）写进 cues。"""
    f = out_dir / "annotations.json"
    if not f.exists():
        return 0
    ann = json.loads(f.read_text(encoding="utf-8"))
    say_cue = {}
    n = 0
    for c in cues:
        if c["role"] != "gap":
            say_cue[n] = c
            n += 1
    missed = []
    for si, spans in ann.get("spans", {}).items():
        c = say_cue.get(int(si))
        if not c:
            continue
        marks = c.setdefault("marks", [])
        for sp in spans:
            pos = c["en"].find(sp["quote"])
            if pos < 0:
                missed.append(sp["quote"][:40])
                continue
            if any(pos < m["p"] + m["l"] and m["p"] < pos + len(sp["quote"]) for m in marks):
                continue
            marks.append({"p": pos, "l": len(sp["quote"]), "t": sp["t"], "note": sp.get("note", "")})
        marks.sort(key=lambda m: m["p"])
    for si, tip in ann.get("tips", {}).items():
        c = say_cue.get(int(si))
        if c:
            c["tip"] = tip
    if missed:
        print(f"警告：{len(missed)} 条标注原文未在句中定位到: {missed[:3]}")
    return sum(len(c.get("marks", [])) for c in cues)


def write_player(cues, mp3_name, path):
    data = json.dumps(cues, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>CET-4 Listening Player</title>
<style>
body{{margin:0;background:#14161a;color:#dfe3e8;font-family:'Segoe UI','Microsoft YaHei',sans-serif;display:flex;flex-direction:column;height:100vh}}
header{{padding:10px 18px;font-weight:600;border-bottom:1px solid #2a2e35;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
#legend{{font-size:12px;font-weight:400;color:#9aa3af}}
#legend b{{padding:1px 8px;border-radius:4px;margin:0 2px}}
#sub{{flex:0 0 auto;text-align:center;padding:14px 30px 6px;min-height:118px}}
#en{{font-size:22px;line-height:1.5;color:#fff}}
#zh{{font-size:19px;line-height:1.4;color:#ffd479;margin-top:5px}}
#tip{{font-size:14px;margin-top:6px;color:#7fc4ff}}
#wrap{{flex:1 1 auto;overflow-y:auto;padding:10px 30px 30px}}
p.line{{margin:6px 0;padding:6px 10px;border-radius:6px;cursor:pointer;line-height:1.6}}
p.line:hover{{background:#1f242c}}
p.line.on{{background:#2b3548}}
p.gap{{color:#6f7885;font-style:italic;cursor:default}}
.zh{{color:#8b93a0;font-size:14px;margin-right:10px}}
.m .en{{color:#7fc4ff}} .w .en{{color:#8fe3a4}} .n .en,.meta .en{{color:#e8c07d}}
.tip-line{{color:#7fc4ff;font-size:13px;margin:-2px 0 6px 22px}}
mark{{color:#10131a;border-radius:3px;padding:0 2px}}
.k-answer{{background:#63d68a}} .k-signal{{background:#ff9d5c}}
.k-detail{{background:#7fc4ff}} .k-trap{{background:#d9a2ff;text-decoration:underline wavy #b3541e}}
#transport{{flex:0 0 auto;display:flex;align-items:center;gap:14px;padding:10px 18px 18px}}
#play{{flex:0 0 auto;width:46px;height:46px;border-radius:50%;border:none;background:#3b82f6;color:#fff;font-size:18px;cursor:pointer}}
#bar{{flex:1 1 auto;height:26px;display:flex;align-items:center;cursor:pointer;touch-action:none}}
#track{{width:100%;height:10px;border-radius:5px;background:#2a2e35;position:relative}}
#fill{{height:100%;border-radius:5px;background:#3b82f6;width:0}}
#knob{{position:absolute;top:50%;width:18px;height:18px;border-radius:50%;background:#fff;transform:translate(-50%,-50%);left:0;box-shadow:0 1px 4px #0008}}
#time{{flex:0 0 auto;font-variant-numeric:tabular-nums;color:#9aa3af}}
audio{{display:none}}
</style></head><body>
<header><span id="title"></span><span id="legend">重点：<b style="background:#63d68a">答案定位</b><b style="background:#ff9d5c">信号词(转折/因果)</b><b style="background:#7fc4ff">细节出题点</b><b style="background:#d9a2ff">视听一致陷阱</b>（鼠标悬停看解析）</span></header>
<div id="sub"><div id="en"></div><div id="zh"></div><div id="tip"></div></div>
<div id="wrap"></div>
<div id="transport">
 <button id="play">▶</button>
 <div id="bar"><div id="track"><div id="fill"></div><div id="knob"></div></div></div>
 <span id="time">0:00 / -:-</span>
</div>
<audio id="a" src="{mp3_name}" preload="metadata"></audio>
<script>
const CUES={data};
const a=document.getElementById('a'),wrap=document.getElementById('wrap');
const fmt=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');
document.getElementById('title').textContent=decodeURIComponent(location.pathname.split('/').slice(-2,-1)[0])+' — Listening';
function enFrag(c){{
 const f=document.createDocumentFragment();let pos=0;
 (c.marks||[]).forEach(m=>{{
  if(m.p>pos)f.append(document.createTextNode(c.en.slice(pos,m.p)));
  const k=document.createElement('mark');k.className='k-'+m.t;
  k.textContent=c.en.substr(m.p,m.l);if(m.note)k.title=m.note;f.append(k);pos=m.p+m.l;}});
 f.append(document.createTextNode(c.en.slice(pos)));return f;}}
CUES.forEach((c)=>{{const p=document.createElement('p');
 if(c.role==='gap'){{p.className='line gap';p.textContent=c.zh||'…';}}
 else{{p.className='line r-'+c.role+' '+c.role;
  if(c.zh){{const z=document.createElement('span');z.className='zh';z.textContent=c.zh;p.append(z);}}
  const e=document.createElement('span');e.className='en';e.append(enFrag(c));p.append(e);}}
 p.onclick=()=>{{a.currentTime=c.start+.02;}};wrap.appendChild(p);c.el=p;
 if(c.tip){{const t=document.createElement('div');t.className='tip-line';t.textContent='🎧 '+c.tip;wrap.appendChild(t);c.tipEl=t;}}}});
let cur=-1;
function paint(i){{
 const en=document.getElementById('en'),zh=document.getElementById('zh'),tip=document.getElementById('tip');
 en.textContent='';zh.textContent='';tip.textContent='';
 if(i<0)return;const c=CUES[i];
 if(c.role==='gap')zh.textContent=c.zh;
 else{{en.append(enFrag(c));zh.textContent=c.zh||'';if(c.tip)tip.textContent='🎧 '+c.tip;}}}}
a.addEventListener('timeupdate',()=>{{const t=a.currentTime;
 let i=CUES.findIndex(c=>t>=c.start&&t<c.end);
 if(i!==cur){{if(cur>=0)CUES[cur].el.classList.remove('on');
  if(i>=0){{CUES[i].el.classList.add('on');CUES[i].el.scrollIntoView({{block:'center',behavior:'smooth'}});}}
  paint(i);cur=i;}}
 const d=a.duration||1;const r=Math.min(t/d,1);
 document.getElementById('fill').style.width=(r*100)+'%';
 document.getElementById('knob').style.left=(r*100)+'%';
 document.getElementById('time').textContent=fmt(t)+' / '+fmt(a.duration||0);}});
const play=document.getElementById('play');
play.onclick=()=>{{a.paused?a.play():a.pause();}};
a.onplay=()=>play.textContent='⏸';a.onpause=()=>play.textContent='▶';
const bar=document.getElementById('bar');
function seekEv(e){{const r=bar.getBoundingClientRect();
 a.currentTime=Math.min(Math.max((e.clientX-r.left)/r.width,0),1)*(a.duration||0);}}
bar.addEventListener('pointerdown',e=>{{bar.setPointerCapture(e.pointerId);seekEv(e);bar._d=true;}});
bar.addEventListener('pointermove',e=>{{if(bar._d)seekEv(e);}});
bar.addEventListener('pointerup',()=>bar._d=false);
</script></body></html>"""
    path.write_text(html, encoding="utf-8")


def mp3_to_pcm(path, ffmpeg):
    wav = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-f", "f32le", "-acodec", "pcm_f32le",
         "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(wav, dtype=np.float32)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mock_dir = Path(args[0]) if args else Path("knowledge/cet4-bank/07-整套模拟卷/mock-01")
    demo = "--demo" in sys.argv
    pause = 2.0 if demo else 10.0
    for a in args[1:]:
        if a.isdigit():
            pause = float(a)
    rate = "-10%" if demo else "+0%"

    md = (mock_dir / "parts" / "part2-listening.md").read_text(encoding="utf-8")
    blocks = list(parse_blocks(md))
    assert len(blocks) == 8, f"应解析出 8 个 tapescript 块，实得 {len(blocks)}"
    items = build_items(blocks, pause)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    out_dir = mock_dir / "audio"
    out_dir.mkdir(exist_ok=True)
    cache = out_dir / ".tts-cache"
    cache.mkdir(exist_ok=True)
    en_texts = [i[1] for i in items if i[0] == "say"]
    (out_dir / "sentences.en.json").write_text(
        json.dumps(en_texts, ensure_ascii=False, indent=1), encoding="utf-8")
    zh = []
    zh_file = out_dir / "subtitles.zh.json"
    if zh_file.exists():
        zh = json.loads(zh_file.read_text(encoding="utf-8"))
        if len(zh) != len(en_texts):
            print(f"警告：subtitles.zh.json 有 {len(zh)} 句，英文 {len(en_texts)} 句，本次仅出英文字幕")
            zh = []

    async def run():
        chunks, seq = [], []
        n_say = 0
        with tempfile.TemporaryDirectory() as td:
            for item in items:
                if item[0] == "gap":
                    seq.append(("gap", item[1]))
                    continue
                text, voice, pad = item[1], item[2], item[3]
                key = hashlib.md5(f"{voice}|{rate}|{text}".encode()).hexdigest()
                f32 = cache / f"{key}.f32"
                if f32.exists():
                    pcm = np.fromfile(f32, dtype=np.float32)
                else:
                    p = Path(td) / f"{key}.mp3"
                    await edge_tts.Communicate(text, voice, rate=rate).save(str(p))
                    pcm = mp3_to_pcm(p, ffmpeg)
                    pcm.tofile(f32)
                    print(f"  tts {n_say + 1}/{len(en_texts)}  {text[:48]}")
                role = "meta" if item[1].startswith(("News Report", "Conversation", "Passage")) else \
                       ("m" if voice == VOICE_M else "w" if voice == VOICE_W else "n")
                seq.append(("say", pcm, pad, text, role, n_say))
                n_say += 1
        sil = lambda s: np.zeros(int(SR * s), dtype=np.float32)
        cues, t = [], 0.0
        for e in seq:
            if e[0] == "gap":
                cues.append({"start": round(t, 3), "end": round(t + e[1], 3), "en": "",
                             "zh": f"⏳ 请作答（{int(e[1])} 秒）", "role": "gap"})
                chunks.append(sil(e[1]))
                t += e[1]
            else:
                _, pcm, pad, text, role, i = e
                dur = len(pcm) / SR
                cues.append({"start": round(t, 3), "end": round(t + dur, 3), "en": text,
                             "zh": zh[i] if i < len(zh) else "", "role": role})
                chunks += [pcm, sil(pad)]
                t += dur + pad
        return np.concatenate(chunks), cues

    audio, cues = asyncio.run(run())
    stem = mock_dir.name
    final = out_dir / f"{stem}-listening.mp3"
    wav_tmp = out_dir / f"{stem}-listening.raw.wav"
    wav_tmp.write_bytes(audio.tobytes())
    subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1",
         "-i", str(wav_tmp), "-codec:a", "libmp3lame", "-b:a", "64k", str(final)], check=True)
    wav_tmp.unlink()
    n_marks = apply_annotations(cues, out_dir)
    write_srt(cues, out_dir / f"{stem}-listening.srt")
    write_player(cues, final.name, out_dir / "player.html")
    dur = len(audio) / SR
    mode = "双语" if zh else "英文（待回填 subtitles.zh.json）"
    print(f"生成 {final}  时长 {dur/60:.1f} 分钟  字幕：{mode}  重点标注：{n_marks} 处\n"
          f"  {out_dir / (stem + '-listening.srt')}\n  {out_dir / 'player.html'}")


if __name__ == "__main__":
    main()
