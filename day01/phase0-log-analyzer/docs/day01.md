# Phase 0 / Day 1：把文本变成可信的数据

今天的目标：建立能运行的 Python 项目，并理解“解析”和“校验”的区别。你不需要今天就吃透整个并发管线。

## 1. 为什么先练日志分析

Agent 调用工具时，模型可能传错字段、漏传字段或生成不合法参数。你最终需要把一段不可靠的外部数据变成可以执行的内部对象。

日志分析同样经历：原始字符串 → 解析字段 → 明确转换 → schema 校验 → 可信对象 → 统计。这很接近设备通信中“收到字节不代表收到合法报文”的判断。

| 工业通信经验 | 今天的对应概念 |
|---|---|
| 报文格式和字段定义 | 五字段文本协议与 LogEntry |
| 字符串转工程量 | `float(latency)` |
| 范围检查、枚举检查 | 非负延迟、合法级别 |
| 错误帧继续接收 | 坏行计数，但不让整个文件失效 |
| 协议异常与系统异常分开 | 坏行可归档；文件打不开应失败退出 |

## 2. 先把工程运行起来

解压训练包后，在终端进入 `phase0-log-analyzer`，确认你能看到 `pyproject.toml`。

```bash
python --version
uv --version
uv sync --locked
uv run --locked agent-logs generate data/device.log --lines 10000
uv run --locked agent-logs analyze data/device.log --output reports/report.json
uv run --locked pytest
uv run --locked mypy --strict
```

macOS 如果只有 `python3`，第一条改为 `python3 --version`。Windows 如果只配置了 Python Launcher，使用 `py --version`。uv 项目默认指定 3.12；已有 3.13 可以使用 `uv sync --python 3.13 --locked`。不要直接运行 `pip install` 把依赖放入其他环境。

输出必须包含：

```json
{
  "total_lines": 10000,
  "valid_lines": 9897,
  "invalid_lines": 103
}
```

原因：生成器每 97 行注入一个坏行，`10000 // 97 = 103`。其他统计字段也会输出；不要仅凭三个数字就认定所有逻辑正确。

`uv run` 使用项目隔离环境；`pyproject.toml` 描述项目与依赖约束；`uv.lock` 记录已解析依赖；`--locked` 防止命令悄悄改动锁文件。`src` 放可复用业务包，`tests` 放验证，`experiments` 放有意制造错误的程序。

## 3. 读懂 LogEntry

打开 `src/log_analyzer/models.py`：

```python
class LogEntry(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    timestamp: datetime
    level: LogLevel
    component: str = Field(min_length=1)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    message: str = Field(min_length=1)
```

逐条理解：

- `BaseModel` 提供运行时数据校验和序列化。
- `strict=True` 不允许随意把错误类型转换成正确类型；具体细节取决于字段类型与 Python/JSON 输入路径。
- `extra="forbid"` 拒绝没有在协议中声明的字段。
- `frozen=True` 限制模型字段重新赋值，降低对象校验后又被修改的风险；不是所有嵌套可变对象都自动深度不可变。
- `timestamp: datetime` 表示业务层得到时间对象，而不是未经检查的字符串。
- `LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]` 限制级别取值。
- `min_length=1` 拒绝空字符串。解析器还会 `strip`，因此只含空格的组件也会拒绝。
- `ge=0` 要求延迟不小于零；`allow_inf_nan=False` 拒绝 NaN 和无穷大。

类型注解与 Pydantic 不同。普通函数的 `latency: float` 不会自动阻止运行时传入字符串；mypy 在执行前检查代码，Pydantic 在执行时检查数据。两层都需要。

这个训练 schema 不强制时区：`datetime.fromisoformat` 也能接收没有偏移的时间。生成器使用 UTC 偏移，真实设备接入前应明确时区政策，不能悄悄混用。

## 4. 读懂 parse_line

```python
def parse_line(line: str) -> LogEntry:
    fields = [field.strip() for field in line.rstrip("\n").split("|", 4)]
    if len(fields) != 5:
        raise ValueError("expected timestamp | level | component | latency_ms | message")
    timestamp, level, component, latency, message = fields
    return LogEntry.model_validate({
        "timestamp": datetime.fromisoformat(timestamp),
        "level": level,
        "component": component,
        "latency_ms": float(latency),
        "message": message,
    })
```

`line: str` 和 `-> LogEntry` 是输入/输出契约。`rstrip("\n")` 去掉行末换行；`split("|", 4)` 最多切四次，保留消息内部的 `|`；列表推导逐一去掉字段两端空白。

长度检查防止解包时报难理解的异常。`raise` 让调用者决定如何处理失败，不在底层函数直接退出整个进程。

`datetime.fromisoformat` 和 `float` 是**明确转换**：日志协议原本就是文本，转换有规则。`model_validate` 是**校验已转换对象**：范围、级别、额外字段等要符合定义。

失败不能全部 `except Exception: pass`：如果磁盘读取失败、程序本身有 bug，应当有可见的失败路径。`parse_batch` 只把预期的数据错误归档，不能把代码错误吞掉当作一条坏日志。

## 5. 第一项独立练习：错误率

自己创建 `src/log_analyzer/metrics.py`，写：

```python
def error_ratio(error_lines: int, valid_lines: int) -> float:
    ...
```

要求：返回合法日志中 ERROR 的比例，范围 0.0–1.0；`valid_lines == 0` 且 `error_lines == 0` 时返回 0.0；任一计数负数或 ERROR 大于合法行数时抛出 `ValueError`。

这里的 ERROR 是**已经通过 schema 的日志级别**，不是 `invalid_lines`。把“业务错误日志”和“无法解析的坏行”混为一谈，会让监控指标失真。

