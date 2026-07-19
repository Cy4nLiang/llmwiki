---
title: 问候设计叙事:从 ADR 到风格指南
description: "问『问候这套设计怎么长成现在这样/各来源谁说了算』读本页:横跨 ADR、踩坑、how-to 与风格指南四份来源的全局叙事与裁决顺位。"
type: synthesis
created: 2026-07-17
updated: 2026-07-17
tags: [synthesis, cluster/greeting, cross-team]
status: mature
sources: [[sources/2026-07-01-adr-greeting-default]]
aliases: ["问候设计叙事", "greeting design story"]
---

# 问候设计叙事:从 ADR 到风格指南

## 问题

greeter 的问候行为由哪些决定拼成?口径冲突时谁说了算?

## 各方观点

- 决策层:[[sources/2026-07-01-adr-greeting-default]] 定默认中文与回退链。
- 实测层:[[sources/2026-07-05-pitfall-emoji-encoding]] 用一次故障补上字符集纪律。
- 操作层:[[sources/2026-07-08-howto-add-greeting-language]] 把回退链落到 registry 登记动作。
- 纪律层:[[sources/guide-style-guide]] 把上述沉淀为滚动指南(现 v3)。

## 证据强度

- 回退链 zh → en → ascii:三份来源互证([[concepts/localization-fallback]]),最强。
- 默认问候语口径:ADR 与指南示例不一致,弱一档(⚠️ 见 [[concepts/greeting-protocol]])。

## 当前结论

裁决顺位 = ADR > 风格指南示例 > 个人习惯:默认中文口径以 ADR-001 为准;
[[entities/greeter-service]] 的行为描述一律链回来源页,不复述二手口径。

## 反例与未解之处

- 风格指南 v4 是否修订示例口径,决定 ⚠️ 矛盾能否关闭。
- 时段问候实验(已回滚)未入库,操作教训暂存 followups。

## 引用来源

[[sources/2026-07-01-adr-greeting-default]] · [[sources/2026-07-05-pitfall-emoji-encoding]] · [[sources/2026-07-08-howto-add-greeting-language]] · [[sources/guide-style-guide]] · 问答缓存 [[queries/how-to-add-greeting-language]]
