# llmwiki — content-free 可复用 agent 说明书库框架

> **English summary** — the rest of this document is in Chinese.
>
> **What**: llmwiki packages a field-tested protocol for agent-maintained, compounding knowledge bases ("LLM wiki", after Karpathy) into a content-free, reusable framework: a slotted CLAUDE.md contract, a `_map` routing page, frozen page-skeleton rules, stdlib-only Python tools, and a day-one golden-eval loop. Instantiate it on any domain — codebase knowledge, ops runbooks, industry intel.
>
> **Why**: agent accuracy is a context problem, and re-deriving knowledge on every query burns tokens. In the reference instance (newpj4), the reading protocol measured 59.6K → 7.1K tokens per question (8.4x) with 8/8 honest refusals on unanswerable probes — measured *there*, not a universal promise.
>
> **Quickstart**: clone this repo → run `/wiki-init` in Claude Code (10 questions → `wiki.config.json` → deterministic render by `tools/init_render.py` → `lint_wiki.py --check-slots` smoke check) → drop your first source into `raw/` and say "ingest it". Instances are single-user + agent by design. MIT licensed.

---

## 定位

llmwiki 把「AI 维护的复利型知识库」协议层从参考实例(newpj4,633 页双厂商 AI 博客知识图谱)中抽出,做成**不含内容、可复用的框架**:套用到任意项目(代码库知识、运维 runbook、行业情报……),让每个项目的 agent 拥有一座持续维护、持续查询的「说明书库 / 第二大脑」,以此提高 agent 的工作效率与准确性。

核心信念:平庸与优秀输出的差距几乎从不在 prompt,而在上下文;agent 运行时拿不到的信息等于不存在。llmwiki 的答案是——不重推导、查询即积累、矛盾与演进被显式管理,且整套协议**被 golden 评测实测过**,不是纸上设计。

形态:模板仓库为主体(hybrid)。实例全持有、可 grep、纯文件、本地优先、核心零第三方依赖;升级靠规则 ID(`W-*`)+ 钉版快照(`framework/VERSION` + `base/`)+ MANIFEST 三档归属。

## 三支柱:协议 + 工具 + 评测

相对「一份 CLAUDE.md 模板」类方案,llmwiki 的差异化在三件事同时发货:

1. **协议**——契约模板(19 槽位 + 命名锚点 + 26 条 `W-*` 规则 ID,见 `framework/RULES.md`)、`_map` 五段路由页、五类页面类型学与冻结骨架、纠偏区机制(exact-match 裁决推翻参数记忆的事实域显式登记,强制后续会话弃训练记忆——RAG 与向量检索都没有这个器官)。每条款背后有参考实例的评测数字与修正案例。
2. **工具**——仅 Python 标准库的确定性工具链:`init_render.py`(agent 只填值,渲染交工具,两次渲染逐字节相同)、`sync.py`(管线编排+pending 持久重算)、`build_site.py`/`build_index.py`(派生索引,W-IDX-1)、`lint_wiki.py`(全量机械体检+`--manifest` frozen 校验)、`eval_retrieval.py`/`eval_compare.py`(零 LLM 评测)、`lib/fm.py`(frontmatter/est_tokens/wikilink 单源)、`gen_manifest.py`;fetcher 契约见 `adapters/CONTRACT.md`。
3. **评测**——golden schema + 6+1 题型(single-hop / multi-hop / comparison / aggregation / timeline / exact-verbatim + unanswerable 诚实探针 + 路由入口选择题)+ 零 LLM 打分器 + 成本客观重算。实例只写题目,就能回归验证自己的协议改动与模型选型。

## 快速开始

前提:macOS/Linux + Python 3(标准库即可);一级宿主为 Claude Code,AGENTS.md-only 运行时按降级矩阵使用。

1. **取框架**
   ```bash
   git clone <repo-url> llmwiki    # 或 degit;实例内建议保留 git remote "framework" 供跟版
   ```
2. **实例化**:在 Claude Code 会话内触发 `/wiki-init`(skill 未触发时直接 Read `.claude/skills/wiki-init/SKILL.md`)。三模式:greenfield(全新)/ adopt(收编存量仓库,绝不覆盖已有文件)/ embedded(渲染进宿主子目录 `knowledge/`,宿主 CLAUDE.md 只追加指针段)。十问收集 domain 取值 → 写 `wiki.config.json` → `python3 tools/init_render.py` 确定性渲染 → `python3 tools/lint_wiki.py --check-slots` 冒烟(零槽位残留)。
3. **首次 ingest**:把第一篇源材料放进 `raw/`(或按捕获协议投递 `raw/inbox/<date>-<slug>.md`),对 agent 说「ingest 这篇」——走 wiki-ingest 七步流,产出七段骨架源页并 touch 聚合页(W-ING-1:full ≥5 / light ≥1),这一步是复利闭环的起点,绝不退化成剪藏。

