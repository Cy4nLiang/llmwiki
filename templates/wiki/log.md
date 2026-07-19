# Log 操作日志

Append-only(W-LOG-1)。每条以 `## [YYYY-MM-DD] <op> | <one-line>` 起手(ASCII 方括号与竖线,便于 grep);op ∈ ingest / bulk-ingest / query-filed / lint / update / note / bootstrap / refactor / upgrade / capture。正文列 created / updated(带关系类型)/ contradictions / notes。读取只用:

```bash
grep '^## \[' wiki/log.md | tail -10
```

---

<!-- 下条为 bootstrap 首条模板:init 当日把 YYYY-MM-DD 替换为实际日期,补齐 notes 后删除本注释。 -->

## [YYYY-MM-DD] bootstrap | 初始化 <SLOT:domain.name> 说明书库

- created: `CLAUDE.md`(契约)、`wiki.config.json`、wiki 目录骨架、`.claude/{rules,agents,skills}/`
- notes: 由 llmwiki 框架 v<SLOT:framework.version> 经 `init_render.py` 确定性渲染;源管线注册于 `wiki.config.json`(pipelines)。首批内容经 sync 报 pending 后按档位 ingest(W-ING-1)。
