#!/usr/bin/env python3
"""
企业综合评估排名系统 v3
新增维度：入职难度、企业氛围、培养方案、招聘比率
基于已有工商数据的合理推断（带标注）
"""

import csv
import re
from datetime import datetime
from collections import Counter

INPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_expanded.csv'
OUTPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_ranked_v3.csv'
OUTPUT_TOP = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_top200_v3.csv'

# ========== 补贴权重 ==========
CITY_SUBSIDY = {
    '常州': 100, '无锡': 70, '苏州': 50, '南京': 40,
    '杭州': 20, '宁波': 15, '上海': 15, '北京': 15, '天津': 15,
    '深圳': 15, '广州': 15, '武汉': 10, '成都': 10, '合肥': 10,
    '嘉兴': 8, '南通': 8, '徐州': 8, '青岛': 8, '济南': 8,
    '西安': 5, '重庆': 5, '郑州': 5, '石家庄': 5, '长沙': 5,
    '沈阳': 3, '福州': 3, '南昌': 3, '太原': 3,
}
PROVINCE_SUBSIDY = {
    '江苏': 50, '浙江': 15, '广东': 15, '上海': 15, '北京': 15,
    '天津': 15, '湖北': 10, '四川': 10, '安徽': 10, '山东': 8,
    '陕西': 5, '重庆': 5, '河南': 5, '河北': 5, '湖南': 5,
    '辽宁': 3, '福建': 3, '江西': 3, '山西': 3,
}

# ========== 城市权重 ==========
CITY_WEIGHT = {
    '江苏': 100, '上海': 95, '北京': 90, '浙江': 85, '广东': 80,
    '天津': 70, '湖北': 50, '四川': 45, '安徽': 40, '山东': 35,
    '陕西': 20, '重庆': 20, '河南': 15, '河北': 15, '湖南': 15,
    '辽宁': 10, '福建': 10, '江西': 10, '山西': 5,
}

# ========== 行业关键词 ==========
# AI 相关（最高权重）
AI_MATCH = ['人工智能', 'AI', '智能', '大模型', '深度学习', '机器学习', '神经网络',
            '算法', 'NLP', '计算机视觉', '自动驾驶', '机器人']
# 计算机/软件核心（高权重）
COMPUTER_MATCH = ['物联网', '云计算', '软件', '信息', '科技', '系统', '数据', '网络',
                  '嵌入式', '传感', '运维', 'DevOps', '互联网', '开发', '程序员',
                  '编程', '代码', '网络安全', '数据库', '前端', '后端', '全栈']
# 电子/通信/自动化（中等权重）
MEDIUM_MATCH = ['电子', '通信', '自动化', '计算机', '数字', '集成', '平台', '技术', '工程',
                '制造', '工业', '硬件', '应用']
# 排除项（负权重）
LOW_MATCH = ['贸易', '餐饮', '建筑', '房地产', '投资', '咨询', '文化', '传媒',
             '广告', '物流', '运输', '农业', '医药', '生物']
HIGH_MATCH = ['物联网', '云计算', '智能', 'AI', '人工智能', '软件', '信息', '科技', '系统',
              '数据', '网络', '嵌入式', '传感', '运维', 'DevOps', '互联网']
MEDIUM_MATCH = ['电子', '通信', '自动化', '计算机', '数字', '集成', '平台', '技术', '工程',
                '制造', '工业', '硬件', '开发', '应用']
LOW_MATCH = ['贸易', '餐饮', '建筑', '房地产', '投资', '咨询', '文化', '传媒',
             '广告', '物流', '运输', '农业', '医药', '生物']

# ========== 入职难度推断关键词 ==========
BIG_NAME = ['腾讯', '阿里', '百度', '字节', '华为', '小米', '京东', '美团', '滴滴',
            '网易', '快手', '哔哩哔哩', 'B站', '携程', '拼多多', 'OPPO', 'vivo',
            '中移', '中国移动', '中国联通', '中国电信', '国家电网',
            '微软', '谷歌', '亚马逊', '苹果', 'IBM', '英特尔', '英伟达',
            '商汤', '旷视', '云从', '依图', '寒武纪', '科大讯飞',
            '深兰', '思必驰', '科沃斯', '追觅', 'Momenta']

# ========== 企业类型推断 ==========
def infer_company_type(name, capital):
    """
    从名字推断企业类型和氛围
    返回: (type_label, 氛围分, 培养方案分)
    """
    name = str(name)
    capital = parse_capital(capital)
    
    # 1. 大厂/名企
    for bn in BIG_NAME:
        if bn in name:
            return '大厂/名企', 20, 25
    
    # 2. 央企/国企
    if any(kw in name for kw in ['中移', '中国', '国家', '电信', '联通', '电网', '中铁', '中交', '中航', '中核']):
        return '央企/国企', 15, 20
    
    # 3. 上市公司（从名字推断）
    if any(kw in name for kw in ['股份', '集团', '控股']):
        if capital >= 5000:
            return '上市公司/大集团', 18, 22
        else:
            return '中小集团', 12, 15
    
    # 4. 研究院/高校背景
    if any(kw in name for kw in ['研究院', '研究所', '实验室', '大学', '学院']):
        return '科研院所', 14, 18
    
    # 5. 外企/合资公司
    if any(kw in name for kw in ['（', '(', '西门子', '霍尼韦尔', '施耐德', 'ABB', '博世', '飞利浦']):
        return '外企/合资', 16, 20
    
    # 6. 普通科技公司
    if capital >= 5000:
        return '大型民企', 14, 16
    elif capital >= 1000:
        return '中型民企', 10, 12
    elif capital >= 100:
        return '小型民企', 6, 8
    else:
        return '微型/初创', 3, 4

