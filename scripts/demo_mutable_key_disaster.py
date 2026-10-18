"""
演示：如果一个对象的哈希值和内容中途变了，会发生什么人间惨剧？
"""
import sys

# 保证 Windows 终端打印中文不爆编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class BuggyKey:
    """一个故意写成可变哈希的危险类"""
    def __init__(self, tag: str):
        self.tag = tag

    def __hash__(self):
        # 拿自身的 tag 去算哈希
        return hash(self.tag)

    def __eq__(self, other):
        return isinstance(other, BuggyKey) and self.tag == other.tag

    def __repr__(self):
        return f"BuggyKey('{self.tag}')"


def simulate_real_dict():
    print("=" * 60)
    print("【实验 1：Python 真实 dict 里的幽灵失踪事件】")
    print("=" * 60)

    # 1. 制造一个钥匙
    key = BuggyKey("版本_v1")
    my_dict = {}

    # 2. 存入绝密数据
    my_dict[key] = "这是价值100万的绝密商业机密"
    print(f"1. 成功存入数据：key={key}，当前哈希值={hash(key)}")
    print(f"   此时能取出来吗？ -> {my_dict[key]}")

    # 3. 事故发生：钥匙在半路上被人悄悄修改了！
    print("\n--- 此时，业务代码悄悄改了 key.tag = '版本_v2' ---")
    key.tag = "版本_v2"
    print(f"2. 钥匙被篡改后：key={key}，新的哈希值={hash(key)}")

    # 4. 尝试取回数据
    print("\n3. 拿着变质后的 key 去字典里取数据：my_dict[key] ...")
    try:
        data = my_dict[key]
        print(f"成功取出: {data}")
    except KeyError as e:
        print(f"[X] 翻车！Python 抛出 KeyError: {e}")
        print("   字典告诉你：根本没有这个 key！")

    # 5. 真相调查：数据真的没了吗？
    print("\n4. 警察去字典内务府抄家，看看数据到底还在不在：")
    print(f"   字典长度 len(my_dict) = {len(my_dict)}")
    print(f"   字典实际内容 items()   = {list(my_dict.items())}")
    print("[!] 结论：数据还在！但再也没有任何人能用正常语法拿到它，它成了内存里的死幽灵！")


def simulate_8_drawers():
    print("\n" + "=" * 60)
    print("【实验 2：手动模拟 8 个抽屉的坐标错位过程】")
    print("=" * 60)

    drawers = [None] * 8  # 0 到 7 号抽屉
    
    # 假设有个 key，算出来模 8 是某个抽屉
    secret_key = "token_A"
    drawer_id_1 = abs(hash(secret_key)) % 8
    secret_value = "数据库Root密码123456"
    
    # 存入抽屉
    drawers[drawer_id_1] = {"key": secret_key, "val": secret_value}
    print(f"1. 原始 Key='{secret_key}' -> 取模计算坐标：{drawer_id_1} 号抽屉")
    print(f"   放进 {drawer_id_1} 号抽屉！当前所有抽屉状态：")
    for i, slot in enumerate(drawers):
        print(f"     [{i}号抽屉]: {slot}")

    # Key 被改成 token_B
    secret_key_tampered = "token_B"
    drawer_id_2 = abs(hash(secret_key_tampered)) % 8
    print(f"\n2. Key 被改成 '{secret_key_tampered}' -> 重新计算坐标：{drawer_id_2} 号抽屉")

    # 去取东西
    print(f"3. 按照新算出的坐标，伸手去拉开 [{drawer_id_2}号抽屉]：")
    target = drawers[drawer_id_2]
    if target is None:
        print(f"   [X] 打开一看，[{drawer_id_2}号抽屉] 里面空空如也！")
    else:
        print(f"   拿到内容：{target}")

    print(f"\n4. 但原本的秘密依然孤零零躺在 [{drawer_id_1}号抽屉] 里发霉！")


if __name__ == "__main__":
    simulate_real_dict()
    simulate_8_drawers()
