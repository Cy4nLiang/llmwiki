# 实施任务清单

> 由 spec.md 生成（2026-07-24，基于 research-tools / research-framework 两份代码调研）
> 任务总数: 15
> 核心原则: 按里程碑推进（M1 检索与图谱 → M2 采集与分发 → M3 生命周期与外延 → M4 RFC）；每任务后 `python3 tests/run_ci.py` 全绿（本仓的"可编译"）；规则条目与实现同任务落地，簿记环（VERSION/UPGRADING/CONTRIBUTING/MANIFEST）按里程碑收口

## 依赖关系总览

```
M1  Task 1 (S1 textindex lib + search-index 派生)
      ↓
    Task 2 (S1 search.py CLI + _map/tools.cmds 布线)   ← 依赖 T1
      ↓
    Task 3 (S1 keyword-miss 题型 + CI hit@3)           ← 依赖 T2
    Task 4 (S2 graph.json + backlinks.md + lint)       ← 可与 T1-3 并行
    Task 5 (S9 secscan)                                ← 可并行
      ↓
    Task 6 (M1 发版簿记 v1.2.0)                        ← 依赖 T1-T5

M2  Task 7 (S3 extras/hooks)      ← 可并行
    Task 8 (S4 分发三件套)         ← 可并行
    Task 9 (S5 bootstrap)          ← 可并行
      ↓
    Task 10 (M2 发版簿记 v1.3.0)   ← 依赖 T7-T9

M3  Task 11 (S6 supersession)      ← 依赖 T4（contradictions 派生结构）
    Task 12 (S7 wiki-research)     ← 可并行
    Task 13 (S8 MCP server)        ← 依赖 T2（wiki_search 复用 search.py）
M4  Task 14 (S10 团队模式 RFC)     ← 可并行
      ↓
    Task 15 (M3/M4 发版簿记 v1.4.0 + 总验收) ← 依赖 T11-T14
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `tools/lib/textindex.py` | 新建 | T1 | tokenizer（CJK bigram+英文小写）+ BM25 构建/查询共享库 |
| `tools/lib/wikigraph.py` | 新建 | T4 | wikilink slug 解析下沉（lint/build_site/build_index 三方复用） |
| `tools/lib/secscan.py` | 新建 | T5 | stdlib 正则密钥扫描 + 行内豁免标注 |
| `tools/build_site.py` | 修改 | T1, T4 | 派生 site/agent/search-index.json、site/agent/graph.json |
| `tools/build_index.py` | 修改 | T4, T11 | 派生 wiki/backlinks.md；contradictions.md 增"演进链"分节 |
| `tools/lint_wiki.py` | 修改 | T4, T5, T11 | derived 集合加 backlinks；索引存在性 soft 检查；W-SEC-2 块扩展；supersession 校验 |
| `tools/search.py` | 新建 | T2 | 排名检索 CLI（--root/--k/--json） |
| `tools/bootstrap_scan.py` | 新建 | T9 | 冷启动候选扫描（只读 repo + 写 state/） |
| `tools/init_render.py` | 修改 | T1, T2, T9 | T1：docs/ 拷贝 skip_dirs 豁免 design-docs；T2/T9：tools.cmds 槽位加行（:500-517） |
| `tools/gen_manifest.py` | 修改 | T1 | EXCLUDE_DIR_NAMES 增 design-docs（开发文档不入三档，与 init_render 豁免同口径） |
| `tools/eval_retrieval.py` | 修改 | T3 | CANONICAL_TYPES 增 keyword-miss（打分器零逻辑改动，route 先例） |
| `evals/golden.schema.json` | 修改 | T3 | canonicalType 枚举 +1 |
| `evals/question-types.md` | 修改 | T3 | 增 keyword-miss 节；"8 题型"→"9 题型" |
| `.claude/skills/wiki-golden/SKILL.md` | 修改 | T3 | 题型表 +1（render-once，升级三方合并） |
| `evals/playbook.md` / `README.md` | 修改 | T3 | 题型计数 "8→9" 同步（实施中发现的 spec-外文件，题型总数出现处；knowledge/ 实例拷贝走自身升级不动） |
| `templates/wiki/_map.md` | 修改 | T2 | 决策表加「关键词不确定」行 + 档位表登记（:39-54, :18-29） |
| `templates/skills/wiki-bootstrap/SKILL.md` | 新建 | T9 | 实例工作流 skill（build_plan 自动枚举，零代码接入） |
| `templates/skills/wiki-research/SKILL.md` | 新建 | T12 | followups 出口工作流 |
| `templates/skills/wiki-ingest/SKILL.md` | 修改 | T5 | 投递/整合步骤提示密钥扫描 |
| `templates/skills/wiki-query/SKILL.md` | 修改 | T11 | 命中 superseded 页必须跟到最新 |
| `.claude/rules/aggregate-pages.md` | 修改 | T11 | supersedes/superseded_by 字段说明（render-once） |
| `extras/hooks/capture_draft.py` | 新建 | T7 | SessionEnd/Stop → 起草 raw/inbox（kind:draft） |
| `extras/hooks/boot_reminder.py` | 新建 | T7 | SessionStart → 注入"先读 _map"提醒 |
| `extras/mcp_server.py` | 新建 | T13 | 纯 stdlib JSON-RPC/stdio，4 工具（**落位偏离 spec，见风险#1**） |
| `extras/README.md` | 修改 | T7, T13 | 登记 hooks 与 mcp_server |
| `.claude-plugin/marketplace.json` 等 | 新建 | T8 | Claude Code plugin 分发（meta 档，升级零干扰） |
| `docs/hooks.md` / `docs/mcp.md` / `docs/rfc-team-mode.md` | 新建 | T7, T13, T14 | 配置片段、协议面、团队 RFC |
| `README.md` | 修改 | T8 | 60 秒 quickstart + 竞品对比表 + add-skill 用法 |
| `framework/RULES.md` | 修改 | T2, T4, T5, **T8**, T11 | 新增 W-IDX-3 / W-IDX-4 / W-SEC-3 / **W-DIST-1（T8 实施中新增，见任务 8）** / W-ING-5（27→**32** 条，头行计数同步；T8 后已达 31） |
| `framework/UPGRADING.md` | 修改 | T6, T10, T15 | 顶插 1.2.0 / 1.3.0 / 1.4.0 迁移条目 |
| `framework/VERSION` + `framework/MANIFEST.json` | 修改 | T6, T10, T15 | 三次 MINOR + gen_manifest --date 重导 |
| `CONTRIBUTING.md` | 修改 | T6, T10, T15 | 断言计数（:20）与规则计数（:31）同步 |
| `tests/run_ci.py` | 修改 | T1-T5, T7, T9, T11-T13 | 新 phase / derived_paths / preflight / ZERO_ERROR 相应扩展 |
| `tests/hello-wiki/` | 修改 | T3, T4, T11 | 现场注入类夹具（tmp 造，主夹具 golden 与 ⚠️ 恰-1 不动） |
| `wiki.config.example.json` / `tests/hello-wiki/config*.json` | 修改 | T6, T10, T15 | framework_version 随版 bump |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `tools/lib/fm.py` 钉死 API | **零改动**（MAJOR 面，禁动） | 全部工具 | — |
| `build_index.py` 数据函数签名（:122 "lint 复用勿改"） | 零改动，仅新增函数 | lint_wiki | T4 |
| `build_site.py --json` 输出 | 增 outputs 键（向后兼容） | sync.py rebuild_derived（:344） | T1, T4 |
| `lint_wiki.py --json` checks[] | 新增检查项（向后兼容） | sync、run_ci、upgrade 门禁 | T4, T5, T11 |
| 新 CLI：search.py / bootstrap_scan.py / mcp_server.py | 新增 | agent（_map/tools.cmds）、MCP 宿主 | T2, T9, T13 |
| golden schema canonicalType | 枚举扩展（旧 golden 全兼容） | eval_retrieval、wiki-golden | T3 |

### 构建系统变更

- `gen_manifest.py` 重导（每里程碑，带 `--date`，坑：不带会丢 generated 键）：新增 tools/*.py、tools/lib/*.py、extras/* 自动收录 frozen；templates/skills 新目录自动 render-once；`.claude-plugin/` 落 meta 档（升级机械零干扰）——T6/T10/T15
- `tests/run_ci.py` preflight 清单（:874-887）补新夹具/新文件——随各任务

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | **S8 落位偏离 spec**：spec 写 `tools/mcp_server.py`，但 tools/ 会自动拷入所有实例并进 tools.cmds 必读面；extras/ 才是"可选组件"语义（serve.py 先例：subprocess 调 tools --json 保单源） | T13 | **按 extras/mcp_server.py 实施**，docs/mcp.md 写清两条启用路径。⚠️ 请在确认本清单时裁决 |
| 2 | **W-LNT-4 取消**：spec 拟为孤立页发新规则，但调研确认孤立页检查已存在（W-PAGE-3 orphans + W-ING-1 quasi_orphan，lint_wiki.py:197-206）；S2 的 lint 增量是口径升级+索引存在性 soft 检查，不需要新 ID。实发规则 4 条：W-IDX-3/W-IDX-4/W-ING-5/W-SEC-3（27→31） | T4 | 已按调研修正，tasks 与 RULES 按 4 条执行 |
| 2b | **集线器提示（hub hint）显式豁免**（T4 review t4-spec F1）：spec §4 S2 设计段列「孤立页警告 **与集线器提示**」两项；孤立页由 W-PAGE-3 orphans 满足，但 hub hint 未实现。**豁免理由**：(a) S2 映射的可验收需求是 **R2**（spec §3「任意页反链可查；孤立页被 lint 捕获」）——R2 本身**不含** hub hint，它只出现在 §4 S2 设计散文里，属超出所映射需求的额外 affordance；豁免它符合 spec §7「每项必须映射 R1-R8，映射不上就砍」的极简纪律（t4-spec 复核补强）。(b) §6 S2 验收未列 hub hint 为硬交付。(c) 中心/hub 分析所需 in-degree 数据已由 `site/agent/graph.json` 边表完整提供（消费方自行统计入度）。(d) lint 是**缺陷检测器**，高入链是良性信号（非缺陷），加 warning 会污染干净实例。比照风险#2 的 W-LNT-4，此处显式记录豁免而非静默遗漏 | T4 | 中心分析走 graph.json 数据面;若后续视为硬需求可加 lint info 或 graph.json `hubs` 字段 |
| 2c | **单源收敛 + 正向断言**（T4 review t4-std/t4-spec）：① `textindex.py` 的 `_ROOT_EXCLUDE_STEMS` 是第二份派生物判定，改用 `wikigraph.is_derived`（坐实 is_derived 单源，跨 T3 文件）；② lint 删本地 `SUBDIRS` 常量、吃 `wikigraph.resolve_slug` 默认（子目录集单源）；③ CI 补 backlinks 正向断言（spec §6「断言反链正确」） | T4 | 已实施 |
| 3 | keyword-miss 走**正式第 9 规范题型**（route 先例：score() 不读 type:254-338，特殊性只在出题面）；CI 题走 tmp 现场造（bad-golden 先例），主夹具 golden 与 EXPECT_SUMMARY（run_ci.py:86）不动 | T3 | 枚举先行、夹具后动（顺序反了 --check-golden warning → run_ci 红） |
| 4 | S6 supersession **不走 ⚠️ 机制**（演进≠真矛盾，W-ING-3 三分本义；且 run_ci:288 断言全库恰 1 条 ⚠️）；contradictions.md 增独立"演进链"分节 | T11 | 夹具不动 ⚠️ 计数 |
| 5 | **本轮零 config schema 改动**：search 参数走 CLI 默认+flag；hooks 走文档+环境变量（实例私有配置留 x- 命名空间）。规避 TOP_KEYS/validate_config/schema 三处联动（init_render.py:51-52,:93-94） | T2, T7 | 若后续要一等特性化，按 schema 自述"高频回流进 MINOR"再升格 |
| 6 | 模板改动（_map、wiki-golden、aggregate-pages）是 render-once 档：真实实例升级会出 `.upgrade-new` 冲突 | T2, T3, T11 | UPGRADING 迁移条目必须写明可执行的实例动作（逐 diff 合并指引） |
| 7 | S3/S4/S7 的"e2e"含宿主行为（hooks 触发、npx/plugin 安装、web 调研），CI 无法全自动复现 | T7, T8, T12 | CI 做机械冒烟（脚本 --help/JSON 可解析/文件存在），人工 e2e 清单落 docs |
| 8 | 禁加新条件模块 key（upgrade.py:114-122 镜像 _compute_conds 仅 3 key，h5 断字节等价）——新模板内容只用固定文本或现有槽位 | T2, T9, T12 | 新 skill 模板不含条件块 |
| 9 | 仓内不得出现 token 样式串（CONTRIBUTING.md:58）——S9 假 token fixture 必须 CI 运行时 tmp 现场造 | T5 | 沿 bad-golden 先例 |
| 10 | knowledge/ dogfood 回归：每发版任务在 knowledge/ 跑 build+lint+golden，P 1.000 / R 0.958 与 tok/题不回退 | T6, T10, T15 | 回退即修复或回滚该里程碑 |
| 11 | **实施中发现（T1 review F-4 补登记）**：spec/tasks 落库 `docs/design-docs/` 使其被 classify 判入 frozen 档——不豁免则 tasks.md 每次编辑打脏 MANIFEST hash（lint --manifest/upgrade fail-fast），且设计文档随 init_render 分发进所有实例 | T1 | 已实施双豁免：gen_manifest EXCLUDE + init_render skip_dirs（同名同口径、注释互指）；CLAUDE.md 已补契约例外说明；T6 UPGRADING 条目提及 |

## 任务列表

### 任务 1: [Completed] S1a 检索索引：tools/lib/textindex.py + build_site 派生 search-index.json
- 文件: `tools/lib/textindex.py`（新建）, `tools/build_site.py`（修改）, `tests/run_ci.py`（修改）
- 依赖: 无
- spec 映射: spec §4 S1
- 说明: 新建共享检索库（tokenize：CJK bigram + 英文小写切词，复用 fm.est_tokens 不复制；BM25 参数 k1=1.5,b=0.75 常量；字段权重 title/aliases×3、description×2、headings×1.5、body×1）；build_site 全文已在手（collect_wiki→read_page），就地建倒排，派生 `site/agent/search-index.json`（排序键固定，无时间戳）。**注意 collect_wiki 只扫四子目录（build_site.py:48），索引需自扫 overview/_map 等根页**。
- context:
  - `tools/build_site.py:331-350 collect_wiki()` / `:400-426 build_jsonl()` / `:464-473` 产出与 mkdir — 派生物接入点
  - `tools/build_site.py:117-124 _write_if_changed`（就近复用本文件版本）
  - `tools/lib/fm.py:115-128 est_tokens` / `:182-196 iter_pages`（钉死 API，只 import 不改）
  - `tests/run_ci.py:196 derived_paths` — 幂等字节断言接入点；`:236 phase_build`
- 验收标准:
  - [x] `python3 tools/build_site.py` 两次运行 search-index.json 字节一致；重跑 outputs 全 "unchanged"
  - [x] search-index.json 进 run_ci derived_paths 确定性断言；run_ci 全绿
  - [x] `grep -rn "import " tools/lib/textindex.py` 仅 stdlib
- 子任务:
  - [x] 1.1 textindex.py：tokenize/_weighted_tf/build_index/search + collect_docs + 自检入口
  - [x] 1.2 build_site 接入（含根页扫描、写盘前派生、紧凑落盘）+ --json outputs 登记
  - [x] 1.3 run_ci derived_paths + preflight 清单更新
  - [x] 1.4 [review] 2 轮修复：写盘次序/索引体积/字段互斥/文案/单源钉子（详见 review 报告）

### 任务 2: [Completed] S1b 查询 CLI：tools/search.py + _map/tools.cmds 布线 + W-IDX-3
- 文件: `tools/search.py`（新建）, `templates/wiki/_map.md`（修改）, `tools/init_render.py`（修改）, `framework/RULES.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: Task 1
- spec 映射: spec §4 S1
- 说明: search.py CLI（`--root/--k 8/--json`；输出 slug/score/description/est_tokens；确定性 tie-break：score desc, slug asc；索引缺失时 exit 2 提示先跑 build_site；**装载时校验 format 字段与基本形状，畸形/版本漂移 → 清晰报错 exit 2**——T1 review F-6 移交：textindex.search() 契约自限于 build_index 产物，防御归装载层）；_map 模板决策表（:44-49）加「关键词不确定/多词模糊 → `python3 tools/search.py "词1 词2" --json`」行、读取档位表（:18-29）登记 search-index grep-only；init_render tools.cmds 槽位（:500-517）按存在性加 search 行；RULES.md 登记 W-IDX-3（机器检索索引派生：单源、确定性、勿手编，头行计数 27→28 暂记，T6 统一核对）。
- context:
  - `templates/wiki/_map.md:39-54` 决策表 / `:18-29` 档位表 / `:73` ≤map_lines 硬预算（加行后仍须 ≤100 行）
  - `tools/init_render.py:500-517 _m2 tools.cmds`（按文件存在性标注的先例）
  - `framework/RULES.md:15` 表行格式 / `:13` 计数行 / `:17-43` 现有 27 条
  - `tools/eval_retrieval.py` CLI 形状先例（--root 解析 resolve :385-388）
