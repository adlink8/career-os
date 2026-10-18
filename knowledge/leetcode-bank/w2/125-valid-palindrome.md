# LC125 验证回文串（简单）

> 一句话考点：把"只看字母数字、不分大小写"的串首尾往中间夹 | 模式：双指针·首尾夹

## 题面

如果在将所有大写字符转换为小写字符、并移除所有非字母数字字符之后，短语正着读和反着读都一样，则可以认为该短语是一个**回文串**。给你一个字符串 `s`，如果是回文串，返回 `true`；否则返回 `false`。

```text
示例 1：s = "A man, a plan, a canal: Panama" → true（清洗后是 "amanaplanacanalpanama"，正反读一样）
示例 2：s = "raceacar"                       → false（清洗后是 "raceacar"，反着读 racaecar 不一样）
示例 3：s = " "                              → true（清洗后是空串，空串算回文）
```

约束：`1 <= s.length <= 2 * 10^5`，`s` 仅由可打印的 ASCII 字符组成。

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
```

在 VSCode 里新建 `lc125.py` 照签名写，本地跑三个示例。

## ✋ 做题纪律

- 先口头三句：输入是啥 / 输出是啥 / 例子怎么走一遍，再说思路。
- 卡死 15 分钟才准展开下面的提示；每展开一档，错题本记一档（0-3）。
- 写完本地三个示例全过，才算做完，再看对账五问。

<details><summary>💡 提示第 1 档·方向（点开前先自己想 3 分钟）</summary>

回文的意思是"正着读反着读一样"。想象两个人分别站在这串字符的**头**和**尾**，一个往右走、一个往左走，边走边对比手里的字：只要一路上俩人手里的字总是"长得一样"，走到中间会合，就是回文。中间的标点空格、大小写的差别，你打算在哪一步把它们抹掉？
</details>

<details><summary>💡 提示第 2 档·模式点名</summary>

双指针——一个叫 left 从头出发，一个叫 right 从尾出发，相向而行。字符判断和大小写归一用 Python 的两个内建方法（判断"是不是字母数字"、转小写）。有个偷懒路线是先整体清洗再比对，先把它想通，再想怎么不清洗也能做。
</details>

<details><summary>💡 提示第 3 档·步骤点破（卡死 15 分钟才许开）</summary>

1. 先想朴素版：把每个字符转小写，只留字母数字，拼成新串，再问"新串反转后和它自己相等吗"——这就够了，能过题；
2. 进阶版（面试要的）：left 站开头、right 站结尾；
3. 循环条件：left 还没越过 right 就继续；
4. left 位置的字符不是字母数字？left 往右挪一格，跳过它，继续下一轮；
5. right 位置的字符不是字母数字？right 往左挪一格，跳过它，继续下一轮；
6. 两边都是正经字符了，转小写比一比——不相等，直接交卷 false；
7. 相等，left 右挪一格、right 左挪一格，靠拢；
8. 走到 left 和 right 相遇或交叉还没发现不等，交卷 true。注意：跳过和比较用的是同一个循环体，while 不是 for。
</details>

<details><summary>📝 三句口述参考</summary>

1. 遍历什么：两个下标 left 和 right，从两头往中间走，走的对象是"下一个合法字符"。
2. 记录什么：不用额外记录，只靠这两个下标。
3. 怎么判断/返回：两头的合法字符转小写比，不等就 return False；全走完 return True。空串和全是标点的串自然走到"相遇"也是 True，正好符合示例 3。
</details>

<details><summary>🔍 参考实现 + 逐行解析</summary>

**解法 A·清洗后比对版（先掌握这个）**

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
        cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
        return cleaned == cleaned[::-1]
```

- 第 3 行 `cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())` —— 一行干三件事：逐个字符问"你是字母数字吗"（isalnum），是就转成小写（lower），最后把挑出来的字粘成一个新串。相当于先把脏数据清洗一遍。
- 第 4 行 `return cleaned == cleaned[::-1]` —— `[::-1]` 是"整串倒过来拷贝一份"，和原串比：一样就是回文。

**解法 B·首尾双指针版（面试要的，不占额外空间）**

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
        left, right = 0, len(s) - 1
        while left < right:
            if not s[left].isalnum():
                left += 1
            elif not s[right].isalnum():
                right -= 1
            elif s[left].lower() != s[right].lower():
                return False
            else:
                left += 1
                right -= 1
        return True
