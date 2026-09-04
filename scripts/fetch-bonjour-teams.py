#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抓取 bonjour.bio 找工地图全部团队档案 → data/jobs/teams-bonjour.json/.csv
用法: python scripts/fetch-bonjour-teams.py
"""
import re, json, csv, html as htmlmod, time, urllib.request, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'jobs'
MAIN = 'https://bonjour.bio/jobs-mapping'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def fetch(url, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if i == retries:
                print(f'  FAIL {url}: {e}', flush=True)
                return ''
            time.sleep(2)

def text(s):
    return htmlmod.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()

def parse_team(slug, html):
    g = lambda p, flags=0: (re.search(p, html, flags) or [None, ''])[1]
    name = text(g(r't4-hero-name">(.*?)<'))
    tagline = text(g(r't4-hero-tag">(.*?)</p>', re.S))
    locs = re.findall(r't4-chip--loc[^>]*>.*?t4-chip-text">(.*?)<', html, re.S)
    locs = [text(x) for x in locs]
    website = g(r't4-chip--website[^>]*href="([^"]+)"')
    size = text(g(r'(\d+\s*[-–~]\s*\d+\s*人|\d+\+\s*人)'))
    # 正文描述:t4-doc 下 hero 之后的段落
    desc_m = re.search(r't4-hero-tag">.*?</p>(.*?)</article>', html, re.S)
    desc = text(desc_m.group(1))[:2000] if desc_m else ''
    founders = []
    for fb in re.findall(r'<div class="t4-founder">(.*?)</div>\s*(?=<div class="t4-founder">|</div>\s*</div>)', html, re.S):
        nm = text(g2 := (re.search(r'class="nm">(.*?)<', fb) or [None, ''])[1])
        rl = text((re.search(r'class="rl">(.*?)<', fb) or [None, ''])[1])
        bio = text((re.search(r'<p class="t4-f[^"]*">(.*?)</p>', fb, re.S) or [None, ''])[1])
        if nm:
            founders.append({'name': nm, 'role': rl, 'bio': bio[:500]})
    jobs = []
    for jm in re.finditer(r'href="(/jobs-mapping/jobs/([0-9a-f-]+))\?src=team".*?detail-job-list-role">(.*?)<', html, re.S):
        jobs.append({'id': jm.group(2), 'title': text(jm.group(3)),
                     'url': 'https://bonjour.bio' + jm.group(1)})
    return {'slug': slug, 'name': name, 'tagline': tagline, 'locations': locs,
            'size': size, 'website': website, 'description': desc,
            'founders': founders, 'jobs': jobs,
            'url': f'https://bonjour.bio/jobs-mapping/team/{slug}'}

def main():
    main_html = fetch(MAIN)
    slugs = sorted(set(re.findall(r'href="/jobs-mapping/team/([^"?#]+)"', main_html)))
    slugs = [s for s in slugs if not s.startswith('team')]
    print(f'teams: {len(slugs)}', flush=True)
    teams = []
    for i, slug in enumerate(slugs, 1):
        html = fetch(f'{MAIN}/team/{slug}')
        if not html:
            continue
        t = parse_team(slug, html)
        teams.append(t)
        if i % 20 == 0:
            print(f'  {i}/{len(slugs)}', flush=True)
        time.sleep(0.2)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'teams-bonjour.json').write_text(
        json.dumps(teams, ensure_ascii=False, indent=1), encoding='utf-8')
    with open(OUT / 'teams-bonjour.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name', 'tagline', 'locations', 'size', 'website', 'jobs_count', 'url'])
        for t in teams:
            w.writerow([t['name'], t['tagline'], ' / '.join(t['locations']),
                        t['size'], t['website'], len(t['jobs']), t['url']])
    print(f'done: {len(teams)} teams -> {OUT}')

if __name__ == '__main__':
    main()
