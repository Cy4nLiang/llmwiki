# 评测执行手册 playbook(M3,2026-07-19)

> 〔D5 裁定〕执行手册**归并于本文件**,`docs/` 不另立 playbook。
> 三件套分工:`golden.schema.json`(单题结构规范)/ `question-types.md`(逐型出题要点)/ 本文(怎么跑)。
> 工具:`tools/eval_retrieval.py`(单 run 打分 + `--check-golden` 校验 + `--export-qrels`)、
> `tools/eval_compare.py`(多方案 arm@tree 横评,W-UPG-2 升级门禁用)。打分零 LLM,ID-based。
> 本文所有具体数字口径均为「参考实例 newpj4 实测」(2026-07-18,16 题),不外推为框架承诺。

## 1. Harness 流程(agent 会话驱动)

评测不是脚本灌题:**每题由一个真实 agent 会话驱动**,harness 只负责发题、回收、记账。

0. **前置**:golden 过机检 `python3 tools/eval_retrieval.py --check-golden evals/golden.jsonl --root .`
   (exit 2 = 结构错误必须先修;exit 1 = 有 warning,逐条过目后可继续)。
1. **每题一个全新会话**(冷启动语义,不复用任何前题上下文);协议组按契约正常 boot(读 `_map` +
   overview),对照组跳过 boot 直接作答。
2. 用固定提示词模板发题(见下),**不向 agent 泄露 golden / answer_keys / 题型**。
3. 会话结束后回收一行 run 记录,追加到 `evals/runs/<date>-<label>.jsonl`。
4. 全部题跑完 → `python3 tools/eval_retrieval.py evals/runs/<date>-<label>.jsonl --root . [--json]`。
5. 横评(协议组 vs 对照组 / 升级前后 / 候选模型):
   `python3 tools/eval_compare.py 协议组=evals/runs/a.jsonl@<树> 裸grep=evals/runs/b.jsonl@<树> --root .`
   结论存 `evals/COMPARISON-<date>.md`,永远双列呈现。

### 固定提示词模板

**协议组**(把库的阅读协议当作被测系统的一部分):

```
你在 wiki 实例 <root> 内回答一个问题。按本库契约(CLAUDE.md/AGENTS.md)与 wiki/_map.md
的阅读协议检索作答;精确事实回 raw exact-match;库未收录就明说,禁止编造。
回答后,如实列出你用 Read 打开过的全部文件路径(grep/glob 命中不算)。
问题:<question>
```

**对照组(同库裸 grep)**:

```
你在目录 <root> 内回答一个问题。不要读 CLAUDE.md/AGENTS.md/wiki/_map.md,不使用本库的
阅读协议;直接用 glob+grep+Read 即兴检索作答;不知道就明说,禁止编造。
回答后,如实列出你用 Read 打开过的全部文件路径(grep/glob 命中不算)。
问题:<question>
```

### 逐题纪律

- **一题一会话**,顺序无关;同一 run 内全部题用同一模型、同一棵内容树(树有变更先提交/打 tag,
  记录 commit,保证可复现)。
- **files_read 以会话中真实 Read 调用为准**:有 transcript 时从 transcript 提取;只能靠 agent
  自报时必须复核异常——`files_read` 为空却答对 = 证据链缺失(要么 grep 输出直接当答案未记账,
  要么动用参数记忆),参考实例 newpj4 实测某模型两题即此,按记账缺陷记录、不给检索分。
- 题面之外不追问、不给提示;agent 反问时统一回「按你的判断作答」。
- 模板措辞在一次横评内**逐字冻结**;改模板 = 新方案,须新开 arm 重跑,不与旧 run 混比。

## 2. Run 文件格式

每行一题(JSONL),与参考实例 newpj4 的 run 文件格式兼容:

```json
{"qid": "q1-default-greeting",
 "files_read": ["concepts/greeting-protocol", "raw/guide/style-guide.dated.md"],
 "answer": "默认问候语是「你好,世界」…"}
```

- `files_read`:agent 实际 Read 打开的路径;`wiki/` 前缀与 `.md` 后缀写不写均可(打分器归一等价),
  `raw/` 路径保留前缀原样;**grep/glob 命中不记入**。
- `answer`:agent 最终回答文本(answer_keys 判卷与诚实探针锚点匹配的对象)。
- 存放:`evals/runs/<date>-<label>.jsonl`,label 注明方案与模型(如 `2026-07-18-sonnet-R3`)。

## 3. 记账口径(与 eval_compare.py 头注同源,勿改)

- **grep 不算 read**:grep/glob 命中行零计费,只有 Read 打开的文件计成本——这是 W-LNT-1
  「大文件 grep-only」协议红利得以量化的前提。
