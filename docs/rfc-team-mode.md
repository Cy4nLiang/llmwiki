# 团队模式 RFC(提案:未实现)

> **RFC / 提案文档**(frozen,domain 无关;随 framework v1.4.0 加入,2026-07-26)。
>
> **这是提案,不是实现。** 框架当前**不提供**团队并发机制:实例定位「单人 + agent」,write 单写者、
> read 可并行,且**均为单会话内语义**;跨会话/多成员的 log 合并与聚合页协调**不提供机制**
> (README「边界(如实声明)」与 CONTRIBUTING §1 的既有声明)。本文是 CONTRIBUTING 所要求的
> 「先开 issue 讨论 v2 方向」的讨论稿。
>
> **v1 语义零改动**:W-ING-2(共享聚合页必须 reduce 收敛单写者)与 W-XRF-1(跨实例引用单向、
> 1 跳、soft-lint)现状不变。本文不新增任何 `W-*` 规则——提案项用「提案 1..5」编号,
> 因为 `W-<域>-<序号>` 是 lint 报告 / UPGRADING / 契约共用的权威命名空间,
> 往里塞未生效的东西会被误读成已生效规则。
>
> **不引入**向量检索 / LLM 打分器 / 服务端 / confidence 衰减 / 跨实例自动同步(引用可以,同步不做)。

## 动机

v1 的单写者语义在单人场景是优点(零协调成本、log 可归因)。多人共用一座 wiki 时,已知缺口有三层,
且**互不相同**——把它们混谈是团队方案最常见的错误:

1. **文件层**:两人同时 ingest,逐篇型管线的 `wiki/sources/` 互不相干(一 raw 一源页,文件集合
   不相交;`kind: rolling` 是例外,见提案 1),
   但一次完整 ingest **从不只写源页**——W-ING-1 强制每篇源页 touch ≥ 档位下限的聚合页
   (full ≥5 / light ≥1),light 档还必记 `wiki/followups.md`。所以 PR 维度必然带上
   聚合页 + followups + `wiki/log.md` + 派生物。「sources append-only 天然可并」只在
   源页文件维度成立,**不能推广成「ingest 天然可并」**。
2. **协调层**:聚合页是跨源汇聚的散文,两人各写一段就是真冲突;W-ING-2 明写「无机检」,
   静默丢写在 v1 **不可检测**(只能靠 log/diff 人审)。
3. **可见性层**:个人笔记与团队共识混在一座库里,没有分区概念——谁都能读到别人的草稿。

## 提案(5 项)

每项固定三段:**现在能做**(v1 已具备、可核实)/ **提案要做**(条件式,未实现)/ **不做什么**。

### 提案 1 — 把「可并的部分」和「必冲突的部分」在流程上分开

**现在能做**:逐篇型管线(pull / push)的源页写入天然不相交(一 raw 一源页);`raw/` 不可变(W-ARCH-1)所以采集侧无冲突。**例外是 `kind: rolling`**:它是唯一获准同名整体覆盖 raw 的管线,且一份源页代表整份滚动源——两人同时刷同一 rolling 源必然改到同一个 raw 快照与同一张源页,git 会报文件级冲突(响亮失败,不是静默丢写),但这类改动**不属于下面说的可并类**。
派生物(`wiki/index*.md`、`wiki/contradictions.md`、`wiki/backlinks.md`)由工具全量重写,
永远可以「重跑而不是合并」。

**提案要做**:PR 模板把一次 ingest 拆成两类改动——**可并类**(源页、`raw/`)与**需协调类**
(聚合页、`followups.md`、`log.md`)。约定:① 派生物**不进 PR 评审**,由合并后重跑
`build_site` + `build_index` 产生(若入库则 `.gitattributes` 对派生物声明「以合并后重跑为准」);
② `wiki/log.md` 是 append-only 且多人同时追加必在尾部冲突,提案给它声明 `merge=union`
(git 的 union 合并把两侧行都保留,恰好符合 append-only 语义);③ 聚合页走提案 2。

**不做什么**:不改 W-ING-1 的 touch 下限(那会把复利闭环换成剪藏);不把派生物排除出实例
(它们是 agent 的检索面);不引入锁服务。

### 提案 2 — 聚合页冲突:复用升级引擎的**形状**,而不是它的算法

**现在能做**:`tools/upgrade.py` 的 render-once 三方合并已经把一套「绝不静默覆盖」的工程范式
跑通了:三者互异时**原文件一字不动**,新版落 `<file>.upgrade-new`,交 agent 逐 diff 合并;
契约〈实例扩展附录〉段合并前摘出、合并后原样接回(私有区永不参与合并);
`wiki/log.md` 因 append-only 被显式剔除出合并。

