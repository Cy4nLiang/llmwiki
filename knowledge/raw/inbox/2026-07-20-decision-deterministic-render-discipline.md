---
title: "决策:确定性渲染纪律——agent 只填值,渲染一律交工具"
date: 2026-07-20
kind: decision
---

# 决策

实例化(greenfield/adopt/embedded)全程,agent 的职责边界是**问答与填 `wiki.config.json`**;所有模板正文由 `python3 tools/init_render.py` 确定性渲染。禁止手写或改写 CLAUDE.md、`_map`、rules、skills 的正文。验收标准:**同一份 config 渲染两次,产物必须逐字节相同**。

# 配套纪律

- config 写完先过 schema 校验(`schema/wiki.config.schema.json`,init_render 内置手写校验器,纯标准库);**报错改 config 重渲染,不改产物**;
- 收尾必跑冒烟 `lint_wiki.py --check-slots`:渲染产物零残留 SLOT 占位符才算完成;
- 可复现锚点:`--date` 固定 bootstrap 日期可获得可复现产物(init_render --help 明示)。

# 理由

PRD 风险表首行:「渲染不一致(agent 自由发挥)」是框架的头号风险——模板仓库形态的全部价值在于把实测验证过的阅读协议**确定性复制**给新 domain(D1 裁决理由「无自著方差」);agent 一旦代笔正文,复制就退化成转述,升级三方合并的 base 基线也随之失效。缓解措施即本纪律 + 每问带默认值和示例。

# 本次 dogfood 实测(参考:本实例 2026-07-20 初始化)

按此纪律执行:写 config(agent 唯一的「写」)→ init_render 出 49 文件 → check-slots 零残留 → 空索引派生,骨架落成约 1 分钟,agent 全程未碰任何模板正文。

# 出处

- `llmwiki/.claude/skills/wiki-init/SKILL.md` 硬约束段(纪律原文);
- `docs/plans/llmwiki-framework-spec.md` §9 实例化三模式(「agent 只填值,不写正文;两次 init 产物必须相同」);
- `docs/plans/llmwiki-framework-prd.md` §9 风险与缓解首行、§2 形态裁决理由。
