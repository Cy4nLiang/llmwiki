---
title: "ADR:rolling 源判新采 rolling_digest(sha256)而非版本号"
date: 2026-07-20
kind: adr
---

# 决策

rolling 型管线的「判新」以**内容摘要**为准:sync 现场重算 faithful 快照全文的 sha256,与源页 frontmatter `rolling_digest:` 比对,不一致 → pending 报一条「刷新滚动源页」(不是新建页)。**版本号仅作报告口径**,不参与判新。

# 理由

- 与 pending 持久重算原则一致:pending = f(raw/, wiki/sources/),不依赖一次性台账,重跑恒得同一结果;
- 版本号是 domain 相关的口径(有的滚动源根本没有版本号),sha256 对任何滚动源都成立——工具去 domain 化的要求;
- 刷新闭环有自愈锚点:刷新滚动源页的最后一步就是回写 digest;忘写 `rolling_digest:` → 该源永远 pending,暴露而非静默。

# 关键机制(实例侧)

- 写入时机:首次 ingest 与每次刷新完成时,agent 把当时 faithful 快照文件的 sha256 写入 `rolling_digest`(格式 `sha256:<64 位十六进制>`),同步更新 `rolling_latest`;
- faithful 快照与 dated 派生分离,变化记「演进」(W-ING-3);
- M1 时期口径不统一,0.2.0 版通过 render-once 三方合并统一为 `rolling_digest`(见 UPGRADING 0.2.0 迁移清单「rolling 判新统一 rolling_digest 口径」)。

# 出处

- `docs/plans/llmwiki-framework-spec.md` §7(「pending 按快照 sha256 与源页 rolling_digest 判新——版本号仅作报告口径」);
- `llmwiki/docs/rolling-source.md` §2.5 rolling_digest 判新;
- `llmwiki/docs/fetcher-contract.md`(忘写 digest → 永远 pending);
- `llmwiki/framework/UPGRADING.md` 0.2.0 条目。
