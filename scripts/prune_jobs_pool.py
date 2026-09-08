#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""岗位池清洗：干跑 / 执行。
用法：
  python scripts/prune_jobs_pool.py --dry-run   # 只输出预览，不改库
  python scripts/prune_jobs_pool.py --apply --buckets A,C --soft
                                                # 执行；--soft=标记归档（可恢复），不加则硬删除
"""
import argparse
import collections
import re
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "career_jobs.sqlite"

# 受保护状态：已产生真实动作的记录不允许删
PROTECTED_STATUS = ("已投递", "待沟通内推", "已面试", "已offer")

RE_CORE_RD = re.compile(
    r"算法|研究员|深度学习|机器学习|大模型|LLM|SLAM|具身智能|自动驾驶|智能驾驶|感知"
    r"|芯片|IC|数字前端|模拟|射频|编译器|内核|驱动开发|视觉|多模态|预训练|强化学习"
    r"|自然语言|语音|AIGC|扩散|运控|电机控制|运动控制|导航|定位|仿真"
)
RE_SOFTWARE = re.compile(
    r"开发工程师|软件工程师|全栈|后端|前端|Java|C\+\+|嵌入式软件|固件|测试开发"
    r"|软件开发|研发工程师|软件研发|嵌入式开发"
)
SLIM_COMPANIES = [
    "国电南瑞", "中电莱斯", "交通银行", "华泰证券", "中移软件", "天翼云", "招银网络",
    "Momenta", "MiniMax", "地平线", "智元机器人", "宇树科技", "追觅", "石头科技",
    "科大讯飞", "秘塔", "第四范式", "网易有道", "博世", "施耐德", "基恩士",
]
# 目标岗位信号：命中则即使公司/标题带研发关键词也不删
RE_TARGET = re.compile(
    r"技术支持|FAE|现场应用|运维|实施|交付|技术服|服务工程|SRE|DevOps|系统管理"
)


def classify(title: str, company: str):
    if RE_CORE_RD.search(title) and not RE_TARGET.search(title):
        return "A"
    if any(k in company for k in SLIM_COMPANIES) and not RE_TARGET.search(title):
        return "C"
    if RE_SOFTWARE.search(title) and not RE_TARGET.search(title):
        return "B"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--buckets", default="A,B,C")
    ap.add_argument("--soft", action="store_true", help="软删除：status 改为 已归档，可恢复")
    args = ap.parse_args()
    want = set(x.strip().upper() for x in args.buckets.split(",") if x.strip())

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "select id,company_name,job_title,city,match_level,salary_text,status from jobs")]

    hit, protected = collections.defaultdict(list), []
    for r in rows:
        b = classify(r["job_title"], r["company_name"])
        if not b:
            continue
        if r["status"] in PROTECTED_STATUS:
            protected.append((b, r))
        else:
            hit[b].append(r)

    print(f"库内岗位总数: {len(rows)}")
    for b in ("A", "B", "C"):
        print(f"  桶 {b}: 命中 {len(hit[b]) + len([p for p in protected if p[0] == b])}"
              f"，其中受保护(不删) {len([p for p in protected if p[0] == b])}"
              f"，可删除 {len(hit[b])}")
    print(f"保留: {len(rows) - sum(len(v) for v in hit.values()) - len(protected)}")
    if protected:
        print("\n受保护、不删除：")
        for b, r in protected:
            print(f"  [{b}] {r['id']}|{r['company_name']}|{r['job_title'][:36]}|{r['status']}")

    if args.dry_run:
        for b in ("A", "B", "C"):
            print(f"\n--- 桶 {b} 明细 ({len(hit[b])}) ---")
            for r in hit[b]:
                print(f"  {r['id']}|{r['company_name'][:24]}|{r['job_title'][:44]}|{r['match_level']}")
        print("\n干跑结束，未修改数据库。")
        return

    if not args.apply:
        print("未指定 --apply，退出。")
        return

    ids = [r["id"] for b in want for r in hit[b]]
    if not ids:
        print("没有可删除的记录。")
        return
    cur = con.cursor()
    if args.soft:
        cur.executemany("update jobs set status='已归档(已剔除)' where id=?",
                        [(i,) for i in ids])
        print(f"已软删除（标记 已归档）：{cur.rowcount} 条")
    else:
        cur.executemany("delete from jobs where id=?", [(i,) for i in ids])
        print(f"已硬删除：{cur.rowcount} 条")
    con.commit()
    print(f"剩余岗位数: {con.execute('select count(*) from jobs').fetchone()[0]}")


if __name__ == "__main__":
    sys.exit(main())