**提案要做**:把上面四条**形状**移植到团队场景,而不是移植算法本身——
① 指定基线 + 绝不静默覆盖;② 冲突产出 `<page>.merge-new` 旁文件,由 agent 按 W-ING-3
三分裁决(时间线变化 → 演进 / 立场差异 → 对比 / 真矛盾 → ⚠️),而不是让人读 `<<<<<<<` 标记;
③ 私有区摘出不合并;④ append-only 数据与派生物不进合并。

**为什么不能直接搬算法**(这条必须写清,否则提案是空的):
- **基线来源不同**:升级的 base 是「实例模板快照 + 旧渲染器」**确定性重渲染**出来的;
  团队场景只能取 `git merge-base`,而聚合页是 agent 手写散文,不存在可重渲染的基线。
- **权威不对称**:升级里框架对框架文本权威、实例对自身编辑权威,天然有特权侧;
  两个对等分支没有,必须外部引入 tie-breaker(这正是提案 3)。
- **粒度更粗**:升级做的是**整文件相等性**三态判定,比 git 自带的行级三方合并**能力更弱**;
  聚合页需要的是「逐条事实 + `(来源:[[sources/X]])`」的条目级并集语义。

**不做什么**:不做自动语义合并(那需要 LLM 打分器,在拒绝清单里);不引入 CRDT/OT。

### 提案 3 — 页面所有权清单(给冲突提供 tie-breaker)

**现在能做**:`wiki-ingest` 的 bulk map-reduce 里,reduce 已经持有聚合页 slug 的**终裁权**;
这在语义上就是「每页一个负责人」的单会话版本。页面 frontmatter 加未知键不会被 lint 拒绝
(必填集合是「缺什么报什么」,没有白名单),所以 `owner:` 这类加性字段在 v1 是**可写但零强制**的。

**提案要做**:一张「聚合页 → 负责人」清单,冲突时负责人裁决(等价于把 reduce 的终裁权
从单会话延伸到跨会话)。落点建议 `docs/` 或 `wiki/` 顶层(根级 `OWNERS.md` 会触发
W-ARCH-3 根命名空间告警)。

**不做什么**:不做强制门禁(v1 没有、也不该有「非 owner 不能改」的机制——那是 git 平台的
CODEOWNERS 的活,不是知识库协议的活)。

### 提案 4 — CI 门禁配方(本仓的 `.github/workflows/ci.yml` 就是活配方)

**现在能做**:门禁命令已存在且零依赖,但**分属两个仓、别混抄**——
- **框架仓专有**:`python3 tests/run_ci.py`(hello-wiki 夹具契约面)。`tests/` 既不入 MANIFEST
  也不随 `init_render` 分发,**你的实例仓里没有这个文件**,抄了会当场报「文件不存在」;
- **任何实例仓可用**:`tools/gen_manifest.py` 重导比对(派生清单无漂移)、
  `tools/eval_retrieval.py --check-golden` 与 golden 回归(W-UPG-2)、
  `tools/lint_wiki.py --manifest`(机械 lint + frozen hash)。

本仓的 `.github/workflows/ci.yml` 按这个序列自用:团队实例仓抄的是它的 **instance job** 那一半,
并把 `--root knowledge` 换成自己的实例根;fixture job 留给框架维护者。

**提案要做**:团队仓把这套配方设为 PR 必过门禁,并在其上追加两条社会性约定——
① PR 描述列出本次 touch 的聚合页(便于人眼发现两个 PR 撞同一页);② golden 回退即 block。

**踩过的坑,抄配方前先看**(全部实测):
- **裸 clone 直接 lint 实例会 exit 1**:实测唯一的 error 是 **W-IDX-1** 判 `wiki/backlinks.md`
  缺失(本仓惯例不提交该派生物);`site/agent/*.jsonl` 三缺只报 **W-IDX-2 soft warning**,
  不影响退出码;`state/` 与退出码无关。让 lint 转绿最少只需 `build_index`,但配方里仍先跑
  `build_site`——W-IDX-2 的 warning 也该清掉,且 `wiki_search` 之类要 `site/` 才有数据。
  (注:`site/` 是否入库看你的实例——`init_render` 生成的默认 `.gitignore` 只忽略 `state/` 与凭证,
  **不含 `site/`**;本仓根 `.gitignore` 额外忽略了 `site/`,所以才有「裸 clone 缺派生物」这一幕。)
