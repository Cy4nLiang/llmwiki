---
paths: ["wiki/entities/**", "wiki/concepts/**", "wiki/syntheses/**", "wiki/queries/**"]
---

# 聚合页写作规则(编辑 entities/concepts/syntheses/queries 时自动加载)

本库五类页面的 domain 语义(config typology_map 渲染):

| 类型 | 本库语义 |
|---|---|
| source | ADR/踩坑记录/how-to/决策记录 |
| entity | 工具/组件 |
| concept | 设计约定/机制 |
| synthesis | 跨里程碑设计叙事 |
| query | 开发问答 |

## 四类骨架(frozen 段落 —— 段落名与顺序不可改,单段可留空但不可删;改 = 显式 fork,W-UPG-1)
<a id="aggregate-skeletons"></a>

### Entity page — `wiki/entities/<slug>.md`
- 顶部:稳定事实(身份、定位、隶属等;entity 在本库指什么见上方类型学表)。
- 段落:概述 / 关键事实 / 关系网络 / 时间线 / 来源 / 待补充。
- 每条事实尽量后接 `(来源:[[sources/X]])`。
- **有版本/状态演进的 entity 页要维护时间线** —— 复利价值最高的一类页。超重时间线拆 `<slug>-timeline.md` 子页,主页留里程碑 + 指针。

### Concept page — `wiki/concepts/<slug>.md`
- 段落:定义 / 核心要点 / 演变与争议 / 相关概念 / 来源 / 未解之处。

### Synthesis page — `wiki/syntheses/<slug>.md`
- 段落:问题 / 各方观点 / 证据强度 / 当前结论 / 反例与未解之处 / 引用来源。

### Query page — `wiki/queries/<slug>.md`
- 段落:问题 / 答案(带 wikilink 引用) / 衍生问题 / 触发的 wiki 更新。
- frontmatter 记 `date_asked:`;答案里每条论断带 [[wikilink]] 出处,便于后续命中直接复用(W-QRY-2 默认归档的落点)。
- 操作类 how-do-I-X 问答是一等公民:`wiki/_map.md` 决策表对「怎么做 X」类问题首查本目录。


## 通用要求

- frontmatter 必带 `description:`(分诊触发器:「问 X 读本页」+ 本页独有价值点,≤150 字,W-PAGE-2);`aliases:` 策略随语言约定:默认用户交互语言:**中文**。源引用保留原文不译;技术术语可保留英文。高频页 `aliases` 必须中英双语(检索锚点)。
- 页面 token 预算 8000(W-PAGE-1):超线拆「精华主页 + `-timeline`/`-appendix` 子页」,主页每个移出节留一行指针。
- 跨页引用一律 `[[wikilink]]`(W-PAGE-3):断链 = 图导航基础设施故障;单提及(rule-of-three 未达)用纯文本 + 记 followups「待晋升」。

## 验证状态与时效(说明书库字段)
<a id="verified-field"></a>

- 聚合页可选 frontmatter `verified: YYYY-MM-DD`(最后核实日期):对着实物/一手源核对过本页关键结论的日期;与 `updated:`(最后编辑)语义不同,编辑不自动等于核实。
- 过期窗口由 config staleness 按 source_kind 声明:`howto` 365d
- lint 依据 `verified:` 与过期窗口报「过期未核实」(W-LNT-3)——stale 的操作性页面是危险品,不是旧文章;核实后 bump `verified:`,推翻的结论按 W-ING-3 处理。

## 矛盾标记(frozen 段落 —— W-ING-3,禁静默覆盖)
<a id="contradiction-format"></a>

```
> ⚠️ 矛盾:此说法与 [[other-page]] 不一致。
> - [[sources/X]] 主张 A
> - [[sources/Y]] 主张 ¬A
> 倾向于 A,因为 ...(或暂未定论)
```

- 三分裁决:时间线冲突优先「演进」;不同主体/口径的做法差异用「对比」;真矛盾才落 ⚠️ 标记。
- 全库 ⚠️ 由 build 派生汇总到 [[contradictions]](W-IDX-1);裁决 = 回原页改标记再重跑派生,勿手编汇总页。
