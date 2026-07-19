---
title: "踩坑:MANIFEST 陈旧导致新渲染实例误报 fork"
date: 2026-07-20
kind: pitfall
---

# 现象

M2 验证阶段发现:改了 frozen 档工具后**忘跑 gen_manifest**,`framework/MANIFEST.json` 里的 sha256 还是旧值;此后新渲染出来的实例一跑 `lint_wiki.py --manifest`,frozen 文件 hash 与 MANIFEST 快照对不上,当场误报 fork 漂移——实例明明一个字节都没改。

# 根因

MANIFEST 是 frozen 漂移判定的唯一依据(W-UPG-1),但它自己也会陈旧:框架仓改动与 MANIFEST 重导之间没有强制耦合时,「基线落后」与「实例改动」在 hash 比对里不可区分,只能表现为 fork 误报。

# 修法(已落位)

1. **MANIFEST 定性为派生物**(W-IDX-1):由 `tools/gen_manifest.py` 从文件树重算,勿手编;改动 frozen 后必须重导;
2. **CI 断言兜底**:`tests/run_ci.py` 在每个新渲染实例上跑 `lint --manifest` 并断言「零 fork 漂移」(phase_lint,`errors == 0`)——框架仓 MANIFEST 一旦陈旧,CI 立即红;
3. 发版流程把「重跑 gen_manifest」写成固定步骤(run_ci 的 h0 造版夹具 build_fw_next 同样如此:改动 → VERSION bump → UPGRADING 顶插 → gen_manifest 重导)。

# 教训

凡「基线文件」都要有派生工具 + 新鲜度断言,否则基线陈旧的报错会伪装成使用方的错。

# 出处

- `llmwiki/tools/gen_manifest.py` docstring;
- `llmwiki/tests/run_ci.py` phase_lint(「lint --manifest 零 fork 漂移」断言)与 build_fw_next(h0 造版含 gen_manifest 重导);
- `llmwiki/tools/lint_wiki.py`(sha256 漂移 → fork 警告,exit 1 供 sync 常跑当场报警)。