- **成本按文件实际体量客观重算,不采信 agent 自报**:对 files_read 每个 wiki 文件按全文
  `est_tokens` 计(profile = config `budgets.est_tokens_profile`);同题同文件去重计一次。
- **raw 切片 flat 计费**:`raw/` 文件按锚定切片计 config `budgets.raw_slice_tokens`(缺省 1200),
  不按全文——协议规定 raw 不整读;若 agent 实际整读了 raw 大文件,flat 口径会低估其成本,
  在报告里注明(参考实例 newpj4 R2-q14 即此)。
- **boot 摊销单列**:协议组每会话固定 boot 成本(`_map` + overview,参考实例 newpj4 实测 ~3.1K)
  不摊进单题明细,单独一行列示,再按题数摊销并入均值对比(newpj4 16 题摊后 +0.8K/题 仍最便宜)。
  对照组无 boot 项。
- 报告最少四列:precision / recall / 均 tok/题 / 最差题 tok;另附诚实探针通过数与漏必读题数。

## 4. est_tokens 重校准方法

`est_tokens` 是启发式(cjk:CJK≈1 字/token、其余≈4 字符/token;latin:≈len/4),不是真 tokenizer:

1. **何时换 profile**:实例语料主语言变化(如英文库用 `latin`)→ 改 config
   `budgets.est_tokens_profile`;
2. **换后必须重跑基线**:成本口径变了,历史 run 的 tok 数字全部按新 profile 重算
   (工具按 config 现值重算,rerun eval_compare 即可),**禁止**新旧 profile 的 tok 数字混表对比;
   P/R 不受影响,可跨 profile 比;
3. **校准判据**:抽 5–10 页典型页面,用可得的真 tokenizer 计数对比两档误差,取误差小者;没有
   tokenizer 时按主语言选(CJK 为主 → cjk,拉丁为主 → latin)即可——est_tokens 只用于**同库内
   相对比较**,系统性偏差不影响方案排序。

## 5. 模型选型方法

框架**只给方法不给结论**:用自家 golden 复跑候选模型,自行裁决。

1. 每个候选模型 × 两方案(协议组 + 裸 grep 对照组)各跑一遍全量 golden;
2. 比五项:precision / recall / API 轮次 / 16 题总成本(按官方定价 + 缓存感知权重)/ 诚实探针;
3. **警示:便宜模型不吃协议红利**(参考实例 newpj4 实测口径):Haiku 4.5 两方案 API 轮次相同
   (115/115),协议未省轮次,只靠协议防错小幅提 recall(0.655→0.696);协议红利在强模型上兑现
   最充分(Sonnet 5:R2→R3 轮次 −49%、成本 −38%、precision +0.035)。若你的实例用便宜模型跑
   检索,先自测再下结论,勿假设协议自动省钱;
4. 也看**证据链质量**:files_read 为空却答对的模型(参考实例 newpj4 实测 Opus 4.8 两题)不适合
   检索岗位——引用命中维度正确捕获了这一缺陷,即使其答案正确率满分;
5. 结论**只在本实例内有效**,不外推、不回流框架当默认值。

## 6. 新实例建基线流程

1. 首批 **~10 篇源**走完 ingest、`_map` 决策表回填后,立即建基线(config 填偏——trust_posture/
   facet 设置错误——要靠它早期显形);
2. 按 `/wiki-golden` + `question-types.md` 出 **≥10 题**:9 题型全覆盖,unanswerable 与 route
   至少各 1;过 `--check-golden`;
3. 双方案各跑一遍(协议组 + 裸 grep 对照),按本文 §1–§3 记账;
4. `eval_compare` 出双列报告存 `evals/COMPARISON-<date>.md`,连同 runs/ 一起提交——这就是实例的
   质量基线;
5. 此后触发复跑的时点:每次 `/wiki-upgrade` 门禁(W-UPG-2:P/R 与 tok/题不回退,回退即回滚)、
   结构性重构(拆页/索引分片)前后各一轮、golden 修题(any-of 校准)后;
6. 复跑后按 `question-types.md` 的校准纪律逐题复盘:答案对路径不同 → any-of 修 golden;
   答案错 → 修协议/修页,不修 golden。

## 补充裁定(v1.0)

- **eval run 豁免 W-QRY-2**:评测会话不归档 queries/(避免污染下轮 route 题的缓存命中);真实查询会话照常归档。
- **unanswerable 题只声明不补背景**:按 W-QRY-3 声明「未收录」即止,不得用库外知识补答(锚点之外的补充会掩盖收录边界)。
- **双盲纪律**:出题人与执行员应为独立会话;执行员不得读 golden/answer_keys(兼任场景须在 run 备注声明,横评以独立会话重跑为准)。
