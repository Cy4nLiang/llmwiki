# UPGRADING — 逐版本迁移说明

> 面向实例维护者(人 + agent):框架每发一个版本,本文件追加一节,列出实例跟版所需的全部动作。
> 实例侧执行入口:`/wiki-upgrade`(skill 未触发时直接 Read `.claude/skills/wiki-upgrade/SKILL.md`);
> 其第 2 步「规则 ID 差距清单」直接消费本文件的迁移清单表。
> semver 判级:MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订。

## 条目格式约定

每个版本条目按以下模板书写,新版本在「条目区」**顶部**插入(新→旧)。
迁移清单**逐条引用 `W-*` 规则 ID**(总表见 `framework/RULES.md`)——lint 报告 / CHANGELOG / 本文件共用同一命名空间,勿另造引用方式;无对应规则的纯工程变更填 `—` 并在「实例动作」写明。

```
## X.Y.Z — YYYY-MM-DD(判级:MAJOR|MINOR|PATCH)

### 变更摘要
- 一句话一条,写「变了什么」,不写实现细节。

### 迁移清单(逐条引规则 ID)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-XXX-n | 新增 / 语义变更 / 文案 | 例:契约追加 Capture 节;或「无动作」 | frozen / render-once / instance |

### frozen 覆盖清单
- tools/foo.py —— hash 变更;MANIFEST 校验干净则整体覆盖,有本地改动 → fork 或回退二选一(W-UPG-1)

### 验收
- lint 全绿 + golden 门禁不回退(W-UPG-2);回滚锚点 = 升级前自动打的 tag。
```

写作约束:
- 「实例动作」必须可执行可核对(具体文件 + 具体操作),不许写「按需调整」;
- 语义变更条目必须写明旧行为 → 新行为,供 agent 判断实例是否受影响;
- 「实例扩展附录」段与 `.claude/rules/local-*.md` 为逃生舱,**承诺永不合并冲突**——任何版本的迁移动作都不得要求改写这两处。

---

## 1.4.0 — 2026-07-26(判级:MINOR)

### 变更摘要
- 生命周期:整页结论被新版取代用 frontmatter `supersedes:` / `superseded_by:` 登记 lineage,lint 校验双向一致 / 目标可解析 / 被替代页横幅存在且未误用 ⚠️(**全 soft warning**);`wiki/contradictions.md` 新增「演进链 / Lineage」分节(**演进 ≠ 矛盾**,不进 ⚠️ 区);查询命中被替代页须跟到后继(W-ING-5)。
- followups 出口:新增 `wiki-research` 实例工作流 skill——从「待读资源/未解问题」选题(用户确认)→ 宿主 web 工具调研 → 逐字快照落逐篇型管线 raw 目录 → 标准 ingest → 勾销台账。**网络只在 agent 侧,工具链保持离线**。
- MCP 接口(可选):新增 `extras/mcp_server.py`——纯标准库 JSON-RPC 2.0 over stdio,协议 `2025-11-25` 钉死,4 工具(`wiki_map` / `wiki_search` / `wiki_page` / `wiki_capture`),供 Claude Desktop / Cursor / Windsurf 等**非 skills 宿主**消费同一座 wiki;配置见 `docs/mcp.md`。
- 团队模式:新增 `docs/rfc-team-mode.md`(**RFC / 提案,未实现**;v1 单写者语义零改动)与本仓自用 CI 配方 `.github/workflows/ci.yml`。

