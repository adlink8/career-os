#!/usr/bin/env python3
"""
批量天眼查公司搜索脚本 - 扩大投递目标池
按行业关键词和城市组合搜索，合并去重后输出筛选后的公司清单
"""

import json
import sys
import os
import time
import subprocess
import csv
from pathlib import Path
from collections import defaultdict

# 配置
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "tianyancha"
OUTPUT_CSV = OUTPUT_DIR / "company_pool_expanded.csv"
SUMMARY_CSV = OUTPUT_DIR / "company_pool_by_city.csv"

# 搜索关键词矩阵
KEYWORDS = [
    # IoT / 嵌入式
    "物联网", "嵌入式", "智能硬件", "传感器",
    # 云计算 / 运维
    "云计算", "云服务", "数据中心", "运维", "IT服务",
    # AI / 智能
    "人工智能", "智能科技", "智能制造", "AI应用",
    # 工业互联网
    "工业互联网", "工业软件", "工业自动化",
    # 软件开发 / 系统集成
    "软件开发", "系统集成", "信息技术", "SaaS",
    # DevOps / 技术支持
    "DevOps", "技术支持", "网络工程",
]

# 目标城市（重点城市优先）
CITIES = [
    "上海", "苏州", "无锡", "南京", "常州", "杭州",
    "北京", "深圳", "广州", "天津", "成都", "武汉",
    "合肥", "宁波", "嘉兴", "南通", "徐州",
]

# 要跳过的省份/地区（偏远、不匹配）
SKIP_PROVINCES = {"新疆", "西藏", "青海", "宁夏", "甘肃", "海南", "云南", "贵州", "广西"}

# 天眼查工具路径（支持环境变量配置）
PLUGIN_DIR = Path(os.environ.get("TIANYANCHA_PLUGIN_DIR", Path.home() / ".career-os" / "plugins" / "tianyancha"))
TOOL = PLUGIN_DIR / "scripts" / "tianyancha_tool.py"

