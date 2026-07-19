# llmwiki — 给每个项目一座 agent 自己维护的说明书库

> v1.1.0 · 纯文件 · 零第三方依赖 · MIT

> **English summary** — the rest of this document is in Chinese.
>
> **What**: llmwiki is a content-free, reusable framework for agent-maintained, compounding knowledge bases ("LLM wiki"): a slotted CLAUDE.md contract, a token-budgeted routing page, frozen page skeletons, stdlib-only deterministic tools, and a day-one golden-eval loop. Drop it into any project — codebase knowledge, ops runbooks, industry intel.
>
> **Why**: agent accuracy is a context problem. Without a repository, every session re-derives what the last one learned, answers version/date questions from parametric memory, and leaves conclusions trapped in chat logs where they never compound.
>
> **How**: clone → say `/wiki-init` in Claude Code (three modes: embedded into an existing repo / greenfield / adopt; rendering is done by a deterministic tool, never hand-written) → drop a note into `raw/inbox/` → say "ingest it". From then on the daily loop is just talking to the agent: capture → sync → ingest → query → lint → golden.
>
> **Proof over promises**: the protocol was measured on the 600+-page production knowledge base that incubated it (59.6K → 7.1K tokens per question, 8/8 honest refusals on unanswerable probes) and on the in-repo dogfood instance `knowledge/` (golden baseline P 1.000 / R 0.958, reproducible from `knowledge/evals/`). Instance measurements, not universal claims.

---

## 为什么需要它

你和 agent 的每次会话都在重复交同一笔税:

- **重复推导**——上个会话刚梳理清楚的架构决策、刚踩过的坑,这个会话又从零 grep 一遍;
- **参数记忆幻觉**——版本、日期、内部约定,agent 凭训练记忆作答而不是查证;
- **知识不复利**——结论散落在对话记录里,对下一次运行的 agent 等于不存在。

llmwiki 的回答:给项目建一座 **agent 自己维护、自己查询的知识库**。平庸与优秀输出的差距几乎从不在 prompt,而在上下文;agent 运行时拿不到的信息等于不存在。于是——**不重推导**(读 wiki、更新 wiki、在 wiki 上复利)、**查询即积累**(有保留价值的回答自动归档成缓存页)、**精确事实只认 exact-match**(凡推翻过参数记忆的事实域登记进路由页「纠偏区」,强制后续会话弃训练记忆)。

## 怎么用

### 30 秒看懂日常形态

装好之后,你几乎只需要对 Claude Code 说话(工作流以 skills 形式随实例渲染,自动触发;未触发时按契约里的文件路径直读):

| 你说 | 发生什么 |
|---|---|
| (会话收尾)「这个坑记一下」 | 捕获协议:agent 把踩坑/决策写成笔记投进 `raw/inbox/`——投递≠整合,不打断手头任务 |
| 「同步一下 / 看看积压」 | wiki-sync:跑采集管线,持久重算 pending,报待整合清单与分档建议 |
| 「ingest 这篇」 | wiki-ingest 七步流:七段骨架源页 + 交叉引用进相关聚合页(touch 下限机检,绝不退化成剪藏) |
| 「X 怎么做?当时为什么这么定?」 | wiki-query:按路由页决策表选最便宜入口作答;未收录就明说,绝不静默编造 |
| 「体检一下」 | wiki-lint:断链 / 预算 / 过期未核实 / 索引新鲜度…… 16 项机械检查 + 语义审清单 |
| 「建个基线」 | /wiki-golden:写 ~10 道题,零 LLM 打分器给出检索质量基线,此后协议调优看数字 |

### 三分钟装进项目

前提:macOS/Linux + Python 3(仅标准库);一级宿主 Claude Code(AGENTS.md-only 运行时按降级矩阵使用)。

```bash
git clone https://github.com/Cy4nLiang/llmwiki    # 实例内建议保留 git remote "framework" 供跟版
```

在 Claude Code 里说 `/wiki-init`,三种落地模式:

| 模式 | 适用场景 | 效果 |
|---|---|---|
| **embedded**(最常用) | 给现有代码仓库配知识库 | 渲染进 `knowledge/` 子目录;宿主 CLAUDE.md 只追加一段指针(含会话收尾捕获检查点),其余零污染 |
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
- **框架升级**:`/wiki-upgrade`——版本差距清单 → 预备份 → frozen hash 校验覆盖 → render-once 三方合并 → lint/golden 门禁;冲突落 `<file>.upgrade-new` 逐 diff 处理,你的内容与本地修改**永不被静默覆盖**。

