---
name: wiki-lint
description: 当例行体检、sync 之后、升级门禁前,或用户说「lint」「体检」「查断链」「查过期」时触发。双层执行:机械层调 tools/lint_wiki.py 出报告;语义层按清单逐条对照反模式与规则 ID 人审。先报告、经批准后改、写 lint log,绝不静默修改。
---

# wiki-lint — 双层体检

## 机械层
<a id="mechanical-layer"></a>

> **M1 注**:先跑 `python3 tools/lint_wiki.py --check-slots`(渲染残留槽位)与 `--check-config`(config schema 校验);全量检查项 M2 落地,未落地项按下表含义手工 grep 替代。

`python3 tools/lint_wiki.py` 检查项 ↔ 规则 ID:

| 检查 | 规则 |
|---|---|
| 渲染残留槽位 / config schema | (init 与升级验收面) |
| 断链 wikilink / rule-of-three 晋升候选 | W-PAGE-3 |
| description 缺失 / frontmatter 必填缺项 | W-PAGE-2 / W-PAGE-4 |
| 页面 token 超 <SLOT:budgets.page_tokens> | W-PAGE-1 |
| 索引/派生物新鲜度(生成区手编检测) | W-IDX-1 / W-IDX-2 |
| ⚠️ 矛盾标记派生汇总 | W-ING-3 |
| log 行格式(append-only ASCII 行) | W-LOG-1 |
| _map 超 <SLOT:budgets.map_lines> 行硬预算 | W-LNT-2 |
| Processing Notes touch 数审计 + light 占比 >50% 告警(档位:<SLOT:ingest.tier_rules>) | W-ING-1 |
| 根命名空间白名单 | W-ARCH-3 |
| MANIFEST hash(frozen 本地改动 = fork 警告) | W-UPG-1 |
| state/ 在 .gitignore、config/manifest 凭证扫描 | W-SEC-2 |

<!--BEGIN:peers-->
peers 附加检查(soft,W-XRF-1):peer 可达 → 校验 `[[alias::...]]` 目标 slug 存在于其 pages.jsonl,断链报 warning;peer 不可达 → soft warning + 计数,**不 fail**。
<!--END:peers-->

## 语义层清单(agent 审)
<a id="semantic-checklist"></a>

机械层管格式,语义层管「写得对不对」。逐条对照,**先报告、批准后改、写 lint log**——绝不边查边改:

1. **剪藏化**(反模式:只写源页不 touch 聚合页):源页 Processing Notes 触及页数低于档位下限、或被触及聚合页里没有该源回链 → W-ING-1;light 页目标 rule-of-three 已达标却未晋升 → 补 touch 并从 followups 销账。
2. **断链与假链**(反模式:给单提及目标建 wikilink):wikilink 指向不存在页;单提及目标本应纯文本 → W-PAGE-3。
3. **静默覆盖**(反模式:时间线/数字被直接改写):旧值消失而无「演进」条目、真分歧无 ⚠️ 块、facet 间差异被写成矛盾 → W-ING-3。
4. **description 写偏**(反模式:写成内容摘要):不回答「何时该读本页」→ W-PAGE-2;终极回归是路由入口 golden 题(见 wiki-golden skill)。
5. **过期未核实**:按时效策略 <SLOT:staleness.rules> 对照各页 `verified:` / `date_ingested`,超窗未核实的源页与依赖它的聚合页逐条列出——stale 说明书是危险品不是旧文章,本条优先级最高。
6. **mature 空段与 overview 脱节**:status 标 mature 但关键段为空;overview 主题地图缺新主题簇;followups 四分类(待读/待验证/未解/待晋升,W-LOG-2)里的陈旧条目清账。
7. **grep-only 违规与档位表过期**:`_map` 档位表列名的大文件近期是否被整读;档位表所记体量与现实是否脱节(拆页/分片后未更新)→ W-LNT-1。

## 产出

lint 报告(逐条挂规则 ID + 建议动作)→ 用户批准 → 执行修复 → 跑索引派生(如有内容变更)→ `wiki/log.md` append 一条 `## [YYYY-MM-DD] lint | ...`(W-LOG-1),正文记发现数/修复数/遗留数。
