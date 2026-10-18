# LC35 搜索插入位置（简单）

> 一句话考点：找不到不用慌，left 停在哪就是该插哪 | 模式：二分变体·找左边界

## 题面

给定一个**排序数组**（无重复元素）和一个目标值 `target`，在数组中找到目标值，并返回其索引。如果目标值不存在于数组中，返回它将会被按顺序**插入的位置**。

请必须使用**时间复杂度为 O(log n)** 的算法。

```text
示例 1：nums = [1,3,5,6], target = 5 → 输出 2（5 就在下标 2）
示例 2：nums = [1,3,5,6], target = 2 → 输出 1（2 不在，插到 3 前面即下标 1）
示例 3：nums = [1,3,5,6], target = 7 → 输出 4（比谁都大，插到末尾下标 4）
```

约束：`1 <= nums.length <= 10^4`，`-10^4 <= nums[i] <= 10^4`，nums 为**无重复元素**的**升序**排列数组，`-10^4 <= target <= 10^4`。

```python
class Solution:
    def searchInsert(self, nums: list[int], target: int) -> int:
```

在 VSCode 里新建 `lc35.py` 照签名写，本地跑三个示例。

## ✋ 做题纪律

- 先口头三句：输入是啥 / 输出是啥 / 例子怎么走一遍，再说思路。
- 卡死 15 分钟才准展开下面的提示；每展开一档，错题本记一档（0-3）。
- 写完本地三个示例全过，才算做完，再看对账五问。

<details><summary>💡 提示第 1 档·方向（点开前先自己想 3 分钟）</summary>

上一题 LC704 的二分你能默写了。这题唯一的新花样：目标不在数组里时，别交 -1，要交"它该住的位置"。问题就变成：**找第一个大于等于目标的数在哪儿**——插进它前面就万事大吉。那"找不到"时，二分循环退出的瞬间，left 和 right 各停在哪？拿 `[1,3,5,6]` 找 2，手动模拟一遍循环，把每轮 left/right/mid 的值写在纸上，看循环结束那一刻谁指着插入点。
</details>

<details><summary>💡 提示第 2 档·模式点名</summary>

还是二分查找，骨架四件套原封不动（left/right 初值、`while left <= right`、mid、±1）。改动只有两处：命中时不急着返回也可以（返回同样对），以及循环退出后返回 **left** 而不是 -1。这叫"找左边界"：答案是第一个满足"大于等于 target"的位置。
</details>

<details><summary>💡 提示第 3 档·步骤点破（卡死 15 分钟才许开）</summary>

1. left 站 0，right 站最后一格，闭区间；
2. 循环条件 left <= right，每轮取 mid；
3. mid 的数等于目标：直接返回 mid（就是它的位置）；
4. mid 的数小于目标：目标（或插入点）在右边，left = mid + 1；
5. mid 的数大于目标：插入点最多在 mid 这儿（mid 自己就是候选的"第一个大于 target 的数"），right = mid - 1，把 mid 圈在嫌疑范围里再验证；
6. 循环退出时 left 停的位置就是插入点——返回 left。为什么是 left 不是 right：退出时 left 恰好指向"第一个比 target 大的数"，right 指着它前面那个"比 target 小的数"，插入点要挤在它俩之间，插进去后新元素占的正是 left 原来的位置。
</details>

<details><summary>📝 三句口述参考</summary>

1. 遍历什么：和普通二分一样，反复看嫌疑范围正中间的数。
2. 记录什么：left/right 圈住的嫌疑范围。
3. 怎么判断/返回：mid 命中返回 mid；mid 偏小 left = mid+1，mid 偏大 right = mid-1；循环退出返回 left——它永远指向"第一个大于等于 target 的位置"。
</details>

<details><summary>🔍 参考实现 + 逐行解析</summary>

```python
class Solution:
    def searchInsert(self, nums: list[int], target: int) -> int:
        left, right = 0, len(nums)
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid
        return left
```

