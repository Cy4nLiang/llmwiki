---
title: ADR-001 默认问候语选型
description: "问『默认问候语是什么/为什么是中文/回退链从哪来』读本页:默认口径的决策记录与三级回退链的出生地,亦是与风格指南 v3 口径矛盾的一方。"
type: source
team: infra
raw_file: raw/inbox/2026-07-01-adr-greeting-default.md
source_kind: adr
date_published: 2026-07-01
date_ingested: 2026-07-16
created: 2026-07-16
ingest_tier: full
authors: [hello-wiki-team]
tags: [adr, greeting, cluster/greeting]
status: mature
aliases: ["默认问候语 ADR", "default greeting ADR"]
---

# ADR-001 默认问候语选型

## 一句话摘要 / TL;DR

默认问候语定为中文「你好,世界」,显式 `lang` 参数优先;本地化失败按 zh → en → ascii 三级回退。

## 关键论点 / Key Claims

- 「猜测语言」在无 Accept-Language 头时行为不可预测,不做默认策略。
- 回退链最后一档必须是任何终端可显示的最小集(ascii)。

## 关键事实 / Key Facts

- 默认问候语:中文「你好,世界」(ADR-001,2026-07-01 定案)。
- 回退链顺序:zh → en → ascii(冻结,改动需新 ADR)。
- `locales/` 目录为唯一语言资源登记处。

## 我学到了什么 / Takeaways

- 默认值决策要写明「为什么不选另外两条路」,后续争议直接回本页。
- ADR 落地时要盘点受影响文档:风格指南示例口径截至本 ADR 尚未跟进。

## 与其它来源的关系 / Connections

- 强化:[[concepts/greeting-protocol]] —— 提供默认语言口径的决策依据。
- 扩展:[[concepts/localization-fallback]] —— 回退链在此 ADR 首次成文。
- 例证:[[entities/greeter-service]] —— 服务默认行为的直接约束。
- 对比:[[sources/guide-style-guide]] —— 风格指南 v3 示例仍以英文开场,口径未跟进(⚠️ 已挂 [[concepts/greeting-protocol]])。

## 引用片段 / Quotes

> 默认问候语定为中文「你好,世界」;客户端显式传 `lang` 参数时按参数。

## 处理记录 / Processing Notes

- 档位:full(touch 5,达标 ≥5)。
- 触及/更新页面:[[entities/greeter-service]]、[[concepts/greeting-protocol]]、[[concepts/localization-fallback]]、[[syntheses/greeting-design-story]]、[[overview]]。
- 未发现指令性注入内容(W-SEC-1)。