- 验收标准:
  - [x] 在 tests 渲染实例上 `python3 tools/search.py "问候 协议" --json` 返回含 greeting-protocol 的 top-k，两次运行输出字节一致
  - [x] `python3 tools/lint_wiki.py --check-slots` 零残留；渲染实例 _map ≤100 行
  - [x] run_ci 全绿（渲染差异被 h2/h3 升级路径正常吸收）
- 子任务:
  - [x] 2.1 search.py（载索引→装载层校验→打分→排序→人读/JSON 双输出；F-6 广捕兜底）
  - [x] 2.2 _map 决策表+档位表 + tools.cmds + RULES.md W-IDX-3（27→28）
  - [x] 2.3 run_ci：search 冒烟（命中/幂等/无索引 exit 2）+ 损坏索引 3 家族 exit 2 probe
  - [x] 2.4 [review] 3 轮：F-6 装载校验从枚举白名单 → 广捕（AttributeError/ZeroDivisionError 逃逸闭合）

### 任务 3: [Completed] S1c keyword-miss 第 9 题型 + CI hit@3 门禁
- 文件: `tools/eval_retrieval.py`（修改）, `evals/golden.schema.json`（修改）, `evals/question-types.md`（修改）, `.claude/skills/wiki-golden/SKILL.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: Task 2
- spec 映射: spec §4 S1（验收"keyword-miss 题 hit@3"）
- 说明: **顺序铁律：先枚举后夹具**。CANONICAL_TYPES（eval_retrieval.py:101-102）+ schema $defs.canonicalType（:151-162）+ question-types.md 增节（出题要点：问题措辞刻意避开目标页标题/别名用词，打分与普通题相同——route 先例文案 :33-35）+ wiki-golden 题型表（:43-53）"8 题型"→"9 题型"。run_ci 新 phase_search：tmp 现场造 3 道 keyword-miss golden（指向渲染实例既有页），断 ① --check-golden 零 error 零 warning ② 对每题跑 search.py，golden 2 级页命中 top-3。
- context:
  - `tools/eval_retrieval.py:101-106` 题型枚举与别名 / `:33-35` route "打分与普通题完全相同" 先例 / `:254-338 score()` 不读 type 的证据
  - `evals/golden.schema.json:151-162` canonicalType / `:174-179` x-alias-map
  - `tests/run_ci.py:449 phase_golden_check`（--check-golden 断言先例）/ `:460 bad-golden tmp 现场造先例` / `:895-906 main()` 挂载顺序（**插在 :904 phase_upgrade 之前**）
- 验收标准:
  - [x] 含 keyword-miss 的 golden 过 `--check-golden` 零 warning
  - [x] 3 题 hit@3 全中；run_ci 断言数净增 ≥6（本任务与 T1/T2 合计）
  - [x] 主夹具 golden/EXPECT_SUMMARY（run_ci.py:85-86）零改动
- 子任务:
  - [x] 3.1 枚举/schema/文档/skill 同步（+README/playbook 题型计数 8→9）
  - [x] 3.2 phase_keyword_miss 实装（造题→check-golden 零 warning→题面派生词 hit@3）
  - [x] 3.3 [review] P2-A 门禁保真度（query 改题面派生词、避答案）+ P2-C provenance 补注

### 任务 4: [Completed] S2 图谱派生：graph.json + backlinks.md + 点名同步 + W-IDX-4
- 文件: `tools/lib/wikigraph.py`（新建）, `tools/build_site.py`（修改）, `tools/build_index.py`（修改）, `tools/lint_wiki.py`（修改）, `framework/RULES.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: 无（与 T1-3 可并行；T11 依赖本任务）
- spec 映射: spec §4 S2
- 说明: wikigraph.py 下沉 slug 解析+边表构建（复用 fm.iter_wikilinks :138-164；与 lint resolves() :160-166 同口径，lint 改为调用 lib 消除第二份实现）；build_site 派生 `site/agent/graph.json`（边表 [{from,to,line}]，排序固定）；build_index 派生 `wiki/backlinks.md`（generated 标记 + _preserved_created :109-119）。**四处点名同步（雷区）**：① RULES.md W-ARCH-2 例外条款文案（:18）加 backlinks.md；② lint derived 集合（lint_wiki.py:158）；③ contradiction_lines 豁免（build_index.py:203）；④ build_index 头注（:16）。lint 增 graph.json/search-index.json 存在性 soft 检查（镜像 pages.jsonl 先例 :344-348）；orphans/quasi_orphan（:197-206）口径不变。RULES.md 登记 W-IDX-4。
- context:
  - `tools/build_index.py:124-216` 数据函数（勿改签名）/ `:203` 豁免名单 / `:304-351` emit 与统计
  - `tools/lint_wiki.py:157-206` 入链计数与孤儿检查 / `:158` derived 集合 / `:294-297` generated 标记检查 / `:344-348` 存在性 soft 先例
  - `tests/run_ci.py:196 derived_paths` / `:284 assert_contradictions 恰-1` / peer 注入模式 `:408-416`（孤儿注入断言沿用）
