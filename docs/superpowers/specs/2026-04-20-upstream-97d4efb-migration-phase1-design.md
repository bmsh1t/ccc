# Upstream `97d4efb` Migration Alignment — Phase 1 Design

日期：2026-04-20  
状态：draft

## 目标

在**不破坏本地当前实战工作流**的前提下，为后续吸收 upstream `97d4efb` 做第一阶段迁移对齐：

- 先做**去耦 + 兼容层**
- 让 slash-command 路径成为主叙事
- 暂时**不直接删除**
  - `tools/cve_hunter.py`
  - `tools/report_generator.py`
  - `memory/hunt_journal.py`

核心原则：

- 最小风险
- 最大实用
- 保持当前 `hunt.py` / `agent.py` / `/pickup` / `/remember` 可用
- 为后续真正吸收 `97d4efb` 降低冲突面

---

## 背景

官方 upstream 在 `97d4efb`（2026-04-18）中做了明显的结构收口：

- 删除 `tools/cve_hunter.py`，改为 `/intel`
- 删除 `tools/report_generator.py`，改为 `/report`
- 删除 `memory/hunt_journal.py`，改为 `/remember`
- `hunt.py` 里相关入口变成 warning/stub

但本地当前仓库并不适合直接吃下这次删除，原因很明确：

1. `hunt.py` 仍直接调用：
   - `run_cve_hunt()`
   - `generate_reports()`
2. `agent.py` 仍直接暴露和调度：
   - `run_cve_hunt`
   - `generate_reports`
3. 多个工具和测试仍直接依赖 `HuntJournal`
   - `tools/remember.py`
   - `tools/resume.py`
   - `tools/hunt.py`
   - `agent.py`
   - 多个 `tests/test_*`
4. 当前本地增强很多都建立在现有 memory / report / hunt wrapper 结构上

所以这次不能采用“官方直接删除”的方式，而要走**迁移式对齐**。

---

## 本轮范围

### In Scope

本轮只做 Phase 1：

1. 建立“主路径 / 兼容路径”的边界
2. 缩小 `hunt.py` / `agent.py` 对旧模块的直接耦合
3. 让后续删旧模块时只需要替换少量适配点
4. 补必要测试，确保当前实战链路不退化

### Out of Scope

本轮明确不做：

- 不删除 `tools/cve_hunter.py`
- 不删除 `tools/report_generator.py`
- 不删除 `memory/hunt_journal.py`
- 不把 `hunt.py` 里的 `run_cve_hunt()` / `generate_reports()` 直接改成 stub
- 不重写整套 `/remember` 持久化模型
- 不大改文档全仓文案
- 不引入大规模目录重构

---

## 方案比较

### 方案 A：直接吸官方删除

做法：

- 直接删旧模块
- 按 upstream 把 `hunt.py` 相关路径改成 warning/stub

优点：

- 对齐官方最快

缺点：

- 会直接破坏本地当前工作流
- `agent.py` / `hunt.py` / 多个测试都会一起炸
- 用户当前“实战稳定版”目标会被破坏

结论：**不选**

---

### 方案 B：只改文档，不动代码

做法：

- 公开叙事继续偏 slash commands
- 代码完全不去耦

优点：

- 风险低

缺点：

- 后续继续对齐 `97d4efb` 时，代码冲突还是会很大
- 没有真正降低维护成本

结论：**不选**

---

### 方案 C：迁移式对齐（推荐）

做法：

- 保留旧模块
- 在调用侧先抽出更稳定的兼容层/桥接点
- 明确哪些是“本地主路径”，哪些是“旧实现兼容层”

优点：

- 风险最低
- 能持续保持当前功能
- 为后续正式删旧模块创造条件

缺点：

- 不是一步到位
- 会短期保留双轨结构

结论：**推荐**

---

## 推荐设计

### 1. 为 legacy capability 建立显式桥接层

新增一个很小的桥接模块，负责统一承接这三类旧能力：

- intel / CVE 能力
- report 生成能力
- hunt memory journal 能力

桥接层的职责不是重写业务，而是：

- 统一 import 入口
- 统一 fallback 位置
- 把调用方从“直接依赖具体旧文件”改成“依赖稳定接口”

这一步的价值在于：后面如果要真正删旧模块，只要替换桥接层，而不是全仓到处改。

