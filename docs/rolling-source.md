# Rolling source — 滚动源协议(框架详解)

> 框架文档(frozen,domain 无关;随 framework v1.0 发布,2026-07-19)。
> kind=rolling 管线(config `pipelines[].kind: "rolling"`)的完整整合协议。实例侧入口:`.claude/skills/wiki-ingest/SKILL.md`「滚动源特例(kind=rolling 的管线)」、`.claude/skills/wiki-sync/SKILL.md`「pending 判定(持久重算)」(`#pending-rule`)的 rolling 例外块、`.claude/rules/source-page.md`「滚动源特有约定(存在 kind=rolling 的管线时生效)」。
> 采集侧合同:`adapters/CONTRACT.md`(rolling 型合规判据)+ `adapters/rolling_source.skeleton.py` 骨架。规则引用以 `framework/RULES.md` 为权威。

## 1. 什么是滚动源

一份**持续演化的单一文档**,而非一篇篇独立文章:软件 CHANGELOG、运维 runbook、团队编码约定、API reference……共同特征:上游只提供「最新全文」,历史以版本号/日期条目内嵌在文档里(或根本没有显式版本)。

若按普通文章处理——每个版本建一张源页——wiki 会退化成上游文档的逐版本镜像:页数爆炸、聚合无从谈起。滚动源协议用以下五条原则替代。

## 2. 五条协议原则

### 2.1 一份源页代表整份滚动文档

`wiki/sources/<date>-<slug>.md` 只有一张,`<date>` 取**首次 ingest 日期**,此后刷新**不建新页**。`source_kind` 按 config 管线声明(如 `changelog` / `runbook-snapshot` / `convention`)。

刷新时 bump `date_ingested`(本次刷新日)与 `date_published`(=快照所含最新条目/版本的日期)及正文「最新版本」表述;历史叙述**只追加不重写**。W-PAGE-4 必填字段照常,另加 §2.5 的两个滚动专用字段。

### 2.2 faithful 快照与 dated 派生分离

- **faithful 快照**:采集工具对上游全文的**同名整体覆盖**。这是 rolling 型 fetcher 合同(`adapters/CONTRACT.md`)声明的行为,也是采集层唯一允许改写 raw 既有文件的路径;对分析 agent 与人工,raw 仍然只读(W-ARCH-1)。快照逐字忠实,不注入任何加工。
- **dated 派生**:工具从快照生成的注日期版本——如把版本标题 `## 1.2.3` 注为 `## 1.2.3 — 2026-06-22`(日期取自采集时顺带获取的版本→日期映射)。供人读与 grep 锚定;可离线重生成(工具提供不联网的 redate 类子命令),faithful 原样不动。
- 分工:**引用与锚点优先 dated;diff 与 digest 只对 faithful**。
- 历史不因整体覆盖而丢失,保存在三处:git 对 raw/ 的提交历史、wiki 时间线的「演进」条目、`wiki/log.md`。

### 2.3 变化一律记「演进」(W-ING-3)

版本 N+1 改变了版本 N 的行为,不是矛盾,是演进:时间线追加条目,旧结论保留并标注被 supersede 的版本/日期;禁静默覆盖。⚠️ 真矛盾标记只留给例外情形(同一快照内自相矛盾、上游无声撤回既有条目等)。

### 2.4 精选进 timeline 实体页,完整条目回 raw grep

- 逐条内容**精选**后并进:对应 entity 的时间线页(**canonical 面,细**——该滚动文档所述对象的版本事实以此页为准)+ synthesis 演进叙事(**粗**——节奏与拐点)+ 被显著触及的 concept 页;
- wiki 永远只是精选;**查任意版本/日期的完整条目回 raw grep**;
- **锚点配方模板化**:每条 rolling 管线在实例 `wiki/_map.md`「标准 grep 配方」(`#grep-recipes`)登记一条,模板:

```
grep -A<N> '^## <条目标题正则>' raw/<raw_dir>/<snapshot>.dated.md
```

配方三要素:**锚定文件**(优先 dated 派生;faithful 本身带日期时可直接锚 faithful)、**条目标题正则**(版本号或日期)、**上下文行数 N**(按条目典型长度定)。实例化见 §4/§5。

### 2.5 rolling_digest 判新(与 sync / CONTRACT 对齐)

滚动源页 frontmatter 额外携带两个字段:

```yaml
rolling_digest: "sha256:<faithful 快照全文的 sha256,64 位十六进制>"
rolling_latest: "1.2.3"   # 快照最新条目的版本号;无版本号的文档记最新条目日期
```

