---
title: "ADR:文件所有权三档 frozen / render-once / instance 与判定规则"
date: 2026-07-20
kind: adr
---

# 决策

框架与实例之间的每个文件归入三档之一,归档记入 `framework/MANIFEST.json`,升级行为按档执行:

| 档 | 判定规则(可机检的裁决标准) | 升级行为 |
|---|---|---|
| frozen | 机器可检 且 domain 无关(工具、schema、契约不变式段、骨架段落) | hash 校验后整体覆盖;本地改动 → fork 警告(W-UPG-1) |
| render-once | 需 domain 取值或 agent 散文,但由模板渲染出生(CLAUDE.md、rules 枚举、meta 页、本地 skills) | base × 现文件 × 新模板三方合并 |
| instance | 实例数据与实现(wiki/、raw/、state/、site/、config、adapters、golden) | 永不触碰 |

# 关键点

- 判定规则是**裁决标准**而非清单:新增文件归档争议时按规则裁决并记入 MANIFEST;
- MANIFEST 本身是派生物(W-IDX-1),由 `tools/gen_manifest.py` 从文件树重算,勿手编;确定性:按路径排序、不写时间戳;
- 框架仓库侧的投影(gen_manifest 分档规则):frozen = tools/**、schema/**、docs/**、evals/**、adapters/**、extras/**;render-once = CLAUDE.template.md、.claude/**、templates/**;其余(README/LICENSE/framework/**、tests 夹具)归 meta;
- `lint_wiki.py --manifest` 校验 hash 与归档完整性,挂 sync 常跑路径:frozen 漂移当场报 fork 警告(未声明的改动在升级时会被覆盖丢失);
- 逃生舱例外:「实例扩展附录」段与 `.claude/rules/local-*.md` 承诺永不合并冲突,任何版本迁移动作不得要求改写。

# 出处

- `docs/plans/llmwiki-framework-spec.md` §1.3 文件归属三档与判定规则、§10 升级协议;
- `llmwiki/tools/gen_manifest.py` docstring(分档规则、派生物纪律);
- `llmwiki/framework/RULES.md` W-UPG-1;`llmwiki/framework/UPGRADING.md` 写作约束。
