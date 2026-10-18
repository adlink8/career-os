# LC278 第一个错误的版本（简单）

> 一句话考点：版本一坏全坏，用"看好坏"代替"比大小"砍一半 | 模式：二分·找边界（测开招牌题）

## 题面

你是产品经理，目前正在带领一个团队开发新的产品。不幸的是，你的最新版本没有通过质量检测。由于每个版本都是基于之前的版本开发的，所以**错误版本之后的所有版本都是错的**。

假设你有 `n` 个版本 `[1, 2, ..., n]`，你想找出导致之后所有版本出错的**第一个错误的版本**。

你可以通过调用 `bool isBadVersion(version)` 接口来判断版本号 `version` 是否在单元测试中出错。实现一个函数查找第一个错误的版本。你应该尽量**减少对调用 API 的次数**。

```text
示例：n = 5，bad = 4（隐藏的，你不许直接看）
     调用 isBadVersion(3) → false
     调用 isBadVersion(5) → true
     调用 isBadVersion(4) → true
     那么 4 就是第一个错误的版本 → 输出 4
```

约束：`1 <= bad <= n <= 2^31 - 1`。

```python
# The isBadVersion API is already defined for you.
# def isBadVersion(version: int) -> bool:

class Solution:
    def firstBadVersion(self, n: int) -> int:
```

在 VSCode 里新建 `lc278.py` 照签名写。本地验证要自己搭一个假 API（参考实现下方给了测试桩），跑 bad=4, n=5。

## ✋ 做题纪律

- 先口头三句：输入是啥 / 输出是啥 / 例子怎么走一遍，再说思路。
- 卡死 15 分钟才准展开下面的提示；每展开一档，错题本记一档（0-3）。
- 写完本地示例全过，才算做完，再看对账五问。

<details><summary>💡 提示第 1 档·方向（点开前先自己想 3 分钟）</summary>

一万个版本里混进了一个坏版本，从它之后全是坏的。想象版本序列像一排灯：前面全亮（好）、后面全灭（坏），亮的和灭的之间有一条**分界线**。每查一个版本，你只得到一个字：好或坏。怎么用最少的查询次数把分界线逼出来？查了中间一个是坏的，分界线在它这边还是那边？
</details>

<details><summary>💡 提示第 2 档·模式点名</summary>

二分查找·找边界——和 LC35 同族：答案不是"某个值"而是"第一个满足某条件的位置"（第一个坏版本）。判断依据从"比 target 大还是小"换成"调一个返回真假黑盒"。mid 是好版本往哪边收？是坏版本又往哪边收？
</details>

<details><summary>💡 提示第 3 档·步骤点破（卡死 15 分钟才许开）</summary>

1. left 站 1（版本号从 1 数起，不是 0！），right 站 n；
2. 循环：left 还没追上 right 就继续；
3. 查 mid 这个版本的好坏（调黑盒 API）；
4. mid 是坏版本：第一个坏版本**可能是 mid 自己**，也可能是它左边——分界线最多推到 mid，把 right 收到 mid（不排除 mid！）；
5. mid 是好版本：坏版本铁定在它右边，left 收到 mid 后一格；
6. left 和 right 相遇时，两人共同站的位置就是第一个坏版本——返回 left（或 right，此刻相等）；
7. 死循环防线：收 right 用 mid、收 left 用 mid+1，保证范围每轮必缩。和 LC35"找左边界"完全同款动作。
</details>

<details><summary>📝 三句口述参考</summary>

1. 遍历什么：反复查嫌疑范围正中间的版本，用 API 问好坏。
2. 记录什么：left/right 圈住"第一个坏版本可能所在的范围"。
3. 怎么判断/返回：mid 坏 → right = mid（答案可能是它）；mid 好 → left = mid + 1（答案在右）；相遇时返回 left。
</details>

<details><summary>🔍 参考实现 + 逐行解析</summary>

```python
class Solution:
    def firstBadVersion(self, n: int) -> int:
        left, right = 1, n
        while left < right:
            mid = (left + right) // 2
            if isBadVersion(mid):
                right = mid
            else:
                left = mid + 1
        return left
```