- **写入时机**:首次 ingest 与每次刷新完成时,agent 把**当时 faithful 快照文件**的 sha256 写入 `rolling_digest`,同步更新 `rolling_latest`;
- **sync 判新** = 现场重算 faithful 快照 sha256,与源页 `rolling_digest` 比对:不一致 → pending 报一条**「刷新滚动源页」**(走 §3 流程,不是新建页)。这与 pending 持久重算原则一致——pending = f(raw/, wiki/sources/),不依赖一次性台账,重跑恒得同一结果;
- **digest 是机械权威**(对无版本号的文档同样成立);`rolling_latest` 是**报告口径**——同步报告有版本号写「版本 X → Y」,没有则写「digest 变更(前 8 位,如 `abcd1234…`)」;
- **fetcher 侧对齐**:rolling 型适配器按 `adapters/CONTRACT.md` 只写快照 + `state/<pipeline>.manifest.json`;判新用的 digest 由 sync 基于 raw 现场计算,不信 manifest 转录(raw wins,W-ARCH-1;工具读 wiki frontmatter 属只读,不违反 W-ARCH-2 写入边界)。

## 3. 刷新流程(七步流的滚动变体)

1. sync 报 pending「刷新滚动源页」(digest 不一致);
2. **定位增量**:在 dated 派生上 grep 出 `rolling_latest` 之后的新条目区段,只读增量不整读全文(W-LNT-1 大文件 grep-only);
3. **更新源页**:bump `date_ingested` / `date_published` / `rolling_latest` / `rolling_digest`,TL;DR 的「最新版本」随之;显著新里程碑追加进源页叙述(不重写历史);
4. **touch 聚合页**:新条目的显著项追加进 timeline 实体页(逐条标「演进」)+ 被触及的 concept 页;档位与 touch 下限照常适用(W-ING-1);
5. 索引派生(W-IDX-1);
6. `wiki/log.md` append 一条(W-LOG-1);
7. 强制回执:created / updated(带关系类型)/ contradictions。

## 4. 场景 A:运维 runbook(无版本号)

某 ops 实例注册 rolling 管线 `runbook`(`raw_dir: raw/runbooks`,source_kind `runbook-snapshot`):

- 快照 = 整份 on-call runbook 的同名整体覆盖;无版本号,条目按 `## 2026-07-02 回滚步骤修订` 类日期小节组织;
- `rolling_latest:` 记快照内最新修订日期;**判新完全依赖 digest**(§2.5 无版本号分支);
- 锚点配方(登记进 `_map` `#grep-recipes`):`grep -A15 '^## 2026-' raw/runbooks/oncall-runbook.md`——faithful 本就带日期标题,无需 dated 派生;
- 时间线面:`entities/oncall-runbook-timeline` 记操作程序变更史(演进条目如「2026-05 起:回滚先切 feature-flag 再 rollback deploy,supersede 2025-11 直接 rollback 流程」);
- **说明书时效**(W-LNT-3):runbook 是操作性内容,相关聚合页配 `verified:` 日期,超过 config `staleness` 声明的窗口未核实即被 lint 报「过期未核实」——stale 的 runbook 是危险品,不是旧文章。

## 5. 场景 B:软件 CHANGELOG(有版本号)

- 快照 = 上游 CHANGELOG.md 全文整体覆盖;fetch 顺带产出版本→日期映射,并生成 dated 派生(`## 1.2.3 — 2026-06-22`);
- `rolling_latest:` 记最高版本号;同步报告口径「版本 1.2.3 → 1.4.0」;
- 锚点配方:`grep -A20 '^## X\.Y\.Z' raw/<raw_dir>/<name>.dated.md`;注意 dated 派生若无 Added/Changed/Fixed 字面分节,引用时说明归类是推断;
- 精选双面:`entities/<product>-timeline`(版本事实 canonical 面,细)+ `syntheses/<product>-evolution`(发布节奏叙事,粗)。

**参考实例**:newpj4 的 Claude Code CHANGELOG 管线(源页 `sources/2026-06-23-claude-code-changelog`)是本协议的出处实例——一张源页覆盖 0.2.21 → 2.1.214 全程,faithful/dated 分离、grep 锚定与「演进」时间线均可在该实例查证。

## 6. 指针

- ingest 侧:`.claude/skills/wiki-ingest/SKILL.md`——「滚动源特例(kind=rolling 的管线)」;
- sync 侧:`.claude/skills/wiki-sync/SKILL.md`——「pending 判定(持久重算)」(`#pending-rule`)rolling 例外块、「同步报告格式(固定产出)」(`#sync-report-format`);
- 源页写法:`.claude/rules/source-page.md`——「滚动源特有约定(存在 kind=rolling 的管线时生效)」;
- 采集合同:`adapters/CONTRACT.md`(rolling 型)+ `adapters/rolling_source.skeleton.py`;
- 批量协议(多篇独立源的 map-reduce,与本协议正交):`docs/bulk-ingest.md`;
- 规则权威表:`framework/RULES.md`(本文引用 W-ARCH-1 / W-ARCH-2 / W-PAGE-4 / W-ING-1 / W-ING-3 / W-IDX-1 / W-LOG-1 / W-LNT-1 / W-LNT-3)。
