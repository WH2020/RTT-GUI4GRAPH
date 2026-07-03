# RTT GUI4GRAPH 完整架构

一个通用的 RTT 上位机工具：读取 J-Link RTT 数据流 → 自动解析 key=value 文本 → 通道化 → 实时绘图；
支持命令下发、调参面板、自定义指令库、打标、会话保存/离线回放。

## 1. 技术选型

| 项 | 选择 | 理由 |
|----|------|------|
| 语言/运行时 | Python 3.10+ | 开发效率高，工具类应用首选 |
| RTT 接入 | pylink-square 直连 J-Link | 无需 RTT Viewer/Server 进程，控制最灵活 |
| GUI | PySide6 | Qt 官方 Python 绑定，Model/View、Dock、信号槽齐全 |
| 绘图 | pyqtgraph | 专为实时数据设计，numpy 直通，性能远超 matplotlib |
| 数据 | numpy 环形缓冲 | 零拷贝取段绘图，高吞吐不卡顿 |

## 2. 总体分层

```
┌──────────────────────────────────────────────────────────────┐
│ UI 层 (PySide6)                                               │
│  MainWindow ─ PlotWidget(主图+状态泳道) ─ ChannelPanel         │
│  ChannelModelEditor ─ MarkerPanel ─ LogView ─ SendPanel       │
│  CmdLibraryEditor ─ ConnectDialog(按 Link 声明自动生成表单)     │
├──────────────────────────────────────────────────────────────┤
│ 数据管道层 (core)                                              │
│  LineAssembler → ParserBase 实现 → ChannelRegistry(环形缓冲)   │
│  MarkerStore ─ Recorder(.rttcap 录制/回放/导出)                │
├──────────────────────────────────────────────────────────────┤
│ 连接层 (core.links, 可插拔)                                    │
│  LinkBase 接口 ← JLinkRttLink / (Serial/Tcp 预留)              │
├──────────────────────────────────────────────────────────────┤
│ 配置层 (config)                                                │
│  QSettings(窗口/最近会话) ─ 会话预设 JSON ─ commands.json       │
└──────────────────────────────────────────────────────────────┘
```

**硬性约束：可扩展性与通用性。** 传输方式和数据协议都不写死——两者均抽象为接口，
J-Link RTT 与 key=value 解析只是默认实现，后续零改动核心即可接入串口/TCP/二进制协议。

## 3. 核心抽象接口（扩展性骨架）

UI 和数据管道只依赖接口，不依赖具体实现：

```python
# core/link_base.py —— 传输层接口
class LinkBase(QObject):
    bytes_received = Signal(bytes)          # 上行数据
    state_changed  = Signal(LinkState, str) # 连接状态（含错误信息）
    def open(self, config: dict): ...
    def close(self): ...
    def send(self, data: bytes): ...
    @classmethod
    def config_fields(cls) -> list[Field]:  # 声明连接参数（设备型号、速率…）
        ...                                  # → 连接对话框据此自动生成表单

# core/parser_base.py —— 协议解析接口
class ParserBase:
    def feed(self, data: bytes) -> list[Sample | Event | LogLine | ParseIssue]: ...

# 统一数据模型（所有 Parser 的输出、所有下游的输入）：
#   Sample(channel, t, value)                     数值采样点
#   Event(channel, t, label)                      离散事件/状态跳变
#   LogLine(terminal, t, text)                    原始日志行
#   ParseIssue(t, severity, key, reason, sample)  解析异常上报（见 §5.3）
```

- **注册表 + 工厂**：`LINKS = {"jlink-rtt": ...}`、`PARSERS = {"kv-line": ...}`；
  连接对话框的下拉框由注册表驱动，新增实现 = 加一个类 + 注册一行。
- **插件目录**：启动扫描 `plugins/*.py`，其中的 LinkBase/ParserBase 子类自动注册；
  私有二进制协议写一个解析器文件丢进去即可，不改主程序。
- **指令库与传输层解耦**：指令模板只做占位符替换 + text/hex 编码，换传输方式后指令库原样可用。

## 4. 线程模型（关键设计）

```
[Reader QThread]                          [GUI 线程]
 loop:                                     QTimer @30fps:
   jlink.rtt_read(0,4096) ──字节──►          drain queue
   LineAssembler(剥0xFF终端转义,拼行)          → 环形缓冲追加
   Parser.feed → Sample/Event/LogLine        → setData 刷新可见曲线
   push 线程安全队列 ────────────────►        → 日志视图追加
   执行 cmd_queue 中的 rtt_write
```

