# AI Agent 开发工程师转型路线图

> For: 一位有 C/C++、Qt、工业软件与设备通信背景的工程师，目标是转成 **AI Agent 开发工程师**（方向 A：LLM 应用与 agent workflow 开发 — RAG、tool calling、multi-agent）。
> Timeline assumption: 约 6 个月，每天可投入 1.5–2.5 小时。这个节奏可调，关键是每个阶段的验收标准，而不是日历。
> Version snapshot: 2026 年 10 月。Fast-moving lines（LangGraph、DeepEval、vLLM）动手前 recheck 一次版本。

## How to use this handbook

1. **Why first.** 每个阶段先讲心智模型，再讲 API。Agent 开发的大部分 bug 都来自错误的心智模型，不是拼写错误。
2. **Framework last.** 先手写核心 loop（ReAct、RAG pipeline），再用框架。You already know this discipline from bare-metal work — 框架是加速器，不是拐杖。
3. **Bug experiments are mandatory.** 每个阶段列了必做的破坏性实验。An agent engineer who can't describe failure modes is an interview red flag.
4. **Eval from day one.** 从 Phase 2 起，每个项目旁边必须有一个 eval harness。2026 年的共识：evaluation 是 agent 工程师和 prompt 玩家之间最大的分水岭。

## Ecosystem snapshot (2026-10, verified)

| Layer | Default choice | Notes |
|---|---|---|
| Agent framework | **LangGraph** (Python 1.2.12) | Production standard, graph-based. LangChain v1 LTS; 0.3/0.4 EOL Dec 2026 |
| RAG framework | LlamaIndex 0.14.25 | 已 reposition 为 agentic document/OCR platform；Workflows 1.0 |
| Lightweight SDK | OpenAI Agents SDK 0.23.1 | Still 0.x；Swarm 已被取代 |
| Multi-agent proto | CrewAI 1.15.25 (fast prototype) / LangGraph supervisor (production) | AutoGen 已死 → Microsoft Agent Framework 1.0 |
| Embeddings (self-host) | bge-m3 / Qwen3-Embedding | Qwen3 是 2026 开源质量跃升最大的一家 |
| Embeddings (API) | OpenAI text-embedding-3-small | 开源与闭源差距是有史以来最小的（~1–2 MTEB points） |
| Vector DB (self-host) | **Qdrant 1.19.2** | Rust, Apache 2.0；1.19 统一为 Query API |
| Vector DB (on Postgres) | pgvector 0.8.7 | <10M vectors 的默认选择；**注意 CVE-2026-103484，promptly upgrade** |
| Reranker | bge-reranker-v2-m3 (open) / Cohere Rerank 3.5 (API) | Pattern: bi-encoder top-50/100 → cross-encoder rerank top-10/20 |
| Eval (OSS) | **DeepEval 4.2.x** | 2026 momentum leader；Ragas 0.4.3 已停滞（且有 CVE-2026-6587） |
| Tracing | LangSmith / Langfuse | LangSmith 2026-07 改 seat-based pricing；Langfuse 被 ClickHouse 收购 |
| Local inference | Ollama 0.40.3 | vLLM 0.31.0 是生产级 GPU serving；**30+ 安全公告（2026-09/10），保持更新** |
| Tool standard | **MCP** (Python SDK 2.0, Sept 2026, BREAKING) | langchain-mcp-adapters 0.3.2 仍 pin `mcp<2.0.0`，升级前检查兼容性 |
| Agent-to-agent | A2A | Cross-framework 通信标准，知道即可 |
| Interface | **OpenAI-compatible `/v1` API** | De facto 标准：Ollama、vLLM、llama-server 全都实现，换 base URL 即可切换 |

## Your unfair advantages (and the real gaps)

What transfers directly:

| 你已有的 | 在 agent 开发里的对应 |
|---|---|
| 工业协议设计（RS-485/CAN/ARINC 429） | Tool schema 设计：边界条件、失败模式、超时重试 — 同一套 discipline |
| Qt 事件循环 / 多线程调试 | Agent loop 的状态机思维、asyncio 并发、死锁/竞态直觉 |
| Linux 系统编程 | 部署、Docker、私有化部署（国内面试高频：私有化部署、数据隔离） |
| 调真实硬件的 bug | Agent failure mode 分析：99% 的 agent 面试问题本质都是"你怎么 debug 一个不确定系统" |
| Rust 目标 | Qdrant 就是 Rust 写的；agent infra 里性能敏感部分永远缺 Rust 人 |

Honest gaps to close:

1. **Python 必须到独立工程水平。** Agent 生态是 Python-first（70.8% 的岗位 mandatory）。不是"会写脚本"，是 typing、asyncio、packaging、testing 全套。
2. **LLM 那一层对你是全新的。** Embeddings、retrieval、agent loop 的失败心智模型 — 需要重建一套 debug 直觉。
3. **Eval/可观测性。** 这是 2026 年面试的第一 differentiator，也是你最容易和别人拉开差距的地方 — 因为你本来就懂"怎么证明一个系统是对的"。

---

## Phase 0 — Python 工程能力 (Weeks 1–3)

**Why:** 你不需要"学 Python 语法"，你需要的是把 C++ 的工程直觉平移到 Python。The failure mode here is writing C++ in Python — 能跑，但没人愿意维护，面试一眼看穿。

**Key concepts:**
- Type system: `typing` / `mypy` strict mode。对比 C++ 的类型系统：Python 的类型是渐进式的，理解 `Any` 的传染性。
- asyncio: 对比 Qt event loop — 同样是"不要阻塞 loop 线程"，但 Python 的 `await` 点是显式的。理解 `asyncio.gather`、task 取消、以及"为什么 CPU-bound 任务不能直接 await"。
- Packaging: `uv`（2026 年标准）+ `pyproject.toml`。对比 CMake 思维：依赖锁定（`uv.lock`）就是你的 vcpkg manifest。
- Testing: `pytest` + fixtures。对比 GoogleTest：fixture 是 RAII 的动态版。
- Data: `pydantic` — 这是 agent 开发的 schema 基石（tool schemas、structured output 全靠它），必须熟。

**Hands-on project:** 写一个异步日志分析 CLI：读取一个大的文本日志文件（自己生成，含时间戳和多级别），async 并发解析，pydantic 建模，输出统计报告。要求：`mypy --strict` 干净、`pytest` 覆盖核心逻辑、`uv` 打包。

**Bug experiments (必做):**
1. 在 async 函数里调一个 blocking 的 `time.sleep(5)`，观察整个 loop 卡死 — 然后换成 `asyncio.to_thread`。理解"阻塞 loop"的精确含义。
2. 可变默认参数 `def f(x=[])` 的经典坑 — 写一个复现，然后解释为什么 C++ 没有这个问题（对象生命周期语义不同）。
3. pydantic v2 的 validation error 长什么样 — 故意传错类型，读懂错误信息，因为 agent tool 调用失败时你天天看这个。

**Acceptance:** `uv run pytest` 全绿；`mypy --strict` 零错误；能向别人解释 GIL 在 I/O-bound vs CPU-bound 场景下的实际影响（不说教科书定义）。

**Suggested duration:** 3 周，每天 1.5h。

---
## Phase 1 — LLM 基础：tokens、context、structured output (Weeks 4–6)

**Why:** 所有 agent 的诡异行为，最终都能追溯到三件事：tokenization、context window 的物理限制、以及"LLM 是概率模型"这个事实。If you don't internalize these, every agent bug will look like magic. 你调过硬件 — 你知道"先理解物理层，再谈协议"的道理，LLM 也一样。

