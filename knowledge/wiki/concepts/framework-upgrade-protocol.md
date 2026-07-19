---
title: 框架升级协议(发版六步 + 实例跟版 + 门禁)
description: "框架仓要发版、实例要跟版、或查『UPGRADING 条目怎么写』『升级验收标准是什么』『钉版快照/三方合并基线怎么来的』时读本页;含 semver 判级三档与逐版本迁移清单机制。"
type: concept
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/upgrade-protocol, release, semver]
status: draft
sources: ["[[sources/2026-07-20-howto-release-framework-version]]", "[[sources/2026-07-20-adr-file-ownership-three-tiers]]", "[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]", "[[sources/2026-07-20-adr-manifest-container-articles]]", "[[sources/2026-07-20-adr-rolling-judge-by-digest]]", "[[sources/2026-07-20-pitfall-template-comment-example-wikilink]]", "[[sources/2026-07-20-decision-deterministic-render-discipline]]"]
aliases: ["框架升级协议", "framework upgrade protocol", "发版流程", "release flow", "升级门禁", "upgrade gates"]
---

# 框架升级协议(发版六步 + 实例跟版 + 门禁)

## 定义

框架版本演进到实例的完整合同:框架侧**发版六步**产出新版与迁移清单,实例侧 `/wiki-upgrade` 按文件三档执行升级,**双门禁**验收。基线机制 = 钉版快照(`framework/VERSION` + base/ 三方合并基线),迁移合同 = `framework/UPGRADING.md` 逐版本条目。(来源:[[sources/2026-07-20-howto-release-framework-version|发版 how-to]],扩展)

## 核心要点

- **发版六步(顺序有依赖)**:落改动 → semver 判级 → UPGRADING.md 顶插条目 → `gen_manifest.py` 重导 MANIFEST → `tests/run_ci.py` 全绿 → bump `framework/VERSION`(实例升级锚点)。MANIFEST 重导必须在 CI 之前、VERSION bump 在最后——顺序错了 CI 抓不住漂移。(来源:[[sources/2026-07-20-howto-release-framework-version]])
- **semver 判级**(判据在 UPGRADING.md 头部):MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订。(同上)
- **UPGRADING 条目格式**:变更摘要 / 迁移清单 / frozen 覆盖清单 / 验收;迁移清单逐条引 `W-*` 规则 ID(总表 `framework/RULES.md`,勿另造引用方式);「实例动作」必须可执行可核对;语义变更写明旧行为 → 新行为。(同上,扩展)
- **基线机制(钉版快照)**:`framework/VERSION` + base/ 三方合并基线,来自 WIKI-SPEC 嫁接(6 项嫁接之②)——补齐模板仓库形态在「演进」lens 的短板(6 分)。(扩展:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]])
- **升级行为按文件三档执行**:frozen hash 校验后整体覆盖 / render-once 三方合并 / instance 永不触碰;逃生舱例外(「实例扩展附录」+ `.claude/rules/local-*.md`)承诺永不合并冲突。(扩展:[[sources/2026-07-20-adr-file-ownership-three-tiers]] → [[concepts/file-ownership-three-tiers]])
- **实例侧跟版**:`/wiki-upgrade`(`tools/upgrade.py`):frozen hash 校验 / render-once 三方合并 / 预备份 / 门禁;**验收 = `lint --manifest` 零漂移 + golden 不回退(W-UPG-2),回退即回滚**。(强化:[[sources/2026-07-20-howto-release-framework-version]])
- **确定性渲染是三方合并的前提**:agent 一旦代笔模板正文,base 基线随之失效。(扩展:[[sources/2026-07-20-decision-deterministic-render-discipline]] → [[concepts/deterministic-render]])
- **流程自身被测试覆盖**:run_ci 的 h0 造版夹具按发版固定顺序模拟造版 + 升级四路径——流程改了测试先红。(例证:[[entities/run-ci]])

## 演变与争议

逐版本迁移清单机制的已落地实例(均为「演进」,无未决 ⚠️):

- 0.2.0(2026-07-19,MINOR):rolling 判新统一 `rolling_digest` 口径(演进:[[sources/2026-07-20-adr-rolling-judge-by-digest]]);overview 模板注释示例链接反引号化,经 render-once 三方合并改净存量模板(例证:[[sources/2026-07-20-pitfall-template-comment-example-wikilink]])。
- 0.3.0(M3):manifest 容器键 items→articles,记入 frozen 覆盖清单,`local_notes.py` 载入时自动迁移(例证:[[sources/2026-07-20-adr-manifest-container-articles]])。

## 相关概念

- [[concepts/file-ownership-three-tiers]] —— 升级行为的分档依据。
- [[concepts/deterministic-render]] —— base 基线成立的前提。
- [[entities/gen-manifest]] / [[entities/lint-wiki]] / [[entities/run-ci]] —— 发版与验收链上的三件工具。
- [[syntheses/framework-design-evolution]] —— 嫁接机制的形态之争背景。

## 来源

- [[sources/2026-07-20-howto-release-framework-version]](扩展 + 强化,六步流与门禁的操作说明书)
- [[sources/2026-07-20-adr-file-ownership-three-tiers]](扩展,按档升级行为与逃生舱)
- [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]](扩展,钉版快照嫁接来源)
- [[sources/2026-07-20-adr-manifest-container-articles]](例证,0.3.0 迁移清单实例)
- [[sources/2026-07-20-adr-rolling-judge-by-digest]](演进,0.2.0 口径统一实例)
- [[sources/2026-07-20-pitfall-template-comment-example-wikilink]](例证,render-once 三方合并应用案例)
- [[sources/2026-07-20-decision-deterministic-render-discipline]](扩展,三方合并前提)

## 未解之处

- UPGRADING 条目格式是否值得独立页(upgrading-doc):现单源提及,记 followups 待晋升。
- 多实例规模下升级成本(逐实例三方合并的人工量)未实测。
