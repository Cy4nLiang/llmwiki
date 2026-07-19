---
title: Fetcher 适配器契约(CONTRACT + manifest 容器 + 管线注册)
description: "要写/接入一个 fetcher 适配器、或 build_site/sync 读不到 manifest 条目排障时读本页;含容器冻结形状 {\"articles\": {slug}}、六必填字段、五步接入路径与 manual 哨兵。"
type: concept
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/pipelines, adapter, contract]
status: draft
sources: ["[[sources/2026-07-20-adr-manifest-container-articles]]", "[[sources/2026-07-20-howto-add-fetcher-adapter]]", "[[sources/2026-07-20-adr-rolling-judge-by-digest]]"]
aliases: ["适配器契约", "fetcher adapter contract", "manifest 容器", "manifest container", "管线注册表", "pipeline registry"]
verified: 2026-07-20
---

# Fetcher 适配器契约(CONTRACT + manifest 容器 + 管线注册)

## 定义

实例自写 fetcher 适配器与框架工具(sync / pending / build_site)之间的行为与数据合同,权威文本 `adapters/CONTRACT.md`。**满足合同即被自动接入,无需改框架代码**;push 型管线免适配器直投 raw/。(来源:[[sources/2026-07-20-howto-add-fetcher-adapter|适配器 how-to]],例证)

## 核心要点

- **容器形状 v1 冻结(0.3.0/M3 起)**:台账 `state/<pipeline>.manifest.json` 顶层为 `{"articles": {slug: {...}}}`,slug 作键——天然去重、幂等可续(已抓跳过按键查)、省一次线性扫描。六必填字段:`slug` / `url`(push 可空)/ `title` / `date` / `fetched` / `raw_file`(CONTRACT §4、§11)。(强化:[[sources/2026-07-20-adr-manifest-container-articles]])
- **冻结动机**:容器键名漂移(如写 `items`)会让 build_site **静默读不到条目**——比报错更危险。兼容策略「读旧写新」:读取端宽容历史形态(顶层 `{"articles": dict|list}` 等旧样),但 `articles` 以外的容器键名不被识别;写入端只认冻结形状。(同上;build_site 工具页待晋升,暂纯文本)
- **五步接入路径**:复制 skeleton(pull 抄 `adapters/article_fetcher.skeleton.py`,rolling 抄 `adapters/rolling_source.skeleton.py`,落位实例 `tools/adapters/<name>.py`)→ 实现 `discover`/`fetch`/`status`(push 型为 `status`/`register`)→ 对照 CONTRACT §11 自查 → config 注册 → sync 试跑。(例证:[[sources/2026-07-20-howto-add-fetcher-adapter]])
- **行为条款**:`--root` 必收且一切路径以之解析(任意 cwd 结果相同);幂等可续(`--force`/`--limit`);限速 sleep + 重试退避;自报 UA;退出码 0/1/2 语义正确;`status --json` 机器可解析;凭证只走环境变量;第三方依赖随附 requirements 并在 docstring 声明(无依赖则纯标准库)。(同上,扩展)
- **写入边界**:只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`,临时件全进 `state/tmp/`;适配器本体落 instance 档实例自持有(→ [[concepts/file-ownership-three-tiers]])。(同上)
- **管线注册表**:`wiki.config.json` `pipelines[]` 注册 `{name, kind, raw_dir, prefix, adapter, source_kinds}`(与适配器内常量一致);人工投放快照的管线用哨兵 `"adapter": "manual"`(sync 跳过抓取不告警);注册后跑 `lint_wiki.py --check-config` 复验。(同上,扩展;例证:[[entities/lint-wiki]])
- **自愈锚点条款**:fetcher-contract 文档载明「忘写 `rolling_digest:` → 该源永远 pending」——失败即暴露而非静默漏更新。(扩展:[[sources/2026-07-20-adr-rolling-judge-by-digest]] → [[concepts/rolling-source-freshness]])
- **raw 文件形状**:YAML frontmatter + 正文;文件名 stem 与源页命名 `<prefix><stem>.md` 对齐。(例证:[[sources/2026-07-20-howto-add-fetcher-adapter]])

## 演变与争议

- 演进:容器键名早期不统一(有适配器写 `items`)→ 0.3.0 冻结 `articles` 形状;随框架发布的 `local_notes.py` 载入时自动迁移旧台账(升级即自愈),记入 UPGRADING 0.3.0 frozen 覆盖清单(→ [[concepts/framework-upgrade-protocol]])。无未决 ⚠️。

## 相关概念

- [[entities/sync-tool]] —— 合同的框架侧主消费方(采集调度 + pending)。
- [[concepts/rolling-source-freshness]] —— rolling 型管线的判新条款。
- [[concepts/file-ownership-three-tiers]] —— 适配器 instance 档归属与写入边界的依据。
- [[entities/lint-wiki]] —— `--check-config` 注册一致性复验。

## 来源

- [[sources/2026-07-20-adr-manifest-container-articles]](强化,容器冻结裁决记录)
- [[sources/2026-07-20-howto-add-fetcher-adapter]](例证 + 扩展,合同的操作化步骤版)
- [[sources/2026-07-20-adr-rolling-judge-by-digest]](扩展,自愈锚点条款)

## 未解之处

- build-site、local-notes-adapter 独立工具页待晋升(现各 1 源提及,记 followups)。
- 本实例仅有 push 型 notes 管线,pull/rolling 合同条款未在本实例实测。