**Key concepts:**
- Tokenization: 用 `tiktoken` 亲手算 token。理解"1 token ≈ 0.75 英文词"只是均值，中文和代码的 token 密度完全不同。**Cost 和 context 预算都按 token 算，不按字符算。**
- Context window vs KV cache: context window 是"标称"，KV cache 是"物理"。为什么 128K context 的模型在 100K 输入时变慢、变蠢 — attention 是 O(n²)，KV cache 吃显存。这是所有"long context 评测很好，生产很烂"的根因。
- Sampling: temperature / top-p 到底在控制什么（logit 分布的形状）。Debug 时 temperature=0 是你的示波器：先排除随机性，再谈逻辑。
- Structured output: JSON schema constrained decoding。理解"模型输出 JSON"和"模型被强制只能输出合法 JSON"是两回事 — 后者是推理时的约束，不是 prompt 技巧。
- Prompt design vs fine-tuning: 2026 年市场数据 — **84.6% 的 AI-first 岗位根本不提 fine-tuning**。你的方向是 integrator，不是 trainer。知道 fine-tuning 存在、知道什么时候不该用，就够了。

**Hands-on project:** 一个 streaming chat CLI：
- 用 OpenAI Python SDK，对着 **OpenAI-compatible API** 写（先接云端 API，再把 base URL 换成 `http://localhost:11434/v1` 对 Ollama — 亲手验证"换 base URL 即可切换"这个 2026 年事实）。
- 本地跑 `ollama pull qwen3:30b` 或 `gpt-oss:20b`（单机 24GB 显存的 2026 默认选择），对比云端和本地的延迟/质量/成本。
- 实现：streaming 输出、token 用量统计（每次请求打印 input/output tokens 和估算成本）、structured output（用 JSON schema 约束返回一个 task 对象）。

**Bug experiments (必做):**
1. 故意塞超过 context window 的输入，观察不同后端的失败模式：API 报 400？Ollama 静默截断？**生产事故里最常见的就是没人处理这个。**
2. temperature=1.0 跑同一个 structured extraction 10 次，统计 JSON 合法率；再 temperature=0 跑 10 次。亲手感受随机性。
3. 让模型数 token："这段文本有多少 token？" — 它会错。理解为什么（模型看不到自己的 tokenizer），以及为什么你必须用 `tiktoken` 在代码侧算。

**Acceptance:** 能准确说出你项目的 $/1K tokens 成本和 p50 延迟；能解释 KV cache 为什么让长 context 又慢又贵；CLI 在云端和本地后端之间切换只需要改一个环境变量。

**Suggested duration:** 3 周。

---

## Phase 2 — RAG：检索是工程，不是魔法 (Weeks 7–11)

**Why:** RAG 是 agent 开发里"看起来最简单、生产最容易翻车"的一层。2026 年的共识已经很清楚：retrieval failures 是有 taxonomy 的（chunking、embedding、ranking、context 组装），每一类都有对应的工程解法。This is the phase where your systems thinking pays off the most.

**Key concepts:**
- Embeddings: 向量是什么（语义相似度的压缩表示）。知道 bge-m3（dense+sparse+multi-vector 三合一）和 Qwen3-Embedding 的定位就行，不需要读论文。
- Chunking 策略（2026 consensus）: baseline 是 recursive split ~512 tokens / 10–20% overlap。但知道两个 2026 年的修正：**overlap 不再是免费午餐**（Jan 2026 study：测不出收益，还增加索引成本 — 只有 eval 证明 boundary split 是问题时才加）；structure-aware chunking（按标题/代码/表格切）是最便宜的有效手段。
- 进阶（按需）: **contextual retrieval**（每 chunk 加 50–100 token 的 LLM 生成 situating context，retrieval failure -35~49%，代价是一次 LLM 调用）；late chunking（先 embed 整篇再 pool，便宜，无 LLM 调用）；parent-child retrieval（小 chunk 匹配，大 chunk 给 context）。
- Hybrid search: dense + sparse (BM25) 用 RRF (k=60) 融合 — 2026 标准模式。
- Rerank: bi-encoder 取 top-50/100 → cross-encoder rerank 取 top-10/20（+3–8 nDCG@10，+50ms–1s 延迟）。这是 latency/quality trade-off 的经典案例，面试必问。
- Vector DB: **Qdrant**（Docker 自托管，1.19 起统一 Query API）或 **pgvector**（已有 Postgres 时）。Chroma 只适合原型。Pinecone 是 managed。
- **Eval（核心）:** 从第一个 RAG 原型起就建 golden dataset。用 **DeepEval**（pytest 风格）。关键指标：faithfulness（答案是否被 context 支持）、context precision/recall。记住 2026 年的 shift：**trajectory > output** — 对 agent 要评 tool 选择、参数正确性、错误恢复，而不只看最终答案。

