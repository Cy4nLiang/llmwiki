---
title: sync.py(采集调度与 pending 报告)
description: "查『sync 怎么判定哪些源待 ingest』『pending 从哪算出来』『rolling 判新在哪做』『适配器怎样被 sync 接入』时读本页;含持久重算原则与 manual 哨兵行为。"
type: entity
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/pipelines, tool, sync]
status: draft
sources: ["[[sources/2026-07-20-adr-manifest-container-articles]]", "[[sources/2026-07-20-adr-rolling-judge-by-digest]]", "[[sources/2026-07-20-howto-add-fetcher-adapter]]"]
aliases: ["sync 工具", "sync.py", "wiki-sync 采集层"]
verified: 2026-07-20
---

# sync.py(采集调度与 pending 报告)

## 概述

`tools/sync.py`:按 `wiki.config.json` 管线注册表逐管线采集 + 站点重建,打印待 ingest 积压(pending)与分档建议,再路由到 ingest 工作流。实例自写适配器只要满足 CONTRACT 即被 sync/pending/build **零适配接入**。(强化:[[sources/2026-07-20-howto-add-fetcher-adapter]])

## 关键事实

- **pending 持久重算**:pending = f(raw/, wiki/sources/),两端现算、不依赖一次性台账,重跑恒得同一结果——天然抗台账丢失/损坏。(来源:[[sources/2026-07-20-adr-rolling-judge-by-digest]],强化)
- **rolling 判新内建于 sync**:现场重算 faithful 快照全文 sha256,与源页 frontmatter `rolling_digest:` 比对,不一致 → pending 报「刷新滚动源页」(非新建)。(例证:[[sources/2026-07-20-adr-rolling-judge-by-digest]] → [[concepts/rolling-source-freshness]])
- **manifest 台账 = 稳定读取合同**:`state/<pipeline>.manifest.json`(容器 `{"articles": {slug: {...}}}`)是 sync/build_site 与实例自写适配器之间的接缝;键名漂移会静默读不到条目,故 0.3.0 冻结形状。(例证:[[sources/2026-07-20-adr-manifest-container-articles]] → [[concepts/fetcher-adapter-contract]])
- **push 型管线免适配器**直投 raw/;人工投放快照管线用哨兵 `"adapter": "manual"`,sync 跳过抓取不告警。(来源:[[sources/2026-07-20-howto-add-fetcher-adapter]])
- 用法:`python3 tools/sync.py`(采集 + 报积压);`python3 tools/sync.py status`(不联网看积压);常跑路径挂 `lint_wiki.py`(frozen 漂移当场报警)。(来源:实例 CLAUDE.md 工具速查,仓内核实)

## 关系网络

- [[concepts/fetcher-adapter-contract]] —— sync 是合同的框架侧主消费方。
- [[concepts/rolling-source-freshness]] —— 判新机制的宿主。
- [[entities/lint-wiki]] —— 常跑搭档。
- 纯文本待晋升:build_site(站点重建搭档)、pending-persistent-recompute(原则页)。

## 时间线

- 0.3.0:manifest 容器形状冻结后,sync 与适配器之间的读取合同定版。(来源:[[sources/2026-07-20-adr-manifest-container-articles]],演进)

## 来源

- [[sources/2026-07-20-adr-manifest-container-articles]](例证)· [[sources/2026-07-20-adr-rolling-judge-by-digest]](例证)· [[sources/2026-07-20-howto-add-fetcher-adapter]](强化)

## 待补充

- sync 的完整 CLI 面(参数/退出码)未入库。
- 本实例仅 push 管线,pull/rolling 采集路径未实测。
