---
title: "踩坑:模板 HTML 注释内示例 wikilink 造成新实例开箱断链"
description: "新渲染实例零内容却报断链、或要在模板/指引里写示例链接语法时读本页:断链检查不解析注释语境,裸写的示例链接会被当真;修法是示例语法一律反引号化。"
type: source
created: 2026-07-20
ingest_tier: light
raw_file: raw/inbox/2026-07-20-pitfall-template-comment-example-wikilink.md
source_kind: pitfall
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: [llmwiki-dev]
tags: [pitfall, templates, lint, cluster/wikilink-discipline]
status: draft
---

# 踩坑:模板 HTML 注释内示例 wikilink 造成新实例开箱断链

## 一句话摘要 / TL;DR

模板 HTML 注释里的填写指引带示例 wikilink,lint 断链检查按文本匹配 `[[...]]` 不解析注释语境,把示例当真实引用——每个新渲染实例开箱即报断链;修法是示例链接一律反引号化(`` `[[wikilink]]` ``),0.2.0 经 render-once 三方合并改净存量模板。

## 关键论点 / Key Claims

- 断链检查按文本匹配 `[[...]]`,模板注释里的「示例」与正文里的「引用」在语法上无法区分;而框架验收标准恰是「新实例开箱 lint 全绿」,两者相撞即开箱断链。
- 模板里的一切「示例语法」都要用与真实语法不同的形态书写(反引号/占位符),否则示例会被机器当真。
- 这与 newpj4 契约「单提及目标用纯文本不用 wikilink」是同一条纪律的模板侧投影:凡不该被当作真实引用的 `[[...]]`,就不要以裸形态出现。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 触发文件:`templates/wiki/overview.md` 等 wiki 骨架模板的 HTML 注释指引(如「每行 `[[syntheses/x]]` · `[[concepts/y]]`」示例——本页照抄时同样必须反引号化,正是本坑的纪律)。
- 判定规则:W-PAGE-3(断链 = 图导航基础设施故障,lint fail)。
- 修法落位(已核实):现行 `templates/wiki/overview.md` 注释内示例链接均为反引号形态(行 26、33–34);渲染进本实例的 `wiki/overview.md` 同样干净。
- 版本记录(已核实):`framework/UPGRADING.md` 0.2.0(2026-07-19,判级 MINOR)迁移清单含「overview 注释示例链接反引号化」,归 render-once 三方合并条目。

## 我学到了什么 / Takeaways

- 「示例会被机器当真」是模板工程的通用坑:凡机检语法(wikilink、指令、宏),示例必须换形态(代码 span/占位符),不能依赖「人看得出这是示例」。
- 框架级验收(开箱 lint 全绿)会把模板里的瑕疵放大成每个实例的出生缺陷——模板质量门禁应等同产物质量门禁。

## 与其它来源的关系 / Connections

- 例证:[[entities/lint-wiki]] —— 断链检查的文本匹配实现(不解析注释语境)是本坑的机检侧成因。
- 例证:[[concepts/framework-upgrade-protocol]] —— 0.2.0 用 render-once 三方合并把存量模板改净,是该机制的实际应用案例(三方合并归属升级协议页)。
- 扩展(纯文本待晋升):wikilink 纪律(wikilink-discipline)—— W-PAGE-3 从「写作时不建单提及链」扩展出「模板示例反引号化」的模板侧推论;仅本篇展开,暂由 [[entities/lint-wiki]] 设计局限段承载。
- 单提及(纯文本,未建链):templates/wiki/overview.md 模板文件本身、「开箱 lint 全绿」验收叙事(out-of-box-green)——仅本篇触及,待晋升。

## 引用片段 / Quotes

> 断链检查按文本匹配 `[[...]]`,模板注释里的「示例」与正文里的「引用」在语法上无法区分;而框架的验收标准恰恰是「新实例开箱 lint 全绿」。——raw 原文「根因」节。

## 处理记录 / Processing Notes

- 档位:light(source_kind=pitfall,touch 下限 1)。
- 触及/更新页面(reduce 落实,2026-07-20):[[entities/lint-wiki]](例证)、[[concepts/framework-upgrade-protocol]](例证)——共 2,超出 light 档下限(W-ING-1)。
- reduce 裁决:wikilink-discipline / render-once-three-way-merge(并入升级协议页)/ out-of-box-green 均未达 rule-of-three,降纯文本并记 followups 待晋升。
- W-SEC-1:内生 inbox 源,未见指令性注入内容。
