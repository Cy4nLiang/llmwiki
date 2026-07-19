---
title: "ADR:适配器 manifest 容器冻结为 {\"articles\": {slug: {...}}}"
description: "写新 fetcher 适配器、或 build_site 读不到 manifest 条目排障时读本页;独有价值:容器形状 v1 冻结裁决 + 六必填字段 + items→articles 自动迁移史。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-adr-manifest-container-articles.md
source_kind: adr
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki-dev"]
tags: [adr, cluster/adapter-contract]
status: draft
ingest_tier: full
---

# ADR:适配器 manifest 容器冻结为 {"articles": {slug: {...}}}

## 一句话摘要 / TL;DR

0.3.0(M3)起,fetcher 适配器台账 `state/<pipeline>.manifest.json` 的容器形状 v1 冻结为顶层 `articles` 键 + 以 slug 为键的对象;这是实例自写适配器与框架工具(build_site/sync)之间的稳定读取合同。

## 关键论点 / Key Claims

- 冻结动机:容器键名漂移(如有的适配器写 `items`)会让 build_site **静默读不到条目**——多适配器与框架工具之间必须有稳定读取合同。
- slug 作键优于 list 容器:天然去重、幂等可续(已抓跳过按键查),省一次线性扫描。
- 兼容策略是「读旧写新」:build_site 兼容读取历史形态(顶层 `{"articles": dict|list}` 等旧样),但 `articles` 以外的容器键名不被识别;新适配器一律用冻结形状。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 冻结版本:0.3.0(M3);冻结形状:`{"articles": {slug: {...}}}`。
- manifest 六必填字段:slug / url(push 可空)/ title / date / fetched / raw_file;CONTRACT §11 自查清单有对应打勾项。
- 随框架发布的 `local_notes.py` 在 0.3.0 完成容器键 items→articles 迁移,**载入时自动迁移**旧台账(UPGRADING 0.3.0 frozen 覆盖清单)。
- 出处锚点:`llmwiki/adapters/CONTRACT.md` §4、§11;`llmwiki/framework/UPGRADING.md` 0.3.0 条目。

## 我学到了什么 / Takeaways

- 工具与自写扩展之间的接缝要尽早冻结形状:静默读不到条目比报错更危险,冻结 + 兼容读取把漂移风险收敛到合同层。
- 迁移的最佳落点是「载入时自动迁移」:旧台账无需手工改写,升级即自愈(local_notes 的 items→articles 即例)。
- 「读旧写新」是低成本兼容范式:读取端宽容历史形态,写入端只认冻结形状。

## 与其它来源的关系 / Connections

- 强化:[[concepts/fetcher-adapter-contract]] —— 容器形状 v1 冻结与六必填字段是适配器契约的核心条款。
- 例证:[[entities/sync-tool]] —— manifest 是 sync/build_site 与实例自写适配器之间的读取合同。
- 例证:[[concepts/framework-upgrade-protocol]] —— 迁移记入 UPGRADING 0.3.0 frozen 覆盖清单,逐版本迁移清单机制的实例。
- 演进:[[syntheses/framework-design-evolution]] —— 0.3.0 容器冻结是 M3 里程碑的接缝定版事件。
- 例证:[[concepts/file-ownership-three-tiers]] —— 实例自写适配器(instance 档)与框架 frozen 工具之间的接缝需要稳定合同。
- 例证(纯文本待晋升):build_site(合同的框架侧读取方,兼容历史形态但不识别 `items`,建议 entities/build-site);local_notes.py(0.3.0 items→articles 载入时自动迁移,建议 entities/local-notes-adapter)。

## 引用片段 / Quotes

> 多适配器(实例自写)与框架工具(build_site/sync)之间需要一个稳定的读取合同;容器键名漂移(如有的适配器写 `items`)会让 build_site 静默读不到条目。

> slug 作键天然去重、幂等可续(已抓跳过按键查),比 list 容器省一次线性扫描。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/fetcher-adapter-contract]](强化)、[[entities/sync-tool]](例证)、[[concepts/framework-upgrade-protocol]](例证)、[[syntheses/framework-design-evolution]](演进)、[[concepts/file-ownership-three-tiers]](例证)——共 5,满足 full 档下限(W-ING-1)。
- reduce 裁决:build-site / local-notes-adapter 各仅 1 源提及(rule-of-three 未达)降纯文本,记 followups 待晋升;其事实由 [[concepts/fetcher-adapter-contract]] 承载。
- 档位:full(source_kind=adr 映射)。
- W-SEC-1:原文为仓内一手 ADR,未发现指令性注入内容。