## 优势

**vs 把知识塞进 CLAUDE.md** —— CLAUDE.md 是地图不是仓库:塞知识必膨胀,且每个会话全额付费。llmwiki 分层:契约(每会话必读,~200 行硬预算)→ 路由页(≤100 行,列出每个文件的 token 体量与读法)→ 页面(按需读,先 TL;DR)。**上下文预算是一等公民**,每条硬规则配一条机械 lint。

**vs RAG / 向量检索** —— 纯文件、可 grep、可读可审计,零服务、零 embedding、零索引运维;矛盾与时间线被显式管理(演进 / 对比 / ⚠️ 真矛盾三分,禁静默覆盖);查询会积累(答案归档);还有向量检索没有的器官——**纠偏区**:被 exact-match 推翻过的参数记忆事实域永久登记,防同类幻觉复发。

**vs 手工维护笔记** —— 维护是 agent 的活:捕获、整合、双向交叉引用、断链把守、过期检测(stale runbook 是危险品,不是旧文章)全部协议化并配好工具;人只负责说话和拍板。

**工程上的硬保证**:

- **确定性**:实例的出生与升级全程由工具执行,agent 不手写协议正文;
- **零依赖**:全部工具 Python 标准库;`python3 tests/run_ci.py` 一条命令 134 断言全闭环回归(含模拟升级四路径);
- **升级契约**:逐文件三档归属(frozen / render-once / instance)+ sha256 派生清单 + 语义化版本 + 逐版本迁移清单(`framework/UPGRADING.md`),协议自身的每次演进都走自己的升级流程;
- **评测闭环 day-one**:golden schema(8 题型,含 unanswerable 诚实探针与路由入口题)+ 零 LLM 确定性打分器 + any-of 组结算——协议改动可量化验收,模型选型用自家数据实测(「便宜模型不吃协议红利」已写入 playbook 警示)。

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

- 孵化本框架的 600+ 页生产知识库:阅读协议实测 **59.6K → 7.1K tokens/题(8.4×)**,未收录问题 0-token 诚实拒答 8/8;
- 仓内 dogfood 实例 `knowledge/`:从零到首批内容落库 **6.6 分钟**;golden 基线 **precision 1.000 / recall 0.958**,诚实探针 2/2(`knowledge/evals/` 内可复算)。

本仓库全部文档统一此口径:数字只以具体实例实测引用,不作通用性能承诺;你的实例请用 `/wiki-golden` 建自己的基线——**框架只给方法,不给结论**。

## 目录导览

```
llmwiki/
├── CLAUDE.template.md      实例契约骨架(槽位 + 命名锚点 + 27 条 W-* 规则 ID + 条件模块)
├── wiki.config.example.json 实例唯一配置示例(schema/ 校验)
├── .claude/                向导 skills(wiki-init / wiki-upgrade / wiki-golden)+ 页面骨架规则 + wiki-reader
├── templates/              渲染进实例的 meta 页骨架与本地工作流 skills(ingest/query/lint/sync)
├── tools/                  frozen 工具链:init_render / sync / build_site / build_index / lint_wiki
│                           / eval_retrieval / eval_compare / upgrade / gen_manifest + lib/fm.py(纯标准库)
├── adapters/               fetcher 契约 + 两型 skeleton + local_notes(inbox 开箱即用)
├── evals/                  golden schema + 8 题型模板 + 执行 playbook
├── framework/              VERSION / MANIFEST(派生)/ RULES(规则 ID 总表)/ UPGRADING(逐版本迁移)
├── extras/                 可选组件:本地阅读器 serve.py / 双语增强 i18n_link.py
├── tests/                  hello-wiki 合成夹具 + run_ci.py(134 断言全闭环)
├── knowledge/              示例实例(框架自身开发知识库,dogfood)
└── docs/  schema/  CONTRIBUTING.md  LICENSE(MIT)
```

## 贡献与 License

约定见 **`CONTRIBUTING.md`**:两档 PR 政策(frozen 不变式不接受放宽类 / convention 可议)、回流通道(实例好约定 → issue/PR → MINOR)、脱敏 checklist、semver 判级表。开发验证一条命令:`python3 tests/run_ci.py`。

MIT(见 `LICENSE`)。Copyright (c) 2026 Cy4nLiang。
