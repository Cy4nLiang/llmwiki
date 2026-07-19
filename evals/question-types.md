# golden 题型手册 — 8 题型逐型出题要点(M3,2026-07-19;any-of 组正式化,2026-07-20)

> 与 `evals/golden.schema.json`(结构规范)、`evals/playbook.md`(执行手册)构成评测三件套。
> 单题结构、分级语义(2=必读 / 1=有帮助)、别名映射表以 schema 为准;本文只管**怎么出好题**。
> 机检:`python3 tools/eval_retrieval.py --check-golden evals/golden.jsonl --root <实例根>`。
> 本文样例一律用 **hello-wiki 合成 domain**(框架 CI 夹具 `tests/hello-wiki/`,〔D5〕全合成语料),
> 勿照抄进真实实例——按自家 domain 重出。

## 总原则

- **题面不泄底**:question 里不出现 golden 页名/路径;route 题型只给需求描述。
- **每型至少覆盖一次**;unanswerable 与 route 至少各 1 题;规模 ≥10 题起步(参考实例 newpj4 实测用 16 题)。
- **golden 是「应读什么」不是「答案是什么」**:答案锚点归 answer_keys;golden 只回答检索路径问题。
- **exact 类事实只认 exact-match**(W-QRY-1):answer_keys 写精确值或「以 raw 某锚为准」的判定基准。

## 8 题型逐型要点

### 1. single-hop — 单页事实

- **考什么**:一页 entity/concept(或 queries/ 缓存)直达命中;回归 description 分诊 + wikilink 0–1 跳。
- **出题要点**:golden 指向一页 2 级 + 至多一页来源 1 级;answer_keys 写精确值。queries/ 缓存命中的
  how-do-I 题也归此型(存量别名 `how-do-I` 经映射表归一)。
- **样例骨架**:

```json
{"qid": "q1-default-greeting", "type": "single-hop",
 "question": "hello-wiki 的默认问候语是什么?",
 "golden": {"concepts/greeting-protocol": 2, "sources/2026-07-01-adr-greeting-default": 1},
 "answer_keys": ["你好,世界"], "notes": "单跳事实,concept 页应直达"}
```

### 2. multi-hop — 跨页链式推导

- **考什么**:2+ 页链式(A 页事实引出 B 页事实);回归 wikilink 跳数纪律(默认 1 跳上限 2 跳)。
- **出题要点**:链条每一环都进 golden(必经环 2 级);**最容易踩 any-of 坑的题型**——出题后主动自问
  「有没有一页同时含全链事实?」有则按下文 any-of 节校准。
- **样例骨架**:

```json
{"qid": "q2-emoji-pitfall-chain", "type": "multi-hop",
 "question": "ascii 档的字符集纪律是什么?这条纪律因哪次事故引入?",
 "golden": {"concepts/localization-fallback": 2, "sources/2026-07-05-pitfall-emoji-encoding": 2},
 "answer_keys": ["只允许可打印 ASCII", "emoji 编码踩坑"], "notes": "两问链式,两环都必经"}
```

### 3. comparison — 立场/口径对照

- **考什么**:预物化对照页(synthesis / concept 内对照小节)命中,不该现场拼装源页。
- **出题要点**:golden 2 级指对照页;若库里有 ⚠️ 真矛盾标记(W-ING-3),围绕矛盾出题最有区分度。
- **样例骨架**:

```json
{"qid": "q3-adr-vs-styleguide", "type": "comparison",
 "question": "ADR 与风格指南对默认问候语的口径有何差异?冲突时谁说了算?",
 "golden": {"syntheses/greeting-design-story": 2, "concepts/greeting-protocol": 1},
 "answer_keys": ["口径不一致(⚠️)", "裁决顺位"], "notes": "对照题应走 synthesis,不下潜源页"}
```

### 4. aggregation — 跨源汇总

- **考什么**:「总共/都有哪些」类问题应命中预物化综合页——回归「一切汇总皆派生」(W-IDX-1),
  现场扫源页拼装 = precision 崩、成本爆。
- **出题要点**:golden 通常只有一页 2 级综合页;答对但 files_read 里出现 3+ 源页 = 协议失败信号
  (分数上表现为 precision 低),notes 里写明这层意图。
- **样例骨架**:

