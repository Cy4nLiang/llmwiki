---
title: greeter 服务
description: "问『greeter 是什么/默认行为/启动加载了什么/版本时间线』读本页:本库唯一服务实体,汇集默认口径、加载规则与演进史。"
type: entity
created: 2026-07-16
updated: 2026-07-17
tags: [service, cluster/greeting, team-infra]
status: mature
sources: [[sources/2026-07-01-adr-greeting-default]]
aliases: ["问候服务", "greeter service"]
---

# greeter 服务

## 概述

greeter 是 hello-wiki 项目的示例问候服务:接收可选 `lang` 参数,返回一句按
[[concepts/greeting-protocol]] 渲染的问候;渲染失败按 [[concepts/localization-fallback]]
降级。

## 关键事实

- 默认问候语:中文「你好,世界」(来源:[[sources/2026-07-01-adr-greeting-default]])。
- 启动时只加载 `locales/registry.txt` 登记过的语言;仅放 `.msg` 不登记无效
  (来源:[[sources/2026-07-08-howto-add-greeting-language]])。
- 文案与资源纪律以团队风格指南为准,现行 v3(来源:[[sources/guide-style-guide]])。

## 关系网络

- 实现协议:[[concepts/greeting-protocol]](默认语言与 `lang` 参数语义)。
- 依赖机制:[[concepts/localization-fallback]](zh → en → ascii 三级回退)。
- 设计叙事:[[syntheses/greeting-design-story]](三份来源如何拼出当前形态)。

## 时间线

- 2026-06-20:风格指南 v1,问候文案纪律成文(来源:[[sources/guide-style-guide]])。
- 2026-07-01:ADR-001 定默认中文口径与回退链(来源:[[sources/2026-07-01-adr-greeting-default]])。
- 2026-07-05:emoji 乱码踩坑,ascii 档补 `strip_non_ascii()`(来源:[[sources/2026-07-05-pitfall-emoji-encoding]])。
- 2026-07-10:风格指南演进至 v3,回退链纪律入指南(演进;来源:[[sources/guide-style-guide]])。

## 来源

[[sources/2026-07-01-adr-greeting-default]] · [[sources/2026-07-08-howto-add-greeting-language]] · [[sources/guide-style-guide]] · [[sources/2026-07-05-pitfall-emoji-encoding]]

## 待补充

- 时段问候(早上好/晚上好)实验已回滚,未建概念页(rule-of-three 未达,记 followups 待晋升)。