### 迁移清单(1.3.0 实例 → 1.4.0,逐条引规则 ID)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-ING-5 | 新增(supersession 演进链) | frozen 工具自动获得(lint_wiki / build_index / lib/wikigraph)。**无强制动作**:不写 `supersedes:` / `superseded_by:` 的实例零影响(字段可选,lint 只在写了之后才校验)。要用:新页记 `supersedes: <旧页 slug>`、旧页记 `superseded_by: <新页 slug>`(**双向必写**,值为页 slug,多个用**单行** `[a, b]`——换行 `- a` 块写法会被 frontmatter 解析器静默丢成空值,lint 会点名),旧页正文留一行 `> **已被取代**:… [[后继]]` 横幅(**不用 ⚠️**);随后重跑 `build_index` 刷新 contradictions 的「演进链」分节。契约「交叉引用」节 + `.claude/rules/aggregate-pages.md` + `templates/skills/wiki-query` 均加了 W-ING-5 条款(render-once):**实例若回填过这三处,升级出 `.upgrade-new`,把对应段落逐 diff 并入本地** | frozen / render-once |
| — | 新增 skill(research 闭环) | `templates/skills/wiki-research/SKILL.md` 是**新增 render-once 文件**,实例无同名文件 → 经 upgrade.py 的 ro_install **直接安装**到 `.claude/skills/wiki-research/SKILL.md`,零冲突。首次使用:grep `wiki/followups.md` 的「待读资源 / 未解问题」选题 → 用宿主 web 工具调研 → 快照投**逐篇型**(`pull`/`push`)管线的 raw 目录(**不要投 `rolling` 管线**)→ 走标准 ingest → 删掉已闭环的 followups 条目 + `wiki/log.md` 记一条 `note` | render-once |
| — | 新增可选组件(MCP) | **无强制动作**(`extras/` 不随实例分发,init_render 不拷)。要启用:按 `docs/mcp.md` 的宿主注册片段,把 `python3 <框架 checkout 绝对路径>/extras/mcp_server.py --root <实例根>` 填进宿主的 `mcpServers` 配置(Claude Code `.mcp.json` / Claude Desktop / Cursor / Windsurf 各自路径见该文档);先在实例里跑过 `build_site` + `build_index`,否则 `wiki_search` 会返回「索引未就位」。`wiki_capture` 的投递口取自 config **第一条 `kind: push` 管线**的 `raw_dir`(不硬编码 `raw/inbox`) | frozen(extras,不分发) |
| — | 新增文档(团队 RFC) | **无实例动作**:`docs/rfc-team-mode.md` 是提案文档,随 `docs/` 分发到实例仅供阅读;其 5 项提案**均未实现**,不要当契约执行。`.github/workflows/ci.yml` 是 meta 档、不随实例分发;团队若要抄门禁配方,抄它的 **instance job** 那一半并把 `--root` 换成自己的实例根(`tests/run_ci.py` 是框架仓专有,实例仓没有该文件) | frozen(文档)/ meta(不分发) |

### frozen 覆盖清单
- `extras/mcp_server.py`、`docs/mcp.md`、`docs/rfc-team-mode.md` —— 新增文件,实例升级走「直接安装」(W-UPG-1;`docs/` 随实例分发,`extras/` 按既有口径不分发、未持有 extras/ 的实例列「未持有跳过」)
- `tools/lib/wikigraph.py` —— hash 变更(新增 `fm_slugs`:lineage 多值解析单源);`tools/lint_wiki.py` —— hash 变更(新增 `lineage` 检查项);`tools/build_index.py` —— hash 变更(新增 `lineage_lines` + 演进链分节);`extras/README.md` —— hash 变更(登记 mcp_server)。MANIFEST 校验干净则整体覆盖,有本地改动 → fork 或回退二选一

### 验收
- lint 全绿 + golden 门禁不回退(W-UPG-2;knowledge dogfood P 1.000 / R 0.958);回滚锚点 = 升级前自动打的 tag。
- `python3 tests/run_ci.py` 全绿(本版断言总数 214→256);渲染实例 `.claude/skills/` 出现 `wiki-research/`;`wiki/contradictions.md` 出现「演进链 / Lineage」分节。
- 注:RULES.md 总表 32 条(本版新增 W-ING-5;实例契约 31 条 W-* 标注——W-DIST-1 是仓级分发壳规则不渲染进实例)。MCP 宿主注册与团队 RFC 属人工面,CI 只做机械冒烟(`tests/run_ci.py` phase_extras 的 stdio 握手段)。

---

## 1.3.0 — 2026-07-25(判级:MINOR)

### 变更摘要
- 自动捕获(可选):`extras/hooks/` 两个 Claude Code hook——`boot_reminder.py`(SessionStart)注入「先读 `wiki/_map.md`」启动提醒;`capture_draft.py`(SessionEnd/Stop)在 `raw/inbox/` 投递 `kind: draft` 占位草稿,让 W-CAP-1 收尾检查点不被遗忘(**opt-in**:不配置不触发;投递 ≠ 整合,草稿是 stub)。
- 冷启动:新增 `tools/bootstrap_scan.py`——只读扫宿主 repo(README*/CHANGELOG*/`**/adr/**`/`docs/**`/仓根 md/工程约定文档/`git log --grep` 决策词;git 缺席自动跳过该组)→ `state/bootstrap-candidates.json`;配 `wiki-bootstrap` 向导(勾选 → 投 inbox → 批量 light 档 ingest → followups 待晋升)。
- 分发:新增 `.claude-plugin/`(marketplace + plugin 清单),框架仓可经 `/plugin marketplace add Cy4nLiang/llmwiki` 安装并暴露 `/wiki-init`·`/wiki-upgrade`·`/wiki-golden` 三向导;README 加「60 秒上手」quickstart 与 LLM-Wiki 竞品对比表(W-DIST-1)。
- 文档:新增 `docs/hooks.md`(settings.json 配置片段 + 人工 e2e 清单)。

