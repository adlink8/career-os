# Career OS — ATS 网申自动填表助手 (Browser Extension)

专为解决**北森（Beisen / zhiye.com / italent.cn）**、Moka、用友、大易等校招网申系统重复繁琐填表问题而开发。

数据源 100% 取自当前项目的 `config/profile.yml`，**本地运行、纯开源、零隐私泄露风险**。

---

## 🚀 极速安装指南（2分钟）

本插件采用标准的 Chrome Extension Manifest V3 规范，兼容 **Microsoft Edge** 和 **Google Chrome**：

1. 打开浏览器扩展管理页面：
   - **Edge**：在地址栏输入 `edge://extensions/`
   - **Chrome**：在地址栏输入 `chrome://extensions/`
2. 打开页面右上角（或左下角）的 **【开发者模式（Developer Mode）】** 开关；
3. 点击 **【加载已解压的扩展程序（Load unpacked）】** 按钮；
4. 在弹出的文件选择器中，选择本项目下的目录：
   ```text
   d:\ADLINK\Myproject\career-os\extensions\ats-autofill
   ```
5. 安装完成！此时浏览器的扩展栏里会出现 `⚡ Career OS 填表` 插件。

---

---

## 🎯 核心架构：通用稳定层 + 岗位 JD 简历绑定层

为了避免每次面对不同岗位时混乱修改基础信息，插件采用了**两层数据绑定架构**：

1. **【通用稳定层】（永不变动）**：
   - 姓名（李硕研）、电话（13091066808）、邮箱（2448366060@qq.com）、常州大学、计算机科学与技术、专升本、大专（江苏信息职院）、个人爱好与特长、获奖荣誉、职业证书、到岗时间等。
   - 这部分数据在所有网申中完全通用固定。

2. **【岗位 JD / 简历轨道动态层】（按投递岗位深度绑定）**：
   - 包含 4 个专属轨道，直接对齐 `data/cv/` 下经过多轮打磨的真实简历：
     - 🎯 **DevOps / Linux 运维**：重点绑定【NovelMind 线上 OOM 治理与 CI 门禁】+【pk-core 解耦】，自我评价侧重 Linux 自动化、容器与稳定性；
     - 🔌 **IoT / 智能硬件与嵌入式技术支持**：重点绑定【T5AI 监控终端与双通道防雪崩】+【小智 ESP32-S3 交互控制】，自我评价侧重 C/C++、固件烧录与串口抓包；
     - 🤖 **AI Agent / 研发效能与数据工程**：重点绑定【NovelMind RAG 平台】+【Personal Data 个人知识库】，自我评价侧重 Python、FastAPI、ChromaDB 与 MCP；
     - 💼 **技术支持工程师 (FAE / IT Support)**：重点绑定【物联网大赛现场排障】+【T5AI 联调交付】，自我评价侧重现场沟通、工单与客户支持。

---

## 💡 如何在北森等页面使用？

当你打开任何一家企业的招聘页面时：

1. **智能识别岗位**：
   - 插件会自动扫描网页标题和职位名称（包含“运维/DevOps”、“硬件/嵌入式”、“AI/Agent”、“技术支持/FAE”等关键词），**自动无感切换到对应简历版本**！
2. **手动一键切换**：
   - 右下角悬浮面板和右上角插件弹窗均带有 **【当前岗位 JD / 简历轨道】** 下拉框，轻点一下即可随时切换；
   - 切换后，自我评价、技能清单、重点项目描述和快捷复制面板**瞬间同步变换为该岗位的专用表述**！
3. **一键填表**：
   - 点击 **【🚀 一键填充当前页面表单】**，通用信息与定制信息一次性全部写入。

---

## 🔄 当你修改了 `config/profile.yml` 时如何更新？

本项目通过脚本一键将 `config/profile.yml` 同步为插件能读取的 `profile.json`：

在项目根目录下运行：
```powershell
python bin/sync_autofill_profile.py
```
运行后，在浏览器的扩展管理页（`edge://extensions/`）找到本插件，点击 **【重新加载（Reload）】** 刷新图标，新数据立刻生效！

---

## 🛠️ 文件结构说明

- `manifest.json`：扩展清单文件（Manifest V3）
- `content.js`：注入页面的核心脚本，负责 DOM 识别、Vue 原生事件分发、悬浮窗注入
- `content.css`：悬浮球与快捷复制面板样式
- `popup.html` / `popup.js`：右上角点击插件图标弹出的状态卡片
- `profile.json`：由 `bin/sync_autofill_profile.py` 自动编译生成的求职画像缓存
