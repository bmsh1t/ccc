# Upstream `97d4efb` Migration Alignment — Compatibility Fork Decision

日期：2026-04-20  
状态：accepted

## 结论

主分支暂不继续“完整吸收” upstream `97d4efb` 的最终删除态。

当前仓库采用 **兼容分叉策略**：

- 继续保留 `tools/cve_hunter.py`
- 继续保留 `tools/report_generator.py`
- 继续保留 `memory/hunt_journal.py`
- 保持 `/intel`、`/report`、`/remember` 作为主叙事入口
- 保持 legacy CLI / Python 能力可运行，但在运行时与文档层标记为 compatibility path

## 已核对事实

### upstream 目标态

upstream `97d4efb` 的核心动作是：

- 删除 `tools/cve_hunter.py`
- 删除 `tools/report_generator.py`
- 删除 `memory/hunt_journal.py`
- 将 `tools/hunt.py` 中的 `run_cve_hunt()` / `generate_reports()` 改为 warning / stub
- 从 `memory/__init__.py` 移除 `HuntJournal`

### 本地当前态

本地仓库当前仍然：

- 通过 `tools/legacy_bridge.py` 承接 legacy CVE / report / journal 能力
- 在 `tools/hunt.py` 中继续执行 legacy backend，而不是改成 stub
- 在 `memory/__init__.py` 中继续 re-export `HuntJournal`
- 在 `agent.py` 中继续保留 legacy tool surface

### 相关验证

2026-04-20 已执行聚焦回归：

```bash
pytest -q tests/test_legacy_bridge.py tests/test_hunt_wrappers.py tests/test_agent_dispatcher_misc.py tests/test_phase2_docs.py tests/test_ctf_mode.py tests/test_validate_ctf_mode.py
```

结果：

- `38 passed in 0.24s`

## 为什么不继续硬吸收

### 1. 这与当前 Phase 1 / Phase 2 的目标不一致

当前两阶段设计目标是：

- 迁移式对齐
- 保留本地实战工作流
- 降低直接耦合
- 弱化 legacy 主叙事

而不是：

- 立即删除旧实现
- 立即切成 upstream 最终 stub 态

### 2. 当前主分支已经形成稳定的本地增强闭环

主分支当前真实依赖以下本地增强链路：

- `request_guard`
- `autopilot_state`
- `resume`
- `remember`
- `surface`
- `source_hunt`
- `legacy_bridge`

如果继续做 upstream 式“彻底删除”，影响范围将超出单纯的 3 个 legacy 文件。

### 3. 继续硬吸收的收益小于破坏成本

当前已经完成：

- 主叙事切换到 slash commands
- legacy 路径降级为 compatibility path
- 关键回归测试补齐

在此基础上继续删除旧后端，主要收益是“更像 upstream”，但会明显增加本地 workflow 回归风险。

## 主分支明确保留的策略

### 保留

- legacy backend 文件
- compatibility bridge
- 兼容导出 `HuntJournal`
- agent 中的 legacy tool surface

### 不再作为主入口

- `run_cve_hunt()`
- `generate_reports()`
- 任何直接依赖 legacy file 的主叙事文案

## 当前不做

- 不删除 `tools/cve_hunter.py`
- 不删除 `tools/report_generator.py`
- 不删除 `memory/hunt_journal.py`
- 不把 `tools/hunt.py` 的相关 wrapper 改成 stub
- 不移除 `memory.__init__` 中的 `HuntJournal`
- 不移除 `agent.py` 中的 legacy tool surface

## 何时再评估 Phase 3

仅在以下条件满足时，才考虑单独开分支推进“硬吸收”：

- 本地 CLI / Python 兼容工作流确认退役
- `remember` / `resume` 的持久化模型完成脱离 journal 的重构
- `agent.py` 已不再依赖 legacy tool surface
- 维护 legacy backend 的成本显著高于兼容收益

## 推荐后续动作

当前主分支后续默认策略：

1. 继续保持兼容分叉
2. 只做必要的 upstream 文案 / 安全修复 / 小型行为对齐
3. 若未来确需完整吸收 upstream `97d4efb`，单独开启 Phase 3 / hard-absorb 分支，不在主分支直接推进
