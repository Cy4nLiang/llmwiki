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