- 验收标准:
  - [x] backlinks.md 不吃 W-PAGE-1 预算检查、带 generated 标记、不被 contradictions 自采集、不把孤儿页"救活"
  - [x] 克隆实例现场注入孤儿页 → checks["orphans"] 计数 +1（warning 级）；base 夹具零孤儿保持
  - [x] graph.json/backlinks.md 进 derived_paths 幂等断言；run_ci 全绿
- 子任务:
  - [x] 4.1 wikigraph.py（is_derived/resolve_slug/build_graph/backlinks 单源）+ lint resolves/derived 下沉
  - [x] 4.2 build_site graph.json + build_index backlinks.md（+新鲜度/存在性 lint）
  - [x] 4.3 四处点名收敛到 is_derived 单源 + W-IDX-4（28→29）+ 确定性修复（边两端须真实节点）
  - [x] 4.4 run_ci：derived_paths + 孤儿注入 + 正向反链断言
  - [x] 4.5 [review] 单源坐实（textindex/lint 收敛 is_derived/SUBDIRS）+ hub hint 显式豁免（#2b）

### 任务 5: [Completed] S9 脱敏扫描：tools/lib/secscan.py + lint 扩展 + W-SEC-3
- 文件: `tools/lib/secscan.py`（新建）, `tools/lint_wiki.py`（修改）, `templates/skills/wiki-ingest/SKILL.md`（修改）, `framework/RULES.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: 无
- spec 映射: spec §4 S9
- 说明: secscan.py：stdlib 正则集（AWS AKIA…、GitHub ghp_/gho_、私钥块 BEGIN.*PRIVATE KEY、通用 key=value 长随机串），`scan_text(text)->[findings]` + 行内豁免标注 `<!-- secscan:allow -->`（豁免下一行）；挂 lint（独立 `content_secrets` _chk，非并入 W-SEC-2）扫描面到 wiki/**.md（**排除派生页避双报**）与 **raw/ 全库内容文件（递归 .md/.txt——inbox 等子目录是密钥落地处，正是要拦的地方；tasks 早稿"顶层"为叙述 imprecision，以递归实现为准）**，**severity 保持 warning**（RULES.md:41 钉死 soft 的先例；只报类型行号**不回显值**）；ingest skill 模板加一步"整合前留意密钥，命中即遮蔽并在 Processing Notes 标注"。RULES.md 登记 W-SEC-3。
  - **review 驱动强化**（T5 t5-robust/t5-spec，5×P2）：allow 用**锚定注释形态**（防散文提及 secscan:allow 绕过）；词表补 client_secret/token/private_key/credential + github_pat/PGP-BLOCK/ASIA（放宽复合名边界）；generic 值需含**熵信号**（≥1 大写或数字，压纯小写连字符散文误报）；解码失败**显式计数**（不静默 fail-open）。R8「拦截或遮蔽」= ingest 遮蔽(preventive) + lint soft(detective)，soft 不 hard-fail CI，与 W-SEC-2 先例及 llmwiki 软治理范式一致（已批准设计）。
- context:
  - `tools/lint_wiki.py:350-364` W-SEC-2 现有块（cred_re 与 soft 语义）/ `:52-57` sys.path 插 lib 的 import 先例 / `:143-145 _chk` 注册
  - `tests/run_ci.py` tmp 现场造负例先例（bad-golden :460；**假 token 严禁入仓** CONTRIBUTING.md:58）
- 验收标准:
  - [x] tmp 实例注入含假 token 页 → lint 报 W-SEC-3 warning 且 exit 仍 0（soft）；加 `secscan:allow` 标注后不再报
  - [x] base 夹具与 knowledge/ 全库零命中；run_ci 全绿
- 子任务:
  - [x] 5.1 secscan.py 正则集（AWS/GCP/GitHub/PAT/Slack/私钥块/generic）+ 锚定 allow 豁免 + 值不回显
  - [x] 5.2 lint 挂 W-SEC-3（排除派生页 + fail-open 计数）+ RULES.md（29→30）+ ingest 脱敏步
  - [x] 5.3 run_ci 命中/豁免两态（假 token 运行时构造）
  - [x] 5.4 [review] 5×P2 修复（allow 锚定/词表/token 形态/熵信号/fail-open）+ 3 精修（带理由 allow/去 pwd/passphrase 限制入头注）

### 任务 6: [Completed] M1 发版簿记 v1.2.0 + dogfood 回归
- 文件: `framework/VERSION`, `framework/UPGRADING.md`, `framework/MANIFEST.json`, `CONTRIBUTING.md`, `wiki.config.example.json`, `tests/hello-wiki/config*.json`, 模板 W-* 行内标注, `CLAUDE.md`（T1 已补 design-docs frozen 例外半句，此处仅终核）
- 依赖: Task 1-5
- spec 映射: spec §5 M1、§6 横切验收
- 说明: VERSION 1.1.1→1.2.0；UPGRADING **顶插** `## 1.2.0 — <日期>（判级:MINOR）` 条目（迁移清单逐行引 W-IDX-3/W-IDX-4/W-SEC-3；**_map 模板变更的实例动作写明 .upgrade-new 逐 diff 合并指引**；信息性提及 `docs/design-docs` 已豁免 frozen 分发面，实例侧无迁移动作）；**规则总数计数四处同步**（随 RULES.md 终值）：`CONTRIBUTING.md:31`、`README.md:114`、`framework/UPGRADING.md:56`、以及 CLAUDE.template.md 的 W-* 行内标注补 W-IDX-3——⚠️ T2 review(t2-std) 指出 README:114 未挂任何任务改动点，**易漏，务必纳入本次核对**；**断言总数计数三处同步**（随 run_ci 实跑值，现 158，仍会随 T4/T5 增长——按最终实跑值一次改到位）：`CONTRIBUTING.md:20`、`README.md:84`、`README.md:124`，并在 UPGRADING 1.2.0 条目记「断言数 134→N」——⚠️ T3 review(t3-std) 指出这是 T1/T2/T3 批次累积漂移（非单任务引入），README:84/124 易漏；模板 W-* 行内标注与 RULES 对齐（无机检，手工核对）；`python3 tools/gen_manifest.py --date <today>`；夹具/示例 config framework_version bump（软 warning 消除）。**dogfood 回归**：knowledge/ 下跑 build_site+build_index+lint+eval_retrieval，golden P 1.000 / R 0.958 不回退。
- context:
  - `framework/UPGRADING.md:10-34` 顶插与条目模板/纪律 / `tests/run_ci.py:594` `^## x.y.z` 解析（条目头格式铁律）
  - `tools/gen_manifest.py:106-107` --date 坑 / `tools/upgrade.py:389-395` mf_stale fail-fast
  - `knowledge/evals/` golden 与基线
