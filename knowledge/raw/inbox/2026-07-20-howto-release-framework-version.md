---
title: "How-to:发一个框架新版"
date: 2026-07-20
kind: howto
---

# 适用

框架仓(llmwiki/)有改动要发版,让实例可以按 UPGRADING 跟版。

# 步骤

1. **落改动**:frozen(tools/schema/docs/evals/adapters/extras)或 render-once(CLAUDE.template / .claude / templates)侧改动完成;
2. **semver 判级**(判据在 `framework/UPGRADING.md` 头部):MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订;
3. **UPGRADING.md 顶插条目**:按「条目格式约定」模板(变更摘要/迁移清单/frozen 覆盖清单/验收),迁移清单逐条引 `W-*` 规则 ID(总表 `framework/RULES.md`,勿另造引用方式);「实例动作」必须可执行可核对,语义变更写明旧行为 → 新行为;
4. **重导 MANIFEST**:`python3 tools/gen_manifest.py`(MANIFEST 是派生物,忘跑会让新实例误报 fork——见同日 pitfall 笔记);
5. **CI 全绿**:`python3 tests/run_ci.py`(0.3.0 时点 119 断言;含 h0 模拟造版 + 升级四路径,验证的正是本流程:frozen+模板改动 → VERSION bump → UPGRADING 顶插 → gen_manifest 重导);
6. **bump `framework/VERSION`**(实例升级锚点)。

实例侧对应动作:`/wiki-upgrade`(tools/upgrade.py:frozen hash 校验/render-once 三方合并/预备份/门禁),验收 = lint --manifest 零漂移 + golden 不回退(W-UPG-2)。

# 出处

- `llmwiki/framework/UPGRADING.md`(条目格式约定、semver 判级、0.2.0/0.3.0 实例条目);
- `llmwiki/tests/run_ci.py` build_fw_next(h0 造版夹具即本流程的可执行版);
- `llmwiki/tools/gen_manifest.py`;`llmwiki/framework/VERSION`;`llmwiki/README.md`「贡献与回流」。
