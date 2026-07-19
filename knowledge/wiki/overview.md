---
title: Overview 综述
description: "全库心智模型:大问题的当前结论 + 主题地图。回答全局/主题/横向问题的第二读入口。"
type: overview
created: 2026-07-20
updated: 2026-07-20
tags: [meta]
status: draft
---

# Overview 综述

<!-- 体量目标 ~1.5K tok(boot 第二读,计入 4000 启动预算)。
     更新时机:synthesis 级结论变化时 bump,不随单篇 ingest 动。 -->

## 这个库是关于什么的

llmwiki 框架(「LLM 主导维护的复利型知识库」模板仓库,v0.3.0,M1–M3 全绿)自身开发过程的知识库:收录本仓真实的设计决策(ADR)、踩坑记录(pitfall)、操作说明(how-to)与裁决记录(decision),经 `raw/inbox/` 内生投递、按档位 ingest 成互链图谱。信任姿态:内部一手材料 = 权威来源,如实收录无需第三方验证;口径冲突以更新的内部决策为准并标「演进」(W-ING-3)。实测数字一律「参考实例 newpj4 实测」口径,不作通用承诺。首批 10 源已 ingest(2026-07-20),覆盖形态裁决、升级协议、适配器契约、判新机制、渲染纪律五簇。

## 几条大问题与目前回答

1. **llmwiki 为什么是模板仓库形态?** 2026-07-19 用户终裁 D1:hybrid 模板仓库——agent-efficacy 权重最高,模板仓库是唯一能把实测验证过的阅读协议确定性复制给新 domain 的形态;演进短板靠 6 项嫁接补齐。→ [[syntheses/framework-design-evolution]]
2. **升级怎么做到既保真又不踩实例?** 文件所有权三档(frozen hash 覆盖 / render-once 三方合并 / instance 永不触碰)+ 发版六步 + 双门禁(manifest 零漂移 + golden 不回退)。→ [[concepts/file-ownership-three-tiers]] · [[concepts/framework-upgrade-protocol]]
3. **实例怎么扩展采集而不改框架?** 合同驱动:满足 CONTRACT(容器冻结 `{"articles": {slug}}` + 六必填字段 + 行为条款)即被 sync/pending/build 零适配接入。→ [[concepts/fetcher-adapter-contract]]
4. **滚动源怎么判定该刷新?** sha256 内容摘要(`rolling_digest`)判新,版本号仅作报告口径;忘写 digest → 永远 pending(自愈锚点,暴露而非静默)。→ [[concepts/rolling-source-freshness]]
5. **实例化为什么禁止 agent 代笔?** 渲染不一致是头号风险:agent 只填 config,产物是 config 的纯函数(逐字节可复现)——代笔即瓦解三方合并基线。→ [[concepts/deterministic-render]]
6. **踩过的坑沉淀成了什么?** 三条坑(代理拦截 loopback / MANIFEST 陈旧误报 fork / 模板注释示例断链)全部固化为机检或 CI 断言。→ [[entities/run-ci]] · [[entities/gen-manifest]] · [[entities/lint-wiki]]

## 主题地图

- **形态与设计叙事**:[[syntheses/framework-design-evolution]]
- **升级与所有权**:[[concepts/file-ownership-three-tiers]] · [[concepts/framework-upgrade-protocol]] · [[entities/gen-manifest]]
- **采集与管线**:[[concepts/fetcher-adapter-contract]] · [[concepts/rolling-source-freshness]] · [[entities/sync-tool]]
- **实例化**:[[concepts/deterministic-render]]
- **质量门禁**:[[entities/lint-wiki]] · [[entities/run-ci]]

## 仍未解决的问题

- 多实例规模下的升级成本(逐实例 render-once 三方合并的人工量)未实测 → [[syntheses/framework-design-evolution]]
- 嫁接项③ --adopt 存量收编尚无源页记载(待读)→ [[syntheses/framework-design-evolution]]
- 本实例仅 push 管线,pull/rolling 采集与判新路径未在本实例实测 → [[concepts/rolling-source-freshness]]