- 第 3 行 `left, right = 0, len(nums)` —— 注意这版用的是**另一套约定**：左闭右开区间 `[left, right)`——left 在嫌疑内、right 在嫌疑外。所以 right 初值是 `len(nums)`（数组末尾再往右一格，给"target 比谁都大、插到末尾"留位置——示例 3 的答案 4 正好是 `len(nums)`）。这套约定和 LC704 那套（闭区间 + `<=`）**不能混用**，认准一套背熟。
- 第 4 行 `while left < right:` —— 左闭右开的"范围还在"是 `left < right`：范围剩一个候选时是 `left == right - 1`，还能查；`left == right` 时范围已经空了。用 `<=` 会死循环（见坑 2）。
- 第 5 行 `mid = (left + right) // 2` —— 正中间，向下取整，同前。
- 第 6-7 行 `if nums[mid] < target: left = mid + 1` —— mid 偏小，mid 及它左边全被排除（都不可能当插入点），left 跳到 mid 后一格。mid 已经比过了，必须 +1 排除，否则死循环。
- 第 8-9 行 `else: right = mid` —— mid 的数大于等于 target：mid 自己**可能就是答案**（它可能是第一个 >= target 的数），不能排除，所以 right 停在 mid——把 mid 留在嫌疑范围里继续验证。这就是本题和 LC704 最关键的一处不同：LC704 是"排 mid ±1"，这里是"答案可能就是 mid，只收 right = mid"。
- 第 10 行 `return left` —— 循环退出时 left == right，范围缩成一点，这点就是"第一个大于等于 target 的位置"：命中时早返回了（走 else 的 num==target 也会被 right=mid 收进范围），找不到时 left 正好停在该插入的空档上。**为什么返回 left 讲透**：整个收缩过程 left 的含义始终是"目前已知：答案不在我左边"——比 target 小的全被踢到左边去了；right 的含义是"答案不在我右边"。两者夹出的唯一交点就是答案。返回 -1 是错的：这题没有"找不到"，找不到的默认答案就是插入点。

**对照版·闭区间写法（和 LC704 完全同款）**

```python
class Solution:
    def searchInsert(self, nums: list[int], target: int) -> int:
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid
            elif nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return left
```

- 与 LC704 一字不差，只有最后一行从 `return -1` 换成 `return left`。闭区间版退出时：left 比 right 大 1，left 恰好指向第一个比 target 大的数——同样是插入点。两版都建议会写：主推上面那版（找边界更标准），对照版胜在"从 LC704 只改一个 return"好记。
</details>

<details><summary>🪤 常见坑（按杀伤力排序）</summary>

1. **两套约定的四件套混搭**：现象——漏查最后一个元素或越界或死循环。病因：闭区间套件（right=len-1、`<=`、±1）和左闭右开套件（right=len、`<`、`left=mid+1`+`right=mid`）混着写。修复：死记一套配齐，别自由发挥——二分的 bug 几乎全出在"改了初值没改循环条件"。
2. **左闭右开却写 `while left <= right`**：现象——`target = 7` 之类越界查询时 `nums[mid]` 直接 `IndexError`，或原地打转。病因：`left == right` 在这套约定里是"空范围"，还进循环就会拿越界的 right 当下标用。修复：左闭右开配 `<`。
3. **找不到时手滑返回 -1 或 right**：现象——示例 2、3 挂掉。病因：肌肉记忆抄了 LC704 的 -1；或以为返回 right 对称成立——闭区间版退出时 right 停在"最后一个比 target 小的数"上，不是插入点。修复：认准"第一个 >= target 的位置"这个答案定义，它对应 left。
4. **mid = (left + right) / 2**：现象——TypeError。病因：`/` 出小数。修复：`//` 整除。
</details>

<details><summary>🎯 对账五问（做完再展开）</summary>

1. 第一个卡点几乎必然在"为什么返回 left"——纯靠想是想不透的，必须拿 `[1,3,5,6]` 找 2 手推一轮：left=0,right=4,mid=2（5>2，right=2）→ left=0,right=2,mid=1（3>2，right=1）→ left=0,right=1,mid=0（1<2，left=1）→ 退出，left=1。答案 1，left 站的位置。
2. 最容易漏的动作：mid 偏大时的 **right = mid**（不 -1，因为 mid 可能就是答案）——这正是本题和 LC704 的分水岭。
3. 为什么快：暴力是线性扫描，从头看到第一个 >= target 的数停——最坏 O(n) 翻一万个格子；二分 O(log n)，每轮砍一半，一万个数 14 步见分晓（题目 O(log n) 的要求就是在逼你二分）。直觉：翻字典猜页码，错的一半整本跳过。
4. 信号词："插入位置""第一个大于等于""排序数组 + 要求 O(log n)"→ 二分找左边界。见"有序 + 查找位置"先条件反射二分，再看答案形态选"精确命中"还是"找边界"。
5. 变式：数组**有重复元素**，找 target 的第一个位置？（LC34 前半题：命中不能返回，继续 right = mid 往左压——本题骨架直接胜任。）找最后一个 <= target 的位置？（对称版：mid <= target 时 left = mid，返回 right。）
</details>

<details><summary>🔗 迁移与同模式下一题</summary>

本题把二分从"精确命中"升级到"找左边界"——退出时 left 的含义（第一个不满足"小于 target"的位置）是整个二分家族的钥匙。下一题 LC278 第一个错误的版本把左边界推向实战：序列从"数字数组"换成"版本好坏"，判断函数从数组取值换成调 API，骨架一字不改。它也是测试岗面试招牌题——"找到第一个引入 bug 的提交"和它同构。
</details>
