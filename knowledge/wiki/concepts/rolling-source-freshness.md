---
title: Rolling 源判新(rolling_digest / sha256)
description: "查『滚动源怎么判定有更新』『rolling_digest 忘写会怎样』『为何不用版本号判新』时读本页;含 digest 格式与写入时机、自愈锚点、pending 持久重算原则。"
type: concept
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/sync-freshness, rolling, digest]
status: draft
sources: ["[[sources/2026-07-20-adr-rolling-judge-by-digest]]", "[[sources/2026-07-20-howto-add-fetcher-adapter]]"]
aliases: ["滚动源判新", "rolling source freshness", "rolling_digest"]
---

# Rolling 源判新(rolling_digest / sha256)

## 定义

rolling 型管线(一份滚动更新的源对应一个源页)的判新机制:sync **现场重算** faithful 快照全文 sha256,与源页 frontmatter `rolling_digest:` 比对;不一致 → pending 报「刷新滚动源页」(非新建页)。**版本号仅作报告口径,不参与判新**。(来源:[[sources/2026-07-20-adr-rolling-judge-by-digest|rolling 判新 ADR]],强化)

## 核心要点

- **digest 格式与写入时机**:`sha256:<64 位十六进制>`;首次 ingest 与每次刷新完成时,agent 把当时 faithful 快照文件的 sha256 写入 `rolling_digest`,同步更新 `rolling_latest`。(来源:[[sources/2026-07-20-adr-rolling-judge-by-digest]])
- **自愈锚点**:刷新滚动源页的最后一步就是回写 digest;忘写 → 该源**永远 pending**——暴露而非静默漏更新。该条款载明于 fetcher-contract 文档(→ [[concepts/fetcher-adapter-contract]])。(同上)
- **pending 持久重算原则**(纯文本待晋升,暂由本页与 [[entities/sync-tool]] 承载):pending = f(raw/, wiki/sources/),持久重算、不依赖一次性台账,重跑恒得同一结果——sha256 判新是该原则在 rolling 管线的落地。(同上,强化)
- **工具去 domain 化**(纯文本待晋升):版本号是 domain 相关口径(有的滚动源根本没有版本号),sha256 对任何滚动源成立。(同上,例证)
- **faithful 快照与 dated 派生分离**;快照变化记「演进」(W-ING-3)。(同上)
- **接入侧**:rolling 型适配器抄 `adapters/rolling_source.skeleton.py`,与 pull 型同受 CONTRACT 约束。(例证:[[sources/2026-07-20-howto-add-fetcher-adapter]])

## 演变与争议

- 演进:M1 时期 rolling 判新口径不统一 → 0.2.0 经 render-once 三方合并统一为 `rolling_digest`(UPGRADING 0.2.0 迁移清单「rolling 判新统一 rolling_digest 口径」→ [[concepts/framework-upgrade-protocol]])。无未决 ⚠️。

## 相关概念

- [[entities/sync-tool]] —— 判新逻辑内建于 sync 管线(现场重算 + 比对)。
- [[concepts/fetcher-adapter-contract]] —— rolling 判新是合同的一个条款面。
- [[concepts/framework-upgrade-protocol]] —— 0.2.0 口径统一的迁移载体。

## 来源

- [[sources/2026-07-20-adr-rolling-judge-by-digest]](强化,裁决记录与权威出处)
- [[sources/2026-07-20-howto-add-fetcher-adapter]](例证,rolling skeleton 接入)

## 未解之处

- 本实例暂无 rolling 管线,判新机制未在本实例实测(依据为框架 spec/docs 与 hello-wiki 夹具)。
- pending-persistent-recompute、tool-de-domainization 独立概念页待晋升(记 followups)。
