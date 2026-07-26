# llmwiki — 给每个项目一座 agent 自己维护的说明书库

> v1.4.0 · 纯文件 · 零第三方依赖 · MIT

> **English summary** — the rest of this document is in Chinese.
>
> **What**: llmwiki is a content-free, reusable framework for agent-maintained, compounding knowledge bases ("LLM wiki"): a slotted CLAUDE.md contract, a token-budgeted routing page, frozen page skeletons, stdlib-only deterministic tools, and a day-one golden-eval loop. Drop it into any project — codebase knowledge, ops runbooks, industry intel.
>
> **Why**: agent accuracy is a context problem. Without a repository, every session re-derives what the last one learned, answers version/date questions from parametric memory, and leaves conclusions trapped in chat logs where they never compound.
>
> **How**: clone → say `/wiki-init` in Claude Code (three modes: embedded into an existing repo / greenfield / adopt; rendering is done by a deterministic tool, never hand-written) → drop a note into `raw/inbox/` → say "ingest it". From then on the daily loop is just talking to the agent: capture → sync → ingest → query → lint → golden.
> Since v1.4.0 also: BM25 ranked search alongside grep, a wikilink backlink/graph layer, secret scanning, opt-in Claude Code hooks, a cold-start repo scanner, supersession lineage, a research loop that drains `followups`, and an **MCP stdio server** so non-skills hosts (Claude Desktop / Cursor / Windsurf) can consume the same wiki.
>
> **Proof over promises**: the protocol was measured on the 600+-page production knowledge base that incubated it (59.6K → 7.1K tokens per question, 8/8 honest refusals — external to this repo, not reproducible here) and on the in-repo dogfood instance `knowledge/` (golden baseline P 1.000 / R 0.958, reproducible from `knowledge/evals/`). Instance measurements, not universal claims.

---

## 60 秒上手

**克隆(完整工具链,推荐)—— 两步到首次入库:**

```bash
git clone https://github.com/Cy4nLiang/llmwiki && cd llmwiki
```

在 Claude Code 里说 `/wiki-init`(向导确定性渲染出实例骨架)→ 把第一篇材料丢进 `raw/inbox/` 说「ingest 这篇」。之后日常闭环只是说话:捕获 → sync → ingest → query → lint → golden(详见下方《怎么用》)。

**作为 Claude Code 插件安装(只要三向导):**

```
/plugin marketplace add Cy4nLiang/llmwiki
/plugin install llmwiki@llmwiki
```

即得 `/wiki-init`、`/wiki-upgrade`、`/wiki-golden` 三个斜杠向导。注:插件只分发向导 skill;渲染 / 升级 / 检索仍由随框架 clone 的 `tools/`(纯标准库)执行,向导会引导定位——**插件是"拿到向导"的便捷通道,完整工具链仍以 clone 为准。**

> 亦有 `npx add-skill Cy4nLiang/llmwiki`——但它装到 `~/.agents/skills/`,而 Claude Code 读 `~/.claude/skills/`,需自行 relink;原生 `/plugin` 通道无此坑,优先用它。

---

## 为什么需要它

你和 agent 的每次会话都在重复交同一笔税:

- **重复推导**——上个会话刚梳理清楚的架构决策、刚踩过的坑,这个会话又从零 grep 一遍;
- **参数记忆幻觉**——版本、日期、内部约定,agent 凭训练记忆作答而不是查证;
- **知识不复利**——结论散落在对话记录里,对下一次运行的 agent 等于不存在。

llmwiki 的回答:给项目建一座 **agent 自己维护、自己查询的知识库**。平庸与优秀输出的差距几乎从不在 prompt,而在上下文;agent 运行时拿不到的信息等于不存在。于是——**不重推导**(读 wiki、更新 wiki、在 wiki 上复利)、**查询即积累**(有保留价值的回答自动归档成缓存页)、**精确事实只认 exact-match**(凡推翻过参数记忆的事实域登记进路由页「纠偏区」,强制后续会话弃训练记忆)。

## v1.4.0 新增能力(v1.1 → v1.4)

