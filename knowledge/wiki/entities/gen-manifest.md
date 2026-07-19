---
title: gen_manifest.py(MANIFEST 派生工具)
description: "查『MANIFEST.json 是谁生成的、能否手编』『改了 frozen 工具后要跑什么』『为何新实例误报 fork』时读本页;含分档投影规则与发版固化位置。"
type: entity
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/upgrade-protocol, tool, manifest]
status: draft
sources: ["[[sources/2026-07-20-adr-file-ownership-three-tiers]]", "[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]", "[[sources/2026-07-20-howto-release-framework-version]]"]
aliases: ["gen_manifest", "MANIFEST 生成工具", "manifest generator"]
verified: 2026-07-20
---

# gen_manifest.py(MANIFEST 派生工具)

## 概述

`tools/gen_manifest.py`:框架仓侧工具,从框架仓文件树**确定性重算** `framework/MANIFEST.json`(按路径排序、不写时间戳)。MANIFEST 记录每个文件的三档归属与 sha256,是升级协议判定 frozen 漂移的唯一基线。**MANIFEST 是派生物(W-IDX-1),勿手编**;改动 frozen 档后必须重导。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers]],例证;docstring 仓内核实:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])

## 关键事实

- 分档投影规则:frozen = `tools/**`、`schema/**`、`docs/**`、`evals/**`、`adapters/**`、`extras/**`;render-once = `CLAUDE.template.md`、`.claude/**`、`templates/**`;其余(README/LICENSE/framework/**、tests 夹具)归 meta。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers]])
- docstring 明写派生物定性:「MANIFEST 本身是派生物(W-IDX-1):由本工具从框架仓库文件树重算,勿手编;升级协议以其中 sha256 判定 frozen 漂移(W-UPG-1)」。(来源:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]],仓内核实)
- 发版第 4 步(CI 之前)固化重导:忘跑会让新实例 `lint --manifest` 误报 fork——基线陈旧伪装成实例改动。(强化:[[sources/2026-07-20-howto-release-framework-version]])
- 确定性保证:按路径排序、不写时间戳——同一文件树重算结果恒同。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers]])

## 关系网络

- [[concepts/file-ownership-three-tiers]] —— 三档归档的执行者与记录载体。
- [[concepts/framework-upgrade-protocol]] —— 发版六步的第 4 步;frozen 保真链的起点。
- [[entities/lint-wiki]] —— MANIFEST 的消费方(`--manifest` sha256 比对)。
- [[entities/run-ci]] —— 新鲜度兜底(phase_lint 对新渲染实例断言零漂移;h0 夹具固化重导顺序)。

## 时间线

- M2 验证阶段:踩到 MANIFEST 陈旧 → 新实例 fork 误报(「基线落后」与「实例改动」在 hash 比对里不可区分)。(来源:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])
- 修法三件套落位:docstring 派生物定性 / run_ci phase_lint 零漂移断言 / 发版清单固化重导步骤。(同上,演进)

## 来源

- [[sources/2026-07-20-adr-file-ownership-three-tiers]](例证,分档投影与确定性)
- [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]](例证,派生物定性与失效模式)
- [[sources/2026-07-20-howto-release-framework-version]](强化,发版固化位置)

## 待补充

- 派生物纪律独立概念页(derived-artifact-discipline)待晋升后回链。
- gen_manifest 的 CLI 参数面(如有)未入库。