def infer_difficulty(name, capital, year):
    """
    推断入职难度 (0-30)
    越高 = 越难进
    """
    name = str(name)
    capital = parse_capital(capital)
    now = datetime.now().year
    age = now - year
    score = 0
    
    # 大厂 = 极难
    for bn in BIG_NAME:
        if bn in name:
            return 28
    
    # 央企/国企 = 较难
    if any(kw in name for kw in ['中移', '中国', '国家', '电信', '联通', '电网']):
        score += 22
    
    # 上市公司/大集团 = 中等偏难
    if '股份' in name or '集团' in name:
        score += 18
    elif capital >= 10000:
        score += 16
    elif capital >= 5000:
        score += 14
    elif capital >= 1000:
        score += 10
    elif capital >= 500:
        score += 7
    else:
        score += 4
    
    # 成立时间越短（初创）= 越容易进（招人多）
    if age < 3:
        score -= 5
    elif age > 20:
        score += 2  # 老牌企业可能更稳定但要求更高
    
    return min(max(score, 2), 28)

def infer_recruit_ratio(name, capital, year):
    """
    推断招聘比率/缺人程度 (0-25)
    越高 = 越缺人 = 越好进
    这个维度纯属推断，基于企业规模和发展阶段
    """
    name = str(name)
    capital = parse_capital(capital)
    now = datetime.now().year
    age = now - year
    score = 10  # 基准分
    
    # 大厂 = 竞争激烈 = 难进 = 招聘比率低
    for bn in BIG_NAME:
        if bn in name:
            return 5
    
    # 快速成长期公司 = 大量招人
    if 3 <= age <= 8:
        score += 8
    
    # 中型公司（1000-5000万）= 扩张期
    if 1000 <= capital < 5000:
        score += 5
    
    # AI/计算机 热门赛道 = 缺人
    if any(kw in name for kw in AI_MATCH + COMPUTER_MATCH):
        score += 5
    if any(kw in name for kw in ['物联网', '人工智能', '智能', '云计算', 'AI']):
        score += 3
    
    # 名字带"科技""信息" = 技术驱动型 = 持续招技术
    if '科技' in name or '信息' in name:
        score += 2
    
    # 初创公司（<3年）= 人少但要求全能 = 招得少但可能愿意培养
    if age < 3:
        score -= 3
    
    return min(max(score, 3), 23)

def parse_capital(capital_str):
    if not capital_str:
        return 0
    s = str(capital_str).strip()
    nums = re.findall(r'[\d.]+', s)
    if not nums:
        return 0
    num = float(nums[0])
    if '亿' in s:
        return num * 10000
    elif '万' in s:
        return num
    return num

def parse_establish_time(time_str):
    if not time_str:
        return 2000
    s = str(time_str).strip()
    m = re.search(r'(\d{4})', s)
    if m:
        return int(m.group(1))
    return 2000

def industry_score(name):
    """
    行业匹配度打分
    AI 相关最高权重，计算机核心次之
    """
    name = str(name)
    score = 0
    
    # AI 相关关键词（最高权重 +25/词）
    for kw in AI_MATCH:
        if kw in name:
            score += 25
    
    # 计算机/软件核心关键词（高权重 +18/词）
    for kw in COMPUTER_MATCH:
        if kw in name:
            score += 18
    
    # 电子/通信/自动化（中等权重 +8/词）
    for kw in MEDIUM_MATCH:
        if kw in name:
            score += 8
    
    # 排除项（负权重 -20/词）
    for kw in LOW_MATCH:
        if kw in name:
            score -= 20
    
    return min(score, 100)  # 封顶提升到 100
    name = str(name)
    score = 0
    for kw in HIGH_MATCH:
        if kw in name:
            score += 15
    for kw in MEDIUM_MATCH:
        if kw in name:
            score += 8
    for kw in LOW_MATCH:
        if kw in name:
            score -= 20
    return min(score, 50)

def capital_score(capital):
    if capital >= 10000: return 30
    elif capital >= 5000: return 25
    elif capital >= 1000: return 20
    elif capital >= 500: return 15
    elif capital >= 100: return 10
    elif capital >= 10: return 5
    return 0

def age_score(year):
    now = datetime.now().year
    age = now - year
    if 5 <= age <= 20: return 15
    elif 3 <= age < 5: return 10
    elif 20 < age <= 30: return 10
    elif age < 3: return 5
    elif age > 30: return 5
    return 0