- 解析在 Reader 线程就地完成（正则很便宜），GUI 线程只做批量入缓冲和绘图。
- 绘图帧率与数据速率完全解耦：RTT 高吞吐时 UI 依然 30fps。
- 所有 pylink 调用收敛在 Reader 线程（JLink 句柄非线程安全），发送经命令队列串行化。
- 断线/目标复位 → `state_changed` 信号 → UI 状态栏提示 + 一键重连。

### 4.1 队列策略（明确定义）

两条队列，性质不同，策略分开：

**① 上行数据队列（Reader → GUI，高吞吐、可容忍丢旧）**

| 项 | 策略 |
|----|------|
| 结构 | `collections.deque(maxlen=QUEUE_CAP)`，SPSC（单生产单消费），`append`/`popleft` 在 CPython 下原子，无需额外锁 |
| 粒度 | **按批入队**：每次 `rtt_read` 周期（~2ms）解析出的全部记录打包为一个 batch，一次 append——队列操作频率 ≈ 500次/s，与数据条数无关 |
| 容量 | maxlen = 2000 批（≈4s 数据），按批计数而非按条，内存上界确定 |
| 溢出策略 | **丢最旧**（deque maxlen 自动行为）+ Reader 侧 `dropped_batches` 原子计数器；GUI 状态栏显示"丢弃 N 批"黄色警告——**只丢不静默** |
| 消费限额 | GUI 每 tick 最多处理 `MAX_RECORDS_PER_TICK`（如 20000 条），超出留到下一 tick——防止积压瞬间涌入卡死 UI；连续 3 tick 达限额也在状态栏警示 |
| 背压 | **上游永不节流**：RTT 目标侧缓冲很小，读得慢固件端就丢（取决于固件 `SEGGER_RTT_MODE`），所以 Reader 始终全速读，压力只允许在上位机队列消化 |

**② 下行命令队列（GUI → Reader，低频、不可丢）**

| 项 | 策略 |
|----|------|
| 结构 | `queue.Queue(maxsize=64)` |
| 满时行为 | `put_nowait` 失败 → **立即向用户报错**（发送按钮旁提示"命令队列满"），绝不静默丢弃、绝不阻塞 GUI 线程 |
| 执行时机 | Reader 每个读循环间隙 drain 全部待发命令，逐条 `rtt_write`；写失败（返回 0/异常）→ 经信号回报 UI，标记该命令发送失败 |
| 顺序保证 | 单队列单消费者，严格 FIFO |

**③ 运行指标（状态栏常驻）**：字节/s、行/s、队列深度、丢批数、解析异常数——性能问题可观测，不靠猜。

## 5. 解析管道（以真实样例走查）

输入行：`TAP RTT dev=0 event=wait_quiet enabled=1 connected=1 align=FULL_LOCKED state=TOE_STRIKE2 wr_dps=173 wy_dps=161 cross=1 span=4 level=3 moving=35 peak=50 quiet=60`

1. **LineAssembler**：剥离 SEGGER 虚拟终端转义（`0xFF`+终端号，即 RTT Viewer 中 `01>` 的来源），
   按 `\n` 切行，半行缓存；成行瞬间打 `time.monotonic()` 时间戳。
2. **KvLineParser**：正则 `(\w+)=(\S+)` 提取全部键值对；首个 kv 之前的裸词取首词（`TAP`）作分组前缀 → 通道名 `TAP.wr_dps`。
3. **值分类**（判定规则见 §5.1）：
   - 数值通道（11 个）：`dev enabled connected wr_dps wy_dps cross span level moving peak quiet` → Sample
   - 枚举通道（3 个）：`event align state` → 每 key 独立维护 str→序号映射 → Event + 阶梯值
4. **ChannelRegistry**：新 key 首现自动注册（发 `channel_added` 信号），**但发现 ≠ 绘图**——
   新通道默认只进"已发现"列表显示最新值，用户手动勾选后才出曲线。

### 5.1 值判定规则（明确文法，不靠 try/except 碰运气）

**Token 级判定**——一个 value 是否"数值"，由显式正则文法决定（大小写不敏感）：