- **别把「build 后 `git diff --exit-code`」当门禁**:`build_index` 把 `updated:` 写成当天日期
  且没有 `--date` 旗标,这种门禁除当天外必红。派生物新鲜度只该由 lint 判。
- `eval_retrieval.py` 的位置参数是 run 文件,`--golden` / `--check-golden` 是**带值选项**;
  两者的相对路径都按 `--root` 解析。
- 最低 Python 3.9(`str.removeprefix()`),而含 3.9 的矩阵要把 runner 写死在有 3.9 制品的镜像上。
- 别给 job 加 `container:`:那会以 root 跑,`run_ci` 里「不可读目录」负例会退化成弱断言。

**不做什么**:CI 不代跑任何写 `wiki/` 的动作(那是 agent 的活,W-ARCH-2 双写入者分权);
不在 CI 里调 LLM。

### 提案 5 — shared / private 分区:形状上已可跑,缺的是三条运维约定

**现在能做**:这就是 peers 机制的现成形状——每人一个 private 实例,团队一个 shared 实例,
private 的 config 把 shared 声明为 peer,用 `[[shared::slug]]` 单向引用。开启只需改 config
重渲染(peers 是条件模块,零代码);README 推荐的「个人 hub 实例」与 `wiki-init` 的 peers 问答
就是同一形状。

**提案要做**三条运维约定(不是新机制):
1. **onboarding 必须含「clone shared 后本机跑一次 `build_site`」**——跨实例检索读的是对方的
   `site/agent/pages.jsonl`。**若 shared 仓不提交 `site/`**(本仓即如此;注意 `init_render`
   生成的实例默认 `.gitignore` 只忽略 `state/` 与凭证,是否忽略 `site/` 由你的仓决定),
   不跑 build 就是空转。反过来把 `site/` 提交进 git 也是一种选择——W-IDX-1 禁的是手编生成区
   与双事实源,并不禁派生物入库——代价是每个 PR 都会在派生物上产生 diff/冲突,得配
   「合并后重跑」的约定(提案 1)。
2. **peers 路径不可共享的解法**:`peers[].path` 是本机路径,每人机器不同,config 里的值
   **无法跨人复用**。零改动的可行方案两条——约定统一挂载点(人人 `~/wikis/<name>`,`~` 展开后一致),
   或 config 留占位符由每人本机替换。**明确否掉**环境变量插值(要动 schema + 渲染器 + sync + lint
   四处,越过「v1 零改动」边界)与 git submodule(把 shared 历史钉进 private,且违反「peers 路径
   不入发布物」的洁净性)。
3. **防 private 内容误入 shared PR**:v1 无机制。可行的零改动配方是 shared 仓侧 CI 门禁
   (提案 4)加一份 CONTRIBUTING 式脱敏 checklist(本仓 §5 已有先例)。

**已知取舍,别当优点卖**:「private 引 shared、shared 不回链」是 W-XRF-1 的单向设计。
好处是零写入越界(不会有人写对方仓)、shared 的反链/图谱不被 N 个 private 的引用噪声污染;
**代价是** shared 侧无法知道某页被谁引用、「这页还有人用吗」在机制上不可答,
而且 shared 的孤儿检查会把「只被外部 private 引用」的页判成孤儿(有机入链不计 `::` 链接)。

**不做什么**:不做 mesh 同步、不做双向自动回链、不做服务端权限模型。

## 边界(如实声明)

- 本文全部提案**未实现**;v1 的单写者语义、W-ING-2、W-XRF-1 一字未改。
- 不做 SaaS / 服务端;不做跨实例自动同步(引用可以,同步不做);不做向量检索;
  不引入 LLM 打分器或 confidence 衰减。这些是框架的既有非目标,团队模式不构成例外。
- 团队协作里**社会性的那一半**(谁负责哪页、冲突谁拍板、什么算「团队共识」)不由工具保证,
  CI 只能兜住机械面。任何声称「装上就能多人协作」的方案都在这一点上不诚实。
- 支持范围仍是单人维护者 best-effort;团队方向请开 issue 讨论,不要提交为多人并发打补丁的 PR。

## 迁移路径(假想版本的清单形状;不 bump 任何版本、不进 UPGRADING)

若某天真做团队模式,迁移清单应当长这样——每条动作**可执行可核对**(照 UPGRADING 的写作约束,
不许写「按需调整」):