- 验收标准:
  - [x] run_ci 全绿（h1-h5 升级路径含新文件"直接安装"分支通过）
  - [x] knowledge/ golden：P/R 与漏必读数与基线一致
  - [x] `git status` 无未登记 frozen 变更（MANIFEST hash 全对）
- 子任务:
  - [x] 6.1 VERSION 1.2.0 + 4 处 framework_version + 规则 27→30 + 断言 134→173 + UPGRADING 1.2.0 条目 + CLAUDE.template W-* 对齐 + gen_manifest（最后一步）
  - [x] 6.2 全量 run_ci（173 PASS，升级模拟 base→1.2.1）+ knowledge/ dogfood 回归（P 1.000/R 0.958 逐位一致，回归后还原）
  - [x] 6.3 [review] P1×2（历史条目误改还原/README banner）+ P2（迁移清单补 wiki-ingest）+ MANIFEST 幂等定验

### 任务 7: [Completed] S3 捕获 hooks：extras/hooks + docs/hooks.md
- 文件: `extras/hooks/capture_draft.py`（新建）, `extras/hooks/boot_reminder.py`（新建）, `docs/hooks.md`（新建）, `extras/README.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: 无（M2 起点）
- spec 映射: spec §4 S3
- 说明: capture_draft.py：读 stdin 的 Claude Code hook JSON（SessionEnd/Stop），起草 `raw/inbox/<date>-session-draft-<sid>.md`（frontmatter title/date/kind:draft——沿 local_notes 最小三字段 :34；**绝不写 wiki/**；**只投递 inbox 文件，不调 register**——pending 由 `sync` 目录 diff 持久重算成立，无需一次性台账，更契合投递≠整合；T7 review t7-spec 确认此简化不偏离 spec〔spec 无 register 要求〕，验收 pending+1 由 sync 重算 + CI 双坐实）；boot_reminder.py：SessionStart 输出「先读 wiki/_map.md」作为 additionalContext；docs/hooks.md 给 settings.json 配置片段（绝对路径调用，实例根经 env `LLMWIKI_ROOT` 传递）与人工 e2e 清单。**opt-in：extras/ 不拷入实例（init_render 拷贝面不含 extras），零新根目录（避 W-ARCH-3）；exit 恒 0**（非字符串 cwd / 未知参数 / 写失败均不打断会话——T7 review t7-robust 修复）。
- context:
  - `adapters/local_notes.py:34-36` inbox 最小 frontmatter / `:95-100` date/kind 校验 / `:130-136` state/tmp 原子写 / `:171-214` register
  - `adapters/CONTRACT.md §3:70-82` 写入边界 / `§5:143-144` 内容文件判定
  - `tests/run_ci.py:783 phase_extras`（serve/i18n 冒烟先例）
- 验收标准:
  - [x] 两脚本纯 stdlib、`--help` 可用；伪造 hook JSON 喂 stdin → inbox 出现合法草稿且 `sync status` pending +1
  - [x] kind:draft 不在 source_kinds → 仅 warning 不 fail（local_notes :98-100 语义保持）
  - [x] run_ci phase_extras 增两脚本冒烟断言，全绿
- 子任务:
  - [x] 7.1 capture_draft.py（投递 kind:draft，绝不写 wiki/，同 session 幂等，exit 恒 0）+ boot_reminder.py
  - [x] 7.2 docs/hooks.md（配置片段+e2e 清单+版本戳+raw_dir caveat）+ extras/README 登记
  - [x] 7.3 run_ci hooks 冒烟 + exit-0 回归锁（非字符串 cwd/未知参数/缺值）
  - [x] 7.4 [review] robust 4 修（cwd 类型守卫/argparse try-except/rglob/sid[:12]）+ spec F1 注记订正 + std 版本戳

### 任务 8: [Completed] S4 分发三件套：plugin + add-skill + README quickstart
- 文件: `.claude-plugin/`（新建：plugin 清单 + marketplace.json）, `README.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: 无
- spec 映射: spec §4 S4
- 说明: .claude-plugin/ 指向现有 `.claude/skills`（wiki-init/wiki-upgrade/wiki-golden 三向导）——调研确认与 build_plan/classify/upgrade 零碰撞（落 meta 档）；README 顶部加"60 秒上手"（clone → /wiki-init → ingest）+ 直接竞品对比表（工程化差异化：eval 门禁/升级契约/零依赖/诚实协议四行）+ `npx add-skill Cy4nLiang/llmwiki` 用法说明（skills 已是 SKILL.md 标准布局）；分发壳不复制正文、只引导进 init_render（确定性渲染不破）。
- context:
  - `tools/gen_manifest.py:35-49 classify`（.claude-plugin → meta 的证据）/ `tools/upgrade.py:359`（升级只碰 frozen+渲染件）
  - `.claude/skills/wiki-init/SKILL.md:10-14` 硬约束（分发文案不得违背：agent 只填 config、渲染归 init_render）
