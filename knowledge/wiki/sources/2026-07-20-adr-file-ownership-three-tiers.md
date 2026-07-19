---
title: "ADR:文件所有权三档 frozen / render-once / instance 与判定规则"
description: "查『某文件升级时会不会被覆盖、能不能改』『frozen/render-once/instance 三档怎么判』『MANIFEST 是谁生成的、能否手编』时读本页;独有价值:三档判定规则表 + 逃生舱例外条款。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-adr-file-ownership-three-tiers.md
source_kind: adr
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki-dev"]
tags: [adr, cluster/upgrade-protocol]
status: draft
ingest_tier: full
---

# ADR:文件所有权三档 frozen / render-once / instance 与判定规则

## 一句话摘要 / TL;DR

框架与实例间每个文件归入 frozen / render-once / instance 三档之一,归档记入 `framework/MANIFEST.json`,升级行为按档执行——frozen hash 校验后整体覆盖(本地改动报 fork 警告 W-UPG-1)、render-once 三方合并、instance 永不触碰。

## 关键论点 / Key Claims

- 三档的判定规则是**裁决标准**而非清单:frozen = 机器可检且 domain 无关;render-once = 需 domain 取值或 agent 散文但由模板渲染出生;instance = 实例数据与实现。新增文件归档争议时按规则裁决并记入 MANIFEST。
- MANIFEST 本身是派生物(W-IDX-1),由 `tools/gen_manifest.py` 从文件树重算,禁手编;确定性:按路径排序、不写时间戳。
- frozen 漂移必须**当场暴露**:`lint_wiki.py --manifest` 挂 sync 常跑路径,未声明的改动在升级时会被覆盖丢失。
- 逃生舱例外:「实例扩展附录」段与 `.claude/rules/local-*.md` 承诺永不合并冲突,任何版本迁移动作不得要求改写。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 三档 × 升级行为:frozen → hash 校验后整体覆盖;render-once → base × 现文件 × 新模板三方合并;instance → 永不触碰。
- 框架仓库侧投影(gen_manifest 分档规则):frozen = `tools/**`、`schema/**`、`docs/**`、`evals/**`、`adapters/**`、`extras/**`;render-once = `CLAUDE.template.md`、`.claude/**`、`templates/**`;其余(README/LICENSE/framework/**、tests 夹具)归 meta。
- render-once 例子:CLAUDE.md、rules 枚举、meta 页、本地 skills;instance 例子:wiki/、raw/、state/、site/、config、adapters、golden。
- 出处锚点:`docs/plans/llmwiki-framework-spec.md` §1.3、§10;`llmwiki/tools/gen_manifest.py` docstring;`llmwiki/framework/RULES.md` W-UPG-1;`llmwiki/framework/UPGRADING.md`。

## 我学到了什么 / Takeaways

- 「判定规则 > 枚举清单」让归档决策可延展:新文件不必等清单更新,按裁决标准即可归档。
- 派生物纪律(W-IDX-1)不只管 wiki index,也管框架侧 MANIFEST——凡汇总皆派生、皆可重算。
- 升级安全的两根支柱:机检(hash + fork 警告)兜住 frozen,三方合并兜住 render-once;instance 靠「永不触碰」承诺 + 逃生舱条款保护实例私有内容。

## 与其它来源的关系 / Connections

- 强化:[[concepts/file-ownership-three-tiers]] —— 本 ADR 即该约定的裁决记录与权威出处。
- 扩展:[[concepts/framework-upgrade-protocol]] —— 升级行为按档执行;三方合并与逃生舱例外是升级协议的组成部分。
- 例证:[[entities/gen-manifest]] —— MANIFEST 由该工具确定性重算(排序、无时间戳)。
- 例证:[[entities/lint-wiki]] —— `--manifest` 校验 hash 与归档完整性,frozen 漂移报 fork 警告。
- 强化:派生物纪律(derived-artifact-discipline,纯文本待晋升)—— MANIFEST 是派生物、勿手编,是 W-IDX-1 在框架侧的延伸例;暂由 [[entities/gen-manifest]] 与 [[concepts/file-ownership-three-tiers]] 承载。
- 例证:[[syntheses/framework-design-evolution]] —— 三档判定规则是「谁能改什么」可裁决化的设计叙事一环。

## 引用片段 / Quotes

> 判定规则是**裁决标准**而非清单:新增文件归档争议时按规则裁决并记入 MANIFEST。

> 逃生舱例外:「实例扩展附录」段与 `.claude/rules/local-*.md` 承诺永不合并冲突,任何版本迁移动作不得要求改写。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/file-ownership-three-tiers]](强化)、[[concepts/framework-upgrade-protocol]](扩展)、[[entities/gen-manifest]](例证)、[[entities/lint-wiki]](例证)、[[syntheses/framework-design-evolution]](例证)——共 5,满足 full 档下限(W-ING-1)。
- reduce 裁决:derived-artifact-discipline 现 2 源支撑(rule-of-three 未达)降纯文本,记 followups 待晋升。
- 档位:full(source_kind=adr 映射)。
- W-SEC-1:原文为仓内一手 ADR,未发现指令性注入内容。
