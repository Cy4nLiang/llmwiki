---
title: 文件所有权三档(frozen / render-once / instance)
description: "查『某文件升级会不会被覆盖、能不能改』『三档怎么判定』『frozen 漂移为何报 fork』时读本页;独有价值:三档判定规则 + 升级行为对照 + 逃生舱条款 + MANIFEST 陈旧失效模式。"
type: concept
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/upgrade-protocol, ownership, manifest]
status: draft
sources: ["[[sources/2026-07-20-adr-file-ownership-three-tiers]]", "[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]", "[[sources/2026-07-20-howto-add-fetcher-adapter]]", "[[sources/2026-07-20-howto-release-framework-version]]", "[[sources/2026-07-20-decision-deterministic-render-discipline]]", "[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]", "[[sources/2026-07-20-adr-manifest-container-articles]]"]
aliases: ["文件所有权三档", "file ownership three tiers", "frozen/render-once/instance"]
verified: 2026-07-20
---

# 文件所有权三档(frozen / render-once / instance)

## 定义

框架与实例之间的**每个文件**归入 frozen / render-once / instance 三档之一,归档记入 `framework/MANIFEST.json`,升级行为按档执行。判定规则是**裁决标准**而非清单:新增文件归档争议时按规则裁决并记档,不必等清单更新。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers|三档 ADR]],强化)

## 核心要点

- **三档判定规则**:frozen = 机器可检且 domain 无关;render-once = 需 domain 取值或 agent 散文、但由模板渲染出生;instance = 实例数据与实现。(来源:[[sources/2026-07-20-adr-file-ownership-three-tiers]])
- **升级行为对照**:frozen → hash 校验后整体覆盖,本地改动报 fork 警告(W-UPG-1);render-once → base × 现文件 × 新模板三方合并;instance → 永不触碰。(同上)
- **逃生舱条款**:「实例扩展附录」段与 `.claude/rules/local-*.md` 承诺永不合并冲突,任何版本迁移动作不得要求改写——升级协议的实例保护条款。(同上,扩展 → [[concepts/framework-upgrade-protocol]])
- **框架仓侧分档投影**(gen_manifest 规则):frozen = `tools/**`、`schema/**`、`docs/**`、`evals/**`、`adapters/**`、`extras/**`;render-once = `CLAUDE.template.md`、`.claude/**`、`templates/**`;其余(README/LICENSE/framework/**、tests 夹具)归 meta。(例证:[[entities/gen-manifest]])
- **frozen 漂移当场暴露**:`lint_wiki.py --manifest` 挂 sync 常跑路径,漂移报 fork 警告——未声明的改动会在升级时被覆盖丢失。(例证:[[entities/lint-wiki]])
- **失效模式(治理盲区,已修)**:MANIFEST 是漂移判定唯一依据,但它自己也会陈旧——框架仓改动与重导无强制耦合时,「基线落后」与「实例改动」在 hash 比对里不可区分,表现为 fork 误报(M2 验证阶段实际踩到)。修法三件套见 [[entities/gen-manifest]] 与 [[entities/run-ci]]。(来源:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive|stale-manifest 踩坑]],扩展)
- **采集层实例**:适配器本体落 instance 档由实例自持有,只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`——三档归属在采集层的投影;实例自写适配器与框架 frozen 工具之间的接缝由稳定读取合同兜住。(例证:[[sources/2026-07-20-howto-add-fetcher-adapter]]、[[sources/2026-07-20-adr-manifest-container-articles]] → [[concepts/fetcher-adapter-contract]])
- **发版侧按档处置**:frozen 档靠 MANIFEST hash 保真,render-once 档靠 UPGRADING 迁移清单 + 三方合并保演化。(例证:[[sources/2026-07-20-howto-release-framework-version]])
- **与确定性渲染的接缝**:渲染纪律只约束「出生时刻」;render-once 产物出生后归实例、可演化——两者共同构成升级三方合并的前提。(扩展:[[sources/2026-07-20-decision-deterministic-render-discipline]] → [[concepts/deterministic-render]])
- **形态背景**:D1 模板仓库形态的「实例全持有」前提,由三档归属操作化落地。(扩展:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]])

## 演变与争议

- 演进:M2 验证阶段踩到 MANIFEST 陈旧 fork 误报 → 修法固化(派生物定性 / CI 零漂移断言 / 发版清单必经步骤),详见 [[entities/gen-manifest]] 时间线。无未决 ⚠️。

## 相关概念

- [[concepts/framework-upgrade-protocol]] —— 三档是升级协议的输入:按档执行升级行为。
- [[concepts/deterministic-render]] —— 出生时刻的纪律;三档管出生之后的归属。
- [[concepts/fetcher-adapter-contract]] —— instance 档适配器与 frozen 工具之间的接缝合同。
- 纯文本待晋升:派生物纪律(derived-artifact-discipline,W-IDX-1 从 wiki 索引延伸到框架侧 MANIFEST——凡汇总皆派生、皆可确定性重算;目前 2 源支撑,记 followups)。

## 来源

- [[sources/2026-07-20-adr-file-ownership-three-tiers]](强化,权威裁决记录)
- [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]](扩展,frozen 治理失效模式)
- [[sources/2026-07-20-howto-add-fetcher-adapter]](例证,采集层归属)
- [[sources/2026-07-20-howto-release-framework-version]](例证,发版按档处置)
- [[sources/2026-07-20-decision-deterministic-render-discipline]](扩展,出生/演化边界)
- [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]](扩展,形态背景)
- [[sources/2026-07-20-adr-manifest-container-articles]](例证,接缝合同)

## 未解之处

- derived-artifact-discipline 是否值得独立概念页:现 2 源支撑(rule-of-three 未达),第三源出现后晋升。