**Hands-on project:** 给自己的技术笔记做一个 docs Q&A：
1. 收集 ~50–100 篇 Markdown 笔记（就用你过去的学习材料），ingest pipeline：parse → chunk（做 3 种 chunking 策略的对比实验）→ embed（bge-m3 本地）→ Qdrant。
2. 实现 hybrid search + rerank，对比"纯 dense" vs "hybrid+rerank" 在你的 golden dataset 上的 faithfulness 和 context recall。
3. 写 eval harness：20–30 个问答对（自己写 golden answers），`deepeval test run` 进 CI（GitHub Actions 跑都行）。**Prompt 或 chunking 策略一改，eval 分数 diff 可见 — "a prompt change is a diff you can review"。**

**Bug experiments (必做):**
1. embedding 维度 mismatch：换一个 embedding 模型但不重建索引，看 Qdrant 报什么错 — 理解"索引和模型是绑定的"。
2. chunk boundary 切断关键信息：构造一个答案横跨两个 chunk 的 case，看 retrieval 失败，然后用 parent-child 或 contextual retrieval 修。
3. top-k 设太大（k=50 全塞进 context）：观察答案质量下降和成本/延迟上升 — 亲手验证"more context ≠ better"。

**Acceptance:** 有一个带 eval 分数的 RAG 系统；能说出你的 chunking 策略为什么是这个参数（有 eval 数据支撑，不是抄的）；golden dataset ≥ 20 条；CI 能跑 eval。

**Suggested duration:** 5 周（这是含金量最高的一段，值得花时间）。

---
## Phase 3 — Tool calling 与 agent loop：先手写，再用框架 (Weeks 12–16)

**Why:** 这是整个转型里最关键的阶段，也是你最容易建立优势的地方。**先不要碰 LangGraph。** 手写一个 ReAct loop（~150 行 Python），你会亲手遇到所有生产问题：loop 停不下来、tool 参数幻觉、context 爆炸、错误恢复。框架只是把这些问题的解法打包了 — 没亲手疼过，用框架也只是调包侠。

**Key concepts:**
- Function calling 的本质：模型输出的是"想调哪个 tool、带什么参数"的结构化意图，**执行是你的代码的事**。Schema（pydantic）就是你和模型之间的"协议" — 对比你写过的通信协议：字段定义、校验、版本，这套直觉直接复用。
- ReAct loop: Thought → Action → Observation 的循环。理解"agent = while loop + LLM + tools + state"，去魅。
- Plan-and-execute: 先规划再执行，适合多步任务。理解它和 ReAct 的 trade-off（延迟 vs 可控性）。
- Context 管理：loop 跑起来 context 只增不减。策略：observation 截断/摘要、只保留最近 N 步、compaction。这是生产 agent 和 demo 的分水岭。
- 错误恢复：tool 抛异常时怎么办？重试（backoff）、降级、还是停下来问人（human-in-the-loop）。**2026 年面试必问："你的 agent 出错时发生什么？"**
- 成本护栏：max iterations、每步 token 上限、单次任务成本上限。没有护栏的 agent = 无限烧钱的 while(true)。