预期样例：

| 输入 | 结果 |
|---|---|
| `error_ratio(2, 10)` | `0.2` |
| `error_ratio(0, 10)` | `0.0` |
| `error_ratio(10, 10)` | `1.0` |
| `error_ratio(0, 0)` | `0.0` |
| `error_ratio(-1, 10)` | ValueError |
| `error_ratio(11, 10)` | ValueError |
| `error_ratio(1, 0)` | ValueError |

先独立实现，再写 `tests/test_metrics.py`，用 pytest 断言正常值并用 `pytest.raises` 检查异常。最后运行 pytest 和 mypy。不要将输出打印出来就当作测试通过。

### 参考答案：写完再对照

```python
def error_ratio(error_lines: int, valid_lines: int) -> float:
    if error_lines < 0 or valid_lines < 0:
        raise ValueError("counts must be non-negative")
    if error_lines > valid_lines:
        raise ValueError("error_lines cannot exceed valid_lines")
    if valid_lines == 0:
        return 0.0
    return error_lines / valid_lines
```

先检查不变量，再计算。Python `/` 返回浮点结果，不同于 C++ 两个整数相除的截断行为。类型注解没有额外保证运行时输入一定是 int，这里把函数用于内部已知计数；外部接口需要输入校验。

测试参考：

```python
import pytest
from log_analyzer.metrics import error_ratio

@pytest.mark.parametrize("errors,total,expected", [(2,10,0.2),(0,0,0.0),(10,10,1.0)])
def test_ratio(errors: int, total: int, expected: float) -> None:
    assert error_ratio(errors, total) == pytest.approx(expected)

@pytest.mark.parametrize("errors,total", [(-1,10),(11,10),(1,0),(0,-1)])
def test_bad_counts(errors: int, total: int) -> None:
    with pytest.raises(ValueError):
        error_ratio(errors, total)
```

## 6. 三个故障实验

### A. 字段协议不合法

```bash
uv run --locked python experiments/validation_error.py
```

程序故意传入非法级别 TRACE、字符串延迟 fast、额外字段。观察三条错误：

- `loc`：哪个字段或嵌套位置错了。
- `type`：错误类别，可用于程序化区分。
- `msg`：给人阅读的解释。

验收：用自己的话解释这三个字段为什么被拒绝。理解 strict 校验不是“把 fast 尽量猜成数字”。实验捕获了预期异常，因此程序可以正常结束，不代表没有制造错误。

### B. 事件循环被阻塞

```bash
uv run --locked python experiments/blocking_loop.py --seconds 5
```

同一个实验分别运行 `time.sleep(5)`、`await asyncio.sleep(5)`、`await asyncio.to_thread(time.sleep, 5)`；并发心跳每 0.05 秒尝试运行。观察 `max_gap`。

正常预期：blocking 分支会出现接近 5 秒的心跳间隔；其他分支约 0.05 秒，但受系统调度影响，不应要求毫秒级完全相同。三个分支顺序运行，总时长约 15.6 秒。

原因：`time.sleep` 让事件循环线程停在同步调用里；`asyncio.sleep` 注册等待并让出循环；`to_thread` 将阻塞调用放到线程池，协程等待其结果。`await` 不会把任意同步代码变成异步，也不会自动把 CPU 计算移到另一颗核心。

### C. 可变默认参数共享

```bash
uv run --locked python experiments/mutable_default.py
```

`def broken(value: str, items: list[str] = [])` 的默认列表在函数定义时创建，并在后续未提供参数的调用之间复用。第一次返回的列表也会因为第二次调用而改变。`first is second` 为 True。

正确做法：使用 None 作为默认值，在函数体中创建新列表。不能用 `items = items or []` 作为通用替代，因为传入空列表时这会换掉调用者提供的对象。

普通 C++ 值默认参数没有这种定义时创建并复用默认列表的语义，但 static 容器或共享引用也能产生类似跨调用状态。应该解释具体生命周期，不用“某语言绝对没有这个坑”概括。

## 7. 思考题与答案

1. **为什么不直接把全部日志读到一个 list？**
   大文件让内存随文件大小增长；逐批处理使待处理数据受 batch/queue 控制。但组件名无限增长或单行特别长仍会增加内存，所以有界队列不是完整内存安全保证。
2. **为什么 ERROR 日志能是合法数据？**
   协议是否合法和业务状态是否成功是两个维度。合法 ERROR 记录可以用于定位设备故障。
3. **为什么 mypy 没报错，运行时还可能报 ValidationError？**
   静态检查源码类型，不能预测文件里每个字符串的真实内容。
4. **多几个 worker 一定更快吗？**
   不一定。GIL、文件读取速度、线程切换、任务和校验开销都会影响；用相同输入比较数据和时间。
5. **报告的哪些不变量能验证？**
   总行数等于合法加非法；级别计数之和等于合法行数；无合法记录时均值/最大值为 None；同一文件不同 worker 统计一致。
6. **`await` 能让两个操作同时发生吗？**
   单纯连续 await 通常是顺序等待。需要显式建立并发任务；任务是否重叠还取决于是否能让出控制以及所做工作。

## 8. Day 1 提交与通过条件

提交：Python/uv 版本；10000 行报告关键字段；pytest/mypy 输出；自己写的 `metrics.py` 和测试；对解析/校验区别的解释；至少 validation error 实验的三条错误说明。

通过条件：本机运行成功；计数正确；独立函数覆盖非法计数和空输入；类型检查通过；你能解释“合法 ERROR”和“坏行”的区别。仅下载代码或复述参考答案不算通过。

下一单元：函数、模块、异常和独立重写解析器。等本单元有提交证据后推进。
