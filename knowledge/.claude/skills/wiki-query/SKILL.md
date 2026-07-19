---
name: wiki-query
description: 当用户就 domain 知识提问——事实、对比、演进、操作方法、全库盘点——时触发。按 _map 决策表选入口检索作答:wikilink 默认 1 跳上限 2 跳;精确事实只认 exact-match;未命中走显式降级链禁静默 fallback 参数记忆;有保留价值的答案默认归档 queries/;广度扫描派 wiki-reader 只回传蒸馏。
---

# wiki-query — 提问检索工作流

语言约定:默认用户交互语言:**中文**。源引用保留原文不译;技术术语可保留英文。高频页 `aliases` 必须中英双语(检索锚点)。

## 按问题类型选入口
<a id="entry-routing"></a>

第一读永远是 `wiki/_map.md`(读取档位表 + 纠偏区 + 决策表);以下为路由骨架,具体页名以 `_map` 决策表回填为准:

| 问题类型 | 路径 | 纪律 |
|---|---|---|
| 全局 / 主题 / 横向对比 | overview 主题地图 → 对应 syntheses 页 | **一页即止**,不下钻源页拼装 |
| 单实体 / 单概念 / 立场 | 直达 `entities/<slug>` 或 `concepts/<slug>` | 先页首 TL;DR 再按需全文;wikilink 默认 1 跳、上限 2 跳 |
| 精确事实(版本/日期/数字) | 关键词扩展 → grep wiki/ 与 raw/ → exact-match 裁决 | 见下方 exact-match 纪律(W-QRY-1) |
| 操作类(怎么做 X) | 先查 `queries/` 命中缓存 → 再 concept 操作段 | 命中缓存直接复用 + 核对时效 |
| 找某篇源 | grep 来源索引 / `site/agent/sources.jsonl` | 条目含 token 预估,先看体量再决定读法 |
| 全库盘点 / 广度扫描(≥10 页) | 派 wiki-reader 只读 subagent(简单 1 个 / 对比 2–4 / 全景 10+) | 只回传带 `[[wikilink]]` 引用的蒸馏结论,不回传原文;主上下文零污染;write 永远单写者 |


引用纪律:回答中的论断一律带 `[[wikilink]]` 出处,文末列引用清单(W-PAGE-3);大文件按 `_map` 档位表 grep-only(W-LNT-1)。

## exact-match 纪律(W-QRY-1)

精确事实(版本号/日期/价格/专名)**只认 grep 原文 exact-match**,不信参数记忆与语义近似;grep 前先做双语/同义关键词扩展。凡发现「参数记忆答案 ≠ 库内事实」,把该事实域登记进 `_map` 纠偏区(Things to remember),防下次再犯。

## 冷启动/未命中降级链(W-QRY-3)
<a id="cold-start-fallback"></a>

逐级**显式**降级,禁止静默 fallback 到参数记忆:

1. wiki 检索未命中 → 明确声明「wiki 未收录」;
2. → grep `raw/`(源已入库但未 ingest 的情形);命中则按 raw 切片预算读,并提示该源待 ingest;
3. → 仍无 → 可以作答,但必须标注「未入 wiki,来自模型知识/现场推导」+ 记 followups 待读资源(W-LOG-2)。

空库/冷启动期(<50 页)整条链照走:第 1 级命中率低是预期行为,不是跳过理由。

## 答案默认归档(W-QRY-2)
<a id="default-archive"></a>

有保留价值(将来还会被问到)的答案默认写 `wiki/queries/<slug>.md`(段落:问题 / 答案带 wikilink 引用 / 衍生问题 / 触发的 wiki 更新;frontmatter 记 `date_asked:`),归档前告知用户、可否决 → 跑索引派生(命令见文末)→ `wiki/log.md` append 一条 query-filed(W-LOG-1)。只对当前对话有效的即弃答案不落盘。答题中发现资料缺口 → 提议下一篇值得读的源,记 followups。


## 本实例工具速查

- `python3 tools/sync.py`:跑全部管线采集 + 打印待 ingest 积压
- `python3 tools/sync.py status`:不联网看积压
- `python3 tools/build_site.py && python3 tools/build_index.py`:索引派生(内容/description 变更后必跑,W-IDX-1)
- `python3 tools/lint_wiki.py`:完整机械 lint(断链/预算/新鲜度/staleness;`--manifest` 校验 frozen,W-UPG-1)
- `python3 tools/eval_retrieval.py evals/golden.jsonl`:golden 回归(W-UPG-2)
- `python3 tools/init_render.py --config wiki.config.json --target .`:补渲染/升级(已存在文件默认跳过)
