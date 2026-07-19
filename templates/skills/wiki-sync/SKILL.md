---
name: wiki-sync
description: 当要刷新知识库存量——用户说「同步」「/wiki-sync」「抓新的」「看看积压」,或宿主会话投递过 inbox 之后——时触发。按 wiki.config.json 管线注册表逐管线采集,持久重算 pending = f(raw/, wiki/sources/),打印积压报告与分档建议,再路由到 wiki-ingest。
---

# wiki-sync — 管线同步与积压报告

> **M1 注**:`tools/sync.py` 于 M2 落地;本 skill 先固化流程与产出格式,工具未就位时按各步「手工替代」逐管线执行,报告格式不变。

## 管线注册表(来自 wiki.config.json `pipelines[]`)

<SLOT:pipelines.table>

三型语义:
- **pull**:调 adapter `discover` → `fetch`(幂等:已抓跳过,`--force` 重抓;限速退避);
- **push**:人/CI 直投 raw 目录(含 inbox 捕获件),sync 不抓取只盘点;
- **rolling**:整体覆盖快照 + dated 派生,pending 按版本 diff。

## 执行流程

1. **逐管线采集**(M2 后:`python3 tools/sync.py`;手工替代:逐管线跑 adapter 子命令,push 型跳过)。工具只写 raw/ + state/ + site/,**不碰 wiki/**(W-ARCH-2);raw 既有文件永不改写(W-ARCH-1)。
2. **重算 pending**(见下节)。
3. **站点/索引重建**(命令见文末工具速查)。
4. **打印同步报告**(格式见下)→ 待 ingest 逐篇/批量路由 wiki-ingest skill。

## pending 判定(持久重算)
<a id="pending-rule"></a>

**pending = raw 现存文件集合 − 已有源页集合**,按管线前缀与 slug 对齐(raw 目录:<SLOT:pipelines.raw_dirs>)。不依赖一次性台账:重跑恒得同一结果;误删源页会重新出现在 pending(raw wins,W-ARCH-1)。

<!--BEGIN:rolling_source-->
rolling 管线例外:快照同名整体覆盖,pending 按「快照最新版本 vs 源页所记最新版本」diff 成立;有新版本 → pending 一条「刷新滚动源页」(走 wiki-ingest 滚动源特例,变化记「演进」),而非新建页。
<!--END:rolling_source-->

## 同步报告格式(固定产出)
<a id="sync-report-format"></a>

```text
== wiki-sync YYYY-MM-DD ==
管线 <name>(<kind>):新抓 N / raw 库存 M(rolling:版本 X → Y)
…每管线一行…
pending 共 K 篇:
- <slug>  [source_kind]  建议档位 full|light  来自 <pipeline>
建议:≤3 篇逐篇 wiki-ingest;≥10 篇走 bulk map-reduce;inbox 捕获件默认 light 档
```

分档建议按 <SLOT:ingest.tier_rules> 由 source_kind 映射得出,用户可逐篇覆盖(W-ING-1 下限随档)。有实际抓取或新发现时,`wiki/log.md` append 一条 `## [YYYY-MM-DD] note | sync ...`(W-LOG-1);纯 status 查看不落 log。

## 本实例工具速查

<SLOT:tools.cmds>
