---
name: wiki-upgrade
description: 当框架发布新版而实例要跟版——用户说「升级框架」「/wiki-upgrade」「跟版到 x.y.z」,或 lint --manifest 报框架版本落后时触发。执行端到端升级时序:拉新版→规则 ID 差距清单→frozen hash 校验覆盖→render-once 三方合并→lint+golden 门禁→更新 VERSION 与 base/ 快照;任一步失败按回滚程序退回升级前 tag。
---

# wiki-upgrade — 实例升级协议

> **M1 注**:MANIFEST hash 校验与三方合并工具于 M3 落地;本 skill 先固化流程,工具未就位的步骤按各步「手工替代」执行,时序与门禁不变。

## 前置

- 升级是**单会话原子操作**:开始前工作区必须干净(`git status` 无未提交改动);
- 自动打 tag:`git tag pre-upgrade-<当前版本>`——这是唯一回滚锚点;
- 全程只动 frozen 与 render-once 两档;instance 档(wiki/、raw/、state/、site/、config、adapters、golden)**永不触碰**。

## 端到端时序
<a id="upgrade-sequence"></a>

1. **拉新版**:git remote `framework` fetch(主通道)/ degit 到临时目录(备选)。
2. **差距清单**:读新版 `framework/UPGRADING.md` 与 CHANGELOG,按规则 ID 生成差距清单——「新增/变更的 W-* 规则 × 实例现状」逐条列出,呈现给用户再动手。semver 判级提示影响面:MAJOR = frozen 工具行为/页面格式字段语义变更;MINOR = 新增可选模块/新增规则/模板增强;PATCH = 文案与锚点修订。
3. **frozen 档**:对照 `framework/MANIFEST.json` 逐文件 hash 校验(M3 前手工替代:diff 实例文件 vs `framework/base/` 快照)。干净 → 整体覆盖;检出本地改动 → 弹 diff,用户二选一:
   - 确认 **fork**(显式声明,记入 log;此后该文件脱离升级轨道,W-UPG-1);
   - 或回退本地改动后接受覆盖。
4. **render-once 档**:`framework/base/`(上版模板)× 实例现文件 × 新版模板 → 真三方合并(M3 前手工替代:base→新模板 diff 得「框架侧变更」,base→现文件 diff 得「实例侧变更」,手工合成),**逐文件 diff 呈现、逐个批准**。逃生舱永不参与合并:`.claude/rules/local-*.md` 与契约「实例扩展附录」段(UPGRADING 承诺永不合并冲突)。
5. **门禁**:`python3 tools/lint_wiki.py` 全绿 + golden 回归(执行方法见 wiki-golden skill):**P/R 与 tok/题不回退**才放行(W-UPG-2)。回退 → 定位引入回退的合并块,就地修复重跑;修不动 → 走回滚。
6. **落账**:更新 `framework/VERSION`、刷新 `framework/base/` 为新版模板快照;`wiki/log.md` append 一条 `## [YYYY-MM-DD] upgrade | <old> -> <new>`(W-LOG-1),正文记差距清单结论、fork 清单、golden 前后数字。

## 回滚
<a id="rollback"></a>

任一步失败且不可就地修复:

1. `git reset --hard pre-upgrade-<版本>`(或对已提交部分 `git revert`);
2. `framework/base/` 与 `framework/VERSION` 随之恢复到升级前;
3. log 记一条失败原因与卡点(便于框架侧回流修复),待新版修复后重试。

instance 档全程无人触碰,回滚不涉及数据层。