```json
{"qid": "q4-decision-layers", "type": "aggregation",
 "question": "greeter 的问候行为总共由哪几层决定拼成?",
 "golden": {"syntheses/greeting-design-story": 2},
 "answer_keys": ["决策/实测/操作/纪律 四层"], "notes": "应读综合页,不该现场扫四份源页"}
```

### 5. timeline — 演进时序

- **考什么**:时间线页(entity 时间线面 / 滚动源页 canonical 面)命中;回归 W-ING-3「演进」标记纪律。
- **出题要点**:answer_keys 写演进链(A→B→C)整串,不只写终态——只答终态说明 agent 没读到演进结构。
- **样例骨架**:

```json
{"qid": "q5-styleguide-evolution", "type": "timeline",
 "question": "风格指南从 v1 到现在经历了哪些演进?",
 "golden": {"sources/guide-style-guide": 2},
 "answer_keys": ["v1→v2→v3 演进链"], "notes": "滚动源题:精选面在源页,完整条目回 raw dated"}
```

### 6. exact-verbatim — 逐字精确条目

- **考什么**:精确版本/原文条目必须回 raw exact-match(W-QRY-1),不信参数记忆与语义近似。
- **出题要点**:golden **必须含 raw 文件本身**(2 级);answer_keys 写判定基准(「以 raw dated 快照
  '## v2' 块为准」),判卷时人工对 raw 原文核对。存量别名 `exact-version` 归此型。
- **样例骨架**:

```json
{"qid": "q6-styleguide-v2-verbatim", "type": "exact-verbatim",
 "question": "风格指南 v2 那一版的完整变更条目是什么?(要求逐字)",
 "golden": {"raw/guide/style-guide.dated.md": 2, "sources/guide-style-guide": 1},
 "answer_keys": ["以 raw dated 'v2' 块为准"], "notes": "golden 含 raw 文件;切片读按 flat 记账"}
```

### 7. unanswerable — 诚实探针

- **考什么**:库范围外问题的正确行为 = 按降级链显式声明「未收录」(W-QRY-3);编造 = 直接判死。
  额外探索越少越好(好的 `_map` 范围声明可 0 探索出答案,参考实例 newpj4 实测)。
- **出题要点**:golden 必须为空 `{}`;**answer_keys 写「未收录声明」锚点关键词**(诚实答案中应出现的
  短子串,如 `"未收录"`;≤20 字符,大小写不敏感)——打分器以锚点匹配自动判诚实。**不要写整句期望
  答案**——超长整句不被打分器当作可用锚点(仅回退 M2 粗启发式并标注;参考实例 newpj4 v0.1 的
  句式写法即此,是本版收敛所消除的误判源)。
- **样例骨架**:

```json
{"qid": "q7-unanswerable-deploy", "type": "unanswerable",
 "question": "hello-wiki 的生产部署流程是什么?",
 "golden": {},
 "answer_keys": ["未收录"], "notes": "库只收问候域知识;编造部署步骤=判死"}
```

### 8. route — 路由入口选择题

- **考什么**:**直接回归 W-PAGE-2 description 触发质量与 `_map` 决策表有效性**。题面只描述需求
  (不指名页面),golden = `_map` 决策表该需求应路由到的入口对应页 / description 应触发选中的页。
- **出题要点**:从 `_map` 决策表逐行反向出题——每个入口挑一个典型需求措辞;answer_keys 写入口名或
  description 里的触发词(判卷核对 agent 是否说得出「为什么进这页」)。description 写偏(触发词与
  用户措辞脱节)会在此型显形为漏读。
- **打分语义**:与普通题**完全相同**(files_read 含 golden 页即命中),无特殊逻辑;特殊性只在出题面。
- **样例骨架**:

```json
{"qid": "q8-route-add-language", "type": "route",
 "question": "「想给 greeter 加一门新问候语言」这类需求,应从库的哪个入口进入?",
 "golden": {"queries/how-to-add-greeting-language": 2},
 "answer_keys": ["queries 直达", "操作类 how-do-I 入口"],
 "notes": "回归 _map『操作类需求→queries 直达』行 + 该页 description 触发质量"}
```

## any-of 组(`golden_groups`)—— 多路径等价的正式语法

多页能**独立**支撑同一答案时,单一 2 级页会产生 recall 假阴性:agent 经替代页答对却被判「漏必读」;
把替代页记 1 级单点也只是缓解——1 级仍进 recall 分母,「一页即止」的最优检索(P 1.0、答案全对)
数学上限被压到 0.4–0.667(参考实例 newpj4 与 llmwiki dogfood 实例两轮实测同一结论)。
2026-07-20 起打分器原生支持 **any-of 组**,旧「枢纽页记 2 + 替代页记 1」的近似编码就此退役。

