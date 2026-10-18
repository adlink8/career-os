# -*- coding: utf-8 -*-
import hashlib
import sys
from pathlib import Path

# 确保控制台支持 UTF-8 打印
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 72)
print("   🧪 现场动手实验：亲眼见证 SHA-256 与文件格式的底层秘密")
print("=" * 72)

# 1. 模拟一段真实的二进制数据（比如一张 1x1 像素 PNG 图片的原始字节）
original_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

temp_dir = Path("tmp_sha_experiment")
temp_dir.mkdir(exist_ok=True)

# 创建 4 个不同后缀名、不同形态的文件（图片、文本、PDF、可执行程序）
files = {
    "cat.png": original_bytes,
    "cat_renamed.txt": original_bytes,
    "cat_renamed.pdf": original_bytes,
    "cat_renamed.exe": original_bytes,
}

print("\n【实验 1：强行修改后缀名，SHA-256 指纹到底会不会变？】")
hashes = {}
for name, data in files.items():
    p = temp_dir / name
    p.write_bytes(data)
    
    # 算每一份文件的 SHA-256
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    hashes[name] = h
    print(f"  文件: {name:<18} -> 实际大小: {len(data)} 字节 -> SHA-256: {h}")

# 校验是否全部一致
all_same = len(set(hashes.values())) == 1
if all_same:
    print("\n  ✅ 亲眼见证事实：")
    print("     无论你把后缀名改成 .txt、.pdf 还是 .exe，算出来的 SHA-256 绝对 100% 一模一样！")
    print("     这证明了：操作系统眼里的格式只是人类标签，在 SHA-256 眼里全世界文件都是同一串 0 和 1！")

print("\n" + "-" * 72)
print("【实验 2：只改动 1 个微小的字母，亲眼见证‘雪崩效应’】")

# 原始文本 vs 只改动了 1 个字母的文本
text_a = b"Hello World."
text_b = b"hello World."  # 仅仅把大写的 H 改成了小写 h (ASCII 码二进制只差 1 个 bit!)

hash_a = hashlib.sha256(text_a).hexdigest()
hash_b = hashlib.sha256(text_b).hexdigest()

print(f"  原始内容: 'Hello World.' -> SHA-256: {hash_a}")
print(f"  修改内容: 'hello World.' -> SHA-256: {hash_b}")

# 统计 64 位字符里有多少位完全变了
different_chars = sum(1 for c1, c2 in zip(hash_a, hash_b) if c1 != c2)
print(f"\n  ⚡ 雪崩结果：")
print(f"     仅仅把 'H' 变成 'h'（只动了 1 个 bit），64 位哈希字符中有 {different_chars} 位彻底翻转面目全非！")
print("     完全看不出两个结果之间有任何血缘关系，这就是‘不可逆’与‘防篡改’的真面目！")

# 清理临时实验文件
for name in files.keys():
    (temp_dir / name).unlink(missing_ok=True)
temp_dir.rmdir()

print("\n" + "=" * 72)
print("  ✨ 实验大获成功！理论在终端里被彻底证实！")
print("=" * 72)
