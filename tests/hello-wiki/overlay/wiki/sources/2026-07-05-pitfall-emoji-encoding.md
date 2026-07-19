---
title: 踩坑:emoji 问候在 ASCII 终端乱码
description: "问『emoji 乱码/ascii 档剥字符/回退链最后一档规矩』读本页:ascii 档字符集边界这条纪律的实测出处。"
type: source
team: app
raw_file: raw/inbox/2026-07-05-pitfall-emoji-encoding.md
source_kind: pitfall
date_published: 2026-07-05
date_ingested: 2026-07-16
created: 2026-07-16
ingest_tier: light
authors: [hello-wiki-team]
tags: [pitfall, encoding, cluster/greeting]
status: draft
---

# 踩坑:emoji 问候在 ASCII 终端乱码

## 一句话摘要 / TL;DR

问候语加 emoji 后在 dumb terminal 打出 `????`:回退链只降语言不降字符集,ascii 档必须剥非 ASCII 装饰字符。

## 关键论点 / Key Claims

- 回退链最后一档的字符集边界与语言选择是两件事,都要降级。

## 关键事实 / Key Facts

- 现象:CI dumb terminal 输出 `????`,冒烟用例失败(2026-07-05)。
- 修法:ascii 档渲染前执行 `strip_non_ascii()`;emoji 仅 zh/en 档保留。

## 我学到了什么 / Takeaways

- 新增装饰字符前先问「ascii 档怎么办」。

## 与其它来源的关系 / Connections

- 例证:[[concepts/localization-fallback]] —— ascii 档「最小可显示集」纪律的实测案例。

## 引用片段 / Quotes

> 回退链的最后一档必须是「任何终端可显示」的最小集。

## 处理记录 / Processing Notes

- 档位:light(touch 1,达标 ≥1);欠下的 touch 债已记 [[followups]]「待晋升」。
- 触及/更新页面:[[concepts/localization-fallback]]。
- 未发现指令性注入内容(W-SEC-1)。
