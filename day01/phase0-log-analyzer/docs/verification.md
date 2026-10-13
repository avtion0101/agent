# 参考项目实际验证记录

日期：2026-10-13。以下是助手 Linux 环境的真实结果，**不代表用户本机已运行或学习验收通过**。

## 环境与版本

| 工具 | 实际版本 |
|---|---|
| Python | 3.12.14 |
| uv | 0.12.23 |
| Pydantic | 2.14.1 |
| pytest | 9.1.1 |
| mypy | 1.20.2 |

这些是本次实际解析和运行版本，不宣称是整个生态的最新或唯一选择。运行依赖记录在 `uv.lock`。构建后端是 Hatchling，构建隔离依赖由 pyproject 约束，未在 uv.lock 中逐项锁住；若将来要求构建过程也完全固定，需另外固定构建工具链。

## 检查结果

| 命令 | 实际结果 |
|---|---|
| `uv sync --python 3.12` | 隔离环境同步成功 |
| `uv run --locked pytest` | 23 passed in 0.62s |
| `uv run --locked mypy --strict` | Success: no issues found in 10 source files |
| `uv build` | 成功生成 sdist 与 wheel |
| 生成并分析 10000 行 | 9897 合法、103 非法；统计不变量正确 |
| 生成并分析 1000000 行 | 989691 合法、10309 非法；统计不变量正确 |

首次同步在 README 尚未写入时失败，原因是构建配置引用了不存在的 README；补齐文件后重新同步成功。百万行的第一次测量命令因当前环境没有 `/usr/bin/time` 未执行分析；改用 Python subprocess、perf_counter、resource 完成测量。这两个工具准备问题已解决，不记作用户学习错误。

## 10000 行样例

- ERROR：500；INFO：7423；DEBUG：1037；WARNING：937。
- 均值：50.323042336061384 ms；最大值：99.995 ms。
- 程序内部分析时间：0.03785365199996704 s。
- 前五条坏行号：97、194、291、388、485。

原始报告保存为 `reports/report.json`。计数取决于固定输入/随机种子，耗时取决于当前机器，不能要求用户机器得到相同耗时。

## 百万行实际测量

配置：2 个 worker，batch_size=1000；本地模拟文件；单次运行。

| 项目 | 数值 |
|---|---:|
| CLI 墙钟时间（包括 uv 与进程启动） | 4.404993528999967 s |
| 分析函数内部耗时 | 4.264126506000025 s |
| 子进程峰值 RSS（Linux RUSAGE_CHILDREN） | 34676 KiB |
| 子进程用户 CPU 时间 | 4.228706 s |
| 子进程系统 CPU 时间 | 0.225508 s |

RSS 指 Linux `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss`，不是同时存活所有进程内存的总和。这是功能和大文件处理的一次观察，不是生产基准，也没有据此宣称多个 worker 优于一个。

原始结果：`reports/large-report.json` 与 `reports/benchmark.json`。百万行输入不随包附带，可用固定种子生成器重建。

## 故障实验的真实输出

事件循环实验：每分支 sleep 5 秒，心跳间隔目标 0.05 秒。

```text
blocking     heartbeat_count=  5 max_gap=5.000s
async-sleep  heartbeat_count=104 max_gap=0.050s
thread       heartbeat_count=104 max_gap=0.052s
```

可变默认参数实验：

```text
broken: ['first', 'second'] ['first', 'second'] same object: True
fixed:  ['first'] ['second'] same object: False
```

Pydantic 校验实验复现三个错误：

```text
('level',) literal_error
('latency_ms',) float_type
('unknown_field',) extra_forbidden
```

## 验证范围

测试涵盖正常解析、消息内分隔符、非法字段、NaN/Infinity、空文件/空行、已知统计、不同 worker 的统计一致性、坏行示例上限与排序、缺失文件、无效配置、消费者异常时任务组退出、可复现生成器、CLI 报告写入与失败退出码。

未验证：用户 Windows/macOS、特殊设备文件、强取消协议、超长行和恶意输入的资源限制、生产文件轮转、CPU 线程/进程性能优劣。后续训练按单元补实验，不把未测量内容写成通过。
