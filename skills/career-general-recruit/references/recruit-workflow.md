# 求职管家工作流详档

> 供 `career-general-recruit` 各模块查询的具体流程、搜索策略、输出规范。

## 一、岗位搜索策略

### 关键词组合模板

按 profile.yml 的目标方向组合搜索词:

```
基础模板:
  "{岗位名} {城市} {实习/应届} 招聘 2026"

方向加强(运维):
  "运维 实习 {城市} Linux Docker 招聘"

方向加强(IoT):
  "物联网 运维 {城市} MQTT 招聘"

平台限定:
  site:zhipin.com / site:lagou.com / site:zhaopin.com
```

### 平台优先级(中文校招/实习)

| 平台 | 优势 | 搜索提示 |
|------|------|---------|
| Boss 直聘 | 实习岗位多、响应快 | 适合中小厂 |
| 拉勾 | 互联网公司全 | 适合大厂 |
| 智联/前程无忧 | 国企/传统行业 | 适合稳定岗位 |
| 牛客 | 校招/内推 | 适合应届 |
| 实习僧 | 纯实习 | 适合在校生 |

### 搜索结果过滤规则

过滤掉以下结果(不展示给用户):
- 薪资明显虚高(应届运维 > 15k 多为诈骗)
- 标题含"高薪急招""日结"(中介/诈骗信号)
- 与用户目标城市不符(除非用户明确说接受异地)

---

## 二、JD 解读输出格式(详细版)

### 5 维解读框架来源

完整框架见 `knowledge/jd-templates/jd-analysis-template.md`,本文件补充执行细节:

### 匹配度评分规则

```
硬性要求命中:
  100% 命中 → 高匹配
  70-99%    → 中匹配
  < 70%     → 低匹配(过筛难)

红旗检测:
  命中 P0 红旗 → 直接建议不投(转 career-company-check)
  命中 P1 警告 → 标注但可投
  无红旗      → 正常推进
```

### 隐性信号词翻译

(详见 `knowledge/jd-templates/ops-keywords.md` 的"隐性信号词"表)
- "抗压能力强" → 可能 996
- "弹性工作" → 加班无边界
- "创业氛围" → 流程乱 + 资源少

---

## 三、简历派生流程

### 派生文件命名

```
data/cv/cv-{role}.md

role 取值:
  ops       → 运维/技术支持版
  iot       → IoT 平台运维版
  ai        → AI Agent 运维版
  network   → 网络运维/集成版
  general   → 通用版(海投)
```

### 派生步骤

```
1. 读 templates/cv-template.md(占位符骨架)
2. 读 config/profile.yml(真实数据)
3. 按 role 调整:
   - 求职意向(role 对应岗位)
   - 技能排序(role 对应的放前面)
   - 项目排序(最对口的放第一)
4. 应用 STAR 重写(参考 knowledge/resume-templates/star-method.md)
5. ATS 关键词检查(参考 knowledge/resume-templates/ats-optimization.md)
6. 写入 data/cv/cv-{role}.md
```

### 多版本维护策略

| 版本 | 强调 | 弱化 | 适用 |
|------|------|------|------|
| ops | Linux/排障/监控 | AI 项目 | 运维岗 |
| iot | MQTT/AWS IoT/设备接入 | 大数据 | IoT 岗 |
| ai | RAG/LangChain/Agent | 网络组网 | AI 运维岗 |
| network | VLAN/抓包/组网 | AI 项目 | 网络岗 |
| general | 平衡 | - | 海投 |

---

## 四、与其它 skill 的协同

### 上游协同

- `career-self-assessment` 输出的方向推荐 → 本 skill 的搜索方向依据
- `career-company-check` 输出的背调结果 → 本 skill 的"建议投/不投"参考

### 下游协同

- 投递后 → 调用 `career-app-tracker` 写入 tracker.tsv
- 收到笔试 → 提示用户切换 `career-assessment-prep`
- 收到面试 → 提示用户切换 `career-interview-master`

### 协同话术

```
搜索完成,匹配度高的岗位已列出。
建议下一步:
A. 解读某个 JD(回复序号)
B. 查某家公司背景(说公司名,转 career-company-check)
C. 定制简历(说"改简历")
```

---

## 五、数据时效声明

- 岗位搜索结果**实时性**,每次搜索都应 WebSearch
- JD 解读结果基于用户粘贴的 JD,**一次性**
- 简历派生文件保存在 `data/cv/cv-{role}.md`,**用户自行维护更新**
- 薪资对照参考 `knowledge/salary-data/ops-salary-bands.md`,**使用前需刷新**(见 KNOW-03)