| 形式 | 示例 | 判定 | 入缓冲值 |
|------|------|------|---------|
| 十进制整数（含符号） | `173` `-45` `+7` | 数值 | float |
| 浮点/科学计数 | `3.14` `-0.5` `1e-3` `2.5E+6` `.5` | 数值 | float |
| `0x` 前缀十六进制 | `0x1A` `0xFFFF` | 数值 | `int(x,16)` 转 float |
| `nan`（任意大小写） | `nan` `NaN` | 数值 | `NaN` 照常入缓冲 → pyqtgraph 曲线**断开**表示数据缺失 |
| `inf` / `-inf` | `inf` | 数值 | **不入缓冲**（会毁掉自动 Y 轴），计 ParseIssue |
| 无前缀十六进制 | `FF` `1A2B` | **枚举**（有歧义，宁可保守；固件需要十六进制请加 `0x`） | 枚举标签 |
| 其余任意字符串 | `FULL_LOCKED` `wait_quiet` | 枚举 | 标签→序号映射 |
| 空值 `key=` | `state=` | 无效对 | 跳过该对，计 ParseIssue |

**通道级类型状态机**——每个 key 独立维护：

```
UNKNOWN ──首个数值 token──► NUMERIC
UNKNOWN ──首个枚举 token──► ENUM

NUMERIC + 枚举 token → 类型冲突：该值不入缓冲，计入该通道 type_errors，发 ParseIssue；
                        滑窗内冲突率 > 20%（最近100个）→ UI 建议改判为 ENUM（用户一键确认）
ENUM    + 数值 token → 合法：数字就是一个枚举标签（如 state=1 与 state=RUN 混用很常见），不报错
用户手动覆盖类型（通道编辑器）→ 强制生效，状态机停用；ENUM→NUMERIC 时历史标签中可转数值的保留，其余丢弃
```

**枚举基数护栏**：ENUM 通道 distinct 标签数 > 64 → 大概率是自由文本（如 msg=xxx），
自动降级为"仅日志"通道（停止生成 Event、冻结映射表），发 ParseIssue 提示——防止映射表无界增长。

**行级规则**：
- 含 ≥1 个合法 kv 对 → 解析；首个 kv 之前的裸词取首词作分组前缀；
- 同一行内重复 key → **后者覆盖前者**（与 printf 追加习惯一致），计 ParseIssue（每 key 只报一次）；
- 无任何 kv → 仅 LogLine；
- 非 UTF-8 字节 → `decode(errors="replace")`，行照常进日志，计 ParseIssue。

### 5.2 时间戳

上位机 `time.monotonic()`，在行成型瞬间打点（同一行内所有 Sample/Event 共享同一 t）。
局限性明示：这是"到达时间"而非固件时间，J-Link 传输抖动 ~ms 级；
若固件行内带 tick 字段（如 `t=12345`），可在通道编辑器把某数值通道指定为"时间源"，该行改用固件时间（预留扩展点）。

### 5.3 错误上报（ParseIssue 通道）

解析异常不静默、也不刷屏，统一走结构化通道：

- `ParseIssue(t, severity, key, reason, sample_text)`，reason 为枚举：
  `TYPE_CONFLICT / INF_DROPPED / EMPTY_VALUE / DUP_KEY / DECODE_ERROR / ENUM_OVERFLOW / MALFORMED`
- **去重限频**：相同 `(key, reason)` 在 5s 窗口内合并为一条并累计次数——单个坏字段以 1kHz 打印时不会淹没 UI；
- **呈现三处**：状态栏异常总数角标（点击展开）→ "解析问题"面板（按 `(key, reason)` 聚合，显示次数、最近样本原文）→ 通道模型编辑器中每通道的"错误数"列；
- 问题面板中每条可跳转到日志视图中对应原始行，方便定位固件侧打印 bug。

## 6. 通道数据模型（UI 可编辑）

通道模型编辑器 = `QAbstractTableModel` 表格视图，改动即生效、随会话预设持久化：

| 属性 | 说明 |
|------|------|
| key | 原始名，只读（`TAP.wr_dps`） |
| 显示名 / 单位 | 图例显示，如 `腕滚角速度 (dps)` |
| **用于绘图** | 手动确认开关，默认关 |
| 类型 | numeric / enum，可覆盖自动推断 |
| scale / offset | 显示值 = 原始 × scale + offset |
| 分组 / 颜色 / 绘图目标 | 主图 / 状态泳道 / 独立子图 |
| 自动打标 | 枚举通道跳变时自动插入标记 |

`channels.py` 持有数据（每通道 numpy 环形缓冲），编辑器与通道树都只是它的视图。

## 7. 绘图

- pyqtgraph 主图多曲线 + 图例点击显隐；枚举通道在下方独立**状态泳道**画阶梯线，
  Y 轴刻度显示原文本（`TOE_STRIKE2`…），与数值曲线共享时间轴。