**Hands-on project:** 手写一个文件操作 agent（no framework）：
- Tools: `read_file`、`write_file`、`list_dir`、`web_search`（用免费 API 或简单 HTTP）、`run_shell`（加 allowlist，安全！）。
- 实现 ReAct loop：system prompt 定义 tool schemas（pydantic → JSON schema）、解析模型输出、执行 tool、把 observation 喂回去、loop 直到模型说 done 或达到 max_iterations。
- 必须实现：max_iterations 护栏、每步 token 计数、tool 错误重试（exponential backoff）、human approval（`run_shell` 和 `write_file` 执行前打印 diff 等用户确认 — 这是 guardrail 的雏形）。
- 任务示例："把这个目录下的所有 Markdown 笔记按主题整理成索引文件"。

**Bug experiments (必做):**
1. 去掉 max_iterations，给一个无解任务，看它烧掉多少 token 才停（设个硬上限，别真烧光）。理解为什么护栏是 non-optional。
2. tool schema 里故意留一个 ambiguous 的字段描述，看模型传错参数的概率 — 然后改写描述，看失败率变化。**Tool design 是 prompt engineering 的硬核版。**
3. 跑 20 步以上的任务，观察 context 增长曲线，然后实现 observation 摘要，对比 token 用量。亲手画出这条曲线。

**Acceptance:** 手写 loop 能稳定完成 3 个不同难度的文件任务；能说出你的 loop 在哪一步可能无限循环、你是怎么防的；有 token/cost 日志。

**Suggested duration:** 5 周。

---

## Phase 4 — 框架与多 agent：LangGraph + MCP (Weeks 17–21)

**Why:** 手写 loop 之后，你才有资格评价框架。2026 年的 production 标准是 **graph-based**（LangGraph），不是链式调用 — 因为真实 agent  workflow 有分支、循环、人工介入，图才是正确的抽象。MCP 则是 2026 年的 tool 标准：tool 不再是你手写的函数，而是可发现、可复用的协议。

**Key concepts:**
- LangGraph 核心：State（跨节点共享的状态，就是你的"全局结构体"）、Node（一步计算）、Edge（条件跳转）。对比：手写 ReAct loop 的 while 循环 → 图里的 cycle edge。理解 checkpointing（状态持久化，长任务可恢复）和 human-in-the-loop（图可以在任意节点暂停等人）。
- Multi-agent 模式：supervisor（一个 planner 拆任务，分给 worker agents）vs 平级协作。2026 年生产主流是 supervisor。理解什么时候"一个 agent + 好 tools"就够了 — **multi-agent 是成本，不是 feature**。
- MCP (Model Context Protocol): tool 的 USB-C 接口。Server 暴露 tools/resources，client（你的 agent）动态发现。**注意 2026-09 的 MCP Python SDK 2.0 是 BREAKING change**，`langchain-mcp-adapters` 0.3.2 还 pin 着 `mcp<2.0.0` — 动手前检查兼容性，别在版本坑里浪费两天。
- A2A：跨框架 agent 通信标准，知道概念即可。
- LlamaIndex / OpenAI Agents SDK / CrewAI：知道定位（RAG 平台 / 轻量 SDK / 快速原型），主攻 LangGraph 一个。

**Hands-on project (二选一，做深一个):**
- **A. 把 Phase 3 的 agent 用 LangGraph 重写**：state 包含 messages + task context + approval queue；节点：plan → act (tool) → observe → check_done；human approval 做成 interrupt（`interrupt()` 暂停图，等用户确认后 resume）。对比手写版：代码量、可靠性、可观测性。
- **B. MCP 实战**：写一个 MCP server（暴露 3–5 个 tools，比如笔记搜索 + 文件操作），再写一个 LangGraph agent 作为 MCP client 去调用它。验证"换一个兼容的 server，agent 不用改代码"。

