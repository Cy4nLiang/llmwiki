---
title: lint_wiki.py(实例机械 lint)
description: "查『lint 都查什么』『--manifest/--check-config/--check-slots 各干什么』『断链检查为何把注释示例当真』时读本页;含 fork 警告语义与已知设计局限。"
type: entity
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/lint, tool, quality-gate]
status: draft
sources: ["[[sources/2026-07-20-adr-file-ownership-three-tiers]]", "[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]", "[[sources/2026-07-20-pitfall-template-comment-example-wikilink]]", "[[sources/2026-07-20-howto-add-fetcher-adapter]]", "[[sources/2026-07-20-decision-deterministic-render-discipline]]", "[[sources/2026-07-20-howto-release-framework-version]]"]
aliases: ["lint_wiki", "wiki lint 工具", "机械体检"]
verified: 2026-07-20
---

# lint_wiki.py(实例机械 lint)

## 概述

`tools/lint_wiki.py`:实例侧机械 lint 工具,覆盖断链/必填字段/token 预算/索引新鲜度/staleness 等检查,并带三个专用子检查(`--manifest` / `--check-config` / `--check-slots`);挂 sync 常跑路径,是「机械层报告 → 语义层人审」双层体检的机械层。

## 关键事实

- **`--manifest`(W-UPG-1)**:以 sha256 对照 `framework/MANIFEST.json` 判 frozen 漂移;漂移报 fork 警告并 exit 1,供 sync 常跑当场报警——未声明的改动会在升级时被覆盖丢失。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers]]、[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]],仓内核实)
- **已知误报模式**:MANIFEST 基线陈旧时,fork 报错会伪装成实例改动(实例一个字节没改却被判 fork);根因在基线侧,兜底在 [[entities/run-ci]] 的零漂移断言。(例证:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])
- **断链检查的设计局限(如实记录)**:按文本匹配 `[[...]]` 实现(码块/行内码豁免),**不解析 HTML 注释语境**——模板注释里的「示例」与正文里的「引用」语法上无法区分,裸示例链接会被当真实引用报断链。修法在模板侧:示例语法一律反引号化。(例证:[[sources/2026-07-20-pitfall-template-comment-example-wikilink]])
- **`--check-config`**:管线注册与适配器常量一致性复验,适配器接入的固定验收动作之一。(例证:[[sources/2026-07-20-howto-add-fetcher-adapter]] → [[concepts/fetcher-adapter-contract]])
- **`--check-slots`**:渲染产物零残留 SLOT 占位符检查,实例化收尾冒烟。(扩展:[[sources/2026-07-20-decision-deterministic-render-discipline]] → [[concepts/deterministic-render]])
- **升级验收角色**:`lint --manifest` 零漂移是实例跟版双门禁之一(W-UPG-2,另一半是 golden 不回退)。(例证:[[sources/2026-07-20-howto-release-framework-version]])

## 关系网络

- [[concepts/file-ownership-three-tiers]] —— frozen 漂移暴露机制的执行者。
- [[concepts/framework-upgrade-protocol]] —— 升级门禁的机械层。
- [[entities/gen-manifest]] —— 上游基线生产者(消费其 MANIFEST)。
- [[entities/run-ci]] —— CI 内被逐实例调用(phase_lint)。
- [[entities/sync-tool]] —— 常跑搭档(sync 路径挂 lint)。

## 时间线

- 0.2.0:模板注释示例 wikilink 致新实例开箱断链——暴露文本匹配局限,修法落在模板侧(render-once 三方合并改净)。(来源:[[sources/2026-07-20-pitfall-template-comment-example-wikilink]],演进)

## 来源

- [[sources/2026-07-20-adr-file-ownership-three-tiers]](例证)· [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]](例证)· [[sources/2026-07-20-pitfall-template-comment-example-wikilink]](例证)· [[sources/2026-07-20-howto-add-fetcher-adapter]](例证)· [[sources/2026-07-20-decision-deterministic-render-discipline]](扩展)· [[sources/2026-07-20-howto-release-framework-version]](例证)

## 待补充

- 完整检查项清单(W-PAGE/W-LNT/W-ING 各项)未逐条入库,可从工具 docstring 派生。
- wikilink-discipline 概念页待晋升后回链(断链纪律的模板侧推论)。
