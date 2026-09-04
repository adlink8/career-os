import csv
from collections import Counter

# 读取 v3 排名数据
INPUT = r'D:/ADLINK/Myproject/career-os/data/tianyancha/company_pool_ranked_v3.csv'
OUTPUT = r'D:/ADLINK/Myproject/career-os/data/tianyancha/投递清单_top500.csv'

with open(INPUT, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    companies = list(reader)

# 按总分排序（应该已经是排好的，但保险起见）
companies.sort(key=lambda x: int(x['total_score']), reverse=True)

# 取 Top 500
top500 = companies[:500]

# 统计
print("=" * 60)
print("Top 500 重点企业投递清单")
print("=" * 60)
print(f"\n总分范围: {top500[-1]['total_score']} ~ {top500[0]['total_score']}")

print(f"\n📊 按城市分布 (Top 10):")
cities = [c['base'] for c in top500]
for city, cnt in Counter(cities).most_common(10):
    pct = cnt / 5
    print(f"  {city}: {cnt} 家 ({pct:.0f}%)")

print(f"\n🏢 企业类型分布:")
types = [c['company_type'] for c in top500]
for t, cnt in Counter(types).most_common():
    print(f"  {t}: {cnt} 家")

print(f"\n🎯 入职难度分布:")
diff_ranges = [
    (0, 8, '容易投递', '小厂/初创，好进'),
    (8, 14, '中等难度', '中型民企，主力目标'),
    (14, 20, '较难', '大厂/国企，需充分准备'),
    (20, 30, '极难', '名企/央企，内推/提前批'),
]
for lo, hi, label, desc in diff_ranges:
    cnt = sum(1 for c in top500 if lo <= int(c['difficulty']) < hi)
    print(f"  {label} ({desc}): {cnt} 家")

print(f"\n💰 补贴收益分布:")
sub_ranges = [
    (70, 101, '超高补贴', '常州/无锡，3年5-10万+'),
    (40, 70, '高补贴', '苏州/南京，3年2-5万'),
    (15, 40, '中补贴', '上海/北京/浙江/广东'),
    (0, 15, '低补贴', '其他城市'),
]
for lo, hi, label, desc in sub_ranges:
    cnt = sum(1 for c in top500 if lo <= int(c['score_subsidy']) < hi)
    print(f"  {label} ({desc}): {cnt} 家")

print(f"\n📈 培养方案分布:")
train_ranges = [(0, 10, '较弱'), (10, 16, '一般'), (16, 22, '较好'), (22, 26, '完善')]
for lo, hi, label in train_ranges:
    cnt = sum(1 for c in top500 if lo <= int(c['training']) < hi)
    print(f"  {label}: {cnt} 家")

# 保存精简版投递清单
key_fields = ['name', 'base', 'regCapital', 'estiblishTime', 'regStatus',
              'total_score', 'company_type', 'difficulty', 'recruit_ratio',
              'atmosphere', 'training', 'score_subsidy', 'score_city',
              'score_industry', 'entry_friendliness']

with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=key_fields)
    writer.writeheader()
    for c in top500:
        row = {k: c.get(k, '') for k in key_fields}
        writer.writerow(row)

print(f"\n✅ Top 500 投递清单已保存: {OUTPUT}")

# 输出 Top 20 预览
print(f"\n🏆 Top 20 预览:")
print(f"{'排名':>4} | {'公司名':<36} | {'城市':>4} | {'类型':<10} | {'总分':>4} | {'难度':>4} | {'补贴':>4} | {'培养':>4}")
print("-" * 90)
for i, c in enumerate(top500[:20], 1):
    name = c['name'][:34]
    print(f"{i:4d} | {name:<36} | {c['base']:>4} | {c['company_type']:<10} | {c['total_score']:>4} | {c['difficulty']:>4} | {c['score_subsidy']:>4} | {c['training']:>4}")
