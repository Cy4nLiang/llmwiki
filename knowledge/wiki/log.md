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