- 验收标准:
  - [x] marketplace.json/plugin 清单 JSON 可解析、路径存在（run_ci 机械断言）
  - [ ]（**未执行:人工 dogfood,发版后**） 全新目录按 README quickstart ≤2 条命令到首次 ingest（人工 e2e 清单落 README，含计时）
  - [x] run_ci 全绿；gen_manifest 后 .claude-plugin 列 meta 档
- 子任务:
  - [x] 8.1 .claude-plugin 清单
  - [x] 8.2 README quickstart+对比表+add-skill
  - [x] 8.3 run_ci JSON/路径断言

### 任务 9: [Completed] S5 冷启动：tools/bootstrap_scan.py + wiki-bootstrap skill
- 文件: `tools/bootstrap_scan.py`（新建）, `templates/skills/wiki-bootstrap/SKILL.md`（新建）, `tools/init_render.py`（修改：tools.cmds）, `tests/run_ci.py`（修改）
- 依赖: 无
- spec 映射: spec §4 S5
- 说明: bootstrap_scan.py：只读扫宿主 repo（README*、docs/**、**/adr/**、CHANGELOG*、`git log --grep` 决策关键词——git 缺席时降级跳过）→ `state/bootstrap-candidates.json`（候选：path/title 猜测/est_tokens/建议 kind；排序固定）；`--root` 指实例根、`--repo` 指宿主根（embedded 默认 ..）。wiki-bootstrap skill（templates/skills → build_plan 自动枚举 :667-693 零代码接入；**不含条件块**，避 h5 雷）：引导用户勾选候选 → 逐篇投 inbox → 批量 light ingest → followups 登记待晋升。
- context:
  - `tools/init_render.py:667-693 build_plan 自动枚举` / `:500-517 tools.cmds`
  - `tools/lib/fm.py:115-128 est_tokens`（token 预估复用）
  - `tests/run_ci.py:874-887 preflight`（新模板文件登记）
- 验收标准:
  - [x] 对 llmwiki 仓自身跑 scan → ≥10 候选；两次运行字节一致；只写 state/
  - [x] 渲染实例出现 .claude/skills/wiki-bootstrap/；run_ci 全绿
  - [ ]（**未执行:人工 dogfood,发版后**） 样例 repo 冷启动 ≤15 分钟到 10 页（人工 dogfood，计时入实例 log——发版后执行，不阻塞本任务）
- 子任务:
  - [x] 9.1 bootstrap_scan.py
  - [x] 9.2 skill 模板 + tools.cmds + preflight
  - [x] 9.3 run_ci：候选数/确定性断言

### 任务 10: [Completed] M2 发版簿记 v1.3.0
- 文件: 同 Task 6 清单
- 依赖: Task 7-9
- spec 映射: spec §5 M2、§6
- 说明: 1.2.0→1.3.0；UPGRADING 顶插（**S3/S5 无新 W-* 规则填「—」；S4 引 W-DIST-1**——T8 实施中新增，非原规划——迁移清单 3 条「—」+ 1 条 W-DIST-1，实例动作：可选启用 hooks 的指引、新 skill 经升级 ro_install 自动落位说明 upgrade.py:486）；gen_manifest --date；CONTRIBUTING 断言计数；dogfood 回归同 T6。
- 验收标准:
  - [x] run_ci 全绿；knowledge/ golden 不回退；MANIFEST 无 stale
- 子任务:
  - [x] 10.1 簿记环 + 回归

### 任务 11: [Completed] S6 supersession lite + W-ING-5
- 文件: `tools/lint_wiki.py`（修改）, `tools/build_index.py`（修改）, `.claude/rules/aggregate-pages.md`（修改）, `templates/skills/wiki-query/SKILL.md`（修改）, `framework/RULES.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: Task 4
- spec 映射: spec §4 S6
- 说明: frontmatter 可选 `supersedes:`/`superseded_by:`（值=slug，fm 解析恒 str/list 零破坏）；lint 新块（放 W-PAGE-4 块 :208-235 后，复用 pages :211 与 wikigraph 解析）：双向一致（A supersedes B ⟺ B superseded_by A）+ 目标可解析 + 被替代页须含指向后继的横幅行——**warning 级**起步；contradictions.md 增"演进链"分节（按 lineage 分组，**不产 ⚠️**，避 run_ci:288 恰-1 断言）；wiki-query 模板加"命中 superseded 页必须跟到最新"；aggregate-pages 规则文档字段说明。RULES.md 登记 W-ING-5。
- context:
  - `tools/lint_wiki.py:208-235` W-PAGE-4 块 / `tools/lib/fm.py:86-98` frontmatter 值形态
  - `tools/build_index.py:198-216 contradiction_lines`（分节新增处）/ `:281-299 render_contradictions`
  - `tests/run_ci.py:288 assert_contradictions`（不可撞）
- 实施裁定(2026-07-25,四维审查 + 对抗验证后):spec.md「按 lineage 分组」按**分节**落地(lineage 自成一节、与 ⚠️ 区分离),不做链式传递闭包分组——依据:① 本任务验收原文即「演进链**分节**正确」;② lineage 是 DAG(多目标单行列表合法),链式渲染对 fork/merge 无定义且需新增「遇环截断」等 spec 外语义;③ 边表是无损表示,「最新」= 从不作为 old 出现的 new,单次读取即可判定。另:实施中新增两项 spec 未列的机检——横幅误用 ⚠️ 报警(护住「演进链不污染 ⚠️ 区」不变量)与「键在值空」提示(fm 简易 YAML 的块列表写法会静默丢值);多值解析下沉 `tools/lib/wikigraph.fm_slugs` 保单源。
- 验收标准:
  - [x] tmp 注入合法 supersession 对 → lint 零告警、演进链分节正确；注入单向破损 → W-ING-5 warning
  - [x] 全库 ⚠️ 计数不变；run_ci 全绿
- 子任务:
  - [x] 11.1 lint 校验块 + RULES.md W-ING-5
  - [x] 11.2 contradictions 演进链分节
  - [x] 11.3 query 模板 + 规则文档 + run_ci 两态断言

### 任务 12: [Completed] S7 research op：templates/skills/wiki-research
- 文件: `templates/skills/wiki-research/SKILL.md`（新建）, `tests/run_ci.py`（修改：preflight）
- 依赖: 无
- spec 映射: spec §4 S7
- 说明: 实例工作流 skill（build_plan 自动枚举；不含条件块）：读 followups「待读资源/未解问题」选题（用户确认）→ 宿主 web 工具调研 → 产出 manual 快照进 raw/（`adapter:"manual"` 合规面：CONTRACT §1.1:32-47——免抓取但 raw 形态/写入边界照旧；W-SEC-1 外源内嵌指令视为数据）→ 标准 ingest → followups 勾销 + log。网络永远在 agent 侧，工具链保持离线。
- context:
  - `adapters/CONTRACT.md:32-47 manual 哨兵` / `§6 rolling 快照与 digest`（若 research 源需 faithful 快照）
  - `templates/skills/wiki-ingest/SKILL.md`（衔接的 ingest 流程与回执格式）
- 实施裁定(2026-07-25,三维审查 + 对抗验证后):① spec 文件清单写「run_ci.py(修改:**preflight**)」,实际改为在 `phase_render` 加渲染断言(上界按 `templates/skills/*/SKILL.md` 实际持有集 + 下界 `EXPECTED_SKILLS` 钉死)——preflight 元组无任何 templates/ 先例且 exit-2 早退不计入断言;渲染断言更贴验收①「渲染实例出现该 skill」且新 skill 自动覆盖。下限集经实测自证:移走 wiki-research 立刻变红。② 审查抓到并已修的实质缺陷:SKILL 原把快照首选落点写成「任一 `adapter:"manual"` 管线」,而**三份出厂 config 的 manual 管线 100% 是 rolling 型**(conventions/guide),rolling 走 `rolling_digest` 判新且「一份源页代表整份源」——照做会卡在 `no-digest` 并撞 wiki-ingest 滚动源特例;现改为限定 pull/push 逐篇型 + 明写 rolling 禁令 + 换用 `<SLOT:pipelines.table>`(带类型/适配器两列供 agent 自辨)。另移除 `<SLOT:trust.clause>`(它是**内生知识**的信任姿态,用在外网调研源上与本文件 W-SEC-1 互斥),改为明确的外源姿态;并补 mkdir/重渲染/push 型 provenance 无机检等可执行性缺口。
- 验收标准:
  - [x] 渲染实例出现 wiki-research skill；SKILL.md 含完整闭环步骤与 W-SEC-1 提示
  - [ ]（**未执行:人工 dogfood,发版后**） 人工 e2e：一条 followup 端到端闭环、源页 provenance 完整（发版后 dogfood，不阻塞）
  - [x] run_ci 全绿
- 子任务:
  - [x] 12.1 SKILL.md 撰写 + 渲染断言(见实施裁定①)

### 任务 13: [Completed] S8 MCP server：extras/mcp_server.py（落位已由用户裁决为 extras/，风险#1 收口）
- 文件: `extras/mcp_server.py`（新建）, `docs/mcp.md`（新建）, `extras/README.md`（修改）, `tests/run_ci.py`（修改）
- 依赖: Task 2
- spec 映射: spec §4 S8
- 说明: 纯 stdlib JSON-RPC 2.0 over stdio，实现 MCP 最小面（initialize / tools/list / tools/call），协议版本常量钉死；4 工具：`wiki_map`（返回 _map 全文+档位表）、`wiki_search`（subprocess 调 `tools/search.py --json`，保单源——serve.py 先例）、`wiki_page`（slug + mode=tldr|full + max_tokens 截断，带 est_tokens）、`wiki_capture`（写 raw/inbox 草稿，复用 local_notes register）；`--root` 指实例。docs/mcp.md：各宿主注册片段 + MCP inspector 验证步骤。
- context:
  - `extras/serve.py`（可选组件+subprocess 调 tools 的先例）/ `extras/README.md` 登记表
  - `adapters/local_notes.py:171-214 register`
  - `tests/run_ci.py:783 phase_extras`（stdio 子进程握手单测挂这里）
- 实施裁定(2026-07-25):① **落位 extras/**(用户明确裁决,风险#1 收口):tools/ 会整树拷进每个实例并进「工具速查」必读面,extras/ 才是可选组件语义(serve.py 先例)。② 协议面按官方规范实现并钉死 `PROTOCOL_VERSION = "2025-11-25"`(CI 侧另写一份字面量**双份钉死**,防协议被无声改动);NDJSON 帧、stdout 只写协议帧(诊断走 stderr,与 serve.py 相反,已在三处声明)、工具失败用 `isError` 而协议错误用 JSON-RPC code 的分层。③ `wiki_capture` 的投递口**取自 config 第一条 push 管线的 raw_dir**,不硬编码 `raw/inbox`(实例可改 raw_dir);与 `extras/hooks/capture_draft.py`(硬编码)的口径分歧已在 docs/mcp.md 如实记录,收敛方向留 T7 回流。④ 审查抓到并已修的真 bug:台账登记旗标写错(`--only` 是 sync.py 的,local_notes 是 `--pipeline`)导致登记 100% 失败且被吞成 ok:true;畸形 params/name(JSON-RPC 允许数组 params)会打死进程丢掉后续帧;title/kind 换行可注入伪 frontmatter;`max_tokens` 类型不符被静默换默认值使「硬承诺」失效;`_import_libs` 多模块 import 让 sys.modules 缓存锁死「退回同仓」回退分支。均已修 + 5 条 CI 负例锁死。⑤ 另修一处自查发现:`max_tokens` 原会超预算 1 token(`est_tokens` 含整除余数、**非线性可加**),改为对最终拼装结果判定 + 收敛,10 档预算全守约。
- 验收标准:
  - [x] CI 内以子进程起服务：initialize 握手 + tools/list 返回 4 工具 + wiki_map 调用返回含 "_map" 内容（JSON-RPC 帧解析断言）
  - [x] 全部 stdlib；docs/mcp.md 含 inspector 人工验证清单
  - [x] run_ci 全绿
- 子任务:
  - [x] 13.1 JSON-RPC/stdio 骨架 + 4 工具
  - [x] 13.2 docs/mcp.md + extras/README
  - [x] 13.3 run_ci 握手单测(11 条正例 + 5 条负例)

### 任务 14: [Completed] S10 团队模式 RFC + CI 配方
- 文件: `docs/rfc-team-mode.md`（新建）, `.github/workflows/ci.yml`（新建，可选）
- 依赖: 无
- spec 映射: spec §4 S10
- 说明: RFC-only：sources append-only 天然可并；聚合页 PR 三方合并（复用 upgrade.py render-once 合并思路）；页面所有权清单提案；CI 门禁配方（PR 上跑 `python3 tests/run_ci.py`+实例 lint+golden 的 GitHub Action——本仓自用即 RFC 的活配方）；shared/private 分区（peers `[[alias::slug]]` 延伸）。**v1 单写者语义零改动**；.github/ 落 meta 档零升级干扰。
- 实施裁定(2026-07-26,四维审查 + 对抗验证后):① 五设计点全覆盖;**提案 2「复用形状而非算法」判定满足 spec**——spec 原文是「复用…**思路**」,且三条不能搬算法的理由经代码证实(base 可确定性重渲染 vs 只能取 merge-base、有特权侧 vs 对等分支、整文件三态判定比 git 行级合并**更弱**);形状四条(绝不静默覆盖 / .merge-new 旁文件 / 私有区摘出 / append-only 与派生物剔除)已落迁移表阶段 4。② 验收②走 tasks 放宽的替代路径(语法校验 + 命令序列逐条实跑);ci.yml 注释如实写明「随 M1–M3 一并提交才会绿」。③ 审查抓到并已修的**事实错误**:提案 4 坑① 把「派生物缺失」的规则归属写错(实测唯一 error 是 W-IDX-1 判 `wiki/backlinks.md` 缺失,W-IDX-2 三缺只是 soft warning、不改退出码,`state/` 与退出码无关);「团队直接抄」漏了 `tests/` 不分发(实例仓**没有** run_ci.py)→ 已按两仓拆开;`site/` 被 gitignore 只在框架仓成立(init_render 生成的实例默认 .gitignore 只忽略 state/ 与凭证)→ 改为两选一并说明代价;迁移表阶段 4 旧信号「peer_links 无 error」**恒真**(该检查 severity 恒 warning)→ 改看计数;指针段 ID 清单漏 W-ARCH-3 且多列正文未引用的 W-UPG-1 → 现与正文 11 个完全一致;动机 1/提案 1 补 `kind: rolling` 例外(它是唯一同名覆盖 raw 且复用同一源页的管线,git 会报冲突故不属可并类)。④ 采纳的驳回:RFC 说 CI 门禁「已生效」不算不诚实——RFC(frozen,随实例分发)与 ci.yml 必属**同一提交**,不存在「读者看到已生效但 GitHub 没跑过」的时刻,按相反标准会连坐 T12/T13 每份新文档。
- 遗留给 T15(不要漏):CONTRIBUTING §1「这类需求先开 issue 讨论 v2 方向」现已有 RFC 落地,该句应指向 `docs/rfc-team-mode.md`(顺带可把 hooks/mcp/rfc 三份 docs 指针一并登记);另核 CONTRIBUTING:31 规则计数口径。
- 验收标准:
  - [x] RFC 文档完整（动机/设计/边界/迁移路径/开放问题）
  - [x] Action 在本仓跑绿（或本地 `act` 冒烟/语法校验）——走后者
- 子任务:
  - [x] 14.1 RFC 撰写
  - [x] 14.2 ci.yml + 验证

### 任务 15: [Completed] M3/M4 发版簿记 v1.4.0 + 总验收
- 文件: 同 Task 6 清单 + `docs/design-docs/optimization-2026-07/`（收尾状态更新）
- 依赖: Task 11-14
- spec 映射: spec §5 M3/M4、§6
- 说明: 1.3.0→1.4.0（W-ING-5 入迁移清单；wiki-research/mcp/supersession 实例动作）；gen_manifest --date；CONTRIBUTING 两计数终核；模板 W-* 标注对齐终核（31 条）；dogfood 回归；spec 覆盖映射逐行复核（R1-R8 全绿）；tasks.md 全部勾销。
- 验收标准:
  - [x] run_ci 全绿且断言数 ≥ 基线 134 + 新增数（**实测 256**，起点 134）；knowledge/ golden 不回退（P 1.000 / R 0.958，lint 0 error 0 warning）
  - [x] RULES.md **32** 条（T11 新增 W-ING-5 后；原写 31 已过期）与计数/模板标注三方一致——RULES 头行 32(frozen 28/convention 4) = CONTRIBUTING:31；实例契约 distinct W-* = **31**（含 W-ING-5、不含仓级 W-DIST-1）= README 目录导览
  - [x] spec §3 R1-R8 逐条对照通过（逐条实测，见下「R1-R8 总验收」）
- 子任务:
  - [x] 15.1 簿记环（8 处版本 bump + UPGRADING 1.4.0 顶插 + CONTRIBUTING 指针与计数 + docs 版本戳统一 + MANIFEST --date 2026-07-26 重导且幂等）
  - [x] 15.2 总验收清单执行

#### R1-R8 总验收（2026-07-26 逐条实测）

| 需求 | 实测证据 | 结论 |
|---|---|---|
| R1 排名检索入口 + keyword-miss hit@3 | `search.py` 对夹具查「问候」count=8、hits[0]=concepts/greeting-protocol;`_map` 决策表含「关键词不确定」入口;golden schema 收录 `keyword-miss`(9 题型);CI phase (k) 断言 `--check-golden` 零 warning + search hit@3 | ✅ |
| R2 反链可查 + 孤立页被捕获 | `wiki/backlinks.md` 派生 11 条反链;`site/agent/graph.json` 57 边;lint 有 `orphans` 检查项(CI phase (o) 注入孤儿页断言计数 +1) | ✅ |
| R3 会话产出零口头成本落 inbox | `capture_draft.py` 实投 `raw/inbox/<date>-session-draft-<sid>.md`;`boot_reminder.py` additionalContext 含 `_map`;两者 opt-in、exit 恒 0(CI phase_extras 有 exit-0 回归锁) | ✅ |
| R4 ≤2 命令装好 | README「60 秒上手」= `git clone …`(1 条) + 会话里说 `/wiki-init`;另有 `/plugin` 通道两行;冷启动 `bootstrap_scan` 对本仓扫出 21 候选 | ✅（「≤15 分钟到 10 页」属人工 dogfood，发版后执行，不阻塞——tasks 任务 9 已声明） |
| R5 supersedes 机器可查 + 跟到最新 | `contradictions.md` 有「演进链 / Lineage」分节(机器面);`wiki-query` 有「命中被替代页必须跟到最新」节;多值解析单源 `wikigraph.fm_slugs`;CI phase (l) 四态断言 | ✅ |
| R6 followups 有出口 | `wiki-research` skill 渲进实例 `.claude/skills/`;CI phase_render 断言 6 个 skill 全部渲进 + `EXPECTED_SKILLS` 下限集 | ✅ |
| R7 非 skills 宿主经 MCP 消费 | `extras/mcp_server.py` 握手成功、协议 `2025-11-25`、`tools/list` 返回 4 工具;CI phase (i2) 16 条断言(11 正 + 5 负) | ✅ |
| R8 密钥进 wiki 前被拦截/遮蔽 | `secscan.scan_text` 对运行时拼接的假 AWS token 命中 1 条 `kind=aws-access-key` 且**值未回显**;lint 挂 soft 检查(CI phase (s) 命中/豁免两态) | ✅ |

拒绝清单终核：全仓无向量检索 / 无 confidence 衰减 / 无 LLM 打分器 / 无语义推断边 / 无常驻服务端（MCP 走 stdio 管道，不开端口）。

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
|-----------|------|------|
| §4 S1（R1 排名检索） | T1, T2, T3 | lib+派生 / CLI+布线 / 题型+CI 门禁 |
| §4 S2（R2 图谱） | T4 | graph.json+backlinks+lint（W-LNT-4 取消，见风险#2） |
| §4 S3（R3 hooks） | T7 | extras/hooks 双脚本 |
| §4 S4（R4 分发） | T8 | plugin+add-skill+README |
| §4 S5（R4 冷启动） | T9 | bootstrap_scan+skill |
| §4 S6（R5 supersession） | T11 | frontmatter+lint+派生分节 |
| §4 S7（R6 research） | T12 | skill 模板 |
| §4 S8（R7 MCP） | T13 | extras/mcp_server（**落位已裁决:extras/**，风险#1 收口） |
| §4 S9（R8 脱敏） | T5 | secscan+lint 扩展 |
| §4 S10（团队 RFC） | T14 | RFC+CI 配方 |
| §5 里程碑 / §6 横切验收 | T6, T10, T15 | 三次 MINOR 发版簿记 + dogfood 回归 |
| §2 拒绝清单 | 全部 | 无向量/无 confidence/无 LLM judge/无语义边/无服务端 ✓ |
