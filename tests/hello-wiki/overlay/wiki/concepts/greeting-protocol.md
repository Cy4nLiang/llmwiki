---
title: 问候协议
description: "问『默认问候语/lang 参数语义/文案格式』读本页:默认口径与文案纪律的汇集面,含 ADR 与风格指南示例口径的未决 ⚠️ 矛盾。"
type: concept
created: 2026-07-16
updated: 2026-07-17
tags: [protocol, cluster/greeting, cross-team]
status: mature
sources: [[sources/2026-07-01-adr-greeting-default]]
aliases: ["问候协议", "greeting protocol"]
---

# 问候协议

## 定义

问候协议约定 greeter 对一次请求返回什么话:默认语言、`lang` 参数语义、文案格式
(一句话、无结尾句号)。

## 核心要点

- 默认问候语为中文「你好,世界」;显式 `lang` 参数优先(来源:[[sources/2026-07-01-adr-greeting-default]])。
- 语言码用 BCP 47 小写短码,文件名即语言码(来源:[[sources/guide-style-guide]])。
- 文案格式「一句话 + 无结尾句号」(来源:[[sources/guide-style-guide]])。
- 操作面(如何新增语言)见 [[sources/2026-07-08-howto-add-greeting-language]]。

## 演变与争议

> ⚠️ 矛盾:默认问候语的示例口径不一致。
> - [[sources/2026-07-01-adr-greeting-default]] 主张默认中文「你好,世界」
> - [[sources/guide-style-guide]] v3 示例代码仍以英文 `greet("Hello, World")` 开场
> 倾向以 ADR-001 为准(风格指南待 v4 修订示例),暂保留 ⚠️ 待上游裁决。

- 风格指南 v2→v3 属「演进」:补齐字符集边界,不构成矛盾(时间线见 [[entities/greeter-service]])。

## 相关概念

- [[concepts/localization-fallback]] —— 协议渲染失败后的降级机制。

## 来源

[[sources/2026-07-01-adr-greeting-default]] · [[sources/guide-style-guide]] · [[sources/2026-07-08-howto-add-greeting-language]]

## 未解之处

- 风格指南 v4 何时修订示例口径(见 [[syntheses/greeting-design-story]] 当前结论)。
