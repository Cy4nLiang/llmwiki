---
title: "ADR:框架形态终裁 hybrid 模板仓库(D1)"
description: "查『llmwiki 为什么是模板仓库而不是 plugin/协议』『三候选 lens 得分』『6 项嫁接机制从哪来』时读本页;独有价值:D1 终裁记录 + 3-lens 评分表 + 嫁接清单溯源。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-adr-form-factor-hybrid-template-repo.md
source_kind: adr
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki-dev"]
tags: [adr, cluster/form-factor]
status: draft
ingest_tier: full
---

# ADR:框架形态终裁 hybrid 模板仓库(D1)

## 一句话摘要 / TL;DR

llmwiki 框架形态定为 **hybrid 模板仓库**:模板仓库为主体,嫁接另两个候选方案(plugin 派、协议派)的 6 项机制;2026-07-19 用户终裁(D1),与评审推荐一致。

## 关键论点 / Key Claims

- 裁决依据:agent-efficacy(agent 使用效率与准确性)是用户的终极目标且权重最高;模板仓库是唯一把「已被 golden 实测验证的阅读协议」**确定性复制**给新 domain 的形态——实例全持有、可 grep、无 skill 触发概率、无跨界指针、无自著方差。
- 模板仓库的短板在「框架演进与升级路径」lens(6 分),通过 6 项嫁接补齐,来源分别是 WIKI-SPEC(协议派)与 plugin 派。
- 检索成本证据(8.4x 等)仅以「参考实例 newpj4 实测」口径引用,不作通用承诺。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 三候选 × 3 lens 得分(0–10,出处 `docs/plans/llmwiki-framework-prd.md` §2):
  - 跨项目复用性与实例化成本:模板仓库派 WikiKit **8** / plugin 派 llm-wiki-kit 7 / 协议派 WIKI-SPEC 5;
  - agent 使用效率与准确性:**8** / 6 / 4.5;
  - 框架演进与升级路径:6 / **8** / 7。
- 6 项嫁接:① 规则 ID(W-* 命名空间,WIKI-SPEC);② 钉版快照(framework/VERSION + base/ 三方合并基线,WIKI-SPEC);③ --adopt 存量收编(plugin 派);④ ingest 分档 light 档(plugin 派);⑤ hello-wiki CI 夹具(plugin 派);⑥ 工作流动词本地化为实例本地 .claude/skills/(改造自 plugin 派)。
- 终裁:2026-07-19,用户裁定 D1;方法:13 agents,workflow wf_e4ae1412(出处 prd §10)。
- 出处锚点:`docs/plans/llmwiki-framework-prd.md` §2、§10;`docs/plans/llmwiki-framework-spec.md` §1。

## 我学到了什么 / Takeaways

- 形态之争的本质是「协议的分发方式」:模板仓库赢在确定性复制,输在演进——于是把演进机制(规则 ID、钉版快照)从败选方案里嫁接过来,而不是换形态。
- lens 加权要回到用户终极目标:三个 lens 得分互有胜负,裁决靠「agent-efficacy 权重最高」这一先验。
- 实测数字跨 domain 引用要降级口径:「参考实例 newpj4 实测」而非通用承诺。

## 与其它来源的关系 / Connections

- 强化:[[syntheses/framework-design-evolution]] —— D1 终裁是跨里程碑设计叙事的起点(形态定盘 → M1–M3 落地)。
- 扩展:[[concepts/framework-upgrade-protocol]] —— 嫁接项②(钉版快照 framework/VERSION + base/ 三方合并基线)直接构成升级协议的基线机制。
- 强化:[[concepts/deterministic-render]] —— D1 裁决理由「确定性复制/无自著方差」与确定性渲染纪律同源。
- 扩展:[[concepts/file-ownership-three-tiers]] —— 「实例全持有」前提由三档归属操作化落地。
- 例证:[[entities/run-ci]] —— hello-wiki CI 夹具(嫁接项⑤)落地为 tests/run_ci.py 全闭环。
- 例证(纯文本待晋升):ingest 分档 light 档(嫁接项④,建议 concepts/ingest-tiering)、W-* 规则 ID 命名空间(嫁接项①,建议 concepts/rule-id-namespace)、工作流动词本地化 .claude/skills/(嫁接项⑥,建议 concepts/local-workflow-skills)。

## 引用片段 / Quotes

> agent-efficacy 是用户的终极目标且权重最高。模板仓库是唯一把「已被 golden 实测验证的阅读协议」**确定性复制**给新 domain 的形态:实例全持有、可 grep、无 skill 触发概率、无跨界指针、无自著方差。

> 检索成本证据(8.4x 等)仅以「参考实例 newpj4 实测」口径引用,不作通用承诺。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[syntheses/framework-design-evolution]](强化)、[[concepts/framework-upgrade-protocol]](扩展)、[[concepts/deterministic-render]](强化)、[[concepts/file-ownership-three-tiers]](扩展)、[[entities/run-ci]](例证)——共 5,满足 full 档下限(W-ING-1)。
- reduce 裁决:ingest-tiering / rule-id-namespace / local-workflow-skills 各仅 1 源提及(rule-of-three 未达)保持纯文本,记 followups 待晋升;hello-wiki-fixture 并入 [[entities/run-ci]] 承载。
- 档位:full(source_kind=adr 映射)。
- W-SEC-1:原文为仓内一手 ADR,未发现指令性注入内容。
