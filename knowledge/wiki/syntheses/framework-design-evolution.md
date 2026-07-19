---
title: 框架设计演进(形态终裁 D1 → M1–M3 淬炼)
description: "查『llmwiki 为什么是模板仓库形态』『三候选怎么比的』『6 项嫁接从哪来』『M1–M3 各踩了什么坑、沉淀了什么机制』时读本页;跨里程碑设计叙事总入口。"
type: synthesis
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/form-factor, design-narrative, cross-milestone]
status: draft
sources: ["[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]", "[[sources/2026-07-20-decision-deterministic-render-discipline]]", "[[sources/2026-07-20-adr-rolling-judge-by-digest]]", "[[sources/2026-07-20-adr-manifest-container-articles]]", "[[sources/2026-07-20-adr-file-ownership-three-tiers]]", "[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]", "[[sources/2026-07-20-pitfall-template-comment-example-wikilink]]"]
aliases: ["框架设计演进", "framework design evolution", "模板仓库形态", "template repo form factor", "D1 终裁"]
---

# 框架设计演进(形态终裁 D1 → M1–M3 淬炼)

## 问题

llmwiki 框架为什么长成「hybrid 模板仓库」这个形态?形态之争如何裁决、败选方案的机制如何被嫁接、纪律与合同如何在 M1–M3 的踩坑中逐步淬炼成机检与流程?

## 各方观点

三候选 × 3 lens 得分(0–10;出处 PRD §2,方法:13 agents,workflow wf_e4ae1412):

| lens | 模板仓库派 WikiKit | plugin 派 llm-wiki-kit | 协议派 WIKI-SPEC |
|---|---|---|---|
| 跨项目复用性与实例化成本 | **8** | 7 | 5 |
| agent 使用效率与准确性 | **8** | 6 | 4.5 |
| 框架演进与升级路径 | 6 | **8** | 7 |

裁决先验:**agent-efficacy 权重最高**(用户终极目标)。模板仓库是唯一把「已被 golden 实测验证的阅读协议」**确定性复制**给新 domain 的形态——实例全持有、可 grep、无 skill 触发概率、无跨界指针、无自著方差。(来源:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]],强化)

## 证据强度

- 一手裁决记录(PRD §2/§10、spec §1),内部权威口径,仓内可核实。
- 检索成本数字(8.4x 等)仅以「参考实例 newpj4 实测」口径引用,**不作通用承诺**。
- M1–M3 踩坑与修法均有仓内锚点(UPGRADING 条目、代码行号)核实,见各源页。

## 当前结论

1. **2026-07-19 用户终裁 D1:hybrid 模板仓库**——模板仓库为主体,嫁接败选方案 6 项机制;与评审推荐一致。(强化:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]])
2. **形态之争的本质是「协议的分发方式」**:模板仓库赢在确定性复制、输在演进,于是把演进机制从败选方案嫁接过来而非换形态。6 项嫁接:① W-* 规则 ID 命名空间(WIKI-SPEC);② 钉版快照 framework/VERSION + base/ 三方合并基线(WIKI-SPEC → [[concepts/framework-upgrade-protocol]]);③ --adopt 存量收编(plugin 派);④ ingest 分档 light 档(plugin 派);⑤ hello-wiki CI 夹具(plugin 派 → [[entities/run-ci]]);⑥ 工作流动词本地化为实例本地 .claude/skills/(改造自 plugin 派)。
3. **头号风险是「渲染不一致(agent 自由发挥)」**(PRD 风险表首行):缓解 = 确定性渲染纪律(agent 只填值,验收逐字节相同)——代笔即瓦解「无自著方差」的形态价值与三方合并基线。(强化:[[sources/2026-07-20-decision-deterministic-render-discipline]] → [[concepts/deterministic-render]])
4. **M1–M3 演进线:每次踩坑都沉淀为机检 + 流程固化**(均标「演进」):
   - M1→0.2.0:rolling 判新口径不统一 → 统一 `rolling_digest`(sha256)并经 render-once 三方合并落存量([[sources/2026-07-20-adr-rolling-judge-by-digest]] → [[concepts/rolling-source-freshness]]);模板注释示例 wikilink 致开箱断链 → 示例反引号化改净([[sources/2026-07-20-pitfall-template-comment-example-wikilink]])。
   - M2:MANIFEST 陈旧 fork 误报 → 派生物定性 + CI 零漂移断言 + 发版固化重导([[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]] → [[entities/gen-manifest]])。
   - M3/0.3.0:manifest 容器形状冻结 `articles` + 载入时自动迁移([[sources/2026-07-20-adr-manifest-container-articles]] → [[concepts/fetcher-adapter-contract]])。
   - 贯穿:文件所有权三档判定规则把「谁能改什么」变成可裁决标准([[sources/2026-07-20-adr-file-ownership-three-tiers]] → [[concepts/file-ownership-three-tiers]])。

## 反例与未解之处

- 模板仓库形态在**多实例规模**下的升级成本(逐实例三方合并)未实测——演进 lens 的 6 分短板是否被嫁接完全补齐,待更多实例检验。
- 嫁接项③(--adopt 存量收编)本库尚无源页记载,记 followups 待读。
- 检索成本对比数字未做跨 domain 复测,维持「参考实例实测」降级口径。

## 引用来源

- [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]](强化,D1 终裁记录)
- [[sources/2026-07-20-decision-deterministic-render-discipline]](强化,头号风险缓解)
- [[sources/2026-07-20-adr-rolling-judge-by-digest]](演进,0.2.0 口径统一)
- [[sources/2026-07-20-adr-manifest-container-articles]](演进,0.3.0 容器冻结)
- [[sources/2026-07-20-adr-file-ownership-three-tiers]](例证,三档判定规则)
- [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]](例证,M2 教训)
- [[sources/2026-07-20-pitfall-template-comment-example-wikilink]](例证,0.2.0 模板改净)