- 每帧只对有新数据的可见曲线 `setData`（numpy 视图零拷贝）。
- 交互：滚轮缩放、拖动平移、十字光标、暂停（数据继续入缓冲不丢）、时间窗 10s/60s/全部。

## 8. 打标与保存/回放

- **手动打标**：工具栏按钮/快捷键在当前时刻插贯穿垂直标记线（可命名）；暂停时可点图补标。
- **自动打标**：按通道开关"枚举值跳变→标记"。
- **标记面板**：列表（时间/名称/备注），重命名/删除/双击跳转。
- **保存 `.rttcap`**（单 zip）：`raw.log` 原始字节流 + `data.npz` 通道数组 + `meta.json`（通道模型+标记+会话信息）。
  保留原始流 → 换解析器后可对旧数据重新解析。
- **回放**：打开 `.rttcap` 进入离线模式，复用同一套绘图/通道模型/标记组件。

## 9. 发送与指令库

- **原始命令**：输入框 + 结尾符选项（\n / \r\n / 无）+ ↑↓ 历史；hex 模式直发字节。
- **指令库** `commands.json`：`{name, template, encoding, params:[{name,type,min,max,default}]}`
  - 无参指令 → 一排按钮，点击即发；
  - 带参指令（模板含 `{kp}` 占位）→ 调参区展开为滑块/SpinBox，支持"改动即发"或"手动发送"。
- **调参面板** = 指令库带参条目的常驻展开视图，同一数据模型，不做两套实现。
- **指令库编辑器**：GUI 内增删改查，导入/导出 JSON（跨项目共享）。

## 10. 文件结构

```
rtt_gui4graph/
  app.py                    # 入口：QApplication + MainWindow
  core/
    link_base.py            # LinkBase 接口 + LinkState + 注册表
    parser_base.py          # ParserBase 接口 + Sample/Event/LogLine + 注册表
    links/
      jlink_rtt.py          # pylink 封装：控制块搜索、读循环、写队列、重连
    line_assembler.py       # 字节流→行：终端转义、半行、\r\n、非UTF8容错
    parsers/
      kv_line.py            # 默认 key=value 解析器
    channels.py             # ChannelRegistry + 通道模型 + numpy 环形缓冲
    markers.py              # MarkerStore
    recorder.py             # .rttcap 读写、CSV 导出、离线回放源
  ui/
    main_window.py          # 工具栏 + 中央绘图 + 底部日志 + 右侧 Dock 面板
    plot_widget.py          # 主图 + 状态泳道 + 标记线渲染
    channel_panel.py        # 通道树：发现列表 + 绘图勾选 + 最新值
    channel_model_editor.py # 通道属性表格编辑器
    marker_panel.py         # 标记列表面板
    log_view.py             # 原始日志（限行/过滤/暂停滚动）
    send_panel.py           # 命令输入 + 指令按钮区 + 调参区
    cmd_library.py          # 指令库编辑对话框
    connect_dialog.py       # 由 Link.config_fields() 自动生成的连接表单
  plugins/                  # 用户自定义 Link/Parser，启动自动注册
  config/
    settings.py             # QSettings：窗口布局、最近会话
    session.py              # 会话预设：传输+参数+协议+通道模型+指令库引用
    commands.json           # 指令库
  tests/
    test_parser.py          # KvParser/LineAssembler 边界单测
  requirements.txt          # pylink-square PySide6 pyqtgraph numpy pytest
```

## 11. 实施里程碑

| 阶段 | 内容 | 可验证结果 |
|------|------|-----------|
| M1 | 接口/注册表 + JLinkRttLink + 日志 + 原始发送 | 连上真实设备后见滚动日志、能发命令 |
| M2 | 解析管道 + 通道发现 + 手动确认 + 实时绘图 | 样例数据发现通道，勾选出曲线 |
| M3 | 通道模型编辑器 + 枚举泳道 + 绘图交互 | 通道属性 UI 可编辑 |
| M4 | 打标 + .rttcap 保存/回放 | 打标、保存、离线浏览 |
| M5 | 指令库 + 调参面板 | 指令增删改查、调参即发 |
| M6 | CSV 导出 + 断线重连 + 会话预设 | 日常可用 |

## 12. 验证方式

1. **真机**：J-Link + 目标板，验证控制块搜索、上行绘图、下行命令。
2. **单测**：pytest 覆盖 §5.1 全部判定分支（半行、终端转义、非UTF8、负数/浮点/科学计数/0x十六进制、
   nan/inf、空值、重复 key、类型冲突与改判建议、枚举基数护栏、纯文本行）以及队列溢出计数。