### 迁移清单(1.2.0 实例 → 1.3.0,逐条引规则 ID)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| — | 新增可选组件(hooks) | **无强制动作**(`extras/` 不随实例分发,init_render 不拷)。要启用:往**你实例/宿主项目**的 `.claude/settings.json` 加 SessionStart 与 Stop 两条 command hook(Claude Code 只读**会话所在项目**的 settings,写进框架 checkout 的不会触发),`command` 填 `python3 <框架 checkout 绝对路径>/extras/hooks/{boot_reminder,capture_draft}.py`,并用 `env.LLMWIKI_ROOT` 或 `--root` 指向实例根(JSON 片段照抄 `docs/hooks.md`「配置」节);不配置则完全不触发。**前提**:实例须有一条 `raw_dir` 为 `raw/inbox` 的 push 管线——capture_draft 以 `raw/inbox/` 存在为「是本框架实例」的判据并投递到该目录,缺它则静默不投(hook 恒 exit 0,无诊断);若只 `mkdir raw/inbox` 而管线 `raw_dir` 另有其值,草稿投了也永不被 `sync.py status` 报 pending(sync 只扫管线声明的 `raw_dir`) | frozen(extras,不分发) |
| — | 新增工具 + 新增 skill(冷启动) | frozen 工具随升级获得 `tools/bootstrap_scan.py`;`templates/skills/wiki-bootstrap/SKILL.md` 是**新增 render-once 文件**,实例无同名文件 → 经 upgrade.py 的 ro_install **直接安装**到 `.claude/skills/wiki-bootstrap/SKILL.md`,零冲突。首次使用:`python3 tools/bootstrap_scan.py`(embedded 默认扫宿主 `..`;别处宿主用 `--repo <宿主根>`)→ 读 `state/bootstrap-candidates.json` → 按向导逐条勾选后投**该 push 管线声明的 `raw_dir`**(默认 `raw/inbox/`;非默认实例照 `sync.py status` 输出的 raw 目录投,否则投了不被报 pending)(**未勾选不投递**,W-CAP-1)→ 批量 light 档 ingest 并记 followups 待晋升(W-ING-1/W-LOG-2) | frozen / render-once |
| — | 契约「工具速查」增行 | `tools.cmds` 新增 `bootstrap_scan.py` 一行(render-once 三方合并自动采用);实例若回填过契约或 ingest/query/sync skill,升级出对应 `.upgrade-new`,把该行逐 diff 并入本地 | render-once |
| W-DIST-1 | 新增(分发壳) | **无实例动作**:`.claude-plugin/` 为仓级 meta 分发壳,init_render 不拷、永不进实例;仅框架仓获得 `/plugin` 安装能力,plugin/marketplace 的 `version` 由 CI 锁定恒等于 `framework/VERSION` | meta(仓级) |

### frozen 覆盖清单
- `tools/bootstrap_scan.py`、`docs/hooks.md` —— 新增文件,实例升级走「直接安装」(W-UPG-1;新文件无本地改动,直接落位)
- `extras/hooks/{capture_draft,boot_reminder}.py`(新增)、`extras/README.md`(hash 变更:登记 hooks 一节)—— `extras/` 不随实例分发,frozen 决策**限实例实际持有路径**:未采纳 `extras/` 的实例升级时列「未持有跳过」,不会落位;曾手工采纳过 `extras/` 的实例按常规——MANIFEST 校验干净则整体覆盖,有本地改动 → fork 或回退二选一
- `tools/init_render.py` —— hash 变更(`tools.cmds` 增行);MANIFEST 校验干净则整体覆盖,有本地改动 → fork 或回退二选一