| 阶段 | 实例动作 | 可核对的完成信号 |
|---|---|---|
| 0 现状 | 无动作 | 单人单写者,CI 绿 |
| 1 上门禁 | 抄 `.github/workflows/ci.yml` 的 **instance job**(`--root` 换成自己的实例根),设为 PR 必过 | PR 上该 job 绿:MANIFEST 无漂移 + golden 机检 + golden 不回退 + build 后 lint rc=0 |
| 2 分派生物 | `.gitattributes` 给 `wiki/log.md` 声明 `merge=union`;约定派生物合并后重跑 | 两个 PR 同时 append log 后无冲突;合并后 lint 的 `stale_index` 为 0 |
| 3 定所有权 | 落一份「聚合页 → 负责人」清单(`docs/` 或 `wiki/` 顶层) | 每张聚合页在清单里有且只有一个负责人 |
| 4 聚合页冲突流程(提案 2) | 约定:冲突页产出 `<page>.merge-new`、原文件不动,由负责人按 W-ING-3 三分裁决后再提交 | 造一次真冲突演练:原文件未被覆盖、`.merge-new` 存在、裁决后 lint rc=0 |
| 5 分区(可选) | private 实例 config 声明 shared 为 peer;onboarding 加「本机跑一次 build_site」 | `[[shared::slug]]` 在 private 侧 lint 的 `peer_links` 计数为 0(peer 可达且目标 slug 存在;该检查恒为 soft warning,故要看**计数**不是看 error) |

**顺序不可交换**:门禁(1)先于协调约定(2–4),协调约定先于分区(5)——否则分区只是把冲突挪到别处。
阶段 4 是提案 2 的落点:它只需要一条**约定 + 一次演练**,不需要任何新工具,所以能排在
「真做团队模式」之前先跑通。

## 开放问题

1. **所有权清单是派生物还是手写文件?** 若手写,它和页面 frontmatter 的 `owner:` 就是双事实源
   (W-IDX-1 禁双源);若派生,v1 没有这个派生工具。**决策所需证据**:先在一个真实多人仓里
   手写维护一个月,看清单漂移频率。
2. **聚合页条目级合并到什么粒度才够用?** 「逐条事实 + 来源」的并集语义听起来对,但真实冲突
   常是**叙事重写**而非条目增删。**决策所需证据**:采集 20 个真实聚合页冲突样本,统计
   「可条目级并集」占比。
3. **静默丢写如何检测?** W-ING-2 明写无机检。可能的方向:源页 Processing Notes 的 touch 清单
   与聚合页实际引用做交叉校验(能查出「声称 touch 了但页面里没有」)。**决策所需证据**:
   这条能否在不误报的前提下做成 lint 项。
4. **`merge=union` 对 log 是否真的安全?** union 会保留两侧行但不保证时间顺序,
   而 W-LOG-1 只要求 append-only 与行格式,未要求全局有序。**决策所需证据**:确认
   `grep '^## \[' log.md | tail -N` 的读取口径在乱序下是否仍可用。
5. **shared 的孤儿检查该不该计 `::` 入链?** 计了要跨实例读对方索引(触碰「不做自动同步」边界);
   不计则「只被外部引用」的页永远显示为孤儿。**决策所需证据**:真实分区仓里这类页的占比。

## 指针

- 单写者语义与支持范围:`README.md` 的「边界(如实声明)」、`CONTRIBUTING.md` §1;
- 升级三方合并(提案 2 的形状来源):`tools/upgrade.py` 的 render-once 合并段与 `framework/UPGRADING.md`;
- 批量并行纪律:`docs/bulk-ingest.md`、`templates/skills/wiki-ingest/SKILL.md` 的 bulk 节;
- 跨实例引用:`framework/RULES.md` 的 W-XRF-1、`templates/skills/wiki-query/SKILL.md` 的跨实例检索节;
- 门禁配方:本仓 `.github/workflows/ci.yml`;
- 需求出处:framework 优化 spec 的 S10 条目(开发过程文档,不随实例分发);
- 规则权威表:`framework/RULES.md`(本文引用 W-ARCH-1 / W-ARCH-2 / W-ARCH-3 / W-IDX-1 / W-IDX-2 / W-ING-1 / W-ING-2 / W-ING-3 / W-LOG-1 / W-UPG-2 / W-XRF-1)。

本文档不含任何机检项:RFC 的正确性靠评审,不靠 lint。`.github/workflows/ci.yml` 里那套门禁是
**已生效**的(本仓自用),而本文的 5 项提案**都没有**对应实现——读到这里如果觉得团队模式已经能用,
请重读顶部声明。
