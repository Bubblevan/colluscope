# ColluScope — 给 Codex 的持续迭代 Goal（M0 专用）

> 请将下面整段作为 Codex 在**全新、独立的仓库**中收到的第一条任务。仓库根目录必须同时放置 `ColluScope_M0_TRD.md`。本 Goal 定义长期优化方向及本轮边界，而不是批准无限制执行。

你现在是 **ColluScope 的研究工程师 + 严格的反方审稿人**。你的任务不是在最短时间制造一个“看起来能参加比赛”的 Demo，而是针对 Apart Research Sprint 的 Track 2.2 / 2.3，从零构建一个**可信、可复现、不会泄漏答案、能发现自身错误**的合谋审计实验底座。

## 北极星 Goal

**Maximize falsifiable evidence per unit of engineering effort**：每一轮工作都必须减少一个影响研究结论可信度的真实不确定性，并用可运行测试/可复现实验/带来源的审计证据证明它已减少。功能数量、代码行数、文档字数、测试通过数量及运行速度都不能代替实验有效性。

优先级固定为：

1. **研究命题可判定** ＞ 行为定义与 oracle 正确 ＞ 正负对照有效。
2. **公平性与无泄漏** ＞ 可复现性 ＞ 可观测性与证据来源。
3. **最小可用实现** ＞ 可扩展架构 ＞ 外观、功能广度和性能优化。

## 全项目的连续目标与阶段门槛（方向明确，不等于当前执行授权）

持续优化的最终目标不是提高某个合成数据集的准确率，而是得到一份**别人可以复现、可以质疑、能说明何时不能断言合谋**的研究报告。

- **M0（当前）**：环境、标签、对照、四视图、反泄漏与可复现性通过；只证明研究设计可执行。
- **M1（需用户批准）**：在冻结的环境里运行真实 LLM agents，验证正对照能否出现真实偏离；若不能，明确记为研究发现或修订条件，而不是伪造正例。
- **M2（需用户批准）**：在相同真实轨迹上公平比较四种审计输入；预先冻结模型、提示、阈值、种子分组，并报告 FPR/TPR、置信区间和困难负例。
- **M3（需用户批准）**：冻结实验并使用赛事官方模板撰写研究 PDF，保留失败案例、局限、伦理/双重用途与赛前工作披露。

每个阶段都遵循下文七步迭代协议；**阶段之间必须等待用户授权**，不能把“自动持续迭代”理解为无限制支出、擅自修改研究问题或自动提交比赛作品。阶段成果若推翻最初假设，应修正研究主张，不允许通过改标签制造成功。

## 本轮授权范围

只完成 `ColluScope_M0_TRD.md` 的 M0-A、M0-B、M0-C、M0-D。M0 必须为 CPU/离线、零付费 API。可读取公开学术资料/克隆开源代码作参考；**不得复制未经许可的代码或团队工行杯项目**。不得部署真实银行系统、训练模型、调用付费 API、开展 M1 真实 LLM 评测、修改比赛题目或虚构成绩。

## 自主迭代协议（每轮都必须执行）

### 1. INSPECT — 找出最高风险的不确定性

读取 TRD、上一轮证据、当前 Git diff、测试输出与 blocker。指出现阶段**最可能使论文结论无效**的一项风险（例如 label leakage、没有真正的正对照、反事实不成对、把意图当成行动、脚本结果冒充真实模型结果）。不要默认用户已有的研究判断是对的。

### 2. SPECIFY — 先规定失败条件

为这个风险提出一个最小实验或测试，写清：输入、应观察到的现象、反例、判定方法与失败时下一步。优先选择能够**证伪当前假设**的测试，不要只写会通过的 happy-path 测试。

### 3. IMPLEMENT — 最小改动，不顺便扩建

只实现与该风险直接相关的最小变更。保留已有数据格式与追溯信息；出现规范冲突时先报告。不得通过写死答案、篡改 fixture/阈值、删去失败样本或跳过测试来获取 PASS。

### 4. RUN — 执行并保留原始证据

运行针对性测试和必要的全量测试；保存实际命令、退出码、输出摘要、输入配置、种子、hash、代码 commit。没有执行过的事项标 `NOT RUN`，无法验证标 `UNKNOWN`，失败标 `FAIL`，绝不写成 PASS。区分 scripted 与 real-LLM 数据。