### 验收
- lint 全绿 + golden 门禁不回退(W-UPG-2;knowledge dogfood P 1.000 / R 0.958);回滚锚点 = 升级前自动打的 tag。
- `python3 tests/run_ci.py` 全绿(本版断言总数 173→214);渲染实例 `.claude/skills/` 出现 `wiki-bootstrap/`。
- 注:RULES.md 总表 31 条(本版新增 W-DIST-1;它是**仓级分发壳规则,不渲染进实例契约**——实例契约仍 30 条 W-* 标注);hooks 与 plugin 安装属宿主行为,CI 只做机械冒烟,真会话/真安装靠 `docs/hooks.md` 与 README 的人工 e2e 清单。

---

## 1.2.0 — 2026-07-24(判级:MINOR)

### 变更摘要
- 排名检索:新增 `tools/search.py`(BM25)+ 派生 `site/agent/search-index.json`;`_map` 决策表加「关键词不确定/模糊探索」入口(W-IDX-3)。
- 链接图谱:派生 `wiki/backlinks.md`(反链)与 `site/agent/graph.json`(边表),供社区/中心/孤立分析(W-IDX-4;只做确定性 wikilink 解析,不做语义推断边)。
- 内容脱敏:lint 对 wiki/raw 文本扫密钥/凭证样式(soft warning,只报类型不回显值),ingest 加遮蔽步(W-SEC-3)。
- 评测:golden 新增第 9 题型 `keyword-miss`(排名检索探针;additive,旧 golden 无需改)。

### 迁移清单(1.1.1 实例 → 1.2.0,逐条引规则 ID)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-IDX-3 | 新增(排名检索索引) | frozen 工具自动获得(search.py/build_site);首次跑 `build_site` 派生 search-index.json;`_map` 模板加「关键词不确定」行——**实例若回填过 `_map`,升级出 `_map.md.upgrade-new`,逐 diff 把新行并入本地 `_map`** | frozen / render-once |
| W-IDX-4 | 新增(链接图谱) | frozen 工具自动获得(wikigraph/build_index/build_site);首次跑 `build_index`+`build_site` 派生 backlinks.md/graph.json;`backlinks.md` 为新 wiki 内派生物,**禁手编**(与 index.md 同,改内容重跑派生) | frozen / render-once |
| W-SEC-3 | 新增(内容脱敏) | lint 自动获得 secscan;命中报 **soft warning 不改 exit**;wiki 页遮蔽或 `<!-- secscan:allow -->` 豁免,raw/ 命中于 ingest 时遮蔽并在源页 Processing Notes 标注。契约硬规则第 13 条 + `templates/skills/wiki-ingest` 加脱敏步(render-once):实例若回填过契约/ingest skill,升级出 `.upgrade-new`,把脱敏 bullet 逐 diff 并入本地 | frozen / render-once |
| — | 新增题型/工具 | golden 可选用 `keyword-miss` 题型;契约「工具速查」新增 search.py 行(render-once 三方合并自动采用) | render-once |

### frozen 覆盖清单
- `tools/lib/{textindex,wikigraph,secscan}.py`、`tools/search.py` —— 新增文件,实例升级走「直接安装」(W-UPG-1;新文件无本地改动,直接落位)
- `tools/{build_site,build_index,lint_wiki,init_render,gen_manifest,eval_retrieval}.py`、`evals/{golden.schema.json,question-types.md,playbook.md}` —— hash 变更;MANIFEST 校验干净则整体覆盖,有本地改动 → fork 或回退二选一

### 验收
- lint 全绿 + golden 门禁不回退(W-UPG-2;knowledge dogfood P 1.000 / R 0.958);回滚锚点 = 升级前自动打的 tag。
- `python3 tests/run_ci.py` 全绿;渲染实例契约含 30 条 W-* 标注(与 RULES.md 对齐)。
- 注:开发文档 `docs/design-docs/` 已豁免 frozen 分发面(不入 MANIFEST、不随实例分发),实例侧无迁移动作;集线器提示未实现(R2 未映射,soft 中心分析走 graph.json 数据面);本版断言总数 134→173。

---

## 1.1.1 — 2026-07-20(判级:PATCH)

### 变更摘要
双线核查(Sonnet 5 × Opus 4.8 双盲)7 条修法落地:契约模板时效条款节补 W-LNT-3 标注
(消除「lint 强制却未契约化」缺口,模板 W-* 达 27 与 RULES.md 对齐);README 措辞修正
(降级矩阵→文件直读、每条硬规则配 lint→如实比例、golden 门禁→回归提醒、指针段=agent 依模板
逐字追加、仓外数字加不可复核注、6.6 分钟回落有记录口径并补录 knowledge log 出处);
wiki-init SKILL 删除不存在的 --adopt 旗标名;CONTRIBUTING 断言数 119→134。