**Bug experiments (必做):**
1. LangGraph 里故意让一个 node 抛异常，观察图的行为 — 然后加 retry policy 和 fallback edge。理解"图"比"try/except"多给了你什么。
2. supervisor 模式下让两个 worker 对同一个文件写冲突，看系统怎么处理 — 理解 multi-agent 的状态一致性问题（和你调过多线程资源竞争是同一个味道）。
3. MCP 版本坑：如果装了 SDK 2.0，复现 breaking change 的报错，读懂 migration。

**Acceptance:** LangGraph 版 agent 跑通 Phase 3 的同等任务，且支持中途人工介入和断点恢复；能画出你的图的 state/edge 设计并解释每个 edge 的条件；能说出 supervisor 模式的 3 个真实缺点。

**Suggested duration:** 5 周。

---
## Phase 5 — 生产工程：tracing、eval、guardrails、部署 (Weeks 22–26)

**Why:** Demo 和产品的距离，就是这一章的全部内容。2026 年的市场数据很残酷：97.1% 的 AI 工程岗位是 applied/production，不是 research；面试官问的从来不是"你会调哪个 API"，而是"它挂了的时候你怎么知道、怎么修"。This phase is what turns you from someone who *uses* agents into someone companies *trust* with agents.

**Key concepts — 三层生产管线 (2026 标准):**
1. **Tracing（每请求）**: 每次 LLM 调用的输入/输出、retrieval 结果、tool 调用、延迟、token、成本，按 request 串起来。工具：LangSmith（LangChain-native）或 Langfuse。**LangSmith 2026-07 改为 seat-based pricing**，选型时看成本。
2. **Offline evals（CI）**: 版本化的 golden dataset + 已知好答案，每次改 prompt / 模型 / chunking 策略都跑。工具：**DeepEval**（pytest 风格，50+ metrics）或 promptfoo（2026-03 被 OpenAI 收购，仍是 MIT 开源）。工作流：synthetic inputs → trace → 人工标注/ critique → 失败聚类 → deterministic checks → LLM judge → golden regression → CI gate。
3. **Online monitoring（生产采样）**: 生产流量采样，用同一套 grader 持续打分，drift 告警。生产失败案例回流进 eval dataset — 闭环。
- **LLM-as-judge 的正确用法（2026 consensus）**: 分层，不是一个分数 — 先验证外部 outcome/state，再用 deterministic assertion，最后才用 LLM judge 评主观标准。Judge 要 calibrated：对着 human golden set 校准；bias 控制（position swap、cross-family judging、隐藏模型身份）。
- **Guardrails**: 输入过滤（prompt injection 检测）、输出校验（schema + 内容政策）、human approval（高风险 tool 执行前确认）、成本熔断。2026 年岗位里 security/guardrails 已是 non-optional。
- **成本/延迟优化**：prompt caching、模型路由（简单任务用小模型）、context 瘦身。面试要你报真实数字：$/1K tokens、p50/p95，优化前后的对比。
- **部署**：FastAPI + Docker 是标准；模型 serving 知道 vLLM 的存在和定位（`vllm serve` 暴露 OpenAI-compatible API）；**vLLM 2026-09/10 有 30+ 安全公告 — 生产用必须跟进版本**。国内高频：私有化部署（private cloud）方案要能讲清楚。

**Hands-on project:** 把 Phase 2 或 Phase 4 的项目产品化：
- FastAPI 封装 + Docker Compose（一键 `docker compose up`：app + Qdrant + Ollama 可选）。
- 接入 tracing（Langfuse 自托管版，ClickHouse 收购后依然可用）。
- DeepEval 进 CI：改 prompt 必须过 eval gate 才能 merge。
- 写一份成本/延迟 case study：记录优化前后的真实数字（比如加 rerank 前后的 nDCG@10 vs p95 延迟，加 prompt caching 前后的 $/1K tokens）。
- **Deploy 到公网**（便宜 VPS 就行），拿到一个 live URL。

