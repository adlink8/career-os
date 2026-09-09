# PLC Homelab：零硬件模拟 PLC 的三条路 + GitHub 项目清单

> 创建：2026-09-07
> 关联：`plc-basics.md`（PLC 基础）、`manufacturing-computer-layers.md`（分层与协议）
> 目标：不买任何硬件，在本机（Windows 11 + WSL2 + Docker）搭出可编程、可采集、可上云的虚拟 PLC 环境，并把它变成可演示的简历项目。

---

## 一、结论

**有，而且不需要虚拟机——Docker 容器就够了。** 三条路：

| 方案 | 成本 | 适合谁 | 本人的判断 |
|------|------|--------|-----------|
| **A. OpenPLC（开源）** | **0 元** | 会 Linux/Docker/Python 的人 | **推荐**。你的技能栈严丝合缝 |
| B. CODESYS（商业免费版） | 0 元 | 想学行业标准 IDE 的人 | 二阶段再上。⚠️ 2026 起免费运行时每 30 分钟重启 |
| C. 西门子 TIA Portal + PLCSIM | 0 元但 **21 天试用** | 明确要去西门子生态的厂 | 不推荐现在碰。试用期一到就卡死 |

**方案 A 的独特优势：OpenPLC Runtime 自带 Modbus TCP 服务器。** 也就是说你可以用 Python 直接读写它的寄存器——这一步正好补上你「L1→边缘」的数据链路缺口，而且是别人简历上没有的东西。

---

## 二、⚠️ 先排一个坑：OpenPLC 官方已经搬家

网上大量中文教程（包括 CSDN/知乎/B 站）指向旧仓库 `thiagoralves/OpenPLC_v3`、网页端口 **8080**。

**2025-2026 现状：项目已迁移到 `Autonomy-Logic` 组织，Runtime 升到 v4，管理端口变为 8443。** 旧教程照抄会卡在"网页打不开"。

| | 旧（教程常见） | 新（当前官方） |
|---|---|---|
| 仓库 | thiagoralves/OpenPLC_v3 | **Autonomy-Logic/openplc-runtime** |
| 版本 | V3 | **Runtime v4** |
| 管理端口 | 8080 | **8443** |
| 部署 | install.sh 裸装 | 官方 Docker 镜像 |

---

## 三、方案 A 详细步骤（OpenPLC Runtime v4 + Docker）

### 1. 起容器（官方 Docker 快速启动路径）

```bash
docker pull ghcr.io/autonomy-logic/openplc-runtime:latest

docker run -d --name openplc-runtime \
  -p 8443:8443 -p 502:502 \
  --cap-add=SYS_NICE --cap-add=SYS_RESOURCE \
  -v openplc-runtime-data:/var/run/runtime \
  ghcr.io/autonomy-logic/openplc-runtime:latest
```

- 8443：Web 管理界面
- 502：内置 Modbus TCP 服务器（⚠️ v4 的 Modbus 端口以启动后 Web 界面显示为准，官方文档未在搜索结果中明确）
- 固定 digest/版本而不是 `latest`，方便复现

### 2. 写程序：OpenPLC Editor（桌面软件）

- 从官方站（autonomylogic.com）下载 Editor，Windows/Linux 都有
- 支持全部 5 种 IEC 61131-3 语言（LD/ST/FBD/IL/SFC）
- Editor 内置**纯软件仿真器**——不上传 runtime 也能在本地模拟跑逻辑
- 第一个程序建议：一个启停自锁回路（START/STOP 按钮 → MOTOR 输出），这是 PLC 界的 "Hello World"

### 3. 采集：Python 当 Modbus 客户端

```python
# pip install pymodbus
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('127.0.0.1', 502)
c.connect()
rr = c.read_holding_registers(0, 1, slave=0)   # 读 %IW0
print(rr.registers)
```

到这一步你就完成了真实工厂里「网关从 PLC 读数」这一环——**和你 AWS IoT 项目里"网关采集 ESP32"完全同构，只是协议从 MQTT 换成了 Modbus。**

### 4. 上云（可选但强烈建议）

用 paho-mqtt 把读到的寄存器发到 EMQX/Mosquitto（你 local-llm-lab 和宠物医院项目都用过 Mosquitto），接 InfluxDB + Grafana 看趋势。

### 完成后的链路

```
[OpenPLC 虚拟 PLC] --Modbus TCP--> [Python 网关] --MQTT--> [Broker --> 时序库 --> 看板]
     L1                                边缘                    云 / 应用
```

