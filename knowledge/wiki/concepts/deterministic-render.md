---
title: 确定性渲染纪律(agent 只填值,渲染交工具)
description: "做实例化(greenfield/adopt/embedded)、写 wiki.config.json、或想手改模板渲染产物之前读本页;含 agent 职责边界、逐字节可复现验收标准、check-slots 冒烟与 dogfood 实测。"
type: concept
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/instantiation, init-render, determinism]
status: draft
sources: ["[[sources/2026-07-20-decision-deterministic-render-discipline]]", "[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]"]
aliases: ["确定性渲染纪律", "deterministic render discipline", "agent 只填值"]
---

# 确定性渲染纪律(agent 只填值,渲染交工具)

## 定义

实例化全程 agent 的职责边界 = **问答 + 填 `wiki.config.json`**;所有模板正文由 `tools/init_render.py` 确定性渲染,禁止手写/改写 CLAUDE.md、`_map`、rules、skills 正文。**验收标准:同一份 config 渲染两次,产物逐字节相同**。(来源:[[sources/2026-07-20-decision-deterministic-render-discipline|渲染纪律决策]],强化)

## 核心要点

- **纠错方向单一化**:schema 校验报错**改 config 重渲染,不改产物**——产物永远是 config 的纯函数。(来源:[[sources/2026-07-20-decision-deterministic-render-discipline]])
- **动机链**:「渲染不一致(agent 自由发挥)」是 PRD 风险表首行、框架头号风险;模板仓库形态的全部价值在把实测验证过的阅读协议**确定性复制**给新 domain(D1 裁决理由「无自著方差」);agent 一旦代笔正文,复制退化成转述,且升级三方合并的 base 基线随之失效——纪律是升级机制的前提,不是风格偏好。(强化:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]] → [[syntheses/framework-design-evolution]])
- **工具支撑**(init-render 工具页待晋升,暂纯文本):init_render.py 内置手写 schema 校验器(`schema/wiki.config.schema.json`,纯标准库);`--date` 固定 bootstrap 日期可获得可复现产物(--help 明示)。(扩展:[[sources/2026-07-20-decision-deterministic-render-discipline]])
- **收尾冒烟**:`lint_wiki.py --check-slots`,渲染产物零残留 SLOT 占位符才算完成。(扩展 → [[entities/lint-wiki]])
- **dogfood 实测(2026-07-20 本实例初始化)**:写 config(agent 唯一的「写」)→ init_render 出 49 文件 → check-slots 零残留 → 空索引派生;骨架落成约 1 分钟,agent 全程未碰任何模板正文——纪律不拖慢流程,慢的从来是自由发挥后的返工。(例证:[[sources/2026-07-20-decision-deterministic-render-discipline]])
- **缓解配套**:每问带默认值和示例,降低 agent 替用户「发挥」的诱因。(同上)

## 演变与争议

- 无演进/矛盾记录;纪律原文落位 `.claude/skills/wiki-init/SKILL.md` 硬约束段,裁决出处 spec §9 与 PRD §9/§2。

## 相关概念

- [[concepts/file-ownership-three-tiers]] —— 纪律只约束「出生时刻」;render-once 产物出生后归实例可演化,两者共同构成三方合并前提。
- [[concepts/framework-upgrade-protocol]] —— base 基线依赖渲染确定性。
- [[syntheses/framework-design-evolution]] —— D1「无自著方差」裁决理由的同源叙事。

## 来源

- [[sources/2026-07-20-decision-deterministic-render-discipline]](强化,决策记录与验收标准出处)
- [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]](强化,形态裁决同源互证)

## 未解之处

- init-render 独立工具页待晋升(现单源提及,记 followups)。
- adopt/embedded 模式下对存量文件的渲染边界(何为「产物」何为「存量」)未在本库有源页展开。
