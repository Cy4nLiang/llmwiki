---
title: "How-to:发一个框架新版"
description: "框架仓(llmwiki/)有改动要发版、或实例要理解跟版验收口径时读本页:发版六步顺序(判级→UPGRADING 顶插→gen_manifest→CI→bump VERSION)+ semver 判级三档判据 + 实例侧 /wiki-upgrade 验收标准。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-howto-release-framework-version.md
source_kind: howto
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki 框架开发会话(内生 capture)"]
tags: [howto, cluster/release, semver, upgrade]
status: draft
ingest_tier: full
---

# How-to:发一个框架新版

## 一句话摘要 / TL;DR

框架发版六步:落改动 → semver 判级 → `framework/UPGRADING.md` 顶插条目 → `gen_manifest.py` 重导 MANIFEST → `tests/run_ci.py` 全绿 → bump `framework/VERSION`;实例侧对应 `/wiki-upgrade`,验收 = lint --manifest 零漂移 + golden 不回退(W-UPG-2)。

## 关键论点 / Key Claims

- 发版顺序有依赖:MANIFEST 重导必须在 CI 之前、VERSION bump 在最后(实例升级锚点)——顺序错了 CI 抓不住漂移。
- MANIFEST 是派生物:忘跑 `gen_manifest.py` 会让新实例误报 fork(与同日 pitfall 笔记同一教训,发版清单把它固化成必经步骤)。
- UPGRADING 条目是给实例 agent 消费的迁移合同:迁移清单逐条引 `W-*` 规则 ID(总表 `framework/RULES.md`,勿另造引用方式),「实例动作」必须可执行可核对,语义变更写明旧行为 → 新行为。
- CI 的 h0 夹具「模拟造版 + 升级四路径」验证的正是本发版流程本身——流程自身被测试覆盖。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- semver 判级(判据在 `framework/UPGRADING.md` 头部):MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订。
- frozen 档范围:tools/schema/docs/evals/adapters/extras;render-once 档:CLAUDE.template / .claude / templates。
- CI:`python3 tests/run_ci.py`,0.3.0 时点 119 断言(参考实例 newpj4 实测);含 h0 模拟造版 + 升级四路径。
- UPGRADING 条目格式:变更摘要 / 迁移清单 / frozen 覆盖清单 / 验收,按「条目格式约定」模板顶插。
- 实例侧工具:`/wiki-upgrade`(`tools/upgrade.py`):frozen hash 校验 / render-once 三方合并 / 预备份 / 门禁。

## 我学到了什么 / Takeaways

- 发版的本质是维护两条契约:frozen 档靠 MANIFEST hash 保真,render-once 档靠 UPGRADING 迁移清单 + 三方合并保演化——六步流程就是围绕这两条契约排序的。
- 规则引用统一走 `W-*` ID 而非文内锚点,让迁移清单跨版本可机检、可核对。
- 「验证发版流程的测试」与「发版流程」同构(h0 造版夹具),流程改了测试会先红——流程本身是被守护的。

## 与其它来源的关系 / Connections

- 扩展 + 强化:[[concepts/framework-upgrade-protocol]] —— 本篇即发版六步与 semver 判级的操作说明书;实例跟版验收 = manifest 零漂移 + golden 不回退(W-UPG-1/W-UPG-2,升级门禁并入该页)。
- 强化:[[entities/gen-manifest]] —— 「MANIFEST 是派生物,忘跑即误报 fork」与 stale-manifest pitfall 同口径互证。
- 例证:[[entities/run-ci]] —— 119 断言、h0 造版夹具覆盖发版四路径。
- 例证:[[entities/lint-wiki]] —— `lint --manifest` 零漂移是跟版验收的机械层。
- 例证:[[concepts/file-ownership-three-tiers]] —— frozen 与 render-once 两档在发版判级与迁移中的不同处置。

## 引用片段 / Quotes

> **重导 MANIFEST**:`python3 tools/gen_manifest.py`(MANIFEST 是派生物,忘跑会让新实例误报 fork——见同日 pitfall 笔记)。

> 迁移清单逐条引 `W-*` 规则 ID(总表 `framework/RULES.md`,勿另造引用方式);「实例动作」必须可执行可核对,语义变更写明旧行为 → 新行为。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/framework-upgrade-protocol]](扩展+强化)、[[entities/gen-manifest]](强化)、[[entities/run-ci]](例证)、[[entities/lint-wiki]](例证)、[[concepts/file-ownership-three-tiers]](例证)——共 5,满足 full 档下限(W-ING-1)。
- reduce slug 终裁:framework-release-flow / upgrade-gates 两个提议目标并入 [[concepts/framework-upgrade-protocol]] 单页(发版与跟版是同一协议的两侧);file-ownership-tiers 调和为 [[concepts/file-ownership-three-tiers]];upgrading-doc(UPGRADING 条目格式)单提及不建页,记 followups 待晋升。
- W-SEC-1 审计:raw 为内生 capture 笔记,未发现疑似注入指令。
