---
name: wiki-init
description: 当用户要把 llmwiki 实例化成一个新知识库——说「初始化 wiki」「/wiki-init」「用 llmwiki 建库」「收编/adopt 现有目录」「把 wiki 嵌进这个项目」时触发。执行三模式实例化向导(greenfield 十问问答 / adopt 布局探测反推 config / embedded 渲染进宿主子目录);agent 只负责问答与填 wiki.config.json,渲染一律交 init_render.py,收尾跑 lint --check-slots 冒烟。
---

# wiki-init — 实例化向导(三模式)

产出物:`wiki.config.json`(实例唯一配置)+ `init_render.py` 渲染出的完整实例骨架。

## 硬约束(先读)

- **agent 只填值,不写正文**:所有模板正文由 `python3 tools/init_render.py` 确定性渲染;禁止手写或改写 CLAUDE.md、`_map`、rules、skills 的正文——同一份 config 渲染两次,产物必须逐字节相同。
- config 写完先过 schema 校验(`schema/wiki.config.schema.json`,init_render 内置);报错改 config 重渲染,**不改产物**。
- 收尾必跑冒烟:`python3 tools/lint_wiki.py --check-slots --target <实例根>`(--target 必填;实例内即 `--target .`)——渲染产物零残留槽位标记才算完成。

## 模式选择

| 模式 | 适用 | 关键约束 |
|---|---|---|
| greenfield | 空目录起新库 | 十问 → 写 config → 渲染 → 冒烟 |
| adopt | 已有布局收编 | 探测反推 config;差量渲染缺失件;**绝不覆盖已有文件** |
| embedded | 渲染进宿主项目子目录 | 宿主根命名空间零污染;宿主 CLAUDE.md 只追加指针段 |

## greenfield:十问清单
<a id="ten-questions"></a>

一次一问,每问先报默认值;用户说「都用默认」则只确认第 2 问(domain 无默认,必答)。

| # | 问题 | config 落点 | 默认值 | 示例 |
|---|---|---|---|---|
| 1 | 落位形态?独立仓 / 收编现有布局 / 嵌进宿主项目 | 决定模式与渲染根 | 独立仓 | embedded → 渲染进 `knowledge/` |
| 2 | 这个库是关于什么的?一个 ASCII 短名 + 三句以内描述 | `domain.name` / `domain.description` | 无(必答) | `acme-ops`:「本团队生产系统的 runbook 与事故知识库,覆盖…」 |
| 3 | 知识从哪来?(源集合,可多条,每条:名称/型/raw 目录/前缀/source_kinds) | `pipelines[]` | 单条 push 型 `notes`(`raw/inbox`,人肉投递) | 加 pull 型 `docs`(adapter 抓外部文档)或 rolling 型 `runbook`(整体快照) |
| 4 | 有没有贯穿全库的切面维度?(厂商/团队/环境…) | `facets[]` | 无(不装载多 facet 模块) | `vendor: [anthropic, openai]`,badges `{"openai": "🟢", "cross": "🔀"}`,分片索引 |
| 5 | 用户语言? | `domain.lang` | zh | en(budgets.est_tokens_profile 随之取 latin) |
| 6 | 源的信任姿态? | `domain.trust_posture` | internal-authoritative | official-biased(官方一手但有立场)/ needs-verification |
| 7 | 预算数值要调吗? | `budgets` | page_tokens 8000 / map_lines 100 / boot_tokens 4000 / raw_slice_tokens 1200 / est_tokens_profile 随第 5 问 | 英文重文档库:est_tokens_profile=latin |
| 8 | ingest 默认档位与例外? | `ingest_tiers` | default full;min_touch {full: 5, light: 1} | `by_source_kind: {"adr": "light", "pitfall": "light"}` |
| 9 | 哪些源会过期?(时效窗口) | `staleness.by_source_kind` | 空(不启用) | `{"runbook-snapshot": "180d", "howto": "365d"}` |
| 10 | 要引用同机其它 llmwiki 实例吗? | `peers[]` | 空(peers 模块不渲染) | `[{"alias": "hub", "path": "~/wikis/personal-hub"}]`(本机路径,不入发布物,W-XRF-1) |

另按第 2/3 问顺带确认 `typology_map`(entity/concept/synthesis 在此 domain 的语义,默认取 canonical 映射表最接近的一列)。问答完 → 写 `wiki.config.json` → `python3 tools/init_render.py` → 冒烟。

## adopt:布局探测反推
<a id="adopt-mode"></a>

1. 探测现有布局:`raw/` 子目录与文件前缀 → 反推 `pipelines[]`;既有源页 frontmatter → 反推 facets / source_kinds / lang;无线索字段按十问默认值填,逐项向用户确认后写 config。
2. `init_render.py`(**不带 `--force`** 即差量模式):只渲染**缺失**件;与已有文件同名的一律跳过并逐个列出,由用户决定是否采纳——**绝不覆盖**(工具无 `--adopt` 旗标,adopt 是流程名不是参数)。
3. 已有 CLAUDE.md:正文一字不动,只追加下方指针段。

## embedded:宿主子目录
<a id="embedded-mode"></a>

1. 渲染根 = 宿主子目录(默认 `knowledge/`,第 1 问可改);实例全部文件收在该目录内,宿主根命名空间零污染(W-ARCH-3)。
2. 宿主 CLAUDE.md **只追加**下方指针段,绝不覆盖、绝不改写其余内容;宿主无 AGENTS.md 时可选建 symlink → CLAUDE.md,已有则不动。
3. **嵌套宿主**:宿主自身也可能位于另一个 llmwiki 风格实例/契约树内(如 monorepo 子项目或 worktree)——多层 CLAUDE.md 依 Claude Code 就近加载规则共存,无需特判。
   边界规则:每层契约只管辖自己的目录树,指针段只指向直属 knowledge 子目录;
   跨层检索走 peers(W-XRF-1)互引,不直读上层 wiki。

## 宿主 CLAUDE.md 指针段标准文本
<a id="host-pointer-block"></a>

逐字使用以下模板(`<WIKI_ROOT>` = embedded 子目录如 `knowledge/`;adopt/独立仓留空前缀):

```markdown
<!-- llmwiki:pointer:begin(本段由 llmwiki 维护;升级时整段替换,请勿手改)-->
## 知识库(llmwiki)
- Boot:domain 知识问题先读 `<WIKI_ROOT>wiki/_map.md` 按决策表路由;工作流见 `<WIKI_ROOT>.claude/skills/`。
- 会话收尾检查点:本次会话是否产生值得留底的踩坑/约定/决策?有则投递 `<WIKI_ROOT>raw/inbox/<date>-<slug>.md`(frontmatter:title/date/kind ∈ adr|pitfall|decision|howto)。投递≠整合、不打断任务主线(W-CAP-1);整合由下次 wiki-sync 报 pending 后走 light 档。
<!-- llmwiki:pointer:end -->
```

## 收尾与首批内容

1. `python3 tools/lint_wiki.py --check-slots --target .` 全绿;
2. 接内容:inbox 直投,或写 `tools/adapters/`(合同见 `adapters/CONTRACT.md`,骨架可抄 skeleton);
3. **首批 ~10 源后**:回填 `_map` 读取档位表与决策表页名、写 `overview.md` 首版、跑 `/wiki-golden` 建评测基线(config 填偏靠它早期显形)。