---

### 2. `hunt.py` 先从“直连旧模块”改成“走桥接入口”

当前 `hunt.py` 是后续对齐 `97d4efb` 的最大冲突点之一。

Phase 1 中它不改变用户可见行为，只改变内部依赖方式：

- `run_cve_hunt()` 仍可用
- `generate_reports()` 仍可用
- journal 读写仍可用

但这些路径内部不再假设某个旧文件永远存在。

这样 Phase 2 才能继续把 `run_cve_hunt()` 从 “直接执行 legacy CVE hunter” 平滑切到 “slash-command / intel 主路径”。

---

### 3. `agent.py` 调度层同步收口

`agent.py` 当前仍直接暴露：

- `run_cve_hunt`
- `generate_reports`

这会把旧实现继续扩散到 agent dispatch 层。

Phase 1 中不删除能力，但要做到：

- agent 侧走统一桥接入口
- 对外 tool 名保持不变，避免当前 CLI / prompt / tests 抖动
- 后续如果改底层实现，不需要再改 agent tool surface

即：**先稳住 tool surface，再替换内部实现**。

---

### 4. `HuntJournal` 保留，但降级为“兼容存储后端”

本地当前很多能力都围绕 `HuntJournal` 工作，直接删除不现实。

Phase 1 的定位：

- 继续保留 `memory/hunt_journal.py`
- 明确它是当前兼容后端
- 让调用方逐步依赖更稳定的 memory access 入口，而不是 everywhere 直接 new `HuntJournal(...)`

注意：

本轮不做全仓 memory API 重构，只做**最小实用收口**。

---

### 5. 用户可见层保持稳定

本轮不改变这些行为：

- `hunt.py --cve-hunt`
- `hunt.py` 自动 report 生成
- `/remember`
- `/pickup`
- agent 自动化路径里的相关 tool 名

也就是说：

- **内部先去耦**
- **外部不抖动**

这符合当前“稳定版优先”的目标。

---

## 计划中的落点

本轮更像“为后续大对齐清地基”，理想结果是：

1. `hunt.py` / `agent.py` 不再深度绑死旧文件路径
2. 旧模块仍然保留且继续可用
3. 新增的桥接层足够小、足够清晰
4. 测试证明：
   - 当前用户可见行为没退化
   - 后续继续迁移时改动面会明显缩小

---

## 文件范围（预期）

### 主要代码

- 新增：一个轻量 bridge / adapter 模块
- 修改：
  - `tools/hunt.py`
  - `agent.py`
  - 可能少量触及：
    - `tools/remember.py`
    - `tools/resume.py`
    - `memory/__init__.py`

### 测试

- `tests/test_hunt_target_types.py`
- `tests/test_hunt_wrappers.py`
- `tests/test_agent_dispatcher_misc.py`
- `tests/test_agent_compat.py`
- 视实际桥接点再补最小测试

---

## 验收标准

本轮完成后，应满足：

1. `hunt.py` 的 CVE/report/journal 路径仍可运行
2. `agent.py` 的 `run_cve_hunt` / `generate_reports` 调度仍可运行
3. `HuntJournal` 相关现有测试仍通过
4. 全量回归通过
5. 新增桥接层后，后续删除 legacy 文件时只需要改少量点，而不是全仓散改

---

## 风险与控制

### 风险 1：桥接层把简单问题复杂化

控制：

- 桥接层只做 import / dispatch / fallback
- 不引入新业务逻辑

### 风险 2：用户可见行为被误改

控制：

- 明确要求 tool surface 与 CLI surface 不变
- 先补 wrapper / dispatch 测试

### 风险 3：memory 路径改动波及面过大

控制：

- 本轮只做局部收口，不做 memory 大重构

---

## 实施顺序建议

1. 先建 bridge 层和最小失败测试
2. 再改 `hunt.py`
3. 再改 `agent.py`
4. 最后看是否需要补 `remember/resume` 的极小收口
5. 跑 focused tests
6. 跑全量 `pytest -q`

---

## 结论

本轮应该采用：

**“保留 legacy、先做桥接、先去耦调用方、保持外部稳定”的迁移式对齐方案。**

这不是一次性吞下 `97d4efb`，而是把最危险的删除动作拆开，先完成最有价值、最不容易把本地实战工作流打坏的第一步。