四个里程碑,每项都配了机械门禁与逐版本迁移条目(`framework/UPGRADING.md`);全部仍是纯文件、纯标准库。

| 能力 | 是什么 | 规则 / 入口 |
|---|---|---|
| **排名检索** | 关键词说不准时的兜底:`python3 tools/search.py "词"` 走 BM25 排名(索引 `site/agent/search-index.json` 由 build 派生),构建与查询共用一份打分实现 | W-IDX-3;`_map` 决策表新增「关键词不确定」入口 |
| **链接图谱** | `wiki/backlinks.md`(反链:谁引用了 X)+ `site/agent/graph.json`(边表,供中心/孤立分析)。**只做确定性 slug 解析,不做语义推断边** | W-IDX-4 |
| **内容脱敏** | lint 对 `wiki/`+`raw/` 扫密钥/凭证样式(AWS/GCP/GitHub/Slack token、私钥块、凭证赋值),**只报类型+行号绝不回显值**;`<!-- secscan:allow -->` 行内豁免 | W-SEC-3(soft) |
| **自动捕获(可选)** | `extras/hooks/`:SessionStart 提醒「先读 `_map`」;SessionEnd/Stop 在 `raw/inbox/` 投占位草稿,让收尾检查点不被遗忘。**opt-in**,不配置不触发,exit 恒 0 不打断会话 | W-CAP-1;配置见 `docs/hooks.md` |
| **插件分发** | `/plugin marketplace add Cy4nLiang/llmwiki` → `/plugin install llmwiki@llmwiki` 直接拿到三向导 | W-DIST-1(版本由 CI 锁定恒等于 `framework/VERSION`) |
| **冷启动** | `python3 tools/bootstrap_scan.py` 只读扫宿主 repo(README/CHANGELOG/ADR/docs/工程约定/`git log` 决策词)产候选清单 → `/wiki-bootstrap` 引导勾选后批量入库。**候选 ≠ 投递**,勾选权在人 | 配 `wiki-bootstrap` 向导 |
| **演进链** | 整页结论被新版取代时登记 `supersedes:` / `superseded_by:`,lint 校验双向一致 + 被替代页横幅;`contradictions.md` 增「演进链」分节。**演进 ≠ 矛盾**——不进 ⚠️ 区;查询命中旧页必须跟到后继 | W-ING-5(soft) |
| **调研闭环** | `/wiki-research`:followups 的「待读资源/未解问题」终于有出口——选题(你确认)→ 用宿主 web 工具查 → 逐字快照落 `raw/` → 标准 ingest → 勾销台账。**网络只在 agent 侧,工具链保持离线** | 配 `wiki-research` 向导 |
| **MCP 接口(可选)** | `extras/mcp_server.py`(纯 stdlib JSON-RPC/stdio,协议 `2025-11-25`)把实例暴露给 **Claude Desktop / Cursor / Windsurf 等非 skills 宿主**:4 工具 `wiki_map` / `wiki_search` / `wiki_page` / `wiki_capture` | 注册片段见 `docs/mcp.md` |
| **团队模式 RFC** | `docs/rfc-team-mode.md`——**提案,未实现**(v1 单写者语义零改动):可并与必冲突分流、聚合页冲突形状、所有权清单、CI 门禁配方、shared/private 分区 | 讨论稿;配方即本仓 `.github/workflows/ci.yml` |

升级走 `/wiki-upgrade`:逐版本迁移清单会告诉你每条要不要动手(多数是「无强制动作」——新工具随 frozen 覆盖自动获得,新 skill 经三方合并直接安装)。

## 怎么用

### 30 秒看懂日常形态

装好之后,你几乎只需要对 Claude Code 说话(工作流以 skills 形式随实例渲染,自动触发;未触发时按契约里的文件路径直读):

