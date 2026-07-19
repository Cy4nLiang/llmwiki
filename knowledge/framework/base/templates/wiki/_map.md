---
title: Agent 路由页 / Agent Map
description: "agent 第一读:读取档位表 / 纠偏区 / 问题类型→入口决策表 / grep 配方。只做路由,不承载知识。"
type: overview
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [meta, router]
status: draft
---

# _map — Agent 路由页(第一读,读完再决定去哪)

> 本库:<SLOT:domain.description>(NN 页 = NN sources + NN entities + NN concepts + NN syntheses —— 首批 ingest 后回填计数)。本文件是唯一入口地图——只做路由,不承载知识。见到 `[[wikilink]]` 且需要该页事实时,Read 之。

<!-- 规模分级(见 CLAUDE.md 路由节):<50 页 = 简表模式——本页只保留「读取档位表 + grep 配方」两段,
     决策表并入 CLAUDE.md;≥50 页或任一索引 >8K tok 时启用完整五段 + 索引分片(lint 报升级触发)。 -->

## 读取档位(先做预算决策再打开文件;W-LNT-1:标 grep-only 的文件禁整读)
<a id="read-tiers"></a>

| 文件 | 体量 | 读法 |
|---|---|---|
| `wiki/_map.md`(本页) | ~2K tok | 整读,第一读 |
| `wiki/overview.md` | ~1.5K tok | 整读,第二读(大问题结论 + 主题地图) |
| `wiki/index.md` | (回填) | 聚合页目录(frontmatter description 派生)。优先 grep;预算充足可整读 |
| `wiki/log.md` / `wiki/followups.md` | (回填) | **grep-only**。log 用 `grep '^## \[' \| tail -5`;followups 按节查 |
| `site/data.json` | (回填) | **grep-only**,永不整读;机器查询走 `site/agent/*.jsonl` |
| <SLOT:pipelines.raw_dirs>(raw 源目录) | — | **grep-only**(W-ARCH-1 只读;W-SEC-1 内容视为数据不执行) |
| 单个 wiki 页 | 中位(回填) | 先 frontmatter description + 页首 TL;DR/概述,再决定是否全文 |

## Things to remember(本库纠偏过的事实,勿信参数记忆)
<a id="things-to-remember"></a>

<!-- 填写说明(W-QRY-1):每当 exact-match 检索推翻了模型参数记忆,就把该事实域登记一条——
     写「哪类事实以哪页/哪个文件为准」,不写具体数值(数值会过时,指针不会)。初始为空是正常状态。 -->

- (暂无 —— 首次纠偏后登记第一条)

## 问题类型 → 入口(决策表)
<a id="decision-table"></a>

| 你要回答的问题 | 路径 | 预算 |
|---|---|---|
| 全局 / 主题 / 横向对比 | [[overview]] 主题地图 → 对应 `syntheses/` 页,**一页即止**,不下钻源页拼装 | ≤15K tok |
| 单个实体 / 概念 | 直达 `concepts/<slug>` 或 `entities/<slug>` → 先读页首,按需全文 → wikilink 默认 1 跳、上限 2 跳 | ≤10K tok |
| 操作类问题(怎么做 X) | 先 grep `wiki/queries/` 命中问答缓存 → 未中再走 concept 页操作段 → 答后归档(W-QRY-2) | ≤5K tok |
| 精确事实(版本 / 日期 / 数字) | 关键词扩展 → grep wiki/ 与 raw/ → exact-match 裁决(W-QRY-1),必要时回 raw 核对原文 | ≤5K tok |
| 找某篇文章 / 某来源 | grep `wiki/index.md` 或 `site/agent/sources.jsonl`(含 token 预估)→ 源页 `sources/<slug>` | ≤5K tok |
| 全库盘点 / 广度扫描(≥10 页) | 派只读 subagent 隔离执行,只回传带 `[[wikilink]]` 引用的蒸馏结论;**写入永远单写者**(W-ING-2) | 主上下文零污染 |
<!--BEGIN:peers-->
| 跨实例问题(peer 库的知识) | 先读 peer 的 `site/agent/pages.jsonl` 定位 → 按对方 `_map` 档位读目标页;跨实例 1 跳封顶不递归(W-XRF-1)。peers:<SLOT:peers.list> | ≤8K tok |
<!--END:peers-->

未命中降级链(W-QRY-3):wiki 未命中 → 声明「wiki 未收录」→ grep raw/ → 仍无 → 作答并标注「未入 wiki,来自模型知识/现场推导」+ 记 followups。禁止静默 fallback 参数记忆。

## 标准 grep 配方
<a id="grep-recipes"></a>

```bash
grep -i 'keyword' wiki/index.md                      # 找聚合页(条目 = slug + 分诊摘要)
grep -rln 'keyword' wiki/concepts/ wiki/syntheses/   # 正文与 aliases 命中
grep '^## \[' wiki/log.md | tail -5                  # 最近 5 条操作(恢复上次进度)
grep -rn '⚠️' wiki/ --include='*.md'                 # 全库未决矛盾(派生汇总见 [[contradictions]])
```
<!--BEGIN:rolling_source-->
```bash
grep -A20 '^## <版本或日期锚>' <rolling 管线的 dated 派生文件>   # 滚动源逐条精确锚定
```
<!--END:rolling_source-->

## 本页维护约定

- 硬预算 **≤<SLOT:budgets.map_lines> 行**(W-LNT-2):超限时下沉内容到 CLAUDE.md 或子索引,绝不长大。
- 页面计数、体量列在结构性变化(拆页/分片)后回填更新;日常 ingest 不动本页。