### 迁移清单(1.1.0 实例 → 1.1.1)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-LNT-3 | 契约文案 | render-once 三方合并自动采用(实例未改契约则零冲突);无行为变化(lint 早已执行该检查) | render-once |

### frozen 覆盖清单
无(本版零工具改动)。

### 验收
`python3 tests/run_ci.py` 全绿;渲染实例契约含 27 条 W-* 标注。

## 1.1.0 — 2026-07-20(判级:MINOR)

### 变更摘要
golden any-of 组结算落地(修校准结构缺陷):schema 增 `golden_groups`(同一信息多条获取路径,
任一命中记满组权),scorer/校验/文档同步,存量无组 golden 打分逐字节不变;新增跨组重复页
warning 校验。CI 增 any-of 两态用例与 stub-ir 回退护栏(升级工具对旧版渲染器的兼容路径入长期
回归),模拟版本号改由 VERSION 派生。wiki-init 补嵌套宿主多层契约边界注。

### 迁移清单(1.0.0 实例 → 1.1.0)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| — | 评测扩展 | frozen 覆盖 tools/eval_retrieval.py 与 evals/{golden.schema.json,question-types.md};存量 golden 无需改动(打分不变),受 weight-1 替代路径压制 recall 的实例可按 question-types any-of 节改组并在 log 记校准修订 | frozen + instance 数据 |
| — | skills 文案 | 三方合并自动采用(wiki-init 嵌套宿主注) | render-once |

### frozen 覆盖清单
tools/eval_retrieval.py、evals/golden.schema.json、evals/question-types.md。

### 验收
`python3 tests/run_ci.py` 全绿(134 断言);golden 门禁按新基线对照(参考实例 knowledge:R 0.633→0.958 为校准修订非能力变化,已 log 留痕)。

## 1.0.0 — 2026-07-20(判级:MINOR;首个稳定版)

### 变更摘要
M4 发布收口:CONTRIBUTING.md(两档 PR 政策/回流格式/脱敏 checklist)、.gitattributes(夹具与
raw LF 钉死)、框架仓开发契约 CLAUDE.md + 内嵌 dogfood 示例实例 knowledge/(框架自身开发知识库:
20 页、golden 10 题、真实基线 P 1.000 / R 0.633);镜像段函数化(upgrade.py 改 import
init_render 的 compute_conds/stamp_dates/snapshot_manifest 单源,镜像仅旧版回退);
dogfood 回流的协议缝隙修复(源页骨架补 created:/ingest_tier: 字段、raw_file/authors 口径、
bulk 贡献 per-claim 粒度与 reduce 终裁权、wiki-init check-slots/--target 口径、
embedded 宿主 AGENTS 注、playbook 三条补充裁定)。

### 迁移清单(0.3.0 实例 → 1.0.0)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-PAGE-4/W-ING-1 | 模板增强 | 三方合并采用新 source-page 规则(新增 created:/ingest_tier: 字段说明);**存量源页**若缺 created: 会被全量 lint 报错,按 date_ingested 补齐 | render-once + instance 数据 |
| — | 工具函数化 | frozen 覆盖 tools/{init_render,upgrade}.py(行为逐字节等价,PATCH 性质) | frozen |
| — | skills/playbook 文案 | 三方合并自动采用(实例未改则零冲突) | render-once |

### frozen 覆盖清单
tools/{init_render,upgrade,gen_manifest}.py、evals/playbook.md。

### 验收
`python3 tests/run_ci.py` 全绿(119 断言);实例升级后全量 lint + golden 不回退(W-UPG-2)。

## 0.3.0 — 2026-07-20(判级:MINOR)

### 变更摘要
M3 质量层落位:升级工具 tools/upgrade.py(frozen hash 校验/render-once 三方合并/预备份/门禁/log 落账)、
评测打包 evals/{golden.schema.json,question-types.md,playbook.md} + eval_retrieval 增 --check-golden 与
answer_keys 化诚实判定、extras/{serve.py,i18n_link.py}(D7 可选组件)、adapter:"manual" 哨兵、
CONTRACT 冻结 manifest 容器推荐形状 {"articles":{slug:{...}}}、sync status 增 peers 段(可达性+版本 skew)。

