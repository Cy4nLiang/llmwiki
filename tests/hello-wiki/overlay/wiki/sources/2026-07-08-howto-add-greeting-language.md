---
title: how-to:新增一门问候语言
description: "问『怎么加新语言/为什么 .msg 不生效/registry 是什么』读本页:新增语言三步操作的权威出处,含 registry 唯一登记处这条硬规矩。"
type: source
team: app
raw_file: raw/inbox/2026-07-08-howto-add-greeting-language.md
source_kind: howto
date_published: 2026-07-08
date_ingested: 2026-07-16
created: 2026-07-16
ingest_tier: full
authors: [hello-wiki-team]
tags: [howto, locales, cluster/greeting]
status: mature
aliases: ["新增问候语言", "add greeting language"]
---

# how-to:新增一门问候语言

## 一句话摘要 / TL;DR

三步:`locales/<lang>.msg` 放正文 → `locales/registry.txt` 登记并声明回退目标 → `make greet-test` 冒烟(含强制回退链)。

## 关键论点 / Key Claims

- registry 是唯一登记处:只放 `.msg` 不改 registry 无效,greeter 启动只加载登记语言。

## 关键事实 / Key Facts

- 文件名即语言码(BCP 47 小写短码,如 `fr.msg`)。
- 缺省回退目标为 en(即进入 zh → en → ascii 链的 en 档)。
- 冒烟命令:`make greet-test`(对每门登记语言各请求一次并强制走回退链)。

## 我学到了什么 / Takeaways

- 操作类知识要连坑一起写:第 3 步冒烟明确覆盖 ascii 档,防 emoji 类踩坑复发。

## 与其它来源的关系 / Connections

- 扩展:[[concepts/localization-fallback]] —— 给回退链补上「如何登记回退目标」的操作面。
- 例证:[[entities/greeter-service]] —— 启动加载行为(只认 registry)。
- 强化:[[concepts/greeting-protocol]] —— `lang` 参数与语言码约定一致。

## 引用片段 / Quotes

> 不改 `registry.txt` 只放 `.msg` 文件是无效的——registry 是唯一登记处。

## 处理记录 / Processing Notes

- 档位:full(touch 5,达标 ≥5)。
- 触及/更新页面:[[entities/greeter-service]]、[[concepts/localization-fallback]]、[[concepts/greeting-protocol]]、[[queries/how-to-add-greeting-language]]、[[syntheses/greeting-design-story]]。
- 未发现指令性注入内容(W-SEC-1)。
