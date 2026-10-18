# LC28 找出字符串中第一个匹配项的下标（简单）

> 一句话考点：拿短条子在长条子上挨个起点比对 | 模式：字符串双指针·暴力枚举

## 题面

给你两个字符串 `haystack`（干草堆）和 `needle`（针），请你在 `haystack` 字符串中找出 `needle` 字符串出现的第一个位置（下标从 0 开始）。如果不存在，则返回 `-1`。当 `needle` 是空字符串时返回 0。

```text
示例 1：haystack = "sadbutsad", needle = "sad" → 0（"sad" 在下标 0 和 6 都出现，返回第一个）
示例 2：haystack = "leetcode", needle = "leeto" → -1（"leeto" 没有出现）
```

约束：`0 <= haystack.length, needle.length <= 5 * 10^4`，`haystack` 和 `needle` 仅由小写英文字符组成。

说明：当 `needle` 是空字符串时，我们应当返回什么值呢？这是一个在面试中很好的问题——本题要求空字符串时返回 0。

```python
class Solution:
    def strStr(self, haystack: str, needle: str) -> int:
```

在 VSCode 里新建 `lc28.py` 照签名写，本地跑两个示例。

## ✋ 做题纪律

- 先口头三句：输入是啥 / 输出是啥 / 例子怎么走一遍，再说思路。
- 卡死 15 分钟才准展开下面的提示；每展开一档，错题本记一档（0-3）。
- 写完本地两个示例全过，才算做完，再看对账五问。

<details><summary>💡 提示第 1 档·方向（点开前先自己想 3 分钟）</summary>

把 needle 想成一张短纸条，haystack 是一长条纸。找子串最朴素的办法：**短纸条往长条上每个位置都盖一次章**，从每个起点开始，一个字一个字地核对——全对上才算找到；任何一个起点整个条子都没对上，换下一个起点。找到的第一个起点就是答案。
</details>

<details><summary>💡 提示第 2 档·模式点名</summary>

双指针暴力枚举：外层指针管 haystack 的起点，内层指针管 needle 逐字符核对。不用任何高级字符串算法，就靠两层耐心。重点是**起点最多到哪里**要想清——比到最后留不下整个 needle 长度的位置就不用试了。
</details>

<details><summary>💡 提示第 3 档·步骤点破（卡死 15 分钟才许开）</summary>

1. 边界：needle 为空，直接交 0；
2. 记下两个长度：长条的、短条的；
3. 外层从 0 开始数起点，起点最大只能到"长条长度减去短条长度"（再往后盖不下整张短条）；
4. 每个起点处，内层从短条第一个字符开始逐个比对：长条上"起点+偏移"处的字 和 短条上"偏移"处的字，全对上就当场交这个起点；有任何一对不上，这个起点作废，break 去下一个起点；
5. 所有起点都试完没对上，交 -1。
</details>

<details><summary>📝 三句口述参考</summary>

1. 遍历什么：haystack 的每个可能的起点（下标 0 到 两串长度之差）。
2. 记录什么：不需要额外容器——每个起点处拿内层指针逐字符核对。
3. 怎么判断/返回：某起点整条 needle 全部对上 → return 起点；内层比对中任何一对不上 → break 换起点；所有起点失败 → return -1。
</details>

<details><summary>🔍 参考实现 + 逐行解析</summary>

```python
class Solution:
    def strStr(self, haystack: str, needle: str) -> int:
        m, n = len(haystack), len(needle)
        if n == 0:
            return 0
        for i in range(m - n + 1):
            for j in range(n):
                if haystack[i + j] != needle[j]:
                    break
            else:
                return i
        return -1
```

- 第 3 行 `m, n = len(haystack), len(needle)` —— 先量两根条子多长，后面边界判断全靠它，也免得循环里反复调 len。
- 第 4-5 行 `if n == 0: return 0` —— 题面钦定的边界：空针返回 0。不写的话，`range(m - 0 + 1)` 会照样跑，空 needle 内层循环直接走 else，返回 0——碰巧也对，但显式写清楚边界是好习惯，面试官会问。
- 第 6 行 `for i in range(m - n + 1):` —— 枚举起点。**范围是 `m - n + 1` 不是 `m`**：起点 i 之后必须还留得下 n 个字符，否则比对时下标越界。反过来说，写成 `range(m)`，当 i 靠近末尾时 `haystack[i + j]` 会越界报 IndexError（Python 字符串越界取字符是报错，不是返回空）。
- 第 7 行 `for j in range(n):` —— 内层指针，从短条第一个字开始逐个核。
- 第 8-9 行 `if haystack[i + j] != needle[j]: break` —— 有一对对不上，这个起点当场作废，break 去试下一个起点。不 break 硬比完也行，但白费工。
- 第 10-11 行 `else: return i` —— **for-else**：for 正常跑完（没被 break 过）才执行 else——意思是"这个起点全对上了"。这是 Python 少见的写法；不熟 for-else 的话，等价写法是内层用 `full = True` 旗标，比对失败置 False，内层结束后 `if full: return i`。
- 第 12 行 `return -1` —— 在外层 for **外面**：所有起点都失败，才交 -1。
- 工业事实：真实工程里 `haystack.find(needle)` 一行搞定。面试练的是手写比对的过程和边界意识，KMP 这类加速算法 LC 简单题不需要。
</details>

<details><summary>🪤 常见坑（按杀伤力排序）</summary>

1. **外层范围写成 `range(m)`**：现象——靠近末尾的起点越界报 IndexError。病因：没算"起点之后要留够 needle 的长度"。修复：`range(m - n + 1)`。
2. **内层比对失败后不 break、误 return**：现象——第一个字符不等就 `return -1`。病因：把"这个起点失败"当成"全局没匹配"。修复：起点失败只 break 内层，-1 要等所有起点试完。
3. **for-else 没见过**：现象——不知道 else 什么时候执行，误以为对应 if。病因：for-else 是"循环没被 break 才执行"，和 if 无关。修复：用旗标变量版等价改写，先写对再学 for-else。
4. **off-by-one：`m - n + 1` 写成 `m - n`**：现象——needle 长度等于 haystack 时返回 -1（两个相等的串都判不匹配）。病因：把"最后合法起点"算丢一个。修复：最后合法起点是 `m - n`，range 上界要 +1。
</details>

<details><summary>🎯 对账五问（做完再展开）</summary>

1. 第一个卡点通常在"外层范围怎么定"——`m - n + 1` 这个边界想不到就会越界或漏判。
2. 最容易漏的动作：内层某对失败要 break（不 break 逻辑也对但白比），以及 for-else 的语义。
3. 为什么它就是"正解"：本题最优是 O((m-n+1)·n) 的暴力在 LC 简单档完全够（KMP 是 O(m+n) 但面试简单题不要求）；对比"用切片 `haystack[i:i+n] == needle`"是同复杂度但每次比对额外造新串，手写双指针省掉这份拷贝开销。
4. 信号词："子串第一次出现""find 的手写版"→ 双指针暴力枚举；面试官追问"能更快吗"才升级 KMP。
5. 变式：找所有出现位置？（起点集合全部收集。）匹配一个带通配符的模式？（进阶递归/DP，先别碰。）
</details>

<details><summary>🔗 迁移与同模式下一题</summary>

下一题 LC88 合并两个有序数组是双指针家族的另一分支：本题是"一个起点核对、一个偏移推进"，下一题是"两个指针各管一个数组、谁小谁先走"。双指针不是一种固定写法，是一种"用两个下标协调两处位置"的思想。
</details>