> 当前为 M3 质量版:工具链、fetcher 契约、评测打包(golden schema/题型/playbook)、升级工具(upgrade.py)与 extras(serve/i18n)已全部落位;剩余 M4 = 真实项目 dogfood + 发布工程。

## 目录导览

```
llmwiki/
├── README.md                        本文件
├── LICENSE                          MIT
├── CLAUDE.template.md               契约骨架:槽位 + 命名锚点 + 规则 ID + 3 个条件模块
├── wiki.config.example.json         实例唯一配置示例(schema/ 校验)
├── .gitignore                       安全默认模板(W-SEC-2)
├── framework/
│   ├── VERSION                      语义版本(实例升级锚点)
│   ├── MANIFEST.json                逐文件归属 frozen|render-once|meta + sha256(派生物,勿手编)
│   ├── RULES.md                     26 条 W-* 规则 ID 总表(权威引用命名空间)
│   └── UPGRADING.md                 逐版本迁移说明(引规则 ID)
├── schema/wiki.config.schema.json   config 的 draft-07 规范文档(运行时校验由 init_render 手写实现)
├── .claude/
│   ├── rules/                       source-page / aggregate-pages(骨架冻结,枚举留槽)
│   ├── agents/wiki-reader.template.md
│   └── skills/                      向导类:wiki-init / wiki-upgrade / wiki-golden
├── templates/
│   ├── wiki/                        _map / overview / log / followups / contradictions 骨架
│   └── skills/                      渲染进实例的本地工作流:wiki-ingest / wiki-query / wiki-lint / wiki-sync
├── tools/                           frozen;仅 Python 标准库
│   ├── init_render.py               确定性渲染器(/wiki-init 的执行引擎)
│   ├── lint_wiki.py                 机械体检(--check-slots / --check-config)
│   └── gen_manifest.py              MANIFEST 派生
└── adapters/(CONTRACT+skeleton×2+local_notes) docs/ tests/hello-wiki/(CI 夹具)   evals/ extras/ ← M3
```

## 实例定位声明:单人 + agent,团队并发出界

- 实例定位**单人 + agent**:read 可并行(只读 subagent 蒸馏回传),write 单写者,均为**单会话内**语义。
- 跨会话/多成员的 log 合并、聚合页协调**不提供机制**(v1 Non-goal,团队并发留 v2)。多会话并行操作同一实例时,用户自行保证「同一时刻单写会话」。
- 支持范围:单人维护者 best-effort。domain 特殊需求优先走 config `x-` 扩展命名空间与「实例扩展附录」逃生舱(lint 豁免),而非修改框架文件——frozen 档禁改,改 = 显式 fork(W-UPG-1)。

## 证据口径

参考实例 newpj4 实测:检索 59.6K→7.1K tok/题(8.4x),诚实探针 8/8——**非通用承诺**。

本仓库全部文档统一此口径:数字只以「参考实例 newpj4 实测」引用,不作任何通用性能承诺;你的实例请用自家 golden 题集复跑(`/wiki-golden` 建基线),框架只给方法不给结论。另注意「便宜模型不吃协议红利」已写入评测 playbook 警示。

## 里程碑状态

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M1 骨架 | 契约挖空+锚点化+规则 ID、rules/meta/skills 模板、config schema、init_render + /wiki-init、lint --check-slots | **完成**(v0.1.0) |
| M2 工具 | 7 件工具去 domain 化 + lib/fm.py、fetcher 契约、local_notes/inbox、hello-wiki 夹具 CI(79 断言) | **完成**(v0.2.0) |
| M3 质量 | 评测打包(题型/playbook/路由入口题)、升级协议(upgrade.py:hash 校验/三方合并/预备份/门禁)、跨实例引用收尾(peers 状态/版本 skew)、extras(serve/i18n)、安全默认 | **完成**(v0.3.0,CI 119 断言) |
| M4 发布 | 真实代码项目 dogfood + 发布工程(公开仓库、贡献指南)→ v1.0.0 | 进行中 |

## 贡献与回流

- 反馈走 **issue / PR**;被采纳的实例好约定进 **MINOR** 版本(co-evolution 双层化:实例侧标「待回流」→ PR 回框架仓库)。
- 回流 PR 必须过脱敏 checklist:去 domain 专名、内部 URL、内部数字;`peers` 为本机路径,**不入发布物与回流 PR**(W-SEC-2 / W-XRF-1)。
- semver 判级:MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订。迁移说明见 `framework/UPGRADING.md`。

## License

MIT(见 `LICENSE`)。Copyright (c) 2026 Cy4nLiang。