def call_tianyancha_search(keyword: str, file_path: str, page_num: int = 1):
    """调用天眼查公司搜索API"""
    params = {
        "search_keyword": keyword,
        "file_path": file_path,
        "page_size": 20,
        "page_num": page_num,
    }
    params_json = json.dumps(params, ensure_ascii=False)
    cmd = [
        sys.executable, str(TOOL), "call",
        "--api-name", "tianyancha_company_search",
        "--params-json", params_json,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def read_csv_companies(filepath: str):
    """读取CSV中的公司列表"""
    companies = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append(row)
    except Exception as e:
        print(f"  读取CSV失败: {e}")
    return companies

def is_valid_company(row: dict) -> bool:
    """筛选有效公司"""
    # 状态检查
    status = row.get("regStatus", "").strip()
    if status not in ("存续", "在业"):
        return False
    
    # 省份检查
    base = row.get("base", "").strip()
    if any(p in base for p in SKIP_PROVINCES):
        return False
    
    # 注册资本检查（排除过小公司）
    capital = row.get("regCapital", "").strip()
    try:
        # 提取数字部分
        num_str = ''.join(c for c in capital if c.isdigit() or c == '.')
        if num_str:
            num = float(num_str)
            # 排除注册资本<10万的公司（可能是壳公司）
            if "万" in capital and num < 10:
                return False
    except:
        pass
    
    return True

def main():
    print("=" * 60)
    print("天眼查批量公司搜索 - 扩大投递目标池")
    print("=" * 60)
    
    all_companies = {}  # name -> row (去重)
    search_stats = defaultdict(int)
    failed_searches = []
    
    total_searches = len(KEYWORDS) + len(CITIES) * 3  # 纯关键词 + 城市关键词组合
    current = 0
    
    # 第一阶段：纯关键词搜索（全国范围内）
    print(f"\n📌 第一阶段：纯关键词搜索（{len(KEYWORDS)}个关键词）")
    for kw in KEYWORDS:
        current += 1
        print(f"\n[{current}/{total_searches}] 搜索: '{kw}'")
        
        tmp_file = str(OUTPUT_DIR / f"_tmp_search_{current}.csv")
        success, stdout, stderr = call_tianyancha_search(kw, tmp_file)
        
        if not success:
            print(f"  ❌ 搜索失败: {stderr[:100]}")
            failed_searches.append((kw, "无城市", stderr[:100]))
            continue
        
        companies = read_csv_companies(tmp_file)
        print(f"  ✅ 获取 {len(companies)} 家公司")
        search_stats[kw] = len(companies)
        
        for row in companies:
            name = row.get("name", "").strip()
            if name and is_valid_company(row) and name not in all_companies:
                all_companies[name] = row
        
        # 清理临时文件
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        
        time.sleep(1)  # 避免频率限制
    
    # 第二阶段：城市+关键词组合搜索（重点城市 + 重点关键词）
    print(f"\n📌 第二阶段：城市+关键词组合搜索")
    priority_keywords = ["物联网", "云计算", "人工智能", "智能科技", "软件开发", "系统集成"]
    city_kw_combos = [(city, kw) for city in CITIES for kw in priority_keywords]
    total_searches = len(KEYWORDS) + len(city_kw_combos)
    
    for city, kw in city_kw_combos:
        current += 1
        query = f"{city} {kw}"
        print(f"\n[{current}/{total_searches}] 搜索: '{query}'")
        
        tmp_file = str(OUTPUT_DIR / f"_tmp_search_{current}.csv")
        success, stdout, stderr = call_tianyancha_search(query, tmp_file)
        
        if not success:
            print(f"  ❌ 搜索失败: {stderr[:100]}")
            failed_searches.append((city, kw, stderr[:100]))
            continue
        
        companies = read_csv_companies(tmp_file)
        print(f"  ✅ 获取 {len(companies)} 家公司")
        
        for row in companies:
            name = row.get("name", "").strip()
            if name and is_valid_company(row) and name not in all_companies:
                all_companies[name] = row
        
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        
        time.sleep(1)
    
    # 输出统计
    print("\n" + "=" * 60)
    print("📊 搜索结果统计")
    print("=" * 60)
    print(f"总搜索次数: {current}")
    print(f"失败搜索: {len(failed_searches)}")
    print(f"去重后有效公司: {len(all_companies)}")
    
    # 按城市统计
    city_counts = defaultdict(int)
    for row in all_companies.values():
        base = row.get("base", "未知").strip()
        city_counts[base] += 1
    
    print("\n按省份/城市分布（Top 15）:")
    for city, cnt in sorted(city_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {city}: {cnt} 家")
    
    # 保存完整数据
    if all_companies:
        # 主CSV
        first_row = next(iter(all_companies.values()))
        fieldnames = list(first_row.keys())
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_companies.values():
                writer.writerow(row)
        
        print(f"\n✅ 完整公司池已保存: {OUTPUT_CSV} ({len(all_companies)} 家)")
        
        # 按城市汇总CSV
        with open(SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["城市/省份", "公司数量", "示例公司"])
            for city, cnt in sorted(city_counts.items(), key=lambda x: -x[1]):
                # 找该城市的3个示例公司
                examples = [r.get("name", "") for r in all_companies.values() if r.get("base", "") == city][:3]
                writer.writerow([city, cnt, ", ".join(examples)])
        
        print(f"✅ 城市汇总已保存: {SUMMARY_CSV}")
    
    # 保存失败记录
    if failed_searches:
        fail_file = OUTPUT_DIR / "search_failed.log"
        with open(fail_file, 'w', encoding='utf-8') as f:
            for city, kw, err in failed_searches:
                f.write(f"{city} | {kw} | {err}\n")
        print(f"⚠️ 失败记录已保存: {fail_file}")

if __name__ == "__main__":
    main()