**Bug experiments (必做):**
1. Prompt injection：构造一个"忽略之前指令"的输入，看你的 guardrail 拦不拦得住 — 然后再加一层 input filter，对比。
2. 把生产流量里一个真实失败 case 加进 golden dataset，看 CI 变红 — 亲手走完"失败回流"闭环。
3. 模拟 API 挂了（mock 抛 500 / 超时）：你的 agent 是重试、降级还是直接崩？把行为写下来 — 这就是面试官要听的答案。

**Acceptance:** 有 live URL；tracing 能看到完整请求链路；CI 里有 eval gate；有一份带真实数字的 cost/latency case study；能讲清楚你的 guardrail 分几层、每层防什么。

**Suggested duration:** 5 周。

---

## 作品集计划 (贯穿 Phase 2–5)

市场共识（2026）：**3–5 个深度 eval 的项目 + live URL**，胜过 10 个 tutorial clone。按这个优先级：

1. **Deployed AI product**（Phase 5 产物）: 真实用户可用 — auth、persistence、streaming、可见的错误处理、working URL。这是含金量最高的。
2. **Eval harness**（Phase 2–3 产物）: golden dataset + assertion + LLM judge，prompt 一改分数 diff 可见。和项目放同一个 repo。
3. **Cost/latency case study**（Phase 5）: 真实数字，before/after。
4. **Differentiator**（二选一）: LangGraph supervisor 多 agent 团队，或 MCP-powered coding agent — 带 retry/backoff、成本上限、guardrails、tracing。**"puts you past 90% of portfolios"。**

Repo 要求：README 讲清楚架构图、失败模式、eval 分数、成本数字。面试官看 README 的时间比看代码多。

## 面试准备清单

2026 年 agent 岗位面试真正问的东西（准备好用你自己的项目回答）：

- "你的 agent 最大的 failure mode 是什么？你怎么发现的？" → 用 Phase 3 的 bug 实验回答。
- "你怎么测成本？p95 延迟多少？" → 用 Phase 5 的 case study 数字回答。
- "Human approval 流程怎么设计的？什么操作需要批？" → Phase 3/4 的 approval queue。
- "API 挂了会发生什么？" → Phase 5 的 bug 实验 3。
- "你怎么防止 prompt injection？" → Phase 5 的 guardrail 分层。
- "为什么选 LangGraph 而不是直接调 API？" → Phase 4 的手写 vs 框架对比。
- 国内加试：私有化部署方案、幻觉治理、数据隔离。**"没用过 eval 框架、讲不清 failure mode"是明确的 red flag。**

## 你的 Rust 线怎么放

别丢。Qdrant 是 Rust 写的，vLLM 的性能瓶颈在 infra 层 — agent infra 里永远缺懂系统的人。建议：转型主攻 Python/agent，但保留 10–15% 时间给 Rust（比如给 Qdrant 或 MCP Rust 生态贡献一个小 PR，就是极强的 portfolio 信号：**既懂 agent 又懂 infra 的人，2026 年很少**）。

## 附：关键链接

- LangChain docs: https://docs.langchain.com
- LlamaIndex: https://developers.llamaindex.ai/
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Microsoft Agent Framework: https://learn.microsoft.com/en-us/agent-framework/
- Qdrant docs: https://qdrant.tech/documentation/
- pgvector: https://github.com/pgvector/pgvector
- DeepEval: https://deepeval.com/docs/introduction
- Ragas: https://docs.ragas.io/en/stable/
- MTEB leaderboard: https://huggingface.co/spaces/mteb/leaderboard
- vLLM docs: https://docs.vllm.ai/en/latest
- Ollama releases: https://github.com/ollama/ollama/releases

---
*Built 2026-10-13. Ecosystem versions verified against Sept–Oct 2026 sources; recheck fast-moving lines (LangGraph, DeepEval, vLLM, MCP SDK) before you build.*
