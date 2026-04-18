# Pickup Command Alignment Design

Date: 2026-04-19
Status: Approved for spec review

## Goal

将本地稳定版的“继续上次狩猎”入口对齐到官方 `/pickup`，同时保留一层很薄的 `/resume` 兼容层，确保后续持续吸收上游更新时冲突更少。

## Core constraint

后续功能演进需要持续对齐官方仓库，因此本次设计遵循以下硬约束：

- 对外主语义优先与官方保持一致
- 后续如继续吸收上游更新，优先保持命令名、文档入口、输出文案与官方一致
- 本地增强尽量挂在扩展层，而不是改写官方主叙事
- 只在确有必要时保留最薄兼容层

## Why

上游官方已在 2026-04-17 将主入口从 `/resume` 切到 `/pickup`，原因是 `/resume` 在 Claude Code CLI 中属于保留命令。当前本地仓库如果继续以 `/resume` 为主，会带来两个问题：

- Claude Code CLI 下实际可用性和官方主用法不一致
- 以后同步上游 `README.md`、`CLAUDE.md`、`commands/*.md` 时更容易出现长期分叉

因此本次改动应优先完成“表层对齐”，而不是进行内部大重命名。

## Design principles

- 对外行为尽量与官方一致
- 对内实现尽量少动，避免破坏当前稳定版增强链路
- 兼容层只做一层，不引入第二套内部逻辑
- 不夹带其它功能增强，严格收口
- 以后继续同步官方时，优先复用本次建立的 `/pickup` 主入口结构

## In scope

### 1. 新增 `/pickup` 主命令文档

新增 `commands/pickup.md`，作为继续上次狩猎的主入口文档。

要求：

- 标题、usage、描述均使用 `/pickup`
- 明确说明该命令由 `/resume` 更名而来
- 文案风格尽量对齐上游官方当前版本

### 2. 将公开主入口切到 `/pickup`

更新以下对外入口，让 `/pickup` 成为默认推荐命令：

- `README.md`
- `CLAUDE.md`
- `commands/autopilot.md`
- `commands/remember.md`
- 其它明确给用户展示“下次继续狩猎”入口的文档

原则：

- 用户可见入口统一写 `/pickup`
- 与官方当前主文档表述尽量一致
- 如无必要，不改内部实现字段名

### 3. 保留 `/resume` 兼容说明页

保留 `commands/resume.md`，但将其定位改为兼容页，而不是主入口页。

要求：

- 明确说明 `/resume` 为兼容保留入口
- 明确建议用户改用 `/pickup`
- 不制造与 `/pickup` 冲突的第二套主叙事

### 4. 终端输出表层对齐官方

在不修改内部函数名和数据字段名的前提下，将 `tools/resume.py` 的终端展示文案对齐到 `/pickup` 主语义。

优先对齐的内容：

- 标题从 `RESUME: <target>` 调整为 `PICKUP: <target>`
- 行为文案从 “Resume hunting...” 调整为更接近官方的 “Continue hunting...”
- 无历史数据时的提示仍保持当前本地流程兼容

## Out of scope

本次不做以下内容：

- `tools/resume.py` 重命名为 `pickup.py`
- `load_resume_summary`、`resume_summary`、`resume_targets` 等内部接口/字段重命名
- `agent.py`、`autopilot_state.py` 内部语义整体迁移到 pickup 命名
- IP/CIDR 支持
- CVSS 4.0
- 其它 upstream cherry-pick

## Compatibility strategy

### External behavior

- 以后对外默认使用 `/pickup`
- 文档、帮助入口、命令说明统一推荐 `/pickup`
- 后续如果官方继续调整 `/pickup` 文案或入口，本地优先跟进官方

### Internal behavior

- 继续复用现有 `tools/resume.py`
- 继续保留现有 summary/helper 接口名
- 通过最小文案调整完成表层统一

### Backward compatibility

- `commands/resume.md` 继续存在
- 老用户看到 `/resume` 时，仍能明确找到迁移路径到 `/pickup`
- 本地现有依赖 `resume_*` 的代码和测试主链不做结构性修改

## Files likely in scope

- `commands/pickup.md`
- `commands/resume.md`
- `README.md`
- `CLAUDE.md`
- `commands/autopilot.md`
- `commands/remember.md`
- `tools/resume.py`
- `tests/test_resume_tool.py`

如果在实现中发现还有少量引用 `/resume` 的用户可见文档，可一并更新，但应避免扩大到内部实现大重构。

## Error handling

- `/pickup` 只是表层入口切换，不应改变 hunt-memory 读取逻辑
- 若某目标无历史数据，仍返回原有“先 recon / 再 hunt”的引导
- 文案调整不得影响 `load_resume_summary()` 返回结构
- 任何兼容页或文案变更都不应破坏 agent helper 调用链

## Testing

需要覆盖以下验证点：

1. `commands/pickup.md` 存在且内容正确
2. `commands/resume.md` 明确标注兼容入口
3. `format_resume_output()` 标题变为 `PICKUP: <target>`
4. 主要动作文案与官方 `/pickup` 语义一致
5. 无历史数据场景仍保持正确引导
6. 现有依赖 `load_resume_summary()` 的测试不因文案变更而失效

## Risks

### Risk 1: 表层术语与内部命名不一致

这是有意接受的短期折中。

Mitigation:

- 只在用户可见层使用 `/pickup`
- 在内部继续保持 `resume_*` 命名，避免大范围破坏

### Risk 2: 文档与输出更新不完整

如果只改部分入口，用户会看到 `/pickup` 与 `/resume` 混杂。

Mitigation:

- 明确把公开主入口统一作为本次验收标准
- 将 `/resume` 明确降级为兼容页

### Risk 3: 以后继续同步官方时再次分叉

Mitigation:

- 本次先完成官方表层对齐
- 以后新增增强优先挂在扩展层，而不是改写官方主命令叙事

## Completion criteria

完成标准为：

1. 仓库公开主入口已统一推荐 `/pickup`
2. `commands/pickup.md` 已存在并作为主命令文档
3. `commands/resume.md` 已转为兼容说明页
4. `tools/resume.py` 输出已使用 `PICKUP` 主标题
5. 相关测试更新并通过
6. 本地增强链路（`resume_summary` / `autopilot_state` / agent bootstrap）未发生结构性回归
7. 后续继续对齐官方时，无需再把 `/resume` 重新作为主入口
