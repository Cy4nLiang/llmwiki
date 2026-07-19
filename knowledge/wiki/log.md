# Log 操作日志

Append-only(W-LOG-1)。每条以 `## [YYYY-MM-DD] <op> | <one-line>` 起手(ASCII 方括号与竖线,便于 grep);op ∈ ingest / bulk-ingest / query-filed / lint / update / note / bootstrap / refactor / upgrade / capture。正文列 created / updated(带关系类型)/ contradictions / notes。读取只用:

```bash
grep '^## \[' wiki/log.md | tail -10
```

---


## [2026-07-20] bootstrap | 初始化 llmwiki-dev 说明书库

- created: `CLAUDE.md`(契约)、`wiki.config.json`、wiki 目录骨架、`.claude/{rules,agents,skills}/`
- notes: 由 llmwiki 框架 v0.3.0 经 `init_render.py` 确定性渲染;源管线注册于 `wiki.config.json`(pipelines)。首批内容经 sync 报 pending 后按档位 ingest(W-ING-1)。

## [2026-07-20] ingest | adr-file-ownership-three-tiers(full)

- created: [[sources/2026-07-20-adr-file-ownership-three-tiers]]
- updated: [[concepts/file-ownership-three-tiers]](强化)、[[concepts/framework-upgrade-protocol]](扩展)、[[entities/gen-manifest]](例证)、[[entities/lint-wiki]](例证)、[[syntheses/framework-design-evolution]](例证)
- contradictions: 0;notes: derived-artifact-discipline 降纯文本(2 源未达 rule-of-three)。

## [2026-07-20] ingest | adr-form-factor-hybrid-template-repo(full)

- created: [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]
- updated: [[syntheses/framework-design-evolution]](强化)、[[concepts/framework-upgrade-protocol]](扩展)、[[concepts/deterministic-render]](强化)、[[concepts/file-ownership-three-tiers]](扩展)、[[entities/run-ci]](例证)
- contradictions: 0;notes: 嫁接项①④⑥(rule-id-namespace/ingest-tiering/local-workflow-skills)纯文本待晋升;⑤并入 run-ci。

## [2026-07-20] ingest | adr-manifest-container-articles(full)

- created: [[sources/2026-07-20-adr-manifest-container-articles]]
- updated: [[concepts/fetcher-adapter-contract]](强化)、[[entities/sync-tool]](例证)、[[concepts/framework-upgrade-protocol]](例证)、[[syntheses/framework-design-evolution]](演进)、[[concepts/file-ownership-three-tiers]](例证)
- contradictions: 0;notes: 0.3.0 items→articles 记「演进」;build-site/local-notes-adapter 待晋升。

## [2026-07-20] ingest | adr-rolling-judge-by-digest(full)

- created: [[sources/2026-07-20-adr-rolling-judge-by-digest]]
- updated: [[concepts/rolling-source-freshness]](强化)、[[entities/sync-tool]](例证)、[[concepts/fetcher-adapter-contract]](扩展)、[[concepts/framework-upgrade-protocol]](演进)、[[syntheses/framework-design-evolution]](演进)
- contradictions: 0;notes: M1→0.2.0 口径统一记「演进」;pending-persistent-recompute/tool-de-domainization 待晋升。

## [2026-07-20] ingest | pitfall-local-proxy-intercepts-loopback(light)

- created: [[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]]
- updated: [[entities/run-ci]](例证)
- contradictions: 0;notes: light 档 touch 1;hermetic-ci、extras/serve.py 记 followups 待晋升。

## [2026-07-20] ingest | pitfall-stale-manifest-fork-false-positive(light)

- created: [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]
- updated: [[entities/gen-manifest]](例证)、[[entities/lint-wiki]](例证)、[[entities/run-ci]](强化)、[[concepts/file-ownership-three-tiers]](扩展)
- contradictions: 0;notes: light 档超额 touch 4;derived-artifact-discipline 记 followups 待晋升。

## [2026-07-20] ingest | pitfall-template-comment-example-wikilink(light)

- created: [[sources/2026-07-20-pitfall-template-comment-example-wikilink]]
- updated: [[entities/lint-wiki]](例证)、[[concepts/framework-upgrade-protocol]](例证)
- contradictions: 0;notes: light 档 touch 2;wikilink-discipline/out-of-box-green 记 followups 待晋升。

## [2026-07-20] ingest | howto-add-fetcher-adapter(full)

- created: [[sources/2026-07-20-howto-add-fetcher-adapter]]
- updated: [[concepts/fetcher-adapter-contract]](例证+强化+扩展)、[[concepts/file-ownership-three-tiers]](例证)、[[entities/sync-tool]](强化)、[[entities/lint-wiki]](例证)、[[concepts/rolling-source-freshness]](例证)
- contradictions: 0;notes: adapter-contract/manifest-container/pipeline-registry 三提议目标并入 fetcher-adapter-contract 单页。

## [2026-07-20] ingest | howto-release-framework-version(full)

- created: [[sources/2026-07-20-howto-release-framework-version]]
- updated: [[concepts/framework-upgrade-protocol]](扩展+强化)、[[entities/gen-manifest]](强化)、[[entities/run-ci]](例证)、[[entities/lint-wiki]](例证)、[[concepts/file-ownership-three-tiers]](例证)
- contradictions: 0;notes: framework-release-flow/upgrade-gates 并入 framework-upgrade-protocol;upgrading-doc 待晋升。

## [2026-07-20] ingest | decision-deterministic-render-discipline(full)

- created: [[sources/2026-07-20-decision-deterministic-render-discipline]]
- updated: [[concepts/deterministic-render]](强化)、[[entities/lint-wiki]](扩展)、[[syntheses/framework-design-evolution]](强化)、[[concepts/file-ownership-three-tiers]](扩展)、[[concepts/framework-upgrade-protocol]](扩展)
- contradictions: 0;notes: template-repo-form-factor 并入 framework-design-evolution;init-render 待晋升。