**语法**(结构规范见 `golden.schema.json` 的 `golden_groups` 定义):

```json
"golden_groups": [{"weight": 2, "pages": ["页A", "页B", ...]}, ...]
```

**语义**:一组 =「同一信息的多条获取路径」,`files_read ∩ pages ≠ ∅` 即记该组**满权一次**
(任一命中即满,多命中不重复计)。打分口径:

- recall 分母 = Σ golden 单点权重 + Σ 组权重;组命中计满组权,组全 miss 计 0;
- precision:golden 单点或**任一组成员**均计 useful(读组内任何一页都不算「多读」);
- 2 权组全 miss 视同漏必读(计入 problem_q → exit 1);1 权组全 miss 只降 recall 不报警;
- per_question 输出带 `groups`(逐组 hit / hit_pages 明细)与 `miss_groups`。

**硬约束**(违规 = 结构错误,`--check-golden` exit 2):weight ∈ 2|1;组内路径归一后 ≥2 页且
互不重复;组页不得与 golden 单点重复;unanswerable 题禁止有组。

**校准手法**:「同一信息的枢纽页 vs 替代/下钻路径」整簇收进一组,组权取被并单点的最高权,
原单点删除;确属「必须额外读」的页(如 exact-verbatim 的 raw 文件本身,W-QRY-1)**仍留单点**,
绝不混进组——进了组就意味着「读了替代页可以不读它」。

**正例**(默认问候语可从 concept 页或 ADR 源页任一获得;raw 必读留单点):

```json
{"qid": "q-anyof-good", "type": "single-hop",
 "question": "hello-wiki 的默认问候语是什么?",
 "golden": {},
 "golden_groups": [{"weight": 2,
   "pages": ["concepts/greeting-protocol", "sources/2026-07-01-adr-greeting-default"]}],
 "answer_keys": ["你好,世界"],
 "notes": "any-of:concept 枢纽页与 ADR 源页为同一信息的两条路径,任一命中即满"}
```

**反例**(每条都是 `--check-golden` 的结构错误):

```json
{"golden_groups": [{"weight": 2, "pages": ["concepts/greeting-protocol"]}]}
```
组内单页——无「任一」可言,应写回 golden 单点。

```json
{"golden": {"concepts/greeting-protocol": 2},
 "golden_groups": [{"weight": 1,
   "pages": ["wiki/concepts/greeting-protocol.md", "syntheses/greeting-design-story"]}]}
```
组页与单点重复(路径归一后判定,加 `wiki/` 前缀 / `.md` 后缀也逃不掉)——同一页不能既是
「必须读」又是「任一即可」。

```json
{"type": "unanswerable", "golden": {}, "golden_groups": [{"weight": 1, "pages": ["a", "b"]}]}
```
unanswerable 禁组——诚实探针不评检索。

**复跑纪律**(不变):每次复跑逐题看 files_read + answer,凡「答案对、路径不同」回查是否该进
any-of 组;方向单行道见下节。

## 「答错不修 golden」原则(改分单行道)

golden 修正的**唯一合法方向**是消假阴性:答案对、路径不同 → any-of 校准(修 golden 使其接受替代页)。
反方向禁止:**答案本身错,永远不通过改 golden / 改 answer_keys 来救分**——答案错说明协议或页面有病
(description 写偏、页缺事实、⚠️ 未标),修协议、修页、记 followups,然后原题复跑。把题改到能过 =
评测网自废。

## 对照组 = 同库裸 grep

同一批题、同一个库,对照组不给协议(不读 `_map`/契约),让 agent 即兴 glob+grep 检索。它标定
「协议红利」:参考实例 newpj4 实测,裸 grep 的 recall 可以不低(0.792 vs 协议组 0.768),但
(a) 路径完全依赖临场发挥、不稳定;(b) 最差题成本约 2 倍(撞上未拆分巨页 31.6K vs 16.2K);
(c) 诚实探针要多花 3–5K token 做排除法确认「未收录」。报告**永远双列呈现**(协议组 vs 裸 grep 组),
不单报绝对值——绝对值好可能只是模型强,双列差值才是协议的成绩。执行细节见 `evals/playbook.md`。