**这就是 ISA-95 里 L1 → 边缘 → 云的完整打通。半天到一天能跑通。**

---

## 四、GitHub 项目清单

### 核心项目（已核实在用）

| 项目 | 说明 | 与你的关系 |
|------|------|-----------|
| **Autonomy-Logic/openplc-runtime** | OpenPLC Runtime v4 官方仓库，支持 Docker 部署 | 主角 |
| **thiagoralves/OpenPLC_v3** | 旧版 runtime，教程海量但已过时 | 只用来查资料，别部署 |
| **HilscherAutomation/netPI-openplc** | OpenPLC 容器 + 工业网关硬件（树莓派 3B 架构） | 学它的 Dockerfile 和 Modbus 配置步骤 |
| **schreinerman/rpi-openplc-docker** | 树莓派 Docker 版 OpenPLC | 同上 |

### Python 配套（稳定知名库，未逐一核验 star 数）

| 库 | 用途 |
|----|------|
| **pymodbus**（pymodbus-dev） | Modbus TCP/RTU 客户端+服务端，纯 Python |
| **opcua-asyncio** | OPC UA 客户端/服务端，asyncio 原生 |
| **python-snap7** | 对接西门子 S7 系列（S7 协议） |
| **paho-mqtt** | MQTT 上行 |

### 进阶方向（安全/靶场，可选）

| 项目 | 说明 |
|------|------|
| **Conpot** | ICS 蜜罐，模拟 Modbus/S7 服务器——如果以后想走工控安全方向 |
| **Factory I/O**（商业，非 GitHub） | 3D 工厂仿真，30 天全功能试用，正式版约 $229（两源报价 $229 / $199-599，未核实）。接你的 OpenPLC 就能看到传送带动起来 |

---

## 五、把它变成简历项目

**项目名（暂定）：`plc2cloud-lab` —— 虚拟 PLC 数据采集与上云管道**

**简历表述：**

> 基于 OpenPLC Runtime v4（Docker）搭建虚拟 PLC 环境，用 Python/pymodbus 实现 Modbus TCP 数据采集网关，经 MQTT 上报时序数据库并可视化；覆盖 IEC 61131-3 梯形图编写、工业协议对接与边缘-云链路。

**面试故事线（和已有项目形成闭环）：**

> 我之前做过 ESP32 → MQTT → 网关 → AWS 的 IoT 管道。为了补工业侧知识，我用 OpenPLC 在 Docker 里模拟了一台 PLC，走同样的"采集 → MQTT → 存储"链路，但这次数据源从开发板换成了 PLC，协议从裸 MQTT 换成了 Modbus TCP。所以工厂里"设备数据上云"这件事，我两端都摸过。

**这句话同时回答了三个面试问题：会不会 OT、会不会 IT、为什么制造业要你。**

### 验证标准（做完要能当场演示）

- [ ] Docker 容器跑起来，浏览器打开 8443 能看到 Web 界面
- [ ] Editor 里写一个启停自锁梯形图，上传后能在线改状态
- [ ] Python 脚本读到寄存器数值变化
- [ ] （加分）Grafana 看到趋势曲线
- [ ] 全程录屏或截图存档（面试放不出来就白做）

---

## 六、时间与优先级

| 阶段 | 内容 | 预算 |
|------|------|------|
| 1 | Docker 起容器 + 第一个梯形图 | 半天 |
| 2 | pymodbus 读寄存器 + MQTT 上报 | 半天 |
| 3 | InfluxDB/Grafana 看板 | 半天（可选） |
| 4 | 整理成 GitHub 仓库 + README | 半天 |

**总预算约 1-2 个非面试日。** 排在投递和面试之后做——它是加分项不是主线，别让它变成新的"1167 道题"。

---

## 七、证据强度

- **强**：OpenPLC 迁移至 Autonomy-Logic 与 Runtime v4 Docker 命令（官方文档经 plcprogramming.io 转述）；CODESYS 免费版 2026 起 30 分钟重启行为；TIA Portal 21 天试用；CCW 免费 Micro800 仿真。
- **中等**：各项目 star 数与活跃度未逐一核验；Factory I/O 价格两源不一致。
- **待验证**：Runtime v4 的 Modbus 服务器端口（部署后以 Web 界面为准）。

## 八、实战部署记录（2026-09-07 已跑通，覆盖第五节部分推测）

### 结论修正

