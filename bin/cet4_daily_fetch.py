#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CET-4 每日选材：抓 RSS → 取正文 → 过滤打分 → 输出候选 JSON（不做改写）。

设计原则
- 只挑选「能改写成一议论文/说明文」的严肃内容：社会、心理、教育、健康、科技、环境、职场。
- 每篇候选都留日志：为什么入选、为什么被拒（字数/关键词/重复/抓取失败）。
- 不做 LLM 改写；改写交给 CodeBuddy，本脚本保证输入干净、可追溯。

用法:
  python bin/cet4_daily_fetch.py [--top 8] [--out var/cet4-daily]

输出:
  <out>/candidates-YYYY-MM-DD.json   当日候选（含正文）
  <out>/log-YYYY-MM.jsonl            逐条日志（含拒绝原因）
  <out>/state.json                  已见 URL / 标题哈希，避免重复
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

SOURCES = [
    {"name": "The Guardian", "url": "https://www.theguardian.com/science/rss", "cat": "主流"},
    {"name": "The Guardian Society", "url": "https://www.theguardian.com/society/rss", "cat": "主流"},
    {"name": "BBC Science", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "cat": "主流"},
    {"name": "BBC Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml", "cat": "主流"},
    {"name": "NYT Science", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", "cat": "主流"},
    {"name": "NYT Health", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml", "cat": "主流"},
    {"name": "ScienceDaily", "url": "https://www.sciencedaily.com/rss/top/science.xml", "cat": "科普"},
    {"name": "Popular Science", "url": "https://www.popsci.com/feed/", "cat": "科普"},
    {"name": "The Conversation", "url": "https://theconversation.com/articles.atom", "cat": "学术/观点"},
    {"name": "WIRED", "url": "https://www.wired.com/feed/rss", "cat": "科技"},
    {"name": "NPR Science", "url": "https://www.npr.org/rss/rss.php?id=1001", "cat": "主流"},
    {"name": "The Atlantic", "url": "https://www.theatlantic.com/feed/all/", "cat": "主流"},
]

TOPIC_WORDS = {
    "education": 3, "school": 2, "student": 2, "university": 2, "learning": 2,
    "work": 2, "job": 2, "career": 2, "office": 2, "boss": 1, "employee": 2,
    "health": 2, "sleep": 2, "exercise": 2, "diet": 2, "food": 2, "brain": 2,
    "psychology": 3, "behavior": 2, "behaviour": 2, "habit": 2, "stress": 2,
    "climate": 3, "environment": 2, "energy": 2, "plastic": 2, "sustainab": 2,
    "technology": 2, "internet": 2, "phone": 1, "social media": 2, "algorithm": 1,
    "money": 1, "economy": 2, "inequality": 2, "remote": 1, "city": 1, "traffic": 1,
    "parent": 1, "family": 1, "teenager": 2, "ageing": 1, "aging": 1, "retire": 1,
}
EXCLUDE_WORDS = ["celebrity", "royal", "murder", "shooting", "war", "election",
                 "olympic", "football", "cricket", "recipe", "horoscope", "lottery"]

MIN_WORDS, MAX_WORDS = 420, 1500


def log_line(path: Path, **kw):
    kw["ts"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def fetch(url: str, timeout=12, retries=1) -> bytes | None:
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if i + 1 == retries:
                return None
            time.sleep(1.0)
    return None


def parse_feed(raw: bytes) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        rec = {}
        for child in el:
            ctag = child.tag.split("}")[-1]
            if ctag == "link":
                rec["link"] = (child.text or "").strip() or child.attrib.get("href", "")
            elif ctag in ("title", "pubDate", "updated", "published", "summary", "description"):
                rec[ctag] = re.sub(r"<[^>]+>", " ", child.text or "").strip()
        if rec.get("link"):
            items.append(rec)
    return items


def html_to_text(raw: bytes) -> str:
    try:
        html = raw.decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return ""
    html = re.sub(r"<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
    text = " ".join(paras) if len(paras) >= 5 else re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_article(title: str, text: str) -> tuple[int, list[str]]:
    low = (title + " " + text[:3000]).lower()
    hits = [w for w in TOPIC_WORDS if w in low]
    score = sum(TOPIC_WORDS[w] for w in hits)
    if any(w in low for w in EXCLUDE_WORDS):
        score -= 6
    return score, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--out", default="var/cet4-daily")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = out / f"log-{today[:7]}.jsonl"
    state_path = out / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"urls": [], "titles": []}
    seen_urls, seen_titles = set(state["urls"]), set(state["titles"])

    candidates = []
    for src in SOURCES:
        raw = fetch(src["url"])
        if not raw:
            log_line(log_path, source=src["name"], status="feed_fail", url=src["url"])
            continue
        items = parse_feed(raw)[:10]
        log_line(log_path, source=src["name"], status="feed_ok", items=len(items))
        for it in items:
            url = it.get("link", "").split("?")[0]
            title = re.sub(r"\s+", " ", it.get("title", "")).strip()
            if not url or not title:
                continue
            th = hashlib.sha1(title.lower().encode()).hexdigest()[:12]
            if url in seen_urls or th in seen_titles:
                log_line(log_path, source=src["name"], status="skip_dup", title=title, url=url)
                continue
            body = fetch(url)
            if not body:
                log_line(log_path, source=src["name"], status="article_fail", title=title, url=url)
                continue
            text = html_to_text(body)
            words = len(text.split())
            if not (MIN_WORDS <= words <= MAX_WORDS):
                log_line(log_path, source=src["name"], status="skip_len", title=title, url=url, words=words)
                continue
            sc, hits = score_article(title, text)
            if sc < 6:
                log_line(log_path, source=src["name"], status="skip_topic", title=title, url=url, score=sc, hits=hits)
                continue
            candidates.append({
                "source": src["name"], "cat": src["cat"], "title": title, "url": url,
                "published": it.get("pubDate") or it.get("updated") or it.get("published") or "",
                "words": words, "score": sc, "hits": hits,
                "text": text,
            })
            log_line(log_path, source=src["name"], status="accept", title=title, url=url,
                     words=words, score=sc, hits=hits)
            seen_urls.add(url); seen_titles.add(th)
            time.sleep(0.3)

    candidates.sort(key=lambda c: (-c["score"], -c["words"]))
    picked = candidates[: args.top]
    for c in picked:
        c["text"] = c["text"][:9000]
    payload = {"date": today, "picked": picked,
               "stats": {"candidates": len(candidates), "sources": len(SOURCES)}}
    (out / f"candidates-{today}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    state["urls"] = sorted(seen_urls)[-2000:]
    state["titles"] = sorted(seen_titles)[-2000:]
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    print(f"candidates={len(candidates)} picked={len(picked)} -> {out}")
    for c in picked:
        print(f"  [{c['score']:2d}] {c['source']:18s} {c['words']:4d}w  {c['title'][:70]}")


if __name__ == "__main__":
    sys.exit(main())
