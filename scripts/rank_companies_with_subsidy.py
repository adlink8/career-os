import csv
import re
from datetime import datetime
from collections import Counter

INPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_expanded.csv'
OUTPUT_CSV = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_ranked_with_subsidy.csv'
OUTPUT_TOP = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_top200_with_subsidy.csv'

# ========== 城市级补贴权重（精确到城市）==========
CITY_SUBSIDY = {
    '常州': 100,    # ~10.76万，全省最高
    '无锡': 70,     # ~5.92万
    '苏州': 50,     # ~2.92万（AI企业）
    '南京': 40,     # ~2.16万
    '杭州': 20,     # 浙江
    '宁波': 15,
    '上海': 15,     # 补贴极少但薪资高
    '北京': 15,     # 补贴极少但薪资高
    '天津': 15,     # ~0.5万
    '深圳': 15,
    '广州': 15,
    '武汉': 10,     # 湖北
    '成都': 10,     # 四川
    '合肥': 10,     # 安徽
    '嘉兴': 8,
    '南通': 8,
    '徐州': 8,
    '青岛': 8,      # 山东
    '济南': 8,
    '西安': 5,      # 陕西
    '重庆': 5,
    '郑州': 5,      # 河南
    '石家庄': 5,    # 河北
    '长沙': 5,      # 湖南
    '沈阳': 3,      # 辽宁
    '福州': 3,      # 福建
    '南昌': 3,      # 江西
    '太原': 3,      # 山西
}

# 省份级补贴权重兜底
PROVINCE_SUBSIDY = {
    '江苏': 50,     # 省内平均（苏州/无锡/南京/常州综合）
    '浙江': 15,     # 杭州20为主
    '广东': 15,     # 深圳/广州
    '上海': 15,
    '北京': 15,
    '天津': 15,
    '湖北': 10,
    '四川': 10,
    '安徽': 10,
    '山东': 8,
    '陕西': 5,
    '重庆': 5,
    '河南': 5,
    '河北': 5,
    '湖南': 5,
    '辽宁': 3,
    '福建': 3,
    '江西': 3,
    '山西': 3,
}

# 城市权重（投递优先级）
CITY_WEIGHT = {
    '江苏': 100, '上海': 95, '北京': 90, '浙江': 85, '广东': 80,
    '天津': 70, '湖北': 50, '四川': 45, '安徽': 40, '山东': 35,
    '陕西': 20, '重庆': 20, '河南': 15, '河北': 15, '湖南': 15,
    '辽宁': 10, '福建': 10, '江西': 10, '山西': 5,
}

HIGH_MATCH = ['物联网', '云计算', '智能', 'AI', '人工智能', '软件', '信息', '科技', '系统',
              '数据', '网络', '嵌入式', '传感', '运维', 'DevOps', '互联网']
MEDIUM_MATCH = ['电子', '通信', '自动化', '计算机', '数字', '集成', '平台', '技术', '工程',
                '制造', '工业', '硬件', '开发', '应用']
LOW_MATCH = ['贸易', '餐饮', '建筑', '房地产', '投资', '咨询', '文化', '传媒',
             '广告', '物流', '运输', '农业', '医药', '生物']

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
    if capital >= 10000:
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
    return 0

def age_score(year):
    now = datetime.now().year
    age = now - year
    if 5 <= age <= 20:
        return 15
    elif 3 <= age < 5:
        return 10
    elif 20 < age <= 30:
        return 10
    elif age < 3:
        return 5
    elif age > 30:
        return 5
    return 0

def get_subsidy_weight(name, base):
    """从公司名中精确匹配城市，再回退到省份"""
    # 先从公司名中匹配城市
    for city, w in CITY_SUBSIDY.items():
        if city in name:
            return w
    # 回退到省份
    for prov, w in PROVINCE_SUBSIDY.items():
        if prov in base:
            return w
    return 3  # 默认最低

