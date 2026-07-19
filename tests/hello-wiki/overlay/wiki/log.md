# Log 操作日志

Append-only(W-LOG-1)。每条以 `## [YYYY-MM-DD] <op> | <one-line>` 起手(ASCII 方括号与竖线,便于 grep);op ∈ ingest / bulk-ingest / query-filed / lint / update / note / bootstrap / refactor / upgrade / capture。读取只用:

```bash
grep '^## \[' wiki/log.md | tail -10
```

---

## [2026-07-16] bootstrap | 初始化 hello-wiki 说明书库(CI 合成夹具)

- created: `CLAUDE.md`(契约)、`wiki.config.json`、wiki 目录骨架、`.claude/{rules,agents,skills}/`
- notes: 由 llmwiki 框架经 `init_render.py` 确定性渲染;管线 notes(push)+ guide(rolling)。

## [2026-07-16] ingest | ADR-001 默认问候语选型(full 档,touch 5)

- created: [[sources/2026-07-01-adr-greeting-default]]、[[entities/greeter-service]]、[[concepts/greeting-protocol]]、[[concepts/localization-fallback]]
- updated: [[overview]](主题地图)
- contradictions: 1(默认口径 vs 风格指南示例,⚠️ 挂 concepts/greeting-protocol)

## [2026-07-16] ingest | 风格指南滚动快照 v3(full 档,touch 5;回写 rolling_digest)

- created: [[sources/guide-style-guide]]
- updated: [[concepts/greeting-protocol]](演进)、[[concepts/localization-fallback]](强化)、[[entities/greeter-service]](时间线)
- notes: faithful 快照 sha256 已回写源页 `rolling_digest`;逐版本锚定走 raw dated 派生件。

## [2026-07-16] ingest | emoji 乱码踩坑(light 档,touch 1;欠债记 followups 待晋升)

- created: [[sources/2026-07-05-pitfall-emoji-encoding]]
- updated: [[concepts/localization-fallback]](例证:ascii 档字符集纪律)

## [2026-07-17] ingest | how-to 新增问候语言(full 档,touch 5)+ synthesis 落地

- created: [[sources/2026-07-08-howto-add-greeting-language]]、[[syntheses/greeting-design-story]]
- updated: [[entities/greeter-service]]、[[concepts/localization-fallback]]、[[concepts/greeting-protocol]]

## [2026-07-18] query-filed | 怎么新增一门问候语言 → queries/how-to-add-greeting-language

- created: [[queries/how-to-add-greeting-language]]
- notes: 答案全部链回源页与概念页;归档后跑索引派生。

## [2026-07-18] note | 时区问候踩坑已投递 raw/inbox,留作 pending 夹具断言

- notes: `raw/inbox/2026-07-15-pitfall-timezone-greeting.md` 故意不建源页;followups 已记待读。
