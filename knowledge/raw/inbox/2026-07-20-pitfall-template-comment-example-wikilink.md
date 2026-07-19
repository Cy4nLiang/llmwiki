---
title: "踩坑:模板 HTML 注释内示例 wikilink 造成新实例开箱断链"
date: 2026-07-20
kind: pitfall
---

# 现象

wiki 骨架模板(如 `templates/wiki/overview.md`)的 HTML 注释里写了填写指引,指引中带示例链接(如「每行 [[syntheses/x]] · [[concepts/y]]」)。lint 的断链检查(W-PAGE-3)不解析注释语境,把示例当真实 wikilink 解析——目标页当然不存在,于是**每个新渲染实例开箱即报断链**,零内容也不干净。

# 根因

断链检查按文本匹配 `[[...]]`,模板注释里的「示例」与正文里的「引用」在语法上无法区分;而框架的验收标准恰恰是「新实例开箱 lint 全绿」。

# 修法(已落位)

示例链接一律**反引号化**:`` `[[wikilink]]` ``——代码 span 内的链接不再被当作引用解析,指引的可读性不受影响。0.2.0 以 render-once 三方合并把存量模板改净(UPGRADING 0.2.0 迁移清单「overview 注释示例链接反引号化」)。现行模板可核实:`templates/wiki/overview.md` 注释内示例均为反引号形态,渲染进本实例的 `wiki/overview.md` 同样干净。

# 教训

模板里的一切「示例语法」都要用与真实语法不同的形态书写(反引号/占位符),否则示例会被机器当真。这与 newpj4 契约「单提及目标用纯文本不用 wikilink」是同一条纪律的模板侧投影。

# 出处

- `llmwiki/templates/wiki/overview.md`(注释内 `` `[[wikilink]]` `` 示例);
- `llmwiki/framework/UPGRADING.md` 0.2.0 迁移清单(render-once 条目);
- `llmwiki/framework/RULES.md` W-PAGE-3(断链 = 基础设施故障)。
