# llmwiki 优化 Spec（2026-07）

> Status: **Approved for implementation**（2026-07-24 用户确认全部 10 项）· 基线 v1.1.1
> 依据：8 个直接竞品实测对比 + Karpathy LLM-Wiki v1/v2 gist（完整对比报告见 pj_discovry/.claude/artifacts/llmwiki-optimization-spec.html）

## 1 背景

llmwiki 是 Karpathy LLM-Wiki 模式（2026-04）的工程化实现，独有四大资产：golden eval 门禁（零 LLM P/R + 诚实探针）、三档所有权升级契约、零依赖确定性工具链、诚实协议（纠偏区/0-token 拒答/降级链）——8 个直接竞品（karpathy-llm-wiki 1.6k★ / obsidian-wiki 3.0k★ / llm-wiki-agent 3.3k★ / nvk 879★ / jackwener 91★ / swarmvault 627★ 等）均不具备。

对照竞品与 LLM-Wiki-v2 生产经验，差距集中在：检索规模（grep-only；v2 经验 index.md 过 100-200 页失效，孵化实例已 600+ 页）、捕获自动化（口头 W-CAP-1 vs hooks；claude-mem 88k★ 证明需求）、图谱通道（无派生反链/孤立页分析）、分发摩擦（clone+init vs npx add-skill / pip 一行）、生命周期（无 supersession lineage）、治理（ingest 无脱敏扫描）。

## 2 目标 / 非目标

**目标**：在零第三方依赖、确定性、三档所有权不变式内补齐上述六块；每项过 golden 门禁（knowledge/ 基线 P 1.000 / R 0.958 不回退）。

**非目标（拒绝清单）**：
- 向量检索进核心（x- 扩展逃生舱留给实例）
- confidence 分数 / 遗忘曲线 / 访问衰减（不确定状态机，破坏可审计；Karpathy 原版同样反对）
- LLM 打分器进 eval（保零 LLM 确定性）
- 语义推断边（图谱只做确定性 wikilink 解析）
- SaaS / 服务端 / 跨实例自动同步（既有边界）

## 3 需求（可验收）

- **R1** 关键词不确定时有排名检索入口；keyword-miss golden 题 hit@3 全中而 grep 基线漏检
- **R2** 任意页反链可查；孤立页被 lint 捕获
- **R3** Claude Code 会话产出可零口头成本落 inbox（opt-in hooks）
- **R4** 新用户 ≤2 条命令装好；embedded 冷启动 ≤15 分钟到首批 10 页
- **R5** supersedes 关系机器可查；查询命中旧版自动跟到最新
- **R6** followups 待读资源/未解问题有出口（research 闭环）
- **R7** 非 skills 宿主可经 MCP 消费 wiki
- **R8** 含密钥的源进 wiki 前被拦截或遮蔽

## 4 设计（10 个工作流，S1-S10）

### S1 排名检索 [P0 · R1]
证据：v2 "index.md breaks past 100-200 pages, hybrid search"；jackwener BM25+CJK；swarmvault SQLite FTS。
设计：build_index.py 增派生 site/agent/search-index.json（倒排 + 字段权重 title/aliases×3、description×2、headings×1.5、body×1；中文 bigram + 英文小写化）；新 tools/search.py "query" [--k 8] [--json] → slug/score/description/token 预估；_map 决策表加行「关键词不确定 → search.py」；档位表登记。确定性 tie-break：score desc, slug asc。
约束：派生物单源（W-IDX-1）；工具只写 site/（W-ARCH-2）；纯 stdlib。
验收：同输入两次 build 字节一致；evals 增 keyword-miss 题型 ≥3 题 hit@3 全中；run_ci +≥6 断言；golden 不回退。
涉及：tools/build_index.py、tools/search.py（新）、tools/lib/fm.py、templates/wiki/_map、framework/RULES.md（新 W-IDX-3）、evals/、tests/。

### S2 链接图谱派生 [P0 · R2]
证据：llm-wiki-agent 图谱双通道；jackwener 社区/中心/孤立分析；swarmvault 图优先。
设计：build_index 派生 site/agent/graph.json（确定性 wikilink 边表）+ wiki/backlinks.md（每页反链，generated 标记）；lint 新增孤立页警告（无入链非 meta 页）与集线器提示。不做语义推断边。
验收：hello-wiki fixture 断言反链正确 + 孤立页告警；字节确定性。
涉及：tools/build_index.py、tools/lint_wiki.py、framework/RULES.md（W-IDX-4 / W-LNT-4）、tests/hello-wiki。

