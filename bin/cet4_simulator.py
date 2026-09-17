# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
SIM_DIR = ROOT / 'knowledge' / 'cet4-bank' / '06-全真阅读模拟器'

def load_all_papers():
    json_files = list(SIM_DIR.rglob('model_test_*.json'))
    papers = []
    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['_path'] = jf
            day_val = data.get('day')
            if day_val is None:
                stem_num = jf.stem.split('_')[-1]
                day_val = int(stem_num) if stem_num.isdigit() else 999
                data['day'] = day_val
            if 'week' not in data:
                data['week'] = (day_val - 1) // 7 + 1
            papers.append(data)
        except Exception as e:
            print(f"警告：读取试卷 {jf.name} 失败: {e}", file=sys.stderr)
    papers.sort(key=lambda p: p.get('day', 999))
    return papers

def run_test(paper, auto_answer=None, auto_show_detail=None):
    title = paper.get('title', '')
    title_cn = paper.get('title_cn', '')
    theme = paper.get('theme', '')
    limit = paper.get('suggested_time_minutes', 10)
    w_count = paper.get('word_count', 400)
    day = paper.get('day', 1)
    week = paper.get('week', 1)

    print('\n' + '='*80)
    print(f'🎯 CET-4 仔细阅读 Section C 全真模拟考场 (Day {day:02d} / Week {week})')
    print(f'📄 篇目：{title}')
    if title_cn:
        print(f'📌 主题：{theme} | 中文对照篇名：{title_cn}')
    print(f'⏱️ 建议限时：{limit} 分钟 | 词数：约 {w_count} 词 | 标准：每题 14.2 分 (满分 71.0 分)')
    print('='*80 + '\n')

    # Print passage
    print(paper.get('passage', ''))
    print('\n' + '-'*80)
    print('📝 请根据文章内容，从每题的四个选项中选出最佳答案：')
    print('-'*80 + '\n')

    questions = paper.get('questions', [])
    for q in questions:
        stem = q.get('stem', '')
        q_type = q.get('question_type', '')
        print(f'{stem} [{q_type}]')
        for opt_key, opt_val in q.get('options', {}).items():
            print(f'   {opt_key}) {opt_val}')
        print()

    print('='*80)
    start_time = time.time()
    if auto_answer:
        user_input = auto_answer
        print(f'👉 [自动作答]：{user_input}')
    else:
        user_input = input('👉 请输入你的 5 道题答案（例如: B A C C B 或 BACCB，直接回车交卷）：').strip()
    elapsed = round(time.time() - start_time, 1)

    clean_ans = [c.upper() for c in user_input if c.upper() in ['A', 'B', 'C', 'D']]
    while len(clean_ans) < 5:
        clean_ans.append('-')
    clean_ans = clean_ans[:5]

    correct_count = 0
    questions = paper.get('questions', [])
    print('\n' + '='*80)
    print(f'📊 考卷批改报告 (作答耗时: {elapsed} 秒)')
    print('='*80)

    for i, q in enumerate(questions):
        user_choice = clean_ans[i]
        correct_choice = q.get('correct')
        stem = q.get('stem', '')
        analysis = q.get('analysis', '')
        if user_choice == correct_choice:
            correct_count += 1
            mark = '✅ 正确 (+14.2分)'
        else:
            mark = f'❌ 错误 (你的选择: {user_choice} | 正确答案: {correct_choice})'

        print(f'\n第 {i+1} 题: {mark}')
        print(f'   题干: {stem}')
        print(f'   解析: {analysis}')

    total_score = round(correct_count * 14.2, 1)
    print('\n' + '-'*80)
    print(f'🏆 本篇总得分: {total_score} / 71.0 分 (答对 {correct_count}/5 题)')
    if total_score >= 56.8:
        print('🎉 评级: 极度优秀 (4题及以上正确，仔细阅读高分保底已达成！)')
    elif total_score >= 42.6:
        print('👍 评级: 稳定及格 (3题正确，达到及格线基准)')
    else:
        print('⚠️ 评级: 需重点复盘 (仔细阅读每题14.2分，是四级拿分命脉，务必细读下方中文对照与生词)')
    print('-'*80)

    if auto_show_detail is not None:
        show_detail = 'y' if auto_show_detail else 'n'
    else:
        show_detail = input('\n是否查看全文逐段精翻与考点词库？(y/n, 默认 y): ').strip().lower()

    if show_detail != 'n':
        print('\n' + '='*80)
        print('🏮 全文地道逐段精翻')
        print('='*80)
        print(paper.get('translation_cn', ''))

        print('\n' + '='*80)
        print('📖 核心考点词库与真题搭配 (建议结合文章回看)')
        print('='*80)
        for w in paper.get('vocabulary_bank', []):
            wd = w.get('word', '')
            ph = w.get('phonetic', '')
            pos = w.get('pos', '')
            mean = w.get('meaning', '')
            coll = w.get('collocation', '')
            print(f'• {wd:<18} {ph:<18} [{pos:<5}] {mean:<20} 搭配: {coll}')
        print('='*80 + '\n')