| 你说 | 发生什么 |
|---|---|
| 「扫一下这个项目有什么值得入库」 | wiki-bootstrap:只读扫宿主 repo 出候选清单,你勾选后批量入库——空库冷启动第一步 |
| (会话收尾)「这个坑记一下」 | 捕获协议:agent 把踩坑/决策写成笔记投进 `raw/inbox/`——投递≠整合,不打断手头任务(想全自动就配 `docs/hooks.md` 的 hook) |
| 「同步一下 / 看看积压」 | wiki-sync:跑采集管线,持久重算 pending,报待整合清单与分档建议 |
| 「ingest 这篇」 | wiki-ingest 七步流:七段骨架源页 + 交叉引用进相关聚合页(touch 下限机检,绝不退化成剪藏) |
| 「X 怎么做?当时为什么这么定?」 | wiki-query:按路由页决策表选最便宜入口作答;未收录就明说,绝不静默编造 |
| 「查一下这个 followup」 | wiki-research:选题(你拍板)→ 宿主 web 工具调研 → 快照进 `raw/` → 标准 ingest → 台账勾销 |
| 「这页还是最新的吗」 | 演进链:被取代的页登记 `superseded_by:` 并留横幅,查询自动跟到后继;全库一览在 `contradictions.md` |
| 「体检一下」 | wiki-lint:断链 / 预算 / 过期未核实 / 索引新鲜度 / 密钥泄漏 / 演进链…… **18 项**机械检查 + 语义审清单 |
| 「建个基线」 | /wiki-golden:写 ~10 道题,零 LLM 打分器给出检索质量基线,此后协议调优看数字 |

### 三分钟装进项目

前提:macOS/Linux + Python 3(仅标准库);一级宿主 Claude Code;AGENTS.md-only 运行时可用——skills 不自动触发时,按契约内的文件路径直读各工作流 SKILL.md。

```bash
git clone https://github.com/Cy4nLiang/llmwiki    # 实例内建议保留 git remote "framework" 供跟版
```

在 Claude Code 里说 `/wiki-init`,三种落地模式:

| 模式 | 适用场景 | 效果 |
|---|---|---|
| **embedded**(最常用) | 给现有代码仓库配知识库 | 渲染进 `knowledge/` 子目录;宿主 CLAUDE.md 由 agent 依固定模板**逐字追加**一段指针(含会话收尾捕获检查点),其余零污染 |
| greenfield | 从零建独立知识库 | 十问问答 → 完整实例仓 |
| adopt | 收编已有的笔记/文档堆 | 探测现有布局反推 config,绝不覆盖已有文件 |

问答只收集 domain 取值,正文一律由工具生成(agent 只填 config,同一 config 两次渲染逐字节相同):

```bash
python3 tools/init_render.py --config wiki.config.json --target <实例目录>
python3 tools/lint_wiki.py --check-slots --target <实例目录>   # 冒烟:零槽位残留
```

然后把第一篇材料丢进 `raw/`(或 inbox),说「ingest 这篇」——复利闭环从这一步开始。

### 接外部源与进阶

- **外部抓取**:按 `adapters/CONTRACT.md` 从 skeleton 复制出适配器(discover/fetch/status 三个子命令、只写 raw/+state/)即被 sync 自动接入;人工投放快照声明 `"adapter": "manual"`;内生知识(ADR/踩坑)走 inbox 零代码;
- **多项目互引**:config 声明 `peers` 后用 `[[alias::slug]]` 跨实例引用(单向、1 跳、peer 不在场仅软警告);推荐建一个个人 hub 实例承载跨项目通用知识;
- **自动化(可选)**:配 `docs/hooks.md` 的两个 hook,让「先读 `_map`」提醒与会话收尾捕获零口头成本;
- **给别的宿主用(可选)**:按 `docs/mcp.md` 注册 `extras/mcp_server.py`,Claude Desktop / Cursor / Windsurf
  等非 skills 宿主也能读同一座库(4 工具:路由页 / 排名检索 / 取页 / 投递);
- **框架升级**:`/wiki-upgrade`——版本差距清单 → 预备份 → frozen hash 校验覆盖 → render-once 三方合并 → lint 门禁 + golden 回归提醒(有 golden 必跑,W-UPG-2);冲突落 `<file>.upgrade-new` 逐 diff 处理,你的内容与本地修改**永不被静默覆盖**。

## 优势

