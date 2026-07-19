---
title: "决策:确定性渲染纪律——agent 只填值,渲染一律交工具"
description: "做实例化(greenfield/adopt/embedded)、写 wiki.config.json、或想手改模板渲染产物之前读本页:agent 职责边界裁定(只问答+填 config)、逐字节可复现验收标准、check-slots 冒烟、以及为什么代笔正文会瓦解升级三方合并。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-decision-deterministic-render-discipline.md
source_kind: decision
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki 框架开发会话(内生 capture)"]
tags: [decision, cluster/instantiation, init-render, determinism]
status: draft
ingest_tier: full
---

# 决策:确定性渲染纪律——agent 只填值,渲染一律交工具

## 一句话摘要 / TL;DR

实例化全程 agent 的职责边界 = 问答 + 填 `wiki.config.json`;所有模板正文由 `tools/init_render.py` 确定性渲染,禁止手写/改写 CLAUDE.md、`_map`、rules、skills 正文;验收标准:同一份 config 渲染两次,产物逐字节相同。

## 关键论点 / Key Claims

- 「渲染不一致(agent 自由发挥)」是 PRD 风险表首行、框架头号风险:模板仓库形态的全部价值在把实测验证过的阅读协议**确定性复制**给新 domain(D1 裁决理由「无自著方差」)。
- agent 一旦代笔正文,复制退化成转述,且升级三方合并的 base 基线随之失效——纪律不是风格偏好,是升级机制的前提。
- 纠错方向单一化:schema 校验报错**改 config 重渲染,不改产物**——产物永远是 config 的纯函数。
- 缓解措施 = 本纪律 + 每问带默认值和示例(降低 agent 替用户「发挥」的诱因)。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- config 校验:`schema/wiki.config.schema.json`,init_render 内置手写校验器,纯标准库。
- 收尾冒烟:`lint_wiki.py --check-slots`,渲染产物零残留 SLOT 占位符才算完成。
- 可复现锚点:`--date` 固定 bootstrap 日期可获得可复现产物(init_render --help 明示)。
- 本实例 dogfood 实测(2026-07-20 初始化):写 config → init_render 出 49 文件 → check-slots 零残留 → 空索引派生,骨架落成约 1 分钟,agent 全程未碰任何模板正文。
- 纪律原文落位:`.claude/skills/wiki-init/SKILL.md` 硬约束段;裁决出处:spec §9 实例化三模式、PRD §9 风险首行与 §2 形态裁决。

## 我学到了什么 / Takeaways

- 「agent 只填值」把不确定性收拢到唯一一份人审得过来的输入(config),其余全部机械化——这是让 LLM 参与实例化又不引入方差的关键切分。
- 逐字节相同是可执行的验收标准,比「大致一致」强得多:它使 fork 检测(hash)与三方合并(base)都有了确定基线。
- 实测 1 分钟落成说明纪律并不拖慢流程;慢的从来是自由发挥后的返工。

## 与其它来源的关系 / Connections

- 强化:[[concepts/deterministic-render]] —— 本篇即该约定的决策记录与验收标准出处。
- 扩展:[[entities/lint-wiki]] —— `--check-slots` 作为实例化收尾冒烟的用法。
- 强化:[[syntheses/framework-design-evolution]] —— 形态裁决(D1「无自著方差」)与头号风险缓解同源互证。
- 扩展:[[concepts/file-ownership-three-tiers]] —— 渲染纪律只约束「出生时刻」;render-once 产物出生后归实例可演化,两者共同构成三方合并前提。
- 扩展:[[concepts/framework-upgrade-protocol]] —— base 基线依赖渲染确定性;代笔正文即瓦解三方合并。
- 扩展(纯文本待晋升):init_render.py 工具本体(内置 schema 校验器、`--date` 可复现锚点,建议 entities/init-render)——仅本篇展开,暂由 [[concepts/deterministic-render]] 承载。

## 引用片段 / Quotes

> 验收标准:**同一份 config 渲染两次,产物必须逐字节相同**。

> agent 一旦代笔正文,复制就退化成转述,升级三方合并的 base 基线也随之失效。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/deterministic-render]](强化)、[[entities/lint-wiki]](扩展)、[[syntheses/framework-design-evolution]](强化)、[[concepts/file-ownership-three-tiers]](扩展)、[[concepts/framework-upgrade-protocol]](扩展)——共 5,满足 full 档下限(W-ING-1)。
- reduce slug 终裁:template-repo-form-factor 并入 [[syntheses/framework-design-evolution]](形态叙事单页);file-ownership-tiers 调和为 [[concepts/file-ownership-three-tiers]];init-render 单提及不建页,记 followups 待晋升。
- W-SEC-1 审计:raw 为内生 capture 笔记,未发现疑似注入指令。