def print_ebbinghaus_schedule(day_map, target_day=None):
    intervals = [
        (1, "1天前 (初次巩固)"),
        (2, "2天前 (隔日强化)"),
        (4, "4天前 (周期对抗)"),
        (7, "7天前 (周度复盘)"),
        (15, "15天前 (半月长效)")
    ]
    if target_day is not None:
        print('='*80)
        print(f'🧠 艾宾浩斯科学遗忘曲线 · 第 {target_day} 天学习与复习作战清单')
        print('='*80)
        if target_day <= 28:
            new_p = day_map.get(target_day, {})
            t = new_p.get('title', '')
            t_cn = new_p.get('title_cn', '')
            theme = new_p.get('theme', '')
            print(f'🎯 【今日新学篇目】: Day {target_day:02d} - {t} ({t_cn})')
            print(f'   所属主题: {theme} | 建议耗时: 15 分钟 (10分钟做题 + 5分钟精读)')
        else:
            print(f'🎉 【新学已通关！】前四周 28 天新课已全部学完，进入纯复习与真题实战阶段！')
        
        print('\n🔄 【今日必复习任务（遗忘临界点激活）】:')
        has_review = False
        for delta, label in intervals:
            r_day = target_day - delta
            if 1 <= r_day <= 28:
                has_review = True
                rp = day_map.get(r_day, {})
                rt = rp.get('title', '')
                rt_cn = rp.get('title_cn', '')
                print(f'  • [{label}] ➔ Day {r_day:02d}: {rt[:38]:<38} ({rt_cn})')
        if not has_review:
            print('  • 今日为初始启动日，暂无旧篇目需要复习，全力拿下今日新篇即可！')
        
        print('\n' + '-'*80)
        print('💡 极速复习 3 步法 (每篇仅需 2~3 分钟，总计 <10 分钟):')
        print('   1. 遮住中文看英文：打开 Markdown 试卷底部的生词表，遮住中文扫一遍 10 个考点词；')
        print('   2. 回看错题定位句：翻到该篇错题对应的【句子图解】和【做题雷达】，加深对命题套路的肌肉记忆；')
        print('   3. 大声朗读金句：挑 1 个最具语感的句子朗读一遍，顺畅语流！')
        print('='*80 + '\n')
        return

    print('='*80)
    print('🧠 艾宾浩斯遗忘曲线 · 前四周 (28天) 科学学习复习全景矩阵')
    print('='*80)
    print(f"{'学习日':<8} | {'今日新学':<10} | {'今日需复习篇目 (按遗忘曲线: 1d, 2d, 4d, 7d, 15d)':<45}")
    print('-'*80)
    for d in range(1, 36):
        new_tag = f"Day {d:02d}" if d <= 28 else "全量复盘"
        review_days = []
        for delta, _ in intervals:
            r = d - delta
            if 1 <= r <= 28:
                review_days.append(f"D{r:02d}")
        rev_str = ", ".join(review_days) if review_days else "无 (首日全力学新)"
        print(f"第 {d:02d} 天   | {new_tag:<10} | {rev_str:<45}")
    print('='*80)
    print('📌 使用指南: 运行 python bin/cet4_simulator.py --today <天数> 即可查看当天具体作战清单！')
    print('='*80 + '\n')