**vs 把知识塞进 CLAUDE.md** —— CLAUDE.md 是地图不是仓库:塞知识必膨胀,且每个会话全额付费。llmwiki 分层:契约(每会话必读,~200 行硬预算)→ 路由页(≤100 行,列出每个文件的 token 体量与读法)→ 页面(按需读,先 TL;DR)。**上下文预算是一等公民**;绝大多数硬规则配机械 lint,7 条协议条款靠 eval/人审兜底(见 `framework/RULES.md`)。

**vs RAG / 向量检索** —— 纯文件、可 grep、可读可审计,零服务、零 embedding、零索引运维;矛盾与时间线被显式管理(演进 / 对比 / ⚠️ 真矛盾三分,禁静默覆盖);查询会积累(答案归档);还有向量检索没有的器官——**纠偏区**:被 exact-match 推翻过的参数记忆事实域永久登记,防同类幻觉复发。

**vs 手工维护笔记** —— 维护是 agent 的活:捕获、整合、双向交叉引用、断链把守、过期检测(stale runbook 是危险品,不是旧文章)全部协议化并配好工具;人只负责说话和拍板。

**工程上的硬保证**:

- **确定性**:实例的出生与升级全程由工具执行,agent 不手写协议正文(唯一例外:embedded 宿主指针段由 agent 依固定模板逐字追加);
- **零依赖**:全部工具 Python 标准库;`python3 tests/run_ci.py` 一条命令 256 断言全闭环回归(含模拟升级四路径);
- **升级契约**:逐文件三档归属(frozen / render-once / instance)+ sha256 派生清单 + 语义化版本 + 逐版本迁移清单(`framework/UPGRADING.md`),协议自身的每次演进都走自己的升级流程;
- **评测闭环 day-one**:golden schema(9 题型,含 keyword-miss 排名检索探针、unanswerable 诚实探针与路由入口题)+ 零 LLM 确定性打分器 + any-of 组结算——协议改动可量化验收,模型选型用自家数据实测(「便宜模型不吃协议红利」已写入 playbook 警示)。

### 放到 LLM-Wiki 浪潮里看

llmwiki 是 Karpathy 提出的 **LLM-Wiki 模式**(2026-04)的一个工程化实现。同类项目多聚焦"让 agent 有个知识库",llmwiki 的差异化是把它做成**可回归、可升级、可审计**的工程件(下表为 2026-07 GitHub 调研快照,★ 数与判定仅供定位参考):

| 项目 | 检索 | 评测门禁 | 升级契约 | 依赖 |
|---|---|---|---|---|
| **llmwiki** | grep + BM25 排名(`tools/search.py`) | ✅ golden 9 题型 + 零 LLM 确定性打分器 | ✅ 三档归属 + sha256 派生清单 + 逐版本迁移 | 零(纯 Python 标准库) |
| karpathy-llm-wiki(1.6k★) | grep(宣言式极简) | — | — | 零 |
| llm-wiki-agent(3.3k★) | 图谱双通道 | — | — | Node |
| obsidian-wiki(3.0k★) | 全文 + 图谱 | — | — | Obsidian |
| basic-memory(3.5k★) | 语义 / SQL(MCP) | — | — | MCP 服务 |
| RAG / mem0 / cognee 等 | 向量检索 | — | — | embedding + 向量库 |

**四大独有资产**:golden eval 门禁(协议改动可量化验收)· 升级契约(frozen / render-once / instance 三档 + 语义化版本)· 零依赖确定性渲染(同 config 两次逐字节相同)· 诚实协议(unanswerable 探针 + 纠偏区永久登记被推翻过的参数记忆事实域)。

## 示例实例:knowledge/

`knowledge/` 是用本框架 embedded 模式实例化出的**框架自身开发知识库**,素材全部来自本仓可核实的真实历史。它是 dogfood 产物而非演示摆件——**浏览它 = 看框架用起来的样子**:

- 入口按其契约走:`knowledge/CLAUDE.md` → `knowledge/wiki/_map.md`(路由页)→ `knowledge/wiki/overview.md`;
- 五类页面类型学在「代码库知识」domain 的映射:entity=工具/组件、concept=设计约定/机制、synthesis=跨里程碑设计叙事、query=开发问答;
- 内容仅 `wiki/` 与 `raw/`;实例自持有的 frozen 拷贝(`tools/` 等)随渲染产物入库,运行态 `state/`、`site/` 被 .gitignore 忽略,clone 后在 `knowledge/` 下跑 `python3 tools/build_site.py && python3 tools/build_index.py` 重建派生索引;
- 实例数据不属框架升级契约(`gen_manifest.py` 排除 `knowledge/`)。

## 边界(如实声明)

- 实例定位**单人 + agent**:read 可并行(只读 subagent 蒸馏回传),write 单写者,均为单会话内语义;团队并发 v2 前出界,多会话操作同一实例请自行保证同一时刻单写。
- domain 特殊需求优先走 config `x-` 扩展命名空间与「实例扩展附录」逃生舱(lint 豁免),而非修改框架文件——frozen 档禁改,改 = 显式 fork。
- 不做向量检索、不做 SaaS/服务端、不做跨实例自动同步(引用可以,同步不做)。支持范围:单人维护者 best-effort。

## 实测数字(具体实例实测,非通用承诺)

- 孵化本框架的 600+ 页生产知识库(**仓外实例,本仓不可复核**):阅读协议实测 **59.6K → 7.1K tokens/题(8.4×)**,未收录问题 0-token 诚实拒答 8/8;
- 仓内 dogfood 实例 `knowledge/`:骨架落成约 **1 分钟**、首批 10 篇内容全部落库**不到 7 分钟**(单次 dogfood 观察,逐步骤计时见 `knowledge/wiki/log.md`);golden 基线 **precision 1.000 / recall 0.958**,诚实探针 2/2(`knowledge/evals/` 内可复算)。

本仓库全部文档统一此口径:数字只以具体实例实测引用,不作通用性能承诺;你的实例请用 `/wiki-golden` 建自己的基线——**框架只给方法,不给结论**。

## 目录导览

```
llmwiki/
├── CLAUDE.template.md      实例契约骨架(槽位 + 命名锚点 + 31 条 W-* 规则 ID + 条件模块)
├── wiki.config.example.json 实例唯一配置示例(schema/ 校验)
├── .claude/                向导 skills(wiki-init / wiki-upgrade / wiki-golden)+ 页面骨架规则 + wiki-reader
├── templates/              渲染进实例的 meta 页骨架与本地工作流 skills(ingest/query/lint/sync/bootstrap/research)
├── tools/                  frozen 工具链:init_render / sync / build_site / build_index / lint_wiki
│                           / search / bootstrap_scan / eval_retrieval / eval_compare / upgrade
│                           / gen_manifest + lib/{fm,textindex,wikigraph,secscan}.py(纯标准库)
├── adapters/               fetcher 契约 + 两型 skeleton + local_notes(inbox 开箱即用)
├── evals/                  golden schema + 9 题型模板 + 执行 playbook
├── framework/              VERSION / MANIFEST(派生)/ RULES(规则 ID 总表)/ UPGRADING(逐版本迁移)
├── extras/                 可选组件(不进核心依赖面):本地阅读器 serve.py / 双语增强 i18n_link.py
│                           / MCP server mcp_server.py / hooks(启动提醒 + 收尾捕获)
├── tests/                  hello-wiki 合成夹具 + run_ci.py(256 断言全闭环)
├── knowledge/              示例实例(框架自身开发知识库,dogfood)
├── docs/                   框架文档:hooks / mcp / rolling-source / bulk-ingest
│                           / fetcher-contract / rfc-team-mode(团队模式提案)
└── schema/  .github/  CONTRIBUTING.md  LICENSE(MIT)
```

## 贡献与 License

约定见 **`CONTRIBUTING.md`**:两档 PR 政策(frozen 不变式不接受放宽类 / convention 可议)、回流通道(实例好约定 → issue/PR → MINOR)、脱敏 checklist、semver 判级表。开发验证一条命令:`python3 tests/run_ci.py`。

MIT(见 `LICENSE`)。Copyright (c) 2026 Cy4nLiang。
