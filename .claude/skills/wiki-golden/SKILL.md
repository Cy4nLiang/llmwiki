---
name: wiki-golden
description: 当实例要建立或修订评测基线——首批 ~10 源落库后、wiki-upgrade 门禁前后、结构性重构(拆页/分片)后,或用户说「建 golden」「/wiki-golden」「出评测题」时触发。引导编写 evals/golden.jsonl:6+1 题型外加路由入口选择题、golden{2,1} 分级、any-of 校准、同库裸 grep 对照组,并固化「grep 不算 read」记账口径。
---

# wiki-golden — golden 评测集编写向导

产出:`evals/golden.jsonl`(JSONL,每行一题)。这是实例的质量基线:description 触发质量、路由协议有效性、升级门禁(W-UPG-2)都以它回归。

## 何时建 / 何时修

- **建基线**:首批 ~10 源落库、`_map` 决策表回填后立刻建——config 填偏(trust_posture/facet)要靠它早期显形;
- **复跑**:每次 wiki-upgrade 门禁;结构性重构(拆页/索引分片)前后各一轮;
- **修题**:发现假阴性(经替代页答对但 golden 不认)→ any-of 修正;答案本身错则不改 golden。

## Schema(每行)

```json
{"qid": "q01-short-slug", "type": "single-hop", "question": "…?",
 "golden": {"entities/foo": 2, "sources/2026-01-01-bar": 1},
 "answer_keys": ["精确值或判定基准"], "notes": "出题意图/校准备注"}
```

## 分级 golden{2,1}
<a id="golden-grading"></a>

- **2 = 必读**:缺了这页答案就不完整或不可靠(recall 分母);每题至少一个 2;
- **1 = 有帮助**:读了更稳但可被替代;
- golden 可以含 raw 文件本身——exact-verbatim 题**必须**含(精确条目以 raw 为准,W-QRY-1)。

## 题型:6+1,外加路由入口选择题
<a id="question-types"></a>

| 题型 | 考什么 | 出题要点 |
|---|---|---|
| single-hop | 单页事实 | golden 指向一页 entity/concept;answer_keys 写精确值 |
| multi-hop | 跨 2+ 页链式推导 | 链条每一环都进 golden;回归 wikilink 跳数纪律 |
| comparison | 立场/做法对照 | golden 应命中预物化对照页,不该现场拼装源页 |
| aggregation | 跨源汇总(「总共/都有哪些」) | 回归「一切汇总皆派生」(W-IDX-1):应命中综合页而非扫源页 |
| timeline | 演进时序 | golden 指时间线页;answer_keys 写演进链(A→B→C) |
| exact-verbatim | 逐字精确条目(版本/原文) | golden 必含 raw 文件;回归回 raw exact-match(W-QRY-1) |
| **unanswerable**(6+1 的 +1,诚实探针) | 库范围外的问题 | 正确行为 = 按降级链声明「未收录」(W-QRY-3),额外探索越少越好;编造 = 直接判死 |
| **路由入口选择题**(新增题型) | 「此问题应命中 _map 决策表哪个入口 / 哪页 description」 | 直接回归 description 触发质量(W-PAGE-2);golden = 应命中页,answer_keys = 入口名 |

规模:**≥10 题起步**,题型全覆盖(unanswerable 与路由入口题至少各 1);参考实例 newpj4 实测用 16 题。

## any-of 校准坑
<a id="any-of"></a>

多页能**独立**支撑同一答案时,golden 必须写成 any-of 组(命中其一即得该档分),否则产生 recall 假阴性——agent 经替代页答对却被判漏读。参考实例 newpj4 实测:一道多跳题经 entities 替代页答对,golden v0.1 未接受,v0.2 以 any-of 修正。校准流程:逐题看 run 的 files_read + answer,凡「答案对、路径不同」一律回查是否该进 any-of;答案错则修协议或修页,**不修 golden**。

## 对照组 = 同库裸 grep
<a id="control-arm"></a>

同一批题、同一个库,对照组不给协议(不读 _map/契约),让 agent 即兴 glob+grep 检索。它标定「协议红利」:参考实例 newpj4 实测,裸 grep 的 recall 可以不低,但路径不稳定、最差题成本显著更高(撞上未拆分巨页)、诚实探针要多花 token 做排除法确认「未收录」。报告永远双列呈现:协议组 vs 裸 grep 组,不单报绝对值。

## 记账口径(打分零 LLM)
<a id="accounting"></a>

- run 文件逐题记 `files_read` + `answer`;P/R 按文件 ID 对 golden 机算(ID-based),不用 LLM 判卷;answer_keys 人工或 exact-match 判;
- **grep 不算 read**:grep/glob 的命中行零计费;只有 Read 打开的文件按实际体量计成本;
- raw 切片按 config `budgets.raw_slice_tokens` flat 计费(切片读不按全文计);
- boot 固定成本(_map + overview)单列,按题摊销后并入均值;
- est_tokens 按 config `budgets.est_tokens_profile`(cjk/latin)校准;
- 模型选型:框架只给方法——用自家 golden 复跑候选模型自行比较;警示:**便宜模型不一定吃得到协议红利**,结论以自测为准,不外推。

> **M1 注**:打分工具(eval_retrieval.py / eval_compare.py)M3 落地;此前按本口径手工对 qrels 记账即可,golden 编写本身不依赖工具。
