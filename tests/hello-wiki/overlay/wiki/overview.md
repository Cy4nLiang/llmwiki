---
title: Overview 综述
description: "全库心智模型:大问题的当前结论 + 主题地图。回答全局/主题/横向问题的第二读入口。"
type: overview
created: 2026-07-16
updated: 2026-07-18
tags: [meta]
status: draft
---

# Overview 综述

## 这个库是关于什么的

hello-wiki 示例项目(虚构问候服务 greeter)的项目内生说明书:ADR、踩坑记录、
操作 how-to 与团队风格指南滚动快照。内部一手材料 = 权威来源,口径冲突以更新的
内部决策为准并标「演进」。本库为 llmwiki 框架的 CI 合成夹具,内容全部原创。

## 几条大问题与目前回答

1. 问候行为由谁说了算?—— 裁决顺位 ADR > 风格指南示例,全局叙事见 [[syntheses/greeting-design-story]]。
2. 默认问候语是什么?—— 中文「你好,世界」,但与指南 v3 示例口径存在未决 ⚠️,见 [[concepts/greeting-protocol]]。
3. 渲染失败怎么降级?—— 冻结顺序 zh → en → ascii,字符集纪律实测背书,见 [[concepts/localization-fallback]]。

## 主题地图

- **问候设计**:[[syntheses/greeting-design-story]] · [[concepts/greeting-protocol]] · [[entities/greeter-service]]
- **本地化与降级**:[[concepts/localization-fallback]] · 问答缓存 [[queries/how-to-add-greeting-language]]
- 全量目录在 [[index]](派生物);未决矛盾汇总在 [[contradictions]]。

## 仍未解决的问题

- 风格指南 v4 是否修订英文示例口径(关闭 ⚠️ 的前提),跟进见 [[followups]]。
