---
title: 问答:怎么新增一门问候语言
description: "how-do-I 缓存:『新增一门语言要动哪几个文件/为什么 .msg 不生效』直接读本页答案,免重推导。"
type: query
created: 2026-07-18
updated: 2026-07-18
date_asked: 2026-07-18
tags: [query, howto, cluster/greeting]
status: mature
sources: [[sources/2026-07-08-howto-add-greeting-language]]
aliases: ["新增语言问答", "add language FAQ"]
---

# 问答:怎么新增一门问候语言

## 问题

给 greeter 新增一门问候语言(例:法语 fr)要做什么?为什么只放 `.msg` 文件不生效?

## 答案

1. `locales/fr.msg` 放问候正文,文件名即语言码([[sources/2026-07-08-howto-add-greeting-language]])。
2. `locales/registry.txt` 追加 `fr` 并声明回退目标(缺省 en,进入 zh → en → ascii 链;机制见 [[concepts/localization-fallback]])。
3. `make greet-test` 冒烟,强制覆盖回退链含 ascii 档。

只放 `.msg` 不生效是因为 [[entities/greeter-service]] 启动只加载 registry 登记过的语言——registry 是唯一登记处。

## 衍生问题

- 新语言的文案格式纪律?见 [[concepts/greeting-protocol]](一句话、无结尾句号)。

## 触发的 wiki 更新

- 无新页;本问答归档时确认 [[concepts/localization-fallback]] 已覆盖回退目标登记的操作面。
