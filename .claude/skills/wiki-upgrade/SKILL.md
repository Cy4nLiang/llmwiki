---
name: wiki-upgrade
description: 当框架发布新版而实例要跟版——用户说「升级框架」「/wiki-upgrade」「跟版到 x.y.z」,或 lint --manifest 报框架版本落后时触发。主线走 tools/upgrade.py:--dry-run 先看计划(规则 ID 差距清单/备份/覆盖/合并/冲突)→ 执行(frozen hash 校验覆盖 + render-once 三方合并 + 预备份 + lint 门禁 + log 落账)→ 处理 .upgrade-new 冲突逐 diff 合并 → golden 回归(W-UPG-2)→ 完成;任一步失败按回滚程序退回升级前锚点。
---

# wiki-upgrade — 实例升级协议

> 实例本地没有 `tools/upgrade.py`(0.2.x 及更早渲染的存量实例)时,直接用新版仓的:
> `python3 <FW>/tools/upgrade.py --root . --framework <FW>`——收尾后实例即持有该工具。
>
> **主线工具**:`tools/upgrade.py`(M3 落地)承担时序中全部机械步骤——版本对比与差距清单、
> 预备份、frozen hash 校验覆盖、render-once 三方合并、VERSION/base/MANIFEST 收尾、lint 门禁、log 落账。
> agent 负责:呈现计划给用户、裁决 fork、合并冲突、跑 golden 回归。工具不可用时按文末附录手工路径执行,时序与门禁不变。

## 前置

- 升级是**单会话原子操作**:开始前工作区必须干净(git 实例:`git status` 无未提交改动;非 git 实例:确认无进行中编辑);
- git 实例:执行前**由 agent 代跑** `git tag pre-upgrade-<当前版本>`(upgrade.py 不打 tag);非 git 实例的回滚锚点 = upgrade.py 自动落的预备份 `state/tmp/pre-upgrade-<旧版>/`(不假设 git);
- 升级前先把实例 lint 调绿:`python3 tools/build_site.py && python3 tools/build_index.py && python3 tools/lint_wiki.py`——门禁不区分「预先存在」与「升级引入」的发现,带病升级会误读门禁结果;
- 全程只动 frozen 与 render-once 两档;instance 档(wiki/、raw/、state/、site/、config、adapters、golden)**永不触碰**——唯一例外:upgrade.py 收尾向 `wiki/log.md` append 一条 upgrade 簿记条目(W-LOG-1;它是唯一获准写 log 的工具,理由见其头注)。

## 端到端时序
<a id="upgrade-sequence"></a>

1. **拉新版**(要一个可指认的新版工作树,fetch 只拿 refs 不产生文件):`git worktree add ../llmwiki-<新版> framework/main`(已加 remote 时),或直接 `git clone <框架仓> ../llmwiki-<新版>`;记下该路径为 `<FW>`。
2. **看计划(必做)**:`python3 tools/upgrade.py --root . --framework <FW> --dry-run`
   —— 零写入,打印:版本差 + UPGRADING.md 介于两版本间的条目(**规则 ID 差距清单**,semver 判级提示影响面:MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订)、预备份清单、frozen 覆盖/新增/fork 候选、render-once 采用/保留/冲突各清单。逐条呈现给用户,确认后再执行。
3. **执行**:`python3 tools/upgrade.py --root . --framework <FW>`
   - frozen 档:实例文件 hash == 旧快照(framework/MANIFEST.json)→ 整体覆盖为新版;被改过 → **fork 候选跳过不覆盖**——用户二选一:确认放弃本地改动补跑 `--force-frozen`(改动已入预备份);或确认保留 = **显式 fork**(记入 log,此后该文件脱离升级轨道,W-UPG-1);
   - render-once 档:三方合并自动落定「实例==base → 采用新版;新==base → 保留实例」;三者互异写 `<file>.upgrade-new` 不动原文件;〈实例扩展附录〉段(lint 豁免区标记以下)与 `.claude/rules/local-*.md` 由工具保证**永不参与合并**(附录自动摘出/原样接回);
   - 工具自动完成:预备份、更新 framework/{VERSION,base/,MANIFEST 快照}、wiki 页有写入时重建派生索引、lint 全量 + `--manifest` 门禁、log 落账。
4. **处理冲突**:对每个 `<file>.upgrade-new` 逐 diff 合并——`diff <file> <file>.upgrade-new` 逐块判断:框架侧改进合入原文件,实例侧改动保留;合并完删除 `.upgrade-new`,复跑 `python3 tools/lint_wiki.py --root . --manifest` 至干净。
5. **golden 回归门禁**:实例有 `evals/golden.jsonl` **必跑**(W-UPG-2,工具会打印提醒;执行方法见 wiki-golden skill):**P/R 与 tok/题不回退**才算完成跟版;回退 → 定位引入回退的合并块就地修复重跑;修不动 → 走回滚。
6. **收尾确认**:upgrade.py exit 0(零冲突零 fork)= 完成;exit 1 = 仍有冲突/fork 待处理,处理完复跑一次确认;按工具提示手动 bump `wiki.config.json` 的 `framework_version`(实例档,工具不代写)。git 实例提交一次升级 commit。

## 回滚
<a id="rollback"></a>

任一步失败且不可就地修复:

1. git 实例:`git reset --hard pre-upgrade-<版本>`(或对已提交部分 `git revert`);
2. 非 git 实例:把 `state/tmp/pre-upgrade-<旧版>/` 下备份按相对路径拷回,删除本次新写的 `.upgrade-new` 与新装文件;
3. `framework/{VERSION,base/,MANIFEST.json}` 随之恢复到升级前;
4. log 记一条失败原因与卡点(便于框架侧回流修复),待新版修复后重试。

instance 档全程无人触碰,回滚不涉及数据层。

## 附录:手工路径(工具不可用时的逐步替代)

时序与门禁不变,各步手工执行:

1. **差距清单**:读新版 `framework/UPGRADING.md` 与 CHANGELOG,按 W-* 规则 ID 列「新增/变更 × 实例现状」,呈现给用户再动手。
2. **frozen**:diff 实例文件 vs `framework/base/` 快照(或对照实例 MANIFEST 快照逐文件 sha256)。干净 → 从新版仓整体覆盖;有本地改动 → 弹 diff,fork 或回退二选一(W-UPG-1)。
3. **render-once**:base→新模板 diff 得「框架侧变更」,base→现文件 diff 得「实例侧变更」,手工合成,逐文件 diff 呈现、逐个批准;〈实例扩展附录〉与 `.claude/rules/local-*.md` 永不参与合并(UPGRADING 承诺永不合并冲突)。
4. **收尾**:手工更新 `framework/VERSION`、刷新 `framework/base/` 为新版模板快照、按实例持有过滤新 MANIFEST 落快照;`python3 tools/lint_wiki.py --root . --manifest` 全绿 + golden 门禁;`wiki/log.md` append 一条 `## [YYYY-MM-DD] upgrade | <old> -> <new>`(W-LOG-1),正文记差距清单结论、fork 清单、golden 前后数字。
