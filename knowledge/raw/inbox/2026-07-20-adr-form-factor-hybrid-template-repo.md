---
title: "ADR:框架形态终裁 hybrid 模板仓库(D1)"
date: 2026-07-20
kind: adr
---

# 决策

llmwiki 框架形态定为 **hybrid 模板仓库**:模板仓库为主体,嫁接另两个候选方案的 6 项机制。2026-07-19 用户终裁(D1),与评审推荐一致。

# 备选与 lens 得分

三个正交方案经 3 lens 评审(0–10 分,出处 `docs/plans/llmwiki-framework-prd.md` §2):

| Lens | 模板仓库派 WikiKit | plugin 派 llm-wiki-kit | 协议派 WIKI-SPEC |
|---|---|---|---|
| 跨项目复用性与实例化成本 | **8** | 7 | 5 |
| agent 使用效率与准确性(用户终极目标) | **8** | 6 | 4.5 |
| 框架演进与升级路径 | 6 | **8** | 7 |

# 理由

agent-efficacy 是用户的终极目标且权重最高。模板仓库是唯一把「已被 golden 实测验证的阅读协议」**确定性复制**给新 domain 的形态:实例全持有、可 grep、无 skill 触发概率、无跨界指针、无自著方差。检索成本证据(8.4x 等)仅以「参考实例 newpj4 实测」口径引用,不作通用承诺。

# 升级短板的 6 项嫁接(补齐演进 lens 的 6 分)

1. 规则 ID(W-* 命名空间,来自 WIKI-SPEC);
2. 钉版快照(framework/VERSION + base/ 三方合并基线,来自 WIKI-SPEC);
3. --adopt 存量收编(来自 plugin 派);
4. ingest 分档 light 档(来自 plugin 派);
5. hello-wiki CI 夹具(来自 plugin 派);
6. 工作流动词本地化为实例本地 .claude/skills/(改造自 plugin 派)。

# 出处

- `docs/plans/llmwiki-framework-prd.md` §2 形态裁决、§10 终裁记录 D1(方法:13 agents,workflow wf_e4ae1412);
- `docs/plans/llmwiki-framework-spec.md` §1 形态与交付物总纲。
