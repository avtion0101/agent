# AI Agent 开发转型训练

从 C/C++、Qt、工业软件和设备通信经验出发，通过可运行项目、独立练习与故障实验，建立 AI Agent 开发能力。

训练路线：Python 工程 → LLM 基础 → RAG → 手写 Agent → LangGraph / MCP → 生产工程。建议周期约 26 周，实际推进以验收结果为准。

## 文档导航

| 材料 | 用途 |
| --- | --- |
| [完整路线图](day01/agent-training/agent-dev-transition-roadmap.md) | 六个阶段的目标、项目和验收要求 |
| [执行手册](day01/agent-training/执行手册.md) | 训练流程、Phase 0 的 21 个训练单元及技术表述校正 |
| [训练记录](day01/agent-training/训练记录.md) | 当前进度、提交格式和决策记录 |
| [Day 1 课程](day01/phase0-log-analyzer/docs/day01.md) | 字段协议、解析与校验、错误率练习和故障实验 |
| [参考项目说明](day01/phase0-log-analyzer/README.md) | 日志分析 CLI 的安装、使用和设计边界 |
| [历史验证记录](day01/phase0-log-analyzer/docs/verification.md) | 原助手环境的验证结果与范围 |
| [原始 Phase 0 训练包](day01/Agent转型训练包_Phase0.zip) | 保留原交付材料，包含历史报告 |

## 运行 Phase 0 参考项目

需要 Python 3.12 或以上版本，以及 uv。在仓库根目录执行：

```bash
cd day01/phase0-log-analyzer
uv sync --locked
uv run --locked agent-logs generate data/device.log --lines 10000
uv run --locked agent-logs analyze data/device.log --output reports/report.json
uv run --locked pytest
uv run --locked mypy --strict
```

默认生成的 10000 行日志包含 9897 条合法记录和 103 条坏行。首次同步需要联网下载依赖；此阶段无需模型 API Key。

## 当前进度

按现有训练记录，当前处于 **Phase 0 / Day 1，待学习者提交本机运行、独立练习与解释并完成验收**。参考材料和历史助手验证已经交付。

Day 1 的下一步：运行参考项目，独立完成 `error_ratio` 函数及测试，解释解析与校验的区别，并说明数据校验故障实验的错误原因。通过验收后进入 Day 2。

## 每次推进后的同步

每次推进项目后，将本次涉及的 day 目录同步到此 GitHub 仓库和 Obsidian。沿用本地 `day01/` 与 Obsidian `agent/day1/` 的对应关系，后续编号依次递增。具体要求见 [项目规则](AGENTS.md) 和 [Day 1 同步说明](day01/同步说明.md)。
