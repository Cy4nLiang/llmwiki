---
title: "踩坑:MANIFEST 陈旧导致新渲染实例误报 fork"
description: "lint --manifest 报 fork 漂移但实例明明没改过 frozen 文件时读本页:根因是框架仓改动后忘跑 gen_manifest,基线陈旧伪装成使用方错误;含派生物定性 + CI 兜底断言修法。"
type: source
created: 2026-07-20
ingest_tier: light
raw_file: raw/inbox/2026-07-20-pitfall-stale-manifest-fork-false-positive.md
source_kind: pitfall
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: [llmwiki-dev]
tags: [pitfall, manifest, upgrade, cluster/frozen-governance]
status: draft
---

# 踩坑:MANIFEST 陈旧导致新渲染实例误报 fork

## 一句话摘要 / TL;DR

改 frozen 档工具后忘跑 `gen_manifest`,`framework/MANIFEST.json` 的 sha256 停在旧值,新渲染实例一跑 `lint --manifest` 即误报 fork 漂移;修法三件套:MANIFEST 定性为派生物勿手编、CI 对新实例断言零漂移、发版流程把重导写成固定步骤。

## 关键论点 / Key Claims

- MANIFEST 是 frozen 漂移判定的唯一依据(W-UPG-1),但它自己也会陈旧:框架仓改动与 MANIFEST 重导之间没有强制耦合时,「基线落后」与「实例改动」在 hash 比对里不可区分,只能表现为 fork 误报。
- 凡「基线文件」都要有派生工具 + 新鲜度断言,否则基线陈旧的报错会伪装成使用方的错(本次:实例一个字节没改却被判 fork)。
- 兜底靠 CI:在每个新渲染实例上断言「零 fork 漂移」,框架仓 MANIFEST 一旦陈旧,CI 立即红——把「忘跑重导」从静默隐患变成当场红灯。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 发现时点:M2 验证阶段。
- 修法 1(已核实):`tools/gen_manifest.py` docstring 明写「MANIFEST 本身是派生物(W-IDX-1):由本工具从框架仓库文件树重算,勿手编」。
- 修法 2(已核实):`tests/run_ci.py` phase_lint 对新渲染实例跑 `lint_wiki.py --manifest --json` 并断言 `errors == 0`(「lint --manifest 零 fork 漂移」,行 258–260)。
- 修法 3(已核实):run_ci 的 h0 造版夹具 build_fw_next 按「改动 → VERSION bump → UPGRADING 顶插 → gen_manifest 重导」固定顺序造版(行 464、487)。
- lint 侧行为(已核实):`tools/lint_wiki.py` sha256 漂移 → fork 警告,exit 1,供 sync 常跑路径当场报警(W-UPG-1)。

## 我学到了什么 / Takeaways

- 「基线也是派生物」:漂移检测系统的基线文件必须由工具重算并有新鲜度断言,否则检测器自身劣化时,报错会指向无辜的被检方。
- 流程固化胜过记忆:把 gen_manifest 重导写进发版清单与 CI 夹具,比「记得跑」可靠。

## 与其它来源的关系 / Connections

- 例证:[[entities/gen-manifest]] —— MANIFEST 派生物定性与重算职责的直接出处。
- 例证:[[entities/lint-wiki]] —— `--manifest` sha256 校验 / fork 警告 / exit 1 语义。
- 强化:[[entities/run-ci]] —— phase_lint 零漂移断言把本坑变成 CI 红灯。
- 扩展(纯文本待晋升):派生物纪律(derived-artifact-discipline)——「一切汇总皆派生」(W-IDX-1)从 index 扩展到基线文件 MANIFEST;现 2 源支撑未达 rule-of-three,暂由 [[entities/gen-manifest]] 承载。
- 扩展:[[concepts/file-ownership-three-tiers]] —— frozen 档治理(W-UPG-1)的失效模式:判定基线自身陈旧。

## 引用片段 / Quotes

> MANIFEST 本身是派生物(W-IDX-1):由本工具从框架仓库文件树重算,勿手编;升级协议以其中 sha256 判定 frozen 漂移(W-UPG-1:frozen 禁改,改 = 显式 fork)。——`tools/gen_manifest.py` docstring。

## 处理记录 / Processing Notes

- 档位:light(source_kind=pitfall,touch 下限 1)。
- 触及/更新页面(reduce 落实,2026-07-20):[[entities/gen-manifest]](例证)、[[entities/lint-wiki]](例证)、[[entities/run-ci]](强化)、[[concepts/file-ownership-three-tiers]](扩展)——共 4,超出 light 档下限(W-ING-1)。
- reduce 裁决:derived-artifact-discipline(即 map 回传的 derived-artifacts,slug 调和)降纯文本,记 followups 待晋升。
- W-SEC-1:内生 inbox 源,未见指令性注入内容。