def get_subsidy_weight(name, base):
    for city, w in CITY_SUBSIDY.items():
        if city in name:
            return w
    for prov, w in PROVINCE_SUBSIDY.items():
        if prov in base:
            return w
    return 3

def main():
    print("=" * 70)
    print("企业综合评估排名系统 v3")
    print("维度：城市 + 补贴 + 行业 + 公司质量 + 入职难度 + 企业氛围 + 培养方案 + 招聘比率")
    print("⚠️  后4个维度基于工商数据的推断，仅供参考")
    print("=" * 70)
    
    companies = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '')
            base = row.get('base', '').strip()
            capital = parse_capital(row.get('regCapital', ''))
            year = parse_establish_time(row.get('estiblishTime', ''))
            
            # === 基础维度 ===
            city_w = CITY_WEIGHT.get(base, 5)
            sub_w = get_subsidy_weight(name, base)
            ind_score = industry_score(name)
            cap_score = capital_score(capital)
            age_s = age_score(year)
            
            status = row.get('regStatus', '').strip()
            status_s = 5 if status == '在业' else (3 if status == '存续' else 0)
            
            # === 新增推断维度 ===
            comp_type, atmosphere_s, training_s = infer_company_type(name, row.get('regCapital', ''))
            difficulty_s = infer_difficulty(name, capital, year)
            recruit_s = infer_recruit_ratio(name, capital, year)
            
            # === 总分计算 ===
            # 策略：补贴和公司质量各占30%，入职难度反向（越低越好），其他补充
            # 入职难度分越低越好进，所以用 (30 - difficulty) 作为正向分
            # 招聘比率越高越好
            
            base_score = city_w + int(sub_w * 0.7) + ind_score + cap_score + age_s + status_s
            
            # 入职友好度 = 容易进的权重 (30 - difficulty) + 招聘比率
            # 难度分范围 2-28，所以 (30 - difficulty) 范围 2-28
            entry_friendliness = (30 - difficulty_s) + recruit_s
            
            # 成长环境 = 氛围 + 培养方案
            growth_env = atmosphere_s + training_s
            
            total = base_score + entry_friendliness * 0.8 + growth_env * 0.5
            
            row['total_score'] = round(total)
            row['base_score'] = base_score
            row['score_city'] = city_w
            row['score_subsidy'] = sub_w
            row['score_industry'] = ind_score
            row['score_capital'] = cap_score
            row['score_age'] = age_s
            row['score_status'] = status_s
            row['entry_friendliness'] = entry_friendliness  # 入职友好度
            row['difficulty'] = difficulty_s  # 入职难度（越高越难）
            row['recruit_ratio'] = recruit_s  # 招聘比率（越高越缺人）
            row['atmosphere'] = atmosphere_s  # 氛围分
            row['training'] = training_s  # 培养方案分
            row['company_type'] = comp_type  # 推断的企业类型
            row['growth_env'] = growth_env  # 成长环境总分
            
            companies.append(row)
    
    companies.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\n总公司数: {len(companies)}")
    
    print(f"\n🏆 Top 30 综合排名（含入职难度/氛围/培养推断）:")
    print(f"{'排名':>4} | {'公司名':<40} | {'类型':<12} | {'总分':>4} | {'基':>3} | {'友':>3} | {'长':>3} | {'难':>3} | {'招':>3}")
    print("-" * 100)
    for i, c in enumerate(companies[:30], 1):
        print(f"{i:4d} | {c['name'][:38]:<40} | {c['company_type']:<12} | {c['total_score']:4} | {c['base_score']:3} | {c['entry_friendliness']:3} | {c['growth_env']:3} | {c['difficulty']:3} | {c['recruit_ratio']:3}")
    
    # Top 200 统计
    top200 = companies[:200]
    print(f"\n📊 Top 200 企业类型分布:")
    types = [c['company_type'] for c in top200]
    for t, cnt in Counter(types).most_common():
        print(f"  {t}: {cnt} 家")
    
    print(f"\n📊 Top 200 入职难度分布:")
    diff_ranges = [(0, 8, '容易(小厂/初创)'), (8, 14, '中等(中型民企)'), (14, 20, '较难(大厂/国企)'), (20, 30, '极难(名企/央企)')]
    for lo, hi, label in diff_ranges:
        cnt = sum(1 for c in top200 if lo <= c['difficulty'] < hi)
        print(f"  {label}: {cnt} 家")
    
    print(f"\n📊 Top 200 培养方案分布:")
    train_ranges = [(0, 10, '较弱'), (10, 16, '一般'), (16, 22, '较好'), (22, 26, '完善')]
    for lo, hi, label in train_ranges:
        cnt = sum(1 for c in top200 if lo <= c['training'] < hi)
        print(f"  {label}: {cnt} 家")
    
    fieldnames = list(companies[0].keys())
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
    print(f"\n✅ 完整排名: {OUTPUT_CSV}")
    
    with open(OUTPUT_TOP, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(top200)
    print(f"✅ Top 200: {OUTPUT_TOP}")

if __name__ == '__main__':
    main()