## [2026-07-20] bulk-ingest | 首批 10 源 reduce 收敛:建 10 聚合页 + overview 首版 + _map 回填

- created: [[concepts/file-ownership-three-tiers]]、[[concepts/framework-upgrade-protocol]]、[[concepts/fetcher-adapter-contract]]、[[concepts/rolling-source-freshness]]、[[concepts/deterministic-render]]、[[entities/gen-manifest]]、[[entities/lint-wiki]]、[[entities/sync-tool]]、[[entities/run-ci]]、[[syntheses/framework-design-evolution]]
- updated: [[overview]](首版:大问题 6 条 + 主题地图 5 簇)、[[_map]](页面计数/档位表体量/决策表页名回填)、[[followups]](待晋升 16 项/待验证 3 项/未解问题 6 项协议缝隙标「待回流」)、10 篇源页 Connections/Processing Notes 回改(slug 终裁 + 降级纯文本)
- contradictions: 0(时间线变化均标「演进」:0.2.0 rolling 口径统一、0.3.0 items→articles、M2 stale-manifest 修法)
- notes: reduce 裁决口径——rule-of-three 未达的侧目标降纯文本记待晋升;full 档源页的主裁决概念(rolling-source-freshness/deterministic-render,各 2 源)按「ADR 主概念例外」建页;W-ING-2 单写者收敛,W-ING-1 touch 下限全部达标(full 档 7 源各 5 touch,light 档 3 源 touch 1/4/2)。

## [2026-07-20] note | golden 基线建立:10 题(6 计分型 + unanswerable×2 + route×2),真实 harness run 打分
- 基线:precision 1.000 / recall 0.633(n=8);unanswerable 2/2 诚实(answer_keys 锚点);miss_must 全空
- recall 缺口全部来自 weight-1 替代路径入分母的校准结构(「一页即止」最优检索的数学上限 0.4–0.667),非路由缺陷;下轮按 question-types 校准纪律评估 any-of 组结算,未经批准本轮未改 golden
- 文件:evals/golden.jsonl + evals/runs/2026-07-20-baseline.jsonl;W-UPG-2 门禁以本条为对照基准

## [2026-07-20] upgrade | framework 0.3.0 -> 1.0.0(frozen 覆盖 3/新增 3, render-once 采用 3, 冲突 0, fork 候选 0)
- 差距条目: 1.0.0(framework/UPGRADING.md);备份: state/tmp/pre-upgrade-0.3.0
- 门禁: lint --manifest rc=0;golden: 提醒已打印,必跑(W-UPG-2)

## [2026-07-20] note | golden any-of 组校准修订(v0.2):6 题假阴性消除,基线 R 0.633 → 0.958
- 背景:上条基线 note 已判定 recall 缺口 100% 来自 weight-1 替代/下钻路径进分母(校准结构缺陷,非路由缺陷);打分器今日起原生支持 golden_groups(组语义=同一信息多条获取路径任一命中即满;规范见 evals/golden.schema.json 与 question-types.md any-of 节)
- 修订(按「答案对才修 golden」单行道,基线 run 答案全对、miss_must 全空):q01/q02/q03/q05/q09 —— 枢纽页与替代/下钻单点合为 2 权组,原单点删除;q06 —— raw 文件留 2 级单点(W-QRY-1 逐字要求,绝不入组),源页+concept 两条导航路径合为 1 权组;q04/q10(单页命中集)与 q07/q08(unanswerable 禁组)不改。逐题改法与理由已写入各题 notes
- 新旧对照(同一 run:evals/runs/2026-07-20-baseline.jsonl,零重跑):precision 1.000 → 1.000;recall 0.633 → 0.958(n=8);problem_q 0 → 0;唯一未满题 q06 R 0.667——grep 直达 raw 的最优路径不读导航组,属有意保留的 1 权导航项,复跑常态化后再议降权
- 机检:--check-golden 10 题 0 错误 0 警告;W-UPG-2 门禁对照基准自本条起更新为 P 1.000 / R 0.958

## [2026-07-20] upgrade | framework 1.0.0 -> 1.1.0(frozen 覆盖 3/新增 0, render-once 采用 1, 冲突 0, fork 候选 0)
- 差距条目: 1.1.0(framework/UPGRADING.md);备份: state/tmp/pre-upgrade-1.0.0
- 门禁: lint --manifest rc=0;golden: 提醒已打印,必跑(W-UPG-2)

## [2026-07-20] note | 补录:M4 dogfood init 逐步骤计时(单次观察;README「实测数字」节出处)
- init 会话 unix 时间戳锚点实测:读 SKILL+CLI 勘察+写 config+渲染 38s → check-slots 冒烟+空索引+config 归位复检 19s(**骨架落成合计 57s ≈ 1 分钟**)→ 仓内取证 146s → 撰写 10 篇 inbox 素材 165s → 宿主契约+AGENTS symlink 19s → 收尾验证(sync status+全量 lint)9s;**总计 396s ≈ 6.6 分钟**
- 口径:单次 dogfood 观察、非通用承诺(W-* 数字纪律);双线核查(2026-07-20)指出此前该数字仓内无出处,本条补录为唯一出处

## [2026-07-20] upgrade | framework 1.1.0 -> 1.1.1(frozen 覆盖 0/新增 0, render-once 采用 1, 冲突 0, fork 候选 0)
- 差距条目: 1.1.1(framework/UPGRADING.md);备份: state/tmp/pre-upgrade-1.1.0
- 门禁: lint --manifest rc=0;golden: 提醒已打印,必跑(W-UPG-2)