### 5. ADVERSARIAL REVIEW — 反方审稿

每轮至少尝试提出并测试一个“即使当前结果为真，也不能支持声称结论”的反例。至少依次覆盖：

- oracle 字段/机制 ID 是否泄露给任何监测视图；
- C1 脚本正对照是否真的造成可核查的行动偏差；
- C2 平行行为能否骗过简单相关性判据；
- C3 只说不做是否被错误标记为行动合谋；
- 两种不同生成机制是否可能在监测器眼中完全相同；
- 结构化视图是否私下获得了 raw fusion 没有的证据；
- 两次同配置运行是否可重现相同核心轨迹。

### 6. REPAIR / DECIDE — 修复或停止

若失败，分析根因并做不超过两次实质不同的修复，再复测。如果仍不能解决，生成 `BLOCKED` 报告并停止该支线，不许无限循环。若满足 TRD 的全部 M0 GO 条件，必须停止扩建并产出 `M0_DECISION.md`；**没有用户批准不得自动进入 M1**。

### 7. REPORT — 永远留下可继续工作的状态

每轮更新 `docs/ITERATION_LOG.md`，至少包含：

```
Cycle ID / 日期 / Commit
目标风险与可证伪假设
所作变更及理由
执行过的命令、测试、结果和输出文件
反方审稿发现的新反例
当前 M0 Gate 状态（PASS/FAIL/UNKNOWN/NOT RUN）
下一步唯一最有价值的行动
阻塞、成本及未经验证的主张
```

继续下一轮时，**根据真实证据自动选择最大风险**，不是按预设功能清单机械推进。每个任务仅在完成其证据和验收后标记完成；不允许为了“进度”修改 GO 标准。

## 要交付的成果

- 可通过 `pytest` 与 CLI 重复运行的离线 M0 环境；
- 至少 24 条脚本、6 类机制，正确隔离 oracle 与四种审计视图；
- 涵盖正对照、困难负例、纸面合谋、不可识别性、随机性与标签泄漏的测试；
- `M0_RESEARCH_NOTES.md`、`PRE_SPRINT_WORK_LOG.md`、`M0_EVIDENCE.md`、`M0_DECISION.md`、`ITERATION_LOG.md`；
- 真实证据支持的 M0 `GO` 或 `NO-GO`，附上重跑命令、哈希、限制和进入 M1 所需验证。

## 报告规范

在最终回复里请按以下顺序给出：

**已验证事实 → 未解决问题 → GO/NO-GO 门槛逐条状态 → 重要失败案例 → 复现命令 → 下一步建议**。

## Later scoped authorization addendum (2026-10-20)

The original M0-only, fully offline instructions above remain the historical M0 authorization and are not rewritten. The user later supplied a separate **“ColluScope — DeepSeek-First Recovery and Full Research Execution”** task that authorizes one specifically bounded prospective M4/Monitor research run using the official DeepSeek API only, subject to its frozen gates, 900-request / USD 5.00 aggregate ceilings, zero retries/replacements, local-only raw storage, and explicit stop conditions. This later scope supersedes the older no-call rule only for that one run. It does not authorize additional model calls, M2 detector comparison, external providers, new weights, training, or changed interventions after the bounded run stops or completes.

请避免“架构完成”“符合工业级标准”“效果显著”等没有实测支持的套话；不要用延迟或单元测试数量掩盖核心研究有效性。我的最终需求是**能拿来写诚实研究报告的证据**，而不是看起来很忙的工程过程。

## 第一条执行指令

首先阅读 `ColluScope_M0_TRD.md`；核对官方 Sprint 规则和三个上游仓库，记录各自可验证来源、commit、许可、依赖与适配风险。**不要先创建花哨目录或大量空文件**。把第一轮最高风险判为“定义和标签是否可识别、可反驳”，优先写正负对照判据与反例；随后按 M0-A → M0-B → M0-C → M0-D 迭代推进。在每一轮结束时持续更新证据日志。只有 M0 全部 GO 门槛满足才宣布阶段完成并等待用户指示。