def main():
    parser = argparse.ArgumentParser(description='CET-4 仔细阅读 Section C 全真模拟考场')
    parser.add_argument('--day', type=int, help='直接指定模拟的天数 (1-28)')
    parser.add_argument('--list', action='store_true', help='列出所有可用模拟试卷')
    parser.add_argument('--answer', type=str, help='非交互式作答 (例如: BACCB)')
    parser.add_argument('--no-detail', action='store_true', help='不展示全文精翻与词库')
    parser.add_argument('--schedule', action='store_true', help='查看基于艾宾浩斯遗忘曲线的28天完整复习日历')
    parser.add_argument('--today', type=int, help='查看指定学习天数的“今日新学+今日必复习”科学清单 (1-35)')
    args = parser.parse_args()

    papers = load_all_papers()
    if not papers:
        print(f'未找到试卷文件，请确认 {SIM_DIR} 是否存在有效 JSON 试卷。')
        return

    day_map = {p['day']: p for p in papers}

    if args.schedule:
        print_ebbinghaus_schedule(day_map)
        return

    if args.today is not None:
        print_ebbinghaus_schedule(day_map, target_day=args.today)
        return

    if args.list:
        print('='*80)
        print(f'📚 CET-4 全真仔细阅读题库目录 (共 {len(papers)} 套试卷)')
        print('='*80)
        cur_w = 0
        for p in papers:
            w = p.get('week', 1)
            if w != cur_w:
                cur_w = w
                theme = p.get('theme', '核心社科专题')
                print(f'\n【Week {w}】主题：{theme}')
                print('-'*80)
            d = p.get('day', 0)
            t = p.get('title', '')
            t_cn = p.get('title_cn', '')
            wc = p.get('word_count', 0)
            print(f'  Day {d:02d} | 词数: {wc} 词 | {t} ({t_cn})')
        print('='*80)
        return

    if args.day:
        if args.day in day_map:
            run_test(day_map[args.day], auto_answer=args.answer, auto_show_detail=(not args.no_detail))
        else:
            print(f'错误：未找到 Day {args.day} 的试卷，目前已有试卷天数: {sorted(list(day_map.keys()))}')
        return

    print('='*80)
    print('📚 欢迎进入 CET-4 仔细阅读情境模拟考场（前四周 28 天冲刺版）')
    print('='*80)
    
    cur_w = 0
    for p in papers:
        w = p.get('week', 1)
        if w != cur_w:
            cur_w = w
            theme = p.get('theme', '核心社科专题')
            print(f'\n【Week {w}】主题：{theme}')
            print('-'*80)
        d = p.get('day', 0)
        t = p.get('title', '')
        t_cn = p.get('title_cn', '')
        print(f'  [{d:02d}] Day {d:02d}: {t[:40]:<40} ({t_cn})')

    print('\n' + '='*80)
    print('💡 提示: 可随时使用 python bin/cet4_simulator.py --schedule 查看艾宾浩斯复习日历')
    choice = input(f'👉 请选择试卷天数 (1-{len(papers)}, 直接回车默认 1，输入 q 退出): ').strip()
    if choice.lower() == 'q':
        print('退出模拟考场。祝备考顺利！')
        return

    selected_day = int(choice) if choice.isdigit() and int(choice) in day_map else 1
    run_test(day_map[selected_day])

if __name__ == '__main__':
    main()