def calculate_score(row):
    score = 0
    details = {}
    
    base = row.get('base', '').strip()
    name = row.get('name', '')
    
    # 1. 城市权重 (0-100)
    city_w = CITY_WEIGHT.get(base, 5)
    score += city_w
    details['city'] = city_w
    
    # 2. 补贴权重 (0-100) —— 新增维度
    sub_w = get_subsidy_weight(name, base)
    score += sub_w
    details['subsidy'] = sub_w
    
    # 3. 行业匹配 (0-50)
    ind_score = industry_score(name)
    score += ind_score
    details['industry'] = ind_score
    
    # 4. 注册资本 (0-30)
    capital = parse_capital(row.get('regCapital', ''))
    cap_score = capital_score(capital)
    score += cap_score
    details['capital'] = cap_score
    
    # 5. 成立时间 (0-15)
    year = parse_establish_time(row.get('estiblishTime', ''))
    age_s = age_score(year)
    score += age_s
    details['age'] = age_s
    
    # 6. 经营状态
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
    print("公司池权重排名系统（含补贴维度 v2）")
    print("=" * 60)
    
    companies = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            score, details = calculate_score(row)
            row['total_score'] = score
            row['score_city'] = details['city']
            row['score_subsidy'] = details['subsidy']
            row['score_industry'] = details['industry']
            row['score_capital'] = details['capital']
            row['score_age'] = details['age']
            row['score_status'] = details['status']
            companies.append(row)
    
    companies.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\n总公司数: {len(companies)}")
    print(f"\n综合分数分布:")
    ranges = [(0, 100), (100, 150), (150, 200), (200, 250), (250, 300), (300, 999)]
    for lo, hi in ranges:
        cnt = sum(1 for c in companies if lo <= c['total_score'] < hi)
        print(f"  {lo}-{hi}: {cnt} 家")
    
    print(f"\n🏆 Top 30 公司（公司质量 + 补贴收益综合排名）:")
    for i, c in enumerate(companies[:30], 1):
        sub_tag = ""
        if c['score_subsidy'] >= 70:
            sub_tag = "💰补贴王"
        elif c['score_subsidy'] >= 50:
            sub_tag = "💰高补贴"
        elif c['score_subsidy'] >= 40:
            sub_tag = "💰中高补贴"
        company_score = c['score_city'] + c['score_industry'] + c['score_capital'] + c['score_age'] + c['score_status']
        print(f"  {i:2d}. {c['name']} ({c['base']}) 总:{c['total_score']} 公司:{company_score} 补贴:{c['score_subsidy']} {sub_tag}")
    
    top200 = companies[:200]
    print(f"\n📊 Top 200 城市分布:")
    cities = [c['base'] for c in top200]
    for city, cnt in Counter(cities).most_common(10):
        print(f"  {city}: {cnt} 家")
    
    print(f"\n💰 Top 200 补贴分布:")
    sub_ranges = [(70, 101, '超高(常州/无锡)'), (40, 70, '高(苏州/南京)'), (15, 40, '中(上海/北京/浙江/广东)'), (0, 15, '低/其他')]
    for lo, hi, label in sub_ranges:
        cnt = sum(1 for c in top200 if lo <= c['score_subsidy'] < hi)
        print(f"  {label}: {cnt} 家")
    
    # 按补贴维度统计 Top 200
    print(f"\n💰 Top 200 中补贴最高的城市:")
    subsidy_cities = Counter()
    for c in top200:
        for city in CITY_SUBSIDY:
            if city in c['name']:
                subsidy_cities[city] += 1
                break
    for city, cnt in subsidy_cities.most_common(10):
        print(f"  {city}: {cnt} 家")
    
    fieldnames = list(companies[0].keys())
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
    print(f"\n✅ 完整排名已保存: {OUTPUT_CSV}")
    
    with open(OUTPUT_TOP, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(top200)
    print(f"✅ Top 200 已保存: {OUTPUT_TOP}")

if __name__ == '__main__':
    main()
