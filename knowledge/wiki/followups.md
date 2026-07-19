---
title: Followups 待跟进
description: "待读资源/待验证/未解问题/待晋升四分类台账。补缺口或 lint 时按节 grep,不整读。"
type: overview
created: 2026-07-20
updated: 2026-07-20
tags: [meta]
status: draft
---

# Followups 待跟进

四分类台账(W-LOG-2),每条注明出处 `[[sources/...]]`;lint 时审视本表,处理完的条目删除。读取按节 grep,勿整读(W-LNT-1)。

## 1. 待读资源 / Resources

*被引用但本库未收录的外部源——值得抓取/投递的下一篇。*

- `--adopt` 存量收编模式(6 项嫁接之③)尚无源页记载,建议投递一篇 how-to/decision。出处:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]
- UPGRADING.md 条目格式约定(upgrading-doc)值得独立成篇投递。出处:[[sources/2026-07-20-howto-release-framework-version]]

## 2. 待验证 / Verify

*单一来源的数字/论断,待第二来源或实测交叉验证。*

- 「init_render 出 49 文件、骨架落成约 1 分钟」为单次 dogfood 观察,版本变化后会漂移。出处:[[sources/2026-07-20-decision-deterministic-render-discipline]]
- 代码行号锚点(run_ci 行 258–260/464/487/602–604)随版本漂移,引用时须当次仓内核实。出处:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]、[[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]]
- 检索成本 8.4x 等数字仅「参考实例 newpj4 实测」,未做跨 domain 复测。出处:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]

## 3. 未解问题 / Questions

*ingest/query 中浮出的开放问题,尚无页面承载答案;全库级的移入 [[overview]]「仍未解决的问题」。*

*以下为首轮 bulk ingest(2026-07-20)暴露的协议缝隙,标「待回流」者建议提 PR 回框架仓:*

- `ingest_tier` 字段未在 `.claude/rules/source-page.md` frontmatter 约定中声明(三组 mapper 均撞到;lint 现未做字段白名单故未报)——建议协议显式收编为可选审计字段。【待回流】出处:[[sources/2026-07-20-adr-file-ownership-three-tiers]] 等全部 10 源
- `raw_file` 相对路径口径歧义(相对实例根 vs raw_dir 内裸文件名)——本批统一采「相对实例根」写法 `raw/inbox/<file>.md`,建议 rules 明示。【待回流】
- 内生 inbox 源 `authors` 无取值约定(本批出现 `llmwiki-dev` 与「llmwiki 框架开发会话(内生 capture)」两种写法)——建议 capture 约定补字段或 source-page 规则放宽。【待回流】
- wiki-ingest SKILL.md bulk 节回传契约 `{slug, title, claims[], relation_type, quote}` 把 relation_type 放贡献级,实际需要 per-claim `{target_page, relation_type}` 粒度(本批即按后者执行)——建议 SKILL 文本精确化。【待回流】
- SKILL.md bulk 节未写明:mapper 源页 Connections 的前向引用由 reduce 终裁 slug 并回改;bulk 模式下 light 档 followups 由 reduce 代记。本批均按此执行,建议明文化。【待回流】
- `_map` 读取档位表将 `raw/inbox/` 标 grep-only,与 ingest 七步流第 1 步「Read raw 全文」字面冲突(语义可调和:档位表管查询路径,ingest 是特许全读)——已在 _map 该行加注,建议框架模板同步。【待回流】
- source-page.md 七段骨架的 frontmatter 示例缺 `created:`,而 lint W-PAGE-4 将其列为全页型必填——首批 10 源全部漏写、lint 报 error 后补齐;建议骨架补该字段。【待回流】出处:本批 reduce lint 记录(见 log 2026-07-20 bulk-ingest 条)

## 4. 待晋升 / Promote

*rule-of-three 未达的纯文本提及(W-PAGE-3),以及 light 档 ingest 欠下的 touch 债(W-ING-1)——达标后晋升为 wikilink / full 档。*

- 概念「派生物纪律」(derived-artifact-discipline,W-IDX-1 凡汇总皆派生):现 2 源,差 1 源晋升。出处:[[sources/2026-07-20-adr-file-ownership-three-tiers]]、[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]
- 概念「pending 持久重算」(pending-persistent-recompute):1 源,暂由 [[entities/sync-tool]] 承载。出处:[[sources/2026-07-20-adr-rolling-judge-by-digest]]
- 概念「工具去 domain 化」(tool-de-domainization):1 源。出处:[[sources/2026-07-20-adr-rolling-judge-by-digest]]
- 概念「ingest 分档」(ingest-tiering,嫁接项④)、「W-* 规则 ID 命名空间」(rule-id-namespace,嫁接项①)、「工作流动词本地化 skills」(local-workflow-skills,嫁接项⑥):各 1 源。出处:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]
- 实体「build_site」(build-site)、「local_notes 适配器」(local-notes-adapter):各 1 源,事实暂由 [[concepts/fetcher-adapter-contract]] 承载。出处:[[sources/2026-07-20-adr-manifest-container-articles]]
- 实体「init_render」(init-render):1 源,暂由 [[concepts/deterministic-render]] 承载。出处:[[sources/2026-07-20-decision-deterministic-render-discipline]]
- 概念「CI 环境自洽」(hermetic-ci)与实体「extras/serve.py 本地阅读器」:各 1 源(light 档欠 touch 债),暂由 [[entities/run-ci]] 承载。出处:[[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]]
- 概念「wikilink 纪律」(wikilink-discipline)、叙事「开箱 lint 全绿」(out-of-box-green)、实体「templates/wiki/overview.md 模板」:各 1 源(light 档欠 touch 债),暂由 [[entities/lint-wiki]] 承载。出处:[[sources/2026-07-20-pitfall-template-comment-example-wikilink]]
