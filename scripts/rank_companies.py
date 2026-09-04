import csv
import re
from datetime import datetime
from collections import Counter

# 输入输出
INPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_expanded.csv'
OUTPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_ranked.csv'
OUTPUT_TOP = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_top200.csv'

# 城市权重（目标城市 = 你的目标区域）
CITY_WEIGHT = {
    # 首选目标城市
    '江苏': 100, '上海': 95, '北京': 90, '浙江': 85, '广东': 80,
    # 次选
    '天津': 70, '湖北': 50, '四川': 45, '安徽': 40, '山东': 35,
    # 其他
    '陕西': 20, '重庆': 20, '河南': 15, '河北': 15, '湖南': 15,
    '辽宁': 10, '福建': 10, '江西': 10, '山西': 5,
}

# 行业关键词匹配（名字中含这些词 = 高匹配）
HIGH_MATCH = ['物联网', '云计算', '智能', 'AI', '人工智能', '软件', '信息', '科技', '系统',
              '数据', '网络', '嵌入式', '传感', '运维', '运维', 'DevOps', '互联网']
MEDIUM_MATCH = ['电子', '通信', '自动化', '计算机', '数字', '集成', '平台', '技术', '工程',
                '制造', '工业', '硬件', '开发', '应用']
LOW_MATCH = ['贸易', '餐饮', '建筑', '房地产', '投资', '咨询', '文化', '传媒',
             '广告', '物流', '运输', '农业', '医药', '生物']

def parse_capital(capital_str):
    """解析注册资本为万元"""
    if not capital_str:
        return 0
    s = str(capital_str).strip()
    # 提取数字
    nums = re.findall(r'[\d.]+', s)
    if not nums:
        return 0
    num = float(nums[0])
    if '亿' in s:
        return num * 10000  # 亿元转万元
    elif '万' in s:
        return num
    else:
        return num  # 默认万元

def parse_establish_time(time_str):
    """解析成立时间，返回年份"""
    if not time_str:
        return 2000
    s = str(time_str).strip()
    m = re.search(r'(\d{4})', s)
    if m:
        return int(m.group(1))
    return 2000

def industry_score(name):
    """行业匹配度打分"""
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
    return min(score, 50)  # 封顶50

def capital_score(capital):
    """注册资本打分（万元）"""
    if capital >= 10000:  # 1亿以上
        return 30
    elif capital >= 5000:
        return 25
    elif capital >= 1000:
        return 20
    elif capital >= 500:
        return 15
    elif capital >= 100:
        return 10
    elif capital >= 10:
        return 5
    else:
        return 0

def age_score(year):
    """成立时间打分"""
    now = datetime.now().year
    age = now - year
    if 5 <= age <= 20:  # 5-20年 = 最佳
        return 15
    elif 3 <= age < 5:
        return 10
    elif 20 < age <= 30:
        return 10
    elif age < 3:
        return 5  # 太新，有风险
    elif age > 30:
        return 5  # 太老，可能转型
    return 0

def calculate_score(row):
    """计算综合权重分"""
    score = 0
    details = {}
    
    # 1. 城市权重 (0-100)
    base = row.get('base', '').strip()
    city_w = CITY_WEIGHT.get(base, 5)
    score += city_w
    details['city'] = city_w
    
    # 2. 行业匹配 (0-50)
    name = row.get('name', '')
    ind_score = industry_score(name)
    score += ind_score
    details['industry'] = ind_score
    
    # 3. 注册资本 (0-30)
    capital = parse_capital(row.get('regCapital', ''))
    cap_score = capital_score(capital)
    score += cap_score
    details['capital'] = cap_score
    
    # 4. 成立时间 (0-15)
    year = parse_establish_time(row.get('estiblishTime', ''))
    age_s = age_score(year)
    score += age_s
    details['age'] = age_s
    
    # 5. 经营状态加成
    status = row.get('regStatus', '').strip()
    if status == '在业':
        score += 5
        details['status'] = 5
    elif status == '存续':
        score += 3
        details['status'] = 3
    else:
        details['status'] = 0
    
    return score, details

def main():
    print("=" * 60)
    print("公司池权重排名系统")
    print("=" * 60)
    
    # 读取数据
    companies = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            score, details = calculate_score(row)
            row['weight_score'] = score
            row['score_city'] = details['city']
            row['score_industry'] = details['industry']
            row['score_capital'] = details['capital']
            row['score_age'] = details['age']
            row['score_status'] = details['status']
            companies.append(row)
    
    # 排序
    companies.sort(key=lambda x: x['weight_score'], reverse=True)
    
    # 统计
    print(f"\n总公司数: {len(companies)}")
    print(f"\n分数分布:")
    score_ranges = [(0, 50), (50, 80), (80, 100), (100, 120), (120, 150), (150, 200), (200, 999)]
    for lo, hi in score_ranges:
        cnt = sum(1 for c in companies if lo <= c['weight_score'] < hi)
        print(f"  {lo}-{hi}: {cnt} 家")
    
    # 按城市统计 Top 公司
    print(f"\nTop 20 公司:")
    for i, c in enumerate(companies[:20], 1):
        print(f"  {i}. {c['name']} ({c['base']}) 注册资本:{c['regCapital']} 得分:{c['weight_score']}")
    
    # 保存完整排名
    fieldnames = list(companies[0].keys())
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
    print(f"\n✅ 完整排名已保存: {OUTPUT_CSV}")
    
    # 保存 Top 200
    top200 = companies[:200]
    with open(OUTPUT_TOP, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(top200)
    print(f"✅ Top 200 已保存: {OUTPUT_TOP}")
    
    # 生成城市分布报告
    print(f"\nTop 200 城市分布:")
    cities = [c['base'] for c in top200]
    for city, cnt in Counter(cities).most_common(10):
        print(f"  {city}: {cnt} 家")

if __name__ == '__main__':
    main()