- 第 3 行 `left, right = 1, n` —— 版本号从 **1** 开始数（题面 `[1, 2, ..., n]`），不是数组的 0！left 从 1、right 从 n，闭着圈住全部版本。照抄别的题的 `0, len-1` 是本题第一坑。
- 第 4 行 `while left < right:` —— 左闭右闭但目标区域最后缩成一点：right 会停在一个"可能是答案"的版本上，直到 left 与它重合。用 `<=` 会死循环（范围剩一点时 mid == left == right，right = mid 不动）。LC35 同款约定。
- 第 5 行 `mid = (left + right) // 2` —— 正中间，向下取整。注意约束里 n 最大 2^31-1——按别的语言的习惯这里要防加法溢出，Python 整数无限大不用管，但面试聊到要能说出 `left + (right - left) // 2` 这个防溢出写法。
- 第 6 行 `if isBadVersion(mid):` —— 调黑盒 API 问中间版本的好坏。本题的"比较"不再是数字和 target 比，而是这个真假返回值——二分的骨架不变，判断的来源变了。
- 第 7 行 `right = mid` —— **最关键的一行**。mid 是坏版本：第一个坏的可能是 mid 自己（它前面可能全好），把 mid 排除就丢答案了，所以只收 right = mid，把 mid 留在嫌疑范围里。反过来会怎样：写成 `right = mid - 1`，当 mid 恰好是第一个坏版本时，答案被踢出范围，最后返回的是它**前面那个好版本**——差一格，全错。
- 第 9 行 `left = mid + 1` —— mid 是好版本：好版本之后才有坏的，mid 连当答案的资格都没有，果断排除，left 跳过它。
- 第 10 行 `return left` —— 循环退出时 left == right，嫌疑范围缩成一点，就是第一个坏版本。返回 left 或 right 都行（相等了），习惯上写 left，和 LC35 的"返回 left"连成肌肉记忆。

**本地测试桩（LeetCode 已帮你写好 API，本地自己搭）**

```python
def isBadVersion(version: int) -> bool:
    BAD = 4  # 假装第 4 版开始坏，模拟隐藏答案
    return version >= BAD

sol = Solution()
print(sol.firstBadVersion(5))  # 期望输出 4
```

- 把测试桩放在 lc278.py 顶部即可本地跑。注意桩里是 `>=`：坏版本之后（含自己）全坏——这正是题面"错误版本之后的所有版本都是错的"的代码化。
</details>

<details><summary>🪤 常见坑（按杀伤力排序）</summary>

1. **left 从 0 起步**：现象——答案偏一，返回 3 而不是 4。病因：惯性抄 `0, len-1`。修复：版本号天然从 1 开始，初值 `1, n`。
2. **坏版本分支写 `right = mid - 1`**：现象——bad=1 或答案恰为 mid 时返回错位结果。病因：把 mid 当"已排除"处理，忘了它可能就是第一个坏版本。修复：找边界的铁律——**mid 满足条件时收 right = mid 不排除**；只有 mid 确定不满足才 mid + 1 排除。
3. **`while left <= right` 配 `right = mid`**：现象——卡死不动。病因：left==right 时 mid 也等于它俩，right = mid 永不缩小。修复：这套约定用 `left < right`，范围缩到一点自然退出。
4. **想线性扫描 `for i in range(1, n+1)`**：现象——本地对、提交**超时**（Time Limit Exceeded）。病因：n 最大约 21 亿，逐个调 API 最坏 21 亿次，判题器等不起；题目"尽量减少调用次数"就是暗语。修复：二分，最多约 31 次调用。
</details>

<details><summary>🎯 对账五问（做完再展开）</summary>

1. 第一个卡点通常在"坏版本时该往哪边收"——问自己一句：mid 是坏的，**它自己有没有可能是第一个坏的**？可能，就不能排除。想通这句，right = mid 顺理成章。
2. 最容易漏的动作：初值从 1 起步，以及坏分支不排除 mid。
3. 为什么快：线性扫描逐版本调 API 是 O(n)——21 亿个版本最坏调 21 亿次 API；二分 O(log n)——每次查询砍掉一半嫌疑，21 亿只需约 31 次调用。直觉：翻字典猜页码，坏的那半整本跳过；API 每次调用都有成本，砍一半就是在省真金白银。
4. 信号词："第一个……的位置""之后全是……""有序 + 真假判断 + 要求少查"→ 二分找边界。本题面没有"有序"两个字，但"一坏全坏"就是隐形的有序（好...好坏...坏）——识别这种**两段式序列**是进阶二分的关键。
5. 变式： LC34 排序数组找 target 的第一个和最后一个位置（本题骨架直接套，条件从 API 换回数字比较）；LC69 x 的平方根（在 1..x 里找第一个平方大于 x 的数，判断函数换成平方计算）；LC162 寻找峰值（两段式换成山峰式）。
</details>

<details><summary>🔗 迁移与同模式下一题</summary>

本题是二分找边界的实战封顶：判断函数黑盒化后骨架纹丝不动——这正是二分的可怕威力：只要序列能劈成"前段不满足、后段满足"两截，无论比数字、调 API 还是算数学，同一套代码通吃。**测试岗的隐喻**：这题就是回归测试里的 git bisect——版本回归时定位"第一个引入 bug 的提交"，engineer 们每天用的正是这道题的二分：中间提交跑一遍测试套件，坏就往左收、好就往右收，几十个提交几轮锁凶。面试官考它是想听到你说出这层同构。w2 到此收束：双指针、栈、二分三板斧齐了，w3 进链表与 DP。
</details>