- **v4 Runtime 可以部署但跑不起来**：`ghcr.io/autonomy-logic/openplc-runtime` 能起容器（Web UI 8443 正常），但 PLC State = EMPTY（`No libplc_*.so`），**Modbus 从站插件只在 RUNNING 状态后才启动**——直连 502 会被 RST。而 RUNNING 需要上传 **OpenPLC Editor 桌面版生成的 STruC++ 工程包**（ZIP 内须有 `generated.hpp` + `*.cpp`；含 `Config0.c`/`glueVars.c` 的旧 MatIEC 包会被 compile.sh 明文拒绝）。裸 .st 文件 v4 不收。
- **所以 headless 路线用 v3**：虽然官方已 EOL（2026-04），但这是唯一能全程 CLI 跑通、网页直接编 .st 的方案。学 Modbus → MQTT 链路完全够用；等装了 OpenPLC Editor 再迁 v4。

### 可复现部署（本机实际执行）

```bash
# 1. 构建官方 v3（勿用 0 星社区镜像，供应链风险）
cd /d/ADLINK/DockerWorkspace/openplc && git clone --depth 1 https://github.com/thiagoralves/OpenPLC_v3.git
cd OpenPLC_v3 && docker build -t openplc:v3 .          # ~5 min

# 2. 数据卷（bind mount 会遮住镜像内 /docker_persistent，必须先用仓库 webserver/ 里的文件预填充）
mkdir -p /d/ADLINK/DockerData/openplc/st_files
cp webserver/{openplc.db,dnp3.cfg} /d/ADLINK/DockerData/openplc/
touch /d/ADLINK/DockerData/openplc/{persistent.file,mbconfig.cfg}
cp st_files/* /d/ADLINK/DockerData/openplc/st_files/

# 3. 启动（v4 容器占着 502 就先 docker stop）
docker run -d --name openplc-v3 -p 8081:8080 -p 502:502 \
  -v "D:/ADLINK/DockerData/openplc:/docker_persistent" openplc:v3
# Web UI: http://localhost:8081  默认账号 openplc/openplc
```

### 编译/启动 API 流程（可脚本化）

1. `POST /login`（表单 openplc/openplc，拿 session cookie）
2. `.st` 放进数据卷 `st_files/` + 往 `openplc.db` 的 Programs 表插一行（File 列=文件名）
3. `GET /compile-program?file=<名>.st`（同步阻塞）
4. 轮询 `GET /compilation-logs` 直到 `Compilation finished successfully!`
5. `GET /start_plc`
6. 脚本：`career-os/scratch/plc_compile_flow.py`（requests 会话流）、`scratch/plc_modbus_smoke.py`（pymodbus 验证）

### MatIEC ST 语法坑（三次编译失败换来的）

1. **不能直接对位置赋值**：`%QX0.0 := x;` 报 "invalid variable before ':='" → 必须用 `AT` 声明：`blink_out AT %QX0.0 : BOOL;`
2. `AT` 声明要放**独立 VAR 块**（与普通变量混在一个 VAR 块里报 invalid declaration）
3. 注释/编码疑似干扰 matiec，**ST 文件保持纯 ASCII 最稳**
4. blink 正确写法：`ton(IN := NOT ton.Q, PT := T#500ms)`（自反馈取反）；写成 `ton(IN := NOT blink)` 会变成 40ms 高脉冲/500ms 低，采样容易漏
5. `NOT` 后面只能跟变量，不能跟 `(表达式)`

### 验证结果（pymodbus 实测）

- HR0（%QW0 扫描计数）：50 次/秒递增 = 20ms 扫描任务在跑 ✅
- 写 HR10=4321 读回 4321：上位机写入路径通 ✅
- coil0（%QX0.0）：`111100000111110000011111`（0.1s 采样）= 500ms 高/500ms 低标准方波 ✅
- 编译耗时 ~5-7 min（gcc 全量，WSL2）；**改一行重编一次 7 分钟，调 ST 程序要有心理预期**

### TON 时基坑（重要）

v3 在 Docker 空载（Blank 驱动）下 **TON 定时器时基不走**：`ton(IN := NOT ton.Q, PT := T#500ms)` 编译通过但 Q 永远 FALSE（ET 不累积），coil 恒 0。官方 blink 例程在此环境失效。**替代方案：扫描计数分频**——`blink := ((count/25) MOD 2) <> 0`（25 扫描 × 20ms = 500ms 半周期），确定性且不依赖系统时基。

### MatIEC 类型坑（补充）

- `counter_out := count;`（DINT→INT）报 "Incompatible data types for ':='" → 必须 `DINT_TO_INT(count)` 显式转换
- 报错行号精确，日志看 `/compilation-logs` 即可定位


