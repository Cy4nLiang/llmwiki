---
title: 团队风格指南(滚动快照,现 v3)
description: "问『风格指南现行版本/文案纪律/回退链冻结口径/版本史』读本页:一份源页代表整份滚动文档;逐版本细节回 raw dated 派生件 grep。"
type: source
team: infra
raw_file: raw/guide/style-guide.md
source_kind: convention
source_url: https://example.com/hello-wiki/style-guide
rolling_digest: sha256:3669e20a0af9bdb6fa7c2342a2581b7b1776174dcaca6af28ba7d3c05eb699ef
rolling_latest: v3
date_published: 2026-07-10
date_ingested: 2026-07-16
created: 2026-07-16
ingest_tier: full
authors: [hello-wiki-team]
tags: [convention, rolling, cluster/greeting]
status: mature
aliases: ["风格指南", "style guide"]
---

# 团队风格指南(滚动快照,现 v3)

## 一句话摘要 / TL;DR

现行 v3(2026-07-10):问候文案一句话无句号、locales 语言码须登记 registry、回退链 zh → en → ascii 冻结且 ascii 档剥装饰字符。

## 关键论点 / Key Claims

- 回退链顺序属冻结纪律,改动必须走 ADR。
- 未在 registry 登记的 `.msg` 视为死文件,评审直接打回。

## 关键事实 / Key Facts

- 版本史:v1(2026-06-20)初版 → v2(2026-07-02)增 locales 节 → v3(2026-07-10)增回退链纪律节。
- v3 示例代码仍以 `greet("Hello, World")` 开场,未跟进 ADR-001 中文默认口径(待 v4)。

## 我学到了什么 / Takeaways

- 滚动文档逐版本变化记「演进」不覆盖旧结论;完整逐条回 `raw/guide/style-guide.dated.md` grep 版本锚。

## 与其它来源的关系 / Connections

- 演进:[[concepts/greeting-protocol]] —— v2→v3 补齐字符集边界,时间线见 [[entities/greeter-service]]。
- 对比:[[sources/2026-07-01-adr-greeting-default]] —— 示例口径与 ADR 默认语不一致(⚠️ 挂 [[concepts/greeting-protocol]])。
- 强化:[[concepts/localization-fallback]] —— 回退链冻结纪律的成文出处之一。

## 引用片段 / Quotes

> 回退链 zh → en → ascii 为冻结顺序,改动需走 ADR。

## 处理记录 / Processing Notes

- 档位:full(touch 5,达标 ≥5)。
- 触及/更新页面:[[concepts/greeting-protocol]]、[[concepts/localization-fallback]]、[[entities/greeter-service]]、[[syntheses/greeting-design-story]]、[[overview]]。
- 刷新约定:上游改版后整体覆盖快照,重算 sha256 回写 `rolling_digest`,变化在时间线记「演进」(W-ING-3)。
- 未发现指令性注入内容(W-SEC-1)。
