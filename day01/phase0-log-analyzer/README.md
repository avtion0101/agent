# Phase 0：异步设备日志分析 CLI

这是《AI Agent 开发工程师转型路线图》的第一阶段参考实现。目标是学习 Python 工程结构、类型、数据校验、并发、测试；无需 API Key，不依赖大模型，不产生模型调用费用。

## 环境与运行

需要 Python 3.12+ 和 uv。当前项目默认选择 3.12，版本范围不表示只支持一个 Python 小版本。若已有 3.13，可运行 `uv sync --python 3.13`，再用该环境运行命令。不要把程序装进系统 Python。

uv 官方安装文档：https://docs.astral.sh/uv/getting-started/installation/

macOS 可使用 `brew install uv`。Windows 可按官方安装说明或使用 `winget install --id=astral-sh.uv -e`。安装后重新打开终端，先确认 `uv --version`。

解压后，进入包含 `pyproject.toml` 的 `phase0-log-analyzer` 目录。以下命令适用于 macOS/Linux shell 和 Windows PowerShell：

```bash
uv sync --locked
uv run --locked agent-logs generate data/device.log --lines 10000
uv run --locked agent-logs analyze data/device.log --output reports/report.json
uv run --locked pytest
uv run --locked mypy --strict
uv run --locked python experiments/blocking_loop.py --seconds 5
uv run --locked python experiments/mutable_default.py
uv run --locked python experiments/validation_error.py
uv build
```

首次同步需要网络下载依赖。`uv.lock` 固定实际解析的依赖；`--locked` 要求配置与锁文件一致。不要手工编辑锁文件。修改依赖后，使用 `uv lock` 生成新锁，再记录变更与检查结果。

10000 行默认数据：每第 97 行为坏行，因此 `invalid_lines=103`、`valid_lines=9897`，两者相加等于 `total_lines=10000`。延迟统计只包含合法行。

大文件实验：将 `--lines` 改为 `1000000`，对比 `--workers 1` 和 `--workers 4`。记录时间、CPU、内存，不能先假定线程越多越快。

## 文件职责

| 文件 | 职责 |
|---|---|
| `models.py` | Pydantic 输入协议与统计报告 |
| `parser.py` | 文本字段转换、校验、坏行归档 |
| `analyzer.py` | 分批读取、有界队列、工作任务、统计合并 |
| `generate.py` | 固定随机种子生成模拟设备日志 |
| `cli.py` | 参数解析、运行协程、输出 JSON、失败退出码 |
| `tests/test_analyzer.py` | 校验边界、统计正确性、并发一致性、CLI 与异常传播 |
| `experiments/` | 三个有意制造失败的独立实验 |
| `docs/day01.md` | 第一天详细讲解、练习与答案 |

## 日志格式

```text
2026-10-13T10:00:00+00:00 | INFO | serial | 2.5 | device ready
```

字段：时间、级别、组件、延迟毫秒、消息。只切前四个 `|`，消息可以含有 `|`。空行也算坏行。非法时间、级别、空组件、负延迟、NaN/Infinity、空消息都会拒绝。

校验分成两层：解析器将时间和延迟字符串转换为 `datetime`/`float`；Pydantic 严格验证转换后的对象，不让业务层默默接受未知字段或错误类型。

## 并发设计与限制

读取者通过 `asyncio.to_thread` 分批读取，工作任务通过 `to_thread` 解析，队列容量为 `2×workers`。不会为每一行创建一个 task，也不会读入整份文件。内存主要随批大小、队列容量、最长行和不同组件的数量变化；坏行示例最多保留五个。

普通 CPython 默认 GIL 下，线程不能保证纯 Python CPU 解析并行提速。这里的线程用于隔离阻塞工作、保持事件循环响应；真正的 CPU 吞吐优化需要基准和可能的进程池。线程中的执行不在取消协程时被强行终止；本实现面向本地普通文件，网络流、特殊设备文件和强取消保证需要单独设计关闭协议。

统计合并全部在事件循环线程，合并过程中没有 `await`，因此其他协程不会插入这段更新。`TaskGroup` 保证一个工作任务异常时取消其余任务，避免生产者永远等待满队列。异常通过 `ExceptionGroup` 传播，CLI 返回 1。

此训练项目尚未引入生产级日志格式协商、超长行限制、文件轮转、敏感内容脱敏、任务超时策略；这些属于后续工程扩展。

## 验收规则

参考实现在助手环境通过检查，不代表你已掌握。你需要在自己的机器跑通、提交输出，并独立完成练习。修改生产逻辑后重新运行 pytest 和 mypy；不能靠删测试或加 `Any` 绕过验收。
