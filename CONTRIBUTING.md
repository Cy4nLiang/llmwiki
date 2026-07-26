# CONTRIBUTING — llmwiki 贡献指南

> 2026-07-20 随 M4 发布工程落款。反馈与回流一律走 issue / PR;本指南列出提交前你需要知道的全部约定。

## 1. 定位与支持范围

- llmwiki 实例定位**单人 + agent**:read 可并行(只读 subagent 蒸馏回传),write 单写者,均为单会话内语义。跨会话/多成员的 log 合并、聚合页协调**不提供机制**(v1 Non-goal,团队并发留 v2)——请不要提交为多人并发打补丁的 PR,这类需求先读 `docs/rfc-team-mode.md`(团队模式 RFC:提案与开放问题,**未实现**),再开 issue 讨论 v2 方向。
- 支持范围:单人维护者 **best-effort**。issue 会看,但没有响应时限承诺。
- domain 特殊需求优先走两条逃生舱,而不是改框架文件:config 的 `x-` 扩展命名空间 + 契约〈实例扩展附录〉/`.claude/rules/local-*.md`(lint 豁免,升级承诺永不合并冲突)。frozen 档禁改,改 = 显式 fork(W-UPG-1)。

## 2. 开发环境

- 前提:macOS/Linux + Python 3,**仅标准库,零第三方依赖**——PR 引入任何 pip 依赖会被直接拒。
- 全部验证一条命令:

  ```bash
  python3 tests/run_ci.py
  ```

  hello-wiki 夹具闭环(渲染→幂等→lint→sync→eval→多分面→golden 校验→模拟升级),当前 256 项断言(以实跑输出为准);产物全部写系统 tmp,不写仓库。提交前必须全绿。
- 改动 `tools/**` 等 frozen 档文件后,重新生成派生物 MANIFEST(勿手编):

  ```bash
  python3 tools/gen_manifest.py
  ```

- 文档数字纪律:性能类数字只允许「参考实例 newpj4 实测」口径(如 59.6K→7.1K tok/题),不作通用承诺;PR 里新增数字请沿用同一口径或给出你实例的 golden 复跑证据。

## 3. 两档规则申明(提 PR 前先看这里)

规则总表见 `framework/RULES.md`(32 条:frozen 28 / convention 4)。两档接受的 PR 类型不同:

| 档位 | 语义 | PR 政策 |
|---|---|---|
| **frozen** | 框架不变式,实例不可改(改 = 显式 fork,W-UPG-1) | **不接受放宽/豁免类 PR**(例:允许改 raw/、放宽断链、跳过 touch 下限)。接受:bug 修复、lint 检查器增强、文案修正。认为某条 frozen 规则本身错了 → 先开 issue 带实例证据,规则语义变更 = MAJOR,门槛按 MAJOR 走 |
| **convention** | 协议默认约定,实例可在〈实例扩展附录〉调整 | **可议**。带上你实例的调整记录(log 条目 + golden eval 前后对比)最有说服力 |

注:标「数值 config」的 frozen 规则(如 W-PAGE-1 页面预算),阈值本来就由 `wiki.config.json` 提供——调阈值改自己的 config 即可,无需 PR。

## 4. 回流通道(实例好约定 → 框架 MINOR)

co-evolution 双层化的标准路径:

1. **实例侧**:好约定先在你的实例落地,log 一条并标「**待回流**」,最好已被自家 golden 题集检验过;
2. **开 issue / 直接 PR**:说明该约定解决什么问题、在哪类 domain 下成立、是否已在实例运行过;
3. **被采纳 → 进 MINOR 版本**:维护者会把它写进 `framework/UPGRADING.md` 的新版本条目。

PR 描述请直接按 UPGRADING 条目格式组织(完整模板见 `framework/UPGRADING.md`「条目格式约定」):**变更摘要**(一句话一条,写「变了什么」)+ **迁移清单**(逐条引 `W-*` 规则 ID,无对应规则填 `—`;实例动作必须可执行可核对,不许写「按需调整」;语义变更写明旧行为 → 新行为)+ **frozen 覆盖清单** + **验收**。这能让维护者采纳时零改写地并入发版条目。

## 5. 脱敏 checklist(回流 PR 必过)

依据 W-SEC-2 / W-XRF-1 与 Spec §14〔D5〕〔D6〕。凡 PR 内容源自你的真实实例,逐项自查:

- [ ] **去 domain 专名**:公司名、项目名、产品内部代号替换为中性占位(如 `<vendor>`、`example-project`);
- [ ] **去内部 URL**:内网地址、私有仓库链接、带 token 的链接一律移除;
- [ ] **去内部数字**:实例私有统计(页数、成本、业务量)不入 PR;需要举证时换算成「相对变化」或复述为「参考实例 newpj4 实测」既有口径;
- [ ] **peers 路径不入 PR**(W-XRF-1):`wiki.config.json` 的 `peers` 是本机路径,属本机环境信息,不入发布物与回流 PR——示例 config 请删掉 peers 段或换 `/path/to/peer` 占位;
- [ ] **凭证零残留**(W-SEC-2):凭证只走环境变量;PR 中 config/manifest/脚本里不得出现 key/token 样式字符串;
- [ ] **fixtures 只收合成语料**(〔D5〕):`tests/` 新增夹具必须全合成原创(hello-wiki 即样板);真实实例的页面/raw 快照**不入公开仓库**,本地回归请自行留存。

## 6. semver 判级表

判级规则源自 Spec §10,与 `framework/UPGRADING.md` 头部声明一致(发版条目落在该文件):

| 判级 | 触发条件 | 例 |
|---|---|---|
| **MAJOR** | frozen 工具行为/页面格式字段语义变更 | lint 某检查从 warning 升 fail;源页骨架段语义改动 |
| **MINOR** | 新增可选模块/新增规则/模板增强(实例好约定回流默认落在这档) | 新增 `W-*` 规则;extras 新组件;skill 模板增强 |
| **PATCH** | 文案与锚点修订 | 契约措辞、注释、README 修订 |

配套动作:MAJOR/MINOR 需在 `framework/UPGRADING.md` 顶部插入新版本条目并 bump `framework/VERSION`;所有档位发版前 `python3 tests/run_ci.py` 全绿 + `python3 tools/gen_manifest.py` 重算。

## 7. 提交前最后一遍

1. `python3 tests/run_ci.py` 全绿;
2. 动过 frozen 档 → MANIFEST 已重算;
3. 回流类 PR → §5 脱敏 checklist 逐项勾完 + §4 条目格式就位;
4. 涉及规则语义 → 确认判级(§6)与档位政策(§3)匹配。
