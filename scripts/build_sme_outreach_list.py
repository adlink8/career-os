# -*- coding: utf-8 -*-
"""从 job_targets 生成中小厂可执行联系清单（去重到公司维度）。

输出：
  data/sme-outreach-list.csv   全量 214 家，按「城市优先级 + 总分」排序
  data/sme-outreach-batch1.md  第一批 20 家（常州优先），可直接打电话/搜 BOSS

用法：python scripts/build_sme_outreach_list.py
"""
import csv
import os
import re
import sqlite3
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'career_jobs.sqlite')
OUT_CSV = os.path.join(ROOT, 'data', 'sme-outreach-list.csv')
OUT_MD = os.path.join(ROOT, 'data', 'sme-outreach-batch1.md')
TC_CSV = os.path.join(ROOT, 'data', 'tianyancha', '重点公司投递信息.csv')

# 城市优先级：用户在常州读书，就近优先
CITY_ORDER = {'常州': 0, '无锡': 1, '苏州': 2, '南京': 3, '南通': 4, '徐州': 5}

# 只保留能投递的赛道（与用户目标一致）
KEEP_CATEGORY = ('技术支持', '项目实施', '运维')
# 明确排除的赛道（已确认不做研发）
DROP_CATEGORY = ('算法',)


def load_targets():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute('select * from job_targets')]
    db.close()
    return rows


