---
title: 本地化回退链
description: "问『回退链精确顺序/ascii 档字符集规矩/回退目标怎么登记』读本页:zh → en → ascii 三级回退的定义、纪律与实测踩坑。"
type: concept
created: 2026-07-16
updated: 2026-07-17
tags: [fallback, cluster/greeting, team-app]
status: mature
sources: [[sources/2026-07-01-adr-greeting-default]]
aliases: ["本地化回退链", "localization fallback chain"]
---

# 本地化回退链

## 定义

本地化渲染失败时的三级降级顺序:**zh → en → ascii**(精确顺序,冻结;改动需走
ADR)。首次成文于 ADR-001(来源:[[sources/2026-07-01-adr-greeting-default]]),
v3 起入风格指南纪律(来源:[[sources/guide-style-guide]])。

## 核心要点

- 最后一档 ascii 必须是「任何终端可显示」的最小集:只允许可打印 ASCII。
- 语言降级与字符集降级是两件事:ascii 档渲染前执行 `strip_non_ascii()`,
  emoji 仅 zh/en 档保留(来源:[[sources/2026-07-05-pitfall-emoji-encoding]])。
- 每门语言的回退目标在 `locales/registry.txt` 声明,缺省回退 en
  (来源:[[sources/2026-07-08-howto-add-greeting-language]])。

## 演变与争议

- ADR-001 成文(2026-07-01)→ emoji 踩坑补字符集纪律(2026-07-05)→ 入风格指南
  v3(2026-07-10,演进)。无未决矛盾。

## 相关概念

- [[concepts/greeting-protocol]] —— 回退链服务于协议的「任何请求必有一句可显示问候」。

## 来源

[[sources/2026-07-01-adr-greeting-default]] · [[sources/2026-07-05-pitfall-emoji-encoding]] · [[sources/2026-07-08-howto-add-greeting-language]] · [[sources/guide-style-guide]]

## 未解之处

- (暂无)
