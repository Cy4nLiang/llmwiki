---
title: "How-to:新增一个 fetcher 适配器"
date: 2026-07-20
kind: howto
---

# 适用

要给实例接一条 pull 或 rolling 管线(抓外部文档/滚动快照)。push 型管线免适配器,直投 raw/ 即可。

# 步骤

1. **复制 skeleton**:pull 型抄 `adapters/article_fetcher.skeleton.py`,rolling 型抄 `adapters/rolling_source.skeleton.py`,落到实例的 `tools/adapters/<name>.py`(instance 档,实例自持有);
2. **实现三子命令**:`discover` / `fetch` / `status`(push 型:status/register);`--root` 必收且一切路径以之解析,任意 cwd 下运行结果相同;
3. **对着 CONTRACT 自查**:逐条打勾 `adapters/CONTRACT.md` §11 合规自查清单,重点:
   - 只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`,临时件全进 `state/tmp/`;
   - manifest 容器用冻结形状 `{"articles": {slug: {...}}}`,六必填字段齐(slug/url/title/date/fetched/raw_file);
   - raw 文件 = YAML frontmatter + 正文,文件名 stem 与源页命名 `<prefix><stem>.md` 对齐;
   - 幂等可续(已抓跳过、--force/--limit)、限速 sleep + 重试退避、自报 UA;
   - 退出码 0/1/2 语义正确,`status --json` 机器可解析;第三方依赖随附 requirements 并在 docstring 声明(无依赖则纯标准库);凭证只走环境变量;
4. **config 注册**:`wiki.config.json` 的 `pipelines[]` 加一条 `{name, kind, raw_dir, prefix, adapter, source_kinds}`,与适配器内常量一致;跑 `lint_wiki.py --check-config` 复验;人工投放快照的管线可用哨兵 `"adapter": "manual"`(sync 跳过抓取不告警);
5. **sync 试跑**:`python3 tools/sync.py`——满足合同即被 sync/pending/build 自动接入;看 status 报告与 pending 是否符合预期。

# 出处

- `llmwiki/adapters/CONTRACT.md`(合同全文 + §11 自查清单);
- `llmwiki/adapters/article_fetcher.skeleton.py`、`rolling_source.skeleton.py`、`local_notes.py`(纯标准库参考实现);
- `llmwiki/docs/fetcher-contract.md`;`llmwiki/schema/wiki.config.schema.json` pipeline 定义。