### 迁移清单(0.2.0 实例 → 0.3.0)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-UPG-1/2 | 新增工具 | 本次升级本身即可用 upgrade.py 执行(实例无该工具时用新版仓的:`python3 <FW>/tools/upgrade.py --root . --framework <FW>`) | frozen |
| — | 评测打包 | 已有 golden 的实例跑 `eval_retrieval.py --check-golden evals/golden.jsonl`,按 warning 收敛题型别名与 unanswerable 短锚点 | instance 数据 |
| — | manual 哨兵 | 人工投放快照的 pull/rolling 管线可在 config 加 `"adapter": "manual"` 消除警告 | config |
| W-XRF-1 | status 增强 | 无动作;`sync.py status` 自动多出 peers 段 | — |
| — | extras | 无动作,可选组件按需取用(不拷入实例,从框架仓 --root 指实例运行) | — |

### frozen 覆盖清单
tools/*(含新增 upgrade.py)、evals/**、adapters/**(local_notes 容器键 items→articles,载入自动迁移)、extras/**。

### 验收
`python3 tests/run_ci.py` 全绿(框架仓,119 断言含模拟升级四路径);实例侧升级后 lint --manifest 零漂移 + golden 不回退(W-UPG-2)。

## 0.2.0 — 2026-07-19(判级:MINOR)

### 变更摘要
M2 工具层落位:sync 管线编排、build_site/build_index 派生索引、全量 lint_wiki(新增 --manifest)、
eval 双件、lib/fm.py 单源库、fetcher 契约(adapters/CONTRACT.md + skeleton×2 + local_notes)、
docs/{bulk-ingest,rolling-source,fetcher-contract}、hello-wiki CI 夹具(tests/run_ci.py,79 断言)。

### 迁移清单(0.1.0 实例 → 0.2.0)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| W-UPG-1 | 新增机制 | 重渲染/覆盖 tools/(frozen 整体覆盖;实例改过工具先按 fork 处理)+ 落新 framework/MANIFEST.json 快照 | frozen |
| W-IDX-1 | 新增工具 | 首跑 `python3 tools/build_site.py && python3 tools/build_index.py` 建立派生索引 | instance 产物 |
| W-LNT-3 等 | lint 扩容 | 跑全量 `lint_wiki.py`,按报告清欠(staleness/light 占比等新检查) | — |
| — | 模板修订 | render-once 三方合并:wiki-sync/wiki-lint skill 去「M1 注」、rolling 判新统一 `rolling_digest` 口径、overview 注释示例链接反引号化、source-page 滚动源块补 digest 字段 | render-once |

### frozen 覆盖清单
tools/*(全部)、adapters/CONTRACT.md、docs/ 三件——W-UPG-1 fork 二选一(覆盖或显式 fork)。

### 验收
`python3 tests/run_ci.py` 全绿(框架仓);实例侧 `lint_wiki.py --manifest` 零漂移 + golden 不回退(W-UPG-2;实例无 golden 时以全量 lint 代)。

## 0.1.0 — 2026-07-19(判级:首版,无迁移)

M1 骨架首发,此前无实例存在,无迁移动作;本条仅立基线:

### 基线内容
- 契约模板 `CLAUDE.template.md`(19 槽位注册表 + 命名锚点 + 3 个条件模块 multi_facet / rolling_source / peers);
- 规则总表 `framework/RULES.md`(26 条 `W-*`:frozen 22 / convention 4);
- `.claude/rules/`(source-page / aggregate-pages,冻结骨架)、`.claude/agents/wiki-reader.template.md`;
- 向导 skills(wiki-init / wiki-upgrade / wiki-golden)+ 实例本地工作流模板(templates/skills/ 四件);
- wiki 骨架模板(templates/wiki/ 五件)、`schema/wiki.config.schema.json` + `wiki.config.example.json`;
- 工具:`init_render.py`(确定性渲染)、`lint_wiki.py`(--check-slots / --check-config)、`gen_manifest.py`。

### 升级锚点自本版生效
- 实例 `framework/VERSION` 钉版 + `framework/base/` 模板快照(init_render 落盘)即三方合并基线;
- `framework/MANIFEST.json` 为派生物(W-IDX-1),frozen 漂移以其 sha256 判定(W-UPG-1)。

### 已知未落位(M2/M3 交付,届时按判级出条目)
- sync / build_index / build_site / eval_retrieval / eval_compare / lib/fm.py、adapters(fetcher 契约 + local_notes)、evals 打包、extras、tests/hello-wiki CI 夹具、MANIFEST hash 挂 sync 常跑路径。