### S3 捕获自动化 hooks [P0 · R3]
证据：claude-mem 88k★；Anthropic Remember 官方插件；claude-memory-compiler（SessionEnd + pre-compaction）；v2 "bookkeeping 必须全自动，否则人们放弃 wiki"。
设计：extras/hooks/：capture_draft.py（SessionEnd/Stop → 起草 raw/inbox/<date>-session-draft.md，frontmatter kind:draft，绝不直写 wiki/）+ boot_reminder.py（SessionStart → 注入「先读 wiki/_map.md」）+ settings.json 配置片段文档。opt-in，不进 frozen 核心。
约束：投递≠整合（W-CAP-1 语义保留）；写 raw/ 在白名单内；宿主特定物一律 extras/。
验收：脚本纯 stdlib；e2e 手测清单过；docs/hooks.md；lint 对 draft 不误报。
涉及：extras/hooks/*（新）、docs/hooks.md（新）、CLAUDE.template.md 条件模块。

### S4 分发三件套 [P1 · R4]
证据：karpathy-llm-wiki 靠 npx add-skill 三个月 1.6k★；obsidian-wiki pip 一行 3.0k★；agentskills.io 成事实标准；llmwiki 0★。
设计：(a) add-skill 兼容布局使 npx add-skill Cy4nLiang/llmwiki 可装向导 skill；(b) Claude Code plugin 化（.claude-plugin/marketplace.json）支持 /plugin install；(c) README 增 60 秒 quickstart + 竞品对比表。分发壳只调用 init_render（确定性渲染不破），版本随 framework/VERSION。
实施偏离（2026-07-25 回写）：本项**新增了 W-DIST-1**（分发壳单源同步：version 恒等于 framework/VERSION、skills 只指向仓内既存 .claude/skills、meta 档永不入实例），由 run_ci phase_dist 机检；原规划估计「S4 无新规则」失准，规则总表因此 30→31。
验收：全新目录 ≤2 条命令到首次 ingest；两条安装路径 e2e。

### S5 冷启动 bootstrap [P1 · R4]
证据：deepwiki-open 17.4k★ 证明 repo 自动首建需求；README 自认冷启动净开销。
设计：tools/bootstrap_scan.py（只读扫 README/docs/**/ADR/CHANGELOG/git log 决策词 → state/bootstrap-candidates.json 候选+token 预估）+ .claude/skills/wiki-bootstrap（用户勾选 → 批量 light ingest → followups 登记待晋升）。工具只读仓库+写 state/；agent 走标准 ingest。
验收：对 llmwiki 自身跑出 ≥10 候选；样例 repo 冷启动 ≤15 分钟到 10 页（dogfood 计时入 log）。

### S6 supersession 生命周期 lite [P1 · R5]
证据：v2 supersession（"version control for knowledge"）；graphiti bi-temporal；现有演进/对比/⚠️ 三分无 lineage 字段。
设计：frontmatter 可选 supersedes:/superseded_by: 双向；lint 校验双向一致 + 被替代页横幅；contradictions.md 派生按 lineage 分组演进链；查询协议：命中 superseded 页必须跟到最新。明确不做 confidence/衰减。
验收：lint fixture（W-ING-5）；模板与规则文档更新；派生分组正确。

### S7 research op [P2 · R6]
证据：nvk thesis-driven research op；v2 crystallization；followups 目前只进不出。
设计：.claude/skills/wiki-research：读 followups 选题 → 宿主 web 工具调研 → manual 快照进 raw/（adapter:"manual"，W-SEC-1 不可信标注）→ 标准 ingest → followups 勾销。网络在 agent 侧，工具链保持离线。
验收：一条 followup 端到端闭环；源页 provenance 完整。

### S8 MCP server [P2 · R7]
证据：swarmvault mcp；memory-bank-mcp 915★；ConPort 764★；basic-memory 3.5k★——MCP 是跨宿主通用接口。
设计：tools/mcp_server.py 纯 stdlib JSON-RPC 2.0/stdio，最小面 4 工具：wiki_map（路由页+档位）、wiki_search（复用 S1）、wiki_page（slug, mode=tldr|full, max_tokens）、wiki_capture（→raw/inbox）。响应带 token 预估，尊重档位。协议版本钉死入 UPGRADING。
验收：MCP inspector 握手+4 工具可调；第二宿主 e2e；run_ci 协议单测。

### S9 ingest 脱敏扫描 [P1 · R8]
证据：v2 "filter on ingest：API keys/credentials/PII"；现有 W-SEC-2 只管 config 不管内容。
设计：tools/lib/secscan.py（stdlib 正则集：AWS/GH token、私钥块、常见凭证形态）挂 lint + ingest 前置；命中 → 拒绝/遮蔽 + Processing Notes 标注；白名单机制控误报。新 W-SEC-3。
验收：含假 token fixture 被拦；白名单豁免路径可用。

### S10 团队模式 RFC [P2 · RFC-only]
证据：teamspwk 团队知识卡；TencentDB-Agent-Memory 9.2k★（团队记忆枢纽）；v2 mesh sync / shared-private scoping。
设计：docs/rfc-team-mode.md：sources append-only 天然可并；聚合页 PR 三方合并（复用升级引擎思路）；页面所有权清单；CI 门禁（PR 上跑 lint+golden 的 GitHub Action 配方）；shared/private 分区（peers 延伸）。不动 v1 单写者语义。
验收：RFC 合入 + 本仓 CI 配方跑绿。

## 5 里程碑

- **M1 v1.2.0 检索与图谱**：S1+S2+S9（纯派生物+lint，零行为风险）
- **M2 v1.3.0 采集与分发**：S3+S4+S5
- **M3 v1.4.0 生命周期与外延**：S6+S7+S8
- **M4 RFC**：S10

## 6 横切验收（每个 S 项通用）

- framework/RULES.md 登记新 W-* 规则；tests/run_ci.py 断言只增不减且全绿；framework/UPGRADING.md 迁移条目；gen_manifest.py 重生成；semver MINOR
- knowledge/ dogfood golden P/R 与 tok/题不回退（W-UPG-2）
- 新工具一律：纯 stdlib、确定性（同输入字节一致）、--json 机器口径

## 7 风险

- 范围膨胀 vs 极简哲学 → 拒绝清单钉死；每项必须映射 R1-R8，映射不上就砍
- BM25 中文 bigram 效果 → golden keyword-miss 题实测裁决
- hooks 宿主锁定 → 全部进 extras/，缺席时协议 100% 可用
- MCP 维护成本 → 钉死最小面（4 工具）+ 协议版本入 UPGRADING
- 0★ 分发冷启动是营销问题 → S4 附 README 对比表与 quickstart，但 star 增长不作验收项
