---
title: "ADR:rolling 源判新采 rolling_digest(sha256)而非版本号"
description: "查『滚动源怎么判定有更新』『rolling_digest 是什么、忘写会怎样』『为何不用版本号判新』时读本页;独有价值:sha256 判新裁决理由 + 自愈锚点机制 + 0.2.0 口径统一史。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-adr-rolling-judge-by-digest.md
source_kind: adr
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki-dev"]
tags: [adr, cluster/sync-freshness]
status: draft
ingest_tier: full
---

# ADR:rolling 源判新采 rolling_digest(sha256)而非版本号

## 一句话摘要 / TL;DR

rolling 型管线判新以内容摘要为准:sync 现场重算 faithful 快照全文 sha256,与源页 frontmatter `rolling_digest:` 比对,不一致 → pending 报「刷新滚动源页」(非新建页);版本号仅作报告口径,不参与判新。

## 关键论点 / Key Claims

- 与 pending 持久重算原则一致:pending = f(raw/, wiki/sources/),不依赖一次性台账,重跑恒得同一结果。
- 工具去 domain 化的要求:版本号是 domain 相关口径(有的滚动源根本没有版本号),sha256 对任何滚动源都成立。
- 刷新闭环有**自愈锚点**:刷新滚动源页的最后一步就是回写 digest;忘写 `rolling_digest:` → 该源永远 pending——暴露而非静默。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- digest 格式:`sha256:<64 位十六进制>`;写入时机:首次 ingest 与每次刷新完成时,agent 把当时 faithful 快照文件的 sha256 写入 `rolling_digest`,同步更新 `rolling_latest`。
- faithful 快照与 dated 派生分离;快照变化记「演进」(W-ING-3)。
- 口径演进:M1 时期口径不统一,0.2.0 版通过 render-once 三方合并统一为 `rolling_digest`(UPGRADING 0.2.0 迁移清单「rolling 判新统一 rolling_digest 口径」)。
- 出处锚点:`docs/plans/llmwiki-framework-spec.md` §7;`llmwiki/docs/rolling-source.md` §2.5;`llmwiki/docs/fetcher-contract.md`;`llmwiki/framework/UPGRADING.md` 0.2.0 条目。

## 我学到了什么 / Takeaways

- 「判新」应挂在内容本身而非元数据口径上:内容摘要是 domain 无关的最小公分母,版本号只配当报告修辞。
- 状态机设计要选「失败即暴露」的缺省:忘写 digest 的后果是永远 pending(可见),而不是静默漏更新(不可见)。
- 持久重算 > 一次性台账:pending 从 raw/ 与 wiki/sources/ 两端现算,天然抗台账丢失/损坏。

## 与其它来源的关系 / Connections

- 强化:[[concepts/rolling-source-freshness]] —— 本 ADR 是 rolling_digest 判新机制的裁决记录与权威出处。
- 例证:[[entities/sync-tool]] —— sync 现场重算快照 sha256 并与源页 frontmatter 比对;pending 持久重算原则的宿主。
- 扩展:[[concepts/fetcher-adapter-contract]] —— fetcher-contract 文档载明「忘写 digest → 永远 pending」的自愈锚点约定。
- 演进:[[concepts/framework-upgrade-protocol]] —— M1 口径不统一 → 0.2.0 经 render-once 三方合并统一为 `rolling_digest`。
- 演进:[[syntheses/framework-design-evolution]] —— 0.2.0 口径统一是 M1→0.2.0 演进线的一站。
- 强化(纯文本待晋升):pending 持久重算原则(pending = f(raw/, wiki/sources/),建议 concepts/pending-persistent-recompute,暂由 [[entities/sync-tool]] 与 [[concepts/rolling-source-freshness]] 承载);工具去 domain 化(sha256 对任何滚动源成立,建议 concepts/tool-de-domainization)。

## 引用片段 / Quotes

> **版本号仅作报告口径**,不参与判新。

> 刷新闭环有自愈锚点:刷新滚动源页的最后一步就是回写 digest;忘写 `rolling_digest:` → 该源永远 pending,暴露而非静默。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/rolling-source-freshness]](强化)、[[entities/sync-tool]](例证)、[[concepts/fetcher-adapter-contract]](扩展)、[[concepts/framework-upgrade-protocol]](演进)、[[syntheses/framework-design-evolution]](演进)——共 5,满足 full 档下限(W-ING-1)。
- reduce 裁决:pending-persistent-recompute / tool-de-domainization 各仅 1 源支撑(rule-of-three 未达)降纯文本,记 followups 待晋升。
- 档位:full(source_kind=adr 映射)。
- W-SEC-1:原文为仓内一手 ADR,未发现指令性注入内容。
