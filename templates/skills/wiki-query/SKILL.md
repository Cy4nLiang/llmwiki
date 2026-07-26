---
name: wiki-query
description: 当用户就 domain 知识提问——事实、对比、演进、操作方法、全库盘点——时触发。按 _map 决策表选入口检索作答:wikilink 默认 1 跳上限 2 跳;精确事实只认 exact-match;未命中走显式降级链禁静默 fallback 参数记忆;有保留价值的答案默认归档 queries/;广度扫描派 wiki-reader 只回传蒸馏。
---

# wiki-query — 提问检索工作流

语言约定:<SLOT:lang.clause>

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

<!--BEGIN:multi_facet-->
**跨 facet 裁决**(facet:<SLOT:facets.fields>):立场/做法对比先查 concept 页内「跨 facet」小节;矩阵/谱系级对照才去对应 syntheses 对照页。facet 间差异是「对比」不是「矛盾」。
<!--END:multi_facet-->

引用纪律:回答中的论断一律带 `[[wikilink]]` 出处,文末列引用清单(W-PAGE-3);大文件按 `_map` 档位表 grep-only(W-LNT-1)。

## exact-match 纪律(W-QRY-1)

精确事实(版本号/日期/价格/专名)**只认 grep 原文 exact-match**,不信参数记忆与语义近似;grep 前先做双语/同义关键词扩展。凡发现「参数记忆答案 ≠ 库内事实」,把该事实域登记进 `_map` 纠偏区(Things to remember),防下次再犯。

## 命中被替代页必须跟到最新(W-ING-5)
<a id="follow-supersession"></a>

命中的页若 frontmatter 带 `superseded_by:`(或正文有 `> **已被取代**` 横幅),**不得直接拿它作答**:跟到后继页读最新口径,答案以后继页为准;确需引用旧结论时明说「旧版口径,已被 [[后继]] 取代」。旧页只作溯源用,不是现行事实。全库 lineage 一览见 `wiki/contradictions.md` 的「演进链」分节(派生物)。

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

<!--BEGIN:peers-->
## 跨实例检索(peers,W-XRF-1)
<a id="peer-search"></a>

本实例声明的 peers:<SLOT:peers.list>

- **先读对方派生索引** `<peer_path>/site/agent/pages.jsonl`(每行含 token 预估),绝不整读对方 wiki;命中后按对方 `_map` 档位读目标页;
- **跨实例 1 跳封顶,不递归**:对方页内的 peer 链接不再跟进;
- 引用语法 `[[alias::path/to/slug|显示名]]`;**单向引用**,不写对方仓(写入越界违反 W-ARCH-2);本仓引用处照常标关系类型;
- peer 不可达(路径不存在/未 clone)→ 降级为纯文本引用 + 记 followups,不阻塞作答(lint 对此只 soft warning)。
<!--END:peers-->

## 本实例工具速查

<SLOT:tools.cmds>
