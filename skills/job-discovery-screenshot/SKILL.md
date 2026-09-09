# 岗位搜寻截图管道（模拟真人浏览 + 视觉提取）

触发场景：用户要求「广泛搜寻岗位机会」「看看 BOSS/智联/本地渠道/国聘有什么新岗位」「刷新岗位线索」时，且明确要求模拟真人浏览、截图提取而非脚本爬取。

## 管道架构（三段式）

```
scripts/job_discovery_screenshot.py   # 浏览 + 截图 + 留痕（列表页 + 详情页 JD）
        ↓ 产物
data/job_discovery/screenshots/<channel>/<日期>/
    p<页>-<关键词>.png            # 列表页（岗位卡片：名称/城市/薪资/社招校招）
    d<页>-<关键词>-<序>.png       # 详情页全页（JD全文/要求/截止日期/HR活跃时间）
data/job_discovery/manifests/*.json   # 截图清单（渠道/关键词/页码/URL/时间）
        ↓ LLM 读图提取（主 Agent 用 Read 工具读截图，人工判断取舍）
data/job_discovery/extracts/*.json    # 结构化提取载荷
        ↓
scripts/job_discovery_import.py       # 写入 platform_recruitment_leads（幂等）
        ↓
data/career_jobs.sqlite               # capture_method='screenshot_vision'
```

## 操作步骤

1. 无登录渠道（guopin/changzhou_rsj/czu_jiuye）直接跑：
   `python scripts/job_discovery_screenshot.py --channel guopin --pages 2`
2. 登录渠道（boss/zhilian）：自动弹窗扫码——脚本轮询登录态选择器（BOSS 用
   `//li[@class='nav-figure']` 头像入口，来源 get_jobs 实测），最长 180s；
   cookie 存 `data/job_discovery/browser_profiles/<channel>/`，一次扫码多日免登。
   **必须在用户在场时运行**，先告知用户准备扫码。
3. 详情页阶段默认开启（`--no-detail` 关闭，`--max-details N` 调数量）：
   BOSS/智联走 href 模式（detail_link_selector），国聘等 SPA 走点击模式
   （detail_click_selector，点击卡片等新标签弹出）。详情页全页截图含
   HR 活跃时间，**提取时 HR 7 天未活跃的岗位标记僵尸岗不优先**。
4. 用 Read 工具逐张读截图提取：公司/岗位/城市/薪资（原文）/社招校招/学历/
   JD 要点（详情页）。取舍规则：视口底部裁切的残卡不收；明显偏离方向的
   噪音岗位不收并在 notes 说明；"面议"保留原文不估值。
5. 写提取 JSON 到 `data/job_discovery/extracts/`，然后
   `python scripts/job_discovery_import.py --input <json>`。
6. 幂等保证：dedupe_key = `platform:md5(company|title|city)`，重跑只跳过不重复入库。

## 反算法搜索策略（社区实践 + get_jobs/jobclaw 源码调研，2026-09）

- **多关键词交叉轮换**（已写入渠道配置 keywords）：运维/技术支持/IT运维/桌面运维/
  系统运维轮换搜，突破算法岗位池盲区
- **HR 活跃过滤**：详情页含 `boss-active-time` 区域，7 天未活跃 = 僵尸岗，不优先
- **PC 网页端补盲**：BOSS/智联 PC 与 APP 岗位池不互通，本管道即 PC 侧
- **刷新窗口**：早 8 / 午 2 / 晚 6 岗位最新、HR 在线高峰（定时任务用这个时段）
- **首次使用 BOSS 的人工一次性设置**：关闭个性化推荐（我的→设置→隐私）、
  筛「精选公司」、屏蔽保险/直播/加盟关键词、**不秒点秒退**（脚本已带随机停留）
- **红线**：本管道只浏览不自动打招呼/不投递——自动沟通是封号红线，投递永远人工

## 关键约定

- 渠道配置在 `config/job_discovery_channels.yml`；页面结构变化时改这里的 selector，不改脚本。
- BOSS 城市码 101191101 / 智联 551 按天气码惯例填常州，**首次运行待校准**：
  页面上手动选城市后，把 URL 里真实城市码回填配置。
- 库表契约：`platform_recruitment_leads` 的 v15 列（salary_text / screenshot_path /
  capture_method / captured_at），迁移入口 `bin/career_os_store.py`。
- 提取诚实边界：残卡不猜全名、截断公司名宁缺毋滥；详情页提取补
  jd_summary/responsibilities/requirements 字段（import 脚本已支持）。
- 截图即证据：入库行必带 screenshot_path，复核时可直接回看原图。
- 已知坑：`.git/refs/heads/` 下新建分支引用曾被异常清除（本机曾出现），
  commit 对象不受影响；若 `git branch` 静默无效，用完整 40 位 sha 手写 ref 文件恢复。