```

- 第 3 行 `left, right = 0, len(s) - 1` —— 两个人就位：left 站第 0 格，right 站最后一格。右边界是 `len(s) - 1` 不是 `len(s)`——下标从 0 数起，最后一格的位置永远是长度减一，写 `len(s)` 一上来就越界。
- 第 4 行 `while left < right:` —— 两人还没碰面就继续干活。相遇即停：两人指向同一个字符时，自己跟自己比必然相等，没必要再比。写成 `<=` 也不会死循环（下一轮就交叉退出），但多走了一步没意义。
- 第 5-6 行 `if not s[left].isalnum(): left += 1` —— 左边这人手里的字符是标点或空格？不算数，往右挪一格跳过它。用 if 不是 elif 之外的结构，是"这轮只处理一件事，处理完回去重新检查"。
- 第 7-8 行 `elif not s[right].isalnum(): right -= 1` —— 同理，右边的是脏字符就往左跳过。注意这必须是 elif 不是并列 if：如果两边都是脏字符，用两个 if 会一口气各跳一格，逻辑倒也对，但三条分支串成 if/elif 链更清晰——每一轮只走其中一条。
- 第 9-10 行 `elif s[left].lower() != s[right].lower(): return False` —— 两边都是正经字符了，统一转小写再比。不等，当场交卷 false，后面的不用看了。忘了 lower 的话，`"Aa"` 会被误判成不是回文——`'A' != 'a'`。
- 第 12-13 行 `else: left += 1 / right -= 1` —— 比过了、相等，两人各往中间挪一步，继续夹。
- 第 14 行 `return True` —— 缩进和 while 平齐，在循环**外面**。走到这儿说明全程没发现不等，才有资格说"是回文"。这行写进循环里，第一个字符相等就提前交卷了，后面不等的情况全部漏判。
</details>

<details><summary>🪤 常见坑（按杀伤力排序）</summary>

1. **忘写 `.lower()`**：现象——`"A man, a plan..."` 返回 false。病因：大写 A 和小写 a 在 Python 眼里是两个不同的字。修复：比较前两头都转小写；清洗版在挑字符时就 lower。
2. **`return True` 缩进写进 while 里**：现象——`"aba"` 返回 true 但 `"abcba"` 错、或第一个对就提前交卷。病因：True 只能是"全程没发现不等"的结论，结论只能在循环走完后下。修复：缩进提到 while 外面、和 while 平齐。
3. **脏字符判断写错**：现象——空格没被跳过，`"a a"` 判成 false。病因：`isalnum()` 是"是字母数字吗"，容易顺手写成 `isalpha()`（漏掉数字）或把 not 丢了（逻辑反了，把好字符跳了、把脏字符拿来比）。修复：背牢 `isalnum() = 字母或数字`，跳过的条件是 `not` 它。
4. **right 初始值写 `len(s)`**：现象——一进循环取 `s[len(s)]` 直接 `IndexError`。病因：下标从 0 数，最后一个字符在 `len(s) - 1`。修复：`right = len(s) - 1`。
</details>

<details><summary>🎯 对账五问（做完再展开）</summary>

1. 第一个卡点通常在"清洗版想到但双指针版想不到跳脏字符"——三个 if/elif 谁先谁后、跳完回去重新查，是纯手熟活，卡住就画 `s = "a.,a"` 一格格推。
2. 最容易漏的动作：**每轮只处理一件事**——left 跳完脏字符后要回到 while 开头重新判断，不能跳完就当两边都干净了直接比。
3. 为什么对/快：清洗版要新开一块和原串一样大的内存存清洗串 O(n) 空间；双指针版原地夹，空间 O(1)。时间两者都是 O(n)——每个字符最多被两个人各看一眼。
4. 信号词："正着读反着读一样""忽略大小写和标点"→ 回文判定 → 首尾双指针。看到"回文"两个字，脑子里就该出现"一头一尾往中间夹"。
5. 变式：最多允许删掉一个字符还能是回文吗？（LC680，还是双指针，遇到不等时分别试"跳过左边"和"跳过右边"各走一遍。）只比字母不比数字？（把 isalnum 换 isalpha。）
</details>

<details><summary>🔗 迁移与同模式下一题</summary>

本题是双指针家族的"首尾夹"形态。下一题 LC344 反转字符串是同一个骨架：还是 left/right 两头出发，只是比的对象从"左右字符是否相等"换成"左右字符要互换"——夹的动作原样搬家。再往后 LC167 两数之和 II、LC977 有序数组的平方，全是这套首尾夹。
</details>
