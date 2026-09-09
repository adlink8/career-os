# Career OS — ATS 网申自动填表助手

填充北森（zhiye.com / italent.cn）、Moka 等校招表单。数据来自本地 `config/profile.yml`，经 `bin/sync_autofill_profile.py` 编译为 `profile.json`（已 gitignore）。

**没有多岗位轨道。** 先点「捕获当前岗位 JD + 表单」，按**这一页的格子**填；求职意向仍是 yaml 解析出的单一岗位名。

画像由扩展后台读取，不注册 `web_accessible_resources`，网页不能直接拉取 `profile.json`。

## 安装

1. 仓库根目录执行：`python bin/sync_autofill_profile.py`
2. Edge / Chrome 打开扩展页，打开开发者模式，加载已解压目录 `extensions/ats-autofill`
3. 改过 `profile.yml` 后重新跑同步脚本，并在扩展页点重新加载

## 使用

- 打开北森 / Moka 等网申页会出现右下角悬浮球。
- **保存位置**：捕获写入 `data/job_discovery/captures/`（走本机 Native Host，不经过 Edge 下载目录，也不走系统代理）。
  首次若提示 Native 失败：扩展页重新加载；仍失败则点弹窗「绑定项目目录」选该 captures 文件夹。
- 入库给 ATS/会审用：
  ```powershell
  python bin/ingest_job_context.py D:\path\career-os-job-context-zhiye.com.json
  python bin/ats_matcher.py --resume <简历.pdf> --job-context D:\path\career-os-job-context-zhiye.com.json
  ```
- 再点「一键填充」：普通输入、北森下拉、日期会按本页表单项逐个写入画像里有的值。
- 运行日志：`data/job_discovery/logs/runtime-YYYY-MM-DD.jsonl`（最近一次还有 `runtime-latest.json`）。F12 控制台过滤 `[Career OS]`。
- **热加载**：画像 `profile.json` 和字段规则 `field-map-rules.json` 每次填充都从磁盘读，改完再点填充即可。下拉点击等 JS 引擎仍受浏览器限制，改脚本才要点「重载扩展脚本」。
- 其它域名可点工具栏图标捕获/填充（注入全部 iframe）。
- 手机、邮箱、身份证：只有 `profile.yml` 里有值才填。
- 北森的 `el-select`、省市区级联、日期组件仍可能填不上，用快捷复制。

## 文件

- `manifest.json`：仅匹配主流 ATS 域名；`all_frames` 用于子帧表单
- `background.js`：读画像、向所有 iframe 发填表指令
- `content.js` / `content.css`：字段匹配与悬浮球
- `popup.html` / `popup.js`：工具栏弹窗
- `profile.json`：本地编译产物，不要提交
