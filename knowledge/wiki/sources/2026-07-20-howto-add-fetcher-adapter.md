---
title: "How-to:新增一个 fetcher 适配器"
description: "要给实例接 pull/rolling 管线(抓外部文档/滚动快照)时读本页:五步接入路径 + CONTRACT §11 自查要点 + manifest 容器六必填字段 + adapter: manual 哨兵用法。push 型免适配器不适用本页。"
type: source
created: 2026-07-20
raw_file: raw/inbox/2026-07-20-howto-add-fetcher-adapter.md
source_kind: howto
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: ["llmwiki 框架开发会话(内生 capture)"]
tags: [howto, cluster/pipelines, adapter, contract]
status: draft
ingest_tier: full
---

# How-to:新增一个 fetcher 适配器

## 一句话摘要 / TL;DR

给实例接 pull/rolling 管线 = 复制 skeleton → 实现 discover/fetch/status 三子命令 → 对照 `adapters/CONTRACT.md` §11 逐条自查 → `wiki.config.json` pipelines 注册 → sync 试跑;满足合同即被 sync/pending/build 自动接入,push 型管线免适配器直投 raw/。

## 关键论点 / Key Claims

- 适配器接入是**合同驱动**的:框架工具不认识具体适配器,只认 CONTRACT 形状——满足合同即自动接入,无需改框架代码。
- 写入边界收紧到「只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`,临时件全进 `state/tmp/`」,与文件归属分层一致。
- `--root` 必收且一切路径以之解析,保证任意 cwd 下运行结果相同(可复现性纪律在采集层的体现)。
- 人工投放快照的管线可用哨兵 `"adapter": "manual"`,sync 跳过抓取不告警——manual 是合法的一等管线形态。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- skeleton 参考实现:pull 型抄 `adapters/article_fetcher.skeleton.py`,rolling 型抄 `adapters/rolling_source.skeleton.py`;落位实例 `tools/adapters/<name>.py`(instance 档,实例自持有)。
- 子命令合同:pull/rolling 为 `discover` / `fetch` / `status`;push 型为 `status` / `register`。
- manifest 容器冻结形状:`{"articles": {slug: {...}}}`;六必填字段:`slug` / `url` / `title` / `date` / `fetched` / `raw_file`。
- raw 文件 = YAML frontmatter + 正文;文件名 stem 与源页命名 `<prefix><stem>.md` 对齐。
- 行为要求:幂等可续(已抓跳过、`--force`/`--limit`)、限速 sleep + 重试退避、自报 UA、退出码 0/1/2 语义正确、`status --json` 机器可解析、凭证只走环境变量;第三方依赖随附 requirements 并在 docstring 声明(无依赖则纯标准库)。
- config 注册字段:`pipelines[]` 加 `{name, kind, raw_dir, prefix, adapter, source_kinds}`,与适配器内常量一致;注册后跑 `lint_wiki.py --check-config` 复验。

## 我学到了什么 / Takeaways

- 「合同 + skeleton + 自查清单」三件套让扩展点外置:实例写适配器不需要读框架工具源码,只需过 §11 清单。
- manifest 容器形状是跨管线互操作的枢纽——形状冻结换来 sync/pending/build 的零适配接入。
- 接入验收动作固定:`--check-config` 复验注册一致性,`sync.py` 试跑看 status 与 pending 是否符合预期。

## 与其它来源的关系 / Connections

- 例证 + 强化 + 扩展:[[concepts/fetcher-adapter-contract]] —— 本篇是 CONTRACT.md 合同的操作化步骤版;与 manifest 容器 ADR 同口径(冻结 `articles` 容器 + 六必填字段);补充 `adapter: "manual"` 哨兵与 `--check-config` 复验环节(容器/注册表条款并入该页)。
- 例证:[[concepts/file-ownership-three-tiers]] —— 适配器落 instance 档、只写自己的 raw/state,是三档归属在采集层的实例。
- 强化:[[entities/sync-tool]] —— 满足合同即被 sync/pending/build 自动接入的机制描述。
- 例证:[[entities/lint-wiki]] —— `--check-config` 是适配器接入的固定验收动作。
- 例证:[[concepts/rolling-source-freshness]] —— rolling 型适配器抄 rolling_source.skeleton.py,同受合同约束。

## 引用片段 / Quotes

> 只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`,临时件全进 `state/tmp/`;manifest 容器用冻结形状 `{"articles": {slug: {...}}}`,六必填字段齐(slug/url/title/date/fetched/raw_file)。

> 人工投放快照的管线可用哨兵 `"adapter": "manual"`(sync 跳过抓取不告警)。

## 处理记录 / Processing Notes

- 触及/更新页面(reduce 落实,2026-07-20):[[concepts/fetcher-adapter-contract]](例证+强化+扩展)、[[concepts/file-ownership-three-tiers]](例证)、[[entities/sync-tool]](强化)、[[entities/lint-wiki]](例证)、[[concepts/rolling-source-freshness]](例证)——共 5,满足 full 档下限(W-ING-1)。
- reduce slug 终裁:adapter-contract / manifest-container / pipeline-registry 三个提议目标并入 [[concepts/fetcher-adapter-contract]] 单页;file-ownership-tiers 调和为 [[concepts/file-ownership-three-tiers]]。
- W-SEC-1 审计:raw 为内生 capture 笔记,内容为操作步骤描述,未发现疑似注入指令。