def load_contacts():
    """已有的电话/邮箱（企查查重点公司，仅 7 家）。"""
    out = {}
    if not os.path.exists(TC_CSV):
        return out
    with open(TC_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            name = (r.get('公司名称') or '').strip()
            if name:
                out[name] = r
    return out


def norm_key(name):
    """公司名归一化：去掉省市前缀、括号后缀、空格，用于匹配联系方式。"""
    s = re.sub(r'^(江苏省|江苏|常州|无锡|苏州|南京|南通|徐州)', '', name)
    s = re.sub(r'[（(].*?[)）]', '', s)
    return re.sub(r'\s+', '', s)


def boss_url(name):
    return 'https://www.zhipin.com/web/geek/job?query=' + quote(name)


def zhilian_url(name):
    return 'https://sou.zhaopin.com/?kw=' + quote(name)


def year_of(date_str):
    if not date_str:
        return ''
    m = re.match(r'(\d{4})', str(date_str))
    return m.group(1) if m else ''


def main():
    rows = load_targets()
    contacts = load_contacts()
    ck = {norm_key(k): v for k, v in contacts.items()}

    comps = {}
    for r in rows:
        cat = r.get('category') or ''
        if any(d in cat for d in DROP_CATEGORY):
            continue
        name = (r.get('company_name') or '').strip()
        if not name:
            continue
        c = comps.setdefault(name, {
            'company_name': name,
            'city': r.get('city') or '',
            'company_type': r.get('company_type') or '',
            'total_score': r.get('total_score') or 0,
            'entry_friendliness': r.get('entry_friendliness') or 0,
            'registration_capital': r.get('registration_capital') or '',
            'establishment_date': r.get('establishment_date') or '',
            'reg_status': r.get('reg_status') or '',
            'titles': [],
        })
        t = (r.get('target_title') or '').strip()
        if any(k in cat for k in KEEP_CATEGORY) and t and t not in c['titles']:
            c['titles'].append(t)
        if not c['titles'] and t and t not in c['titles']:
            c['titles'].append(t)

    items = list(comps.values())

    def sort_key(c):
        city = c['city']
        ci = CITY_ORDER.get(city, 9)
        if '待核实' in city:
            ci = 8
        return (ci, -float(c['total_score'] or 0))

    items.sort(key=sort_key)

    header = [
        '序号', '城市', '公司名称', '公司类型', '目标岗位', '总分', '入门友好度',
        '注册资本', '成立年', '登记状态', 'BOSS搜索', '智联搜索',
        '电话/邮箱', '投递方式', '已确认岗位', '是否在招', '联系状态', '备注',
    ]

    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, c in enumerate(items, 1):
            ct = ck.get(norm_key(c['company_name']), {})
            titles = ' / '.join(c['titles'][:3])
            w.writerow([
                i,
                c['city'],
                c['company_name'],
                c['company_type'],
                titles,
                c['total_score'],
                c['entry_friendliness'],
                c['registration_capital'],
                year_of(c['establishment_date']),
                c['reg_status'],
                boss_url(c['company_name']),
                zhilian_url(c['company_name']),
                (ct.get('招聘邮箱/电话') or '').replace('--', ''),
                (ct.get('投递方式') or '').replace('--', ''),
                (ct.get('已确认岗位') or '').replace('--', ''),
                '',  # 是否在招：人工填
                '',  # 联系状态：未联系 / 已搜无岗 / 已打电话 / 已投
                '',
            ])

    # 第一批：常州优先，评分 top 20
    batch = [c for c in items if CITY_ORDER.get(c['city'], 9) <= 1][:20]

    lines = [
        '# 第一批联系清单（常州 + 无锡，共 {} 家）'.format(len(batch)),
        '',
        '> 生成时间：脚本 `scripts/build_sme_outreach_list.py`，数据源 `job_targets`（企查查工商名录）。',
        '> 全量 214 家见 `data/sme-outreach-list.csv`。',
        '',
        '## 用法',
        '',
        '1. 点 BOSS 搜索链接，看这家公司有没有在招岗位。**看有没有岗位，不看岗位名是不是校招。**',
        '2. 有岗 → 直接直聊，不用投简历。',
        '3. 无岗但有电话 → 打电话问「有没有实习或应届的技术支持/运维岗」。',
        '4. 在 CSV 里把「是否在招 / 联系状态」填上，隔天复查。',
        '',
        '## 清单',
        '',
        '| # | 城市 | 公司 | 类型 | 目标岗位 | 评分 | 电话/邮箱 | 操作 |',
        '|---|---|---|---|---|---|---|---|',
    ]
    for i, c in enumerate(batch, 1):
        ct = ck.get(norm_key(c['company_name']), {})
        phone = (ct.get('招聘邮箱/电话') or '').replace('--', '').strip()
        if not phone:
            phone = '—'
        lines.append('| {} | {} | {} | {} | {} | {} | {} | [BOSS搜]({}) · [智联搜]({}) |'.format(
            i, c['city'], c['company_name'], c['company_type'],
            ' / '.join(c['titles'][:2]) or '—',
            c['total_score'], phone,
            boss_url(c['company_name']), zhilian_url(c['company_name']),
        ))

    lines += [
        '',
        '## 数据质量提醒（必读）',
        '',
        '**这份清单不是「已确认在招的岗位」，是「工商名录里筛选出来的公司名」。**',
        '',
        '- `job_targets` 来源是企查查工商名录按「江苏中小/微型 + IoT/云/AI/系统集成关键词」评分筛出，',
        '  **未经任何在招状态核实**（`verification_status` 全为「待核实」，`application_url` 全为空）。',
        '- 公司名高度同质（大量「常州X智能系统集成有限公司」），**存在空壳、批量注册、同名重复的可能**。',
        '- `目标岗位` 列是脚本按赛道生成的**假想岗位标题**，不是真实 JD，不要照抄到简历或自荐里。',
        '',
        '**验证顺序（从上到下，成本递增）：**',
        '',
        '1. BOSS 搜公司名 → 看有没有在招岗位（最快）',
        '2. 企查查/天眼查查**参保人数** → 参保 0 人或 1-2 人的，大概率是空壳，跳过',
        '3. 打电话 → 直接问有没有实习/应届技术支持岗',
        '',
        '**验证后请在 `data/sme-outreach-list.csv` 里把「是否在招 / 联系状态」填上**，否则这份清单两周后就是死数据。',
        '',
        '## 电话开场白（有电话的用这个）',
        '',
        '> 您好，我是常州大学计算机专业的，2027 年毕业。做过物联网网关接入云平台的项目，',
        '> MQTT、Linux、Docker 都会一些。想问问咱们这边有没有实习或者应届的技术支持/运维岗位？',
        '',
        '## BOSS 首聊话术（有岗的用这个）',
        '',
        '> 你好，我是常州大学 2027 届计算机专业的。看到贵司在招技术支持，',
        '> 我做过 ESP32→MQTT→网关→云平台的完整链路，GitHub 有 1500+ commits，',
        '> 也能跑现场出差。想问下这个岗还招应届吗？',
        '',
    ]

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('全量清单:', OUT_CSV)
    print('  {} 家公司'.format(len(items)))
    print('第一批:', OUT_MD)
    print('  {} 家（常州/无锡优先）'.format(len(batch)))
    print()
    print('城市分布:')
    cnt = {}
    for c in items:
        cnt[c['city']] = cnt.get(c['city'], 0) + 1
    for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
        print('  {}: {}'.format(k, v))


if __name__ == '__main__':
    main()
