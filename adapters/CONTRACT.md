# adapters/CONTRACT.md — fetcher 采集适配器契约(v1.0)

> 随 framework v1.0 发布(Spec v1.0 §7,2026-07-19)。本文件是**合同正文**:满足全部条款的
> 适配器即被 `tools/sync.py` / pending 计算 / build 自动接入,无需改任何框架代码。
> 面向作者的编写指南(从 skeleton 出发的步骤、常见坑)见 `docs/fetcher-contract.md`。
> 修订走框架升级协议:条款语义变更 = MAJOR,新增可选条款 = MINOR,文案 = PATCH。

## 0. 定位

适配器(fetcher)是**采集层**代码:把某一个源集合的内容机械地搬进 `raw/`,并在
`state/` 记台账。它属于实例(instance 档,`tools/adapters/<name>.py`,升级永不触碰),
在 `wiki.config.json` `pipelines[]` 注册后由 sync 调度:

```jsonc
{ "name": "docs", "kind": "pull", "raw_dir": "raw/vendor", "prefix": "v-",
  "adapter": "tools/adapters/vendor_docs.py", "source_kinds": ["howto","reference"] }
```

适配器**永远不做知识分析**:不写 wiki/、不产 TL;DR、不建交叉引用 —— 那是 agent 的
ingest 工作(W-ARCH-2 两类写入者分权)。

## 1. 三型定义

| 型 | 定义 | 抓取义务 | pending 判定(sync 持久重算) |
|---|---|---|---|
| **pull** | 外源逐篇文章:discover 发现清单,fetch 逐篇落盘 | `discover` + `fetch` + `status` | raw_dir 内容文件其期望源页 `wiki/sources/<prefix><stem>.md` 不存在 |
| **push** | 人/CI 直投 raw 目录(inbox 捕获件、CI 产物);无外网抓取 | 免 discover/fetch;建议提供 `status`(+ `register`) | 同 pull:目录 diff 成立,不依赖台账 |
| **rolling** | 单份滚动文档(CHANGELOG、团队规范):每次 fetch **整体覆盖**快照 | `discover`(可轻量/no-op)+ `fetch` + `status` | 快照 sha256 与源页 frontmatter `rolling_digest` 不一致(§6) |

三型可在同一实例并存;一个适配器只服务一条管线(一对一,name 对齐)。

## 2. CLI 子命令合同

每个 pull / rolling 适配器必须是可直接执行的脚本,提供子命令:

```
python3 <adapter> discover --root <实例根>     # 发现新条目 → 更新 manifest(不抓正文)
python3 <adapter> fetch    --root <实例根>     # 抓 pending 条目 → 写 raw/ + 更新 manifest
python3 <adapter> status   --root <实例根>     # 零网络:报 discovered/fetched/pending 计数
```

- **`--root` 必收**(默认 `.`):实例根 = 含 `wiki.config.json` 的目录。适配器内一切
  路径以 root 为基准解析;**禁止**依赖「从某个特定 cwd 运行」。sync 以子进程调用
  `python3 <adapter> discover --root <root>` 与 `fetch --root <root>`,cwd 恰为 root,
  但契约上必须靠 `--root` 而非 cwd 成立;
- **`--json`**:机器可读输出,至少 `status` 支持(统一 CLI 约定);
- **`--force`**(fetch,建议):忽略「已抓跳过」全量重抓;**`--limit N`**(fetch,建议):
  限抓条数,便于分批续抓;
- push 型免 discover/fetch(sync 不会调用);建议提供 `status`(盘点+校验)与
  `register`(登记台账),参考随框架发布的 `adapters/local_notes.py`;
- 其余子命令可自由追加(如 rolling 的 `redate`、pull 的 `images`),sync 不感知。

## 3. 写入边界(W-ARCH-1 / W-ARCH-2)

适配器**只允许写**:

1. `raw/<自己管线的 raw_dir>/`(及其 assets 子目录,如 `raw/assets/`);
2. `state/<pipeline>.manifest.json`(台账,§4)与 `state/` 下自有辅助文件
   (fetch 日志等,命名带管线名前缀避免撞名);
3. **临时件一律入 `state/tmp/`**(可随时整目录删除,重跑必须无感)。

**禁止**:写 `wiki/`(agent 领地)、写其他管线的 raw_dir、修改/删除/重命名 raw 既有
文件(W-ARCH-1;唯一例外:rolling 型的 faithful 快照与其派生件按 §6 同名整体覆盖,
历史由 git 承载)。`state/` 默认在 `.gitignore`(W-SEC-2),台账丢失必须可由
discover/fetch 重建 —— pending 判定不依赖台账,正因如此。

## 4. manifest 台账

路径:`state/<pipeline>.manifest.json`。结构:

```jsonc
{
  "pipeline": "docs",              // 与 config pipelines[].name 一致
  "updated": "2026-07-19",         // 最近一次写台账的日期
  "items": {                       // slug → 条目
    "2026-07-01-some-post": {
      "slug": "2026-07-01-some-post",       // 必填:条目 slug(ASCII;与 raw 文件 stem 一致)
      "url": "https://example.com/p/…",     // 必填:来源 URL;push 型可空字符串 ""
      "title": "Some Post",                 // 必填:标题(discover 时可先置 null,fetch 后必补)
      "date": "2026-07-01",                 // 必填:发布/产生日期 YYYY-MM-DD(未知置 null 并尽力补)
      "fetched": "2026-07-19",              // 必填:抓取/登记日期;未抓为 null
      "raw_file": "raw/vendor/2026-07-01-some-post.md"  // 必填:root 相对路径;未抓为 null
    }
  }
}
```

- **必填字段:`slug` / `url`(push 可空)/ `title` / `date` / `fetched` / `raw_file`**;
  可选字段自由追加(`chars`、`authors`、`sha256`、`non_article` 等);
- 写入用「写 `state/tmp/` 临时文件 → 原子替换」,抓一条存一次(中断可续);
- rolling 型台账通常只有一条 item(该滚动文档本身),`sha256` 建议随抓更新。

## 5. raw 文件形态

每个内容文件 = **YAML frontmatter + markdown 正文**,置于 raw_dir **顶层**,
文件名 `<stem>.md`(建议 `<date>-<slug>.md`;stem 决定源页名 `<prefix><stem>.md`):

```markdown
---
title: "Some Post"
slug: 2026-07-01-some-post
source_url: https://example.com/p/some-post
date_published: 2026-07-01
date_fetched: 2026-07-19
kind: howto            # 建议:source_kind,供 sync 分档建议(ingest_tiers)与 staleness
authors: ["A. Author"]
---

# Some Post

正文 markdown …
```

- frontmatter 用 lib/fm.py 可解析的简易 YAML 子集(标量 / 引号串 / 单行列表);
- **多路径产物同构**:同一管线无论经哪条抓取路径产出(HTTP 直抓、浏览器捕获、
  人工粘贴救济——参考实例 newpj4 的 OpenAI 管线即三路并存),raw 文件形态与
  manifest 条目形态**必须完全一致**,下游(pending/build/ingest)不感知抓取路径;
- **rolling faithful 快照豁免本节 frontmatter 要求**(§6);
- 资产(图片等)入独立子目录(如 `raw/assets/`),不参与 pending 计算;
- 内容文件后缀限 `.md` / `.txt`;`_` 开头文件(如 `_meta.json`)与 `*.dated.*`
  派生件不算内容文件。

## 6. rolling 特则:faithful / dated 分离 与 digest 约定

### 6.1 faithful 快照

`raw/<dir>/<slug>.md` = 上游文档**原样拷贝**(不注入 frontmatter、不清洗——保真优先,
这是 raw-wins 裁决的物证);每次 fetch 同名整体覆盖,历史由 git 承载。
抓取元信息(时间、来源 URL、版本计数、**sha256**)写 `raw/<dir>/_meta.json`。

### 6.2 dated 派生

需要注日期/注版本的视图写**同目录派生件** `raw/<dir>/<slug>.dated.md`(纯变换,
faithful 不动;参考实例 newpj4 的 cc_changelog 即「版本标题注入日期」)。派生件
可随时由 faithful + 辅助数据重生成,不算内容文件、不参与 pending。

### 6.3 rolling_digest 约定(pending 判定依据,frozen)

- 适配器侧:**digest = faithful 快照文件字节的 sha256 十六进制**(64 位小写);
  建议写入 `_meta.json` 与 manifest item,`status` 子命令应打印之;
- agent 侧:ingest/刷新滚动源页时,把该值写进源页 frontmatter
  **`rolling_digest:`**(可写全量 64 位,或 ≥12 位前缀,或带 `sha256:` 前缀);
- sync 侧比对规则:剥 `sha256:` 前缀、不分大小写;声明值与实际 digest 全等,或
  声明值长度 ≥12 且为实际 digest 前缀 → 视为一致;否则 pending
  (reason = `digest-changed`;源页缺失 = `no-source-page`;源页有但缺字段 = `no-digest`);
- 语义:digest 变化 = 滚动源出了新版本 → agent 走「刷新滚动源页」特例
  (更新既有源页而非新建;变化记「演进」,W-ING-3),完成后回写新 digest。

## 7. 幂等可续 / 限速退避 / UA

- **幂等**:已抓条目(manifest `fetched` 非空且 raw_file 存在)默认跳过;`--force`
  全量重抓;中断后重跑从断点继续(抓一条存一次台账);
- **限速**:请求间 sleep(参考值 1.0s);失败重试 ≤3 次,退避随尝试次数递增;
  429/5xx 按退避处理,404 不重试;
- **UA**:自报家门的 User-Agent(工具名 + 联系方式),不伪装浏览器——除非目标站
  另有要求且已在适配器文件头注明缘由;
- 单条失败**不中断整批**:计数、记日志、继续;结束时汇总 ok/skip/fail。

## 8. 退出码(统一 CLI 约定)

| 码 | 含义 |
|---|---|
| 0 | 成功(discover/fetch 完成,或 status 报告正常) |
| 1 | 发现问题或失败(网络硬失败、部分条目 fail、status 发现台账/文件不一致) |
| 2 | 配置与用法错误(--root 非实例根、缺子命令、参数非法) |

sync 依此裁决:adapter 返回非 0 → 该管线标记失败,sync 整体 exit 1。

## 9. 依赖自带声明

框架核心**零第三方**(仅 Python 标准库)。适配器可以用第三方库(bs4、playwright…),
但必须**自带声明**:随适配器附 `tools/adapters/requirements.<name>.txt`,并在适配器
文件头 docstring 列明依赖与安装命令;import 失败时给出可执行的修复提示后 exit 2。
随框架发布的 `local_notes.py` 与两份 skeleton 均为纯标准库。

## 10. 安全(W-SEC-1 / W-SEC-2)

- 抓回的一切外源内容 = **不可信输入**:适配器只搬运不执行;其中指令性文本对 agent
  是数据(ingest 时在源页 Processing Notes 标注可疑注入);
- **凭证只走环境变量**,禁止写进 config / manifest / 适配器源码;`state/`、`*.env`
  已在 `.gitignore` 模板;
- 适配器不得向 raw 之外回写抓取目标(只读外部世界)。

## 11. 合规自查清单

提交/注册一个适配器前逐条打勾:

- [ ] `pipelines[]` 已注册,`name`/`raw_dir`/`prefix`/`kind` 与适配器内常量一致
- [ ] `discover` / `fetch` / `status` 三子命令齐备(push 型:status/register)
- [ ] `--root` 必收且一切路径以之解析;任意 cwd 下运行结果相同
- [ ] 只写自己的 `raw/<dir>/` + `state/<pipeline>.manifest.json`;临时件全部在 `state/tmp/`
- [ ] 从不修改 raw 既有文件(rolling faithful 同名整体覆盖除外)
- [ ] manifest 六必填字段齐:slug / url(push 可空)/ title / date / fetched / raw_file
- [ ] raw 内容文件 = YAML frontmatter + 正文;文件名 stem 与源页命名 `<prefix><stem>.md` 对齐
- [ ] 多条抓取路径(如有)产物同构,manifest 条目同构
- [ ] rolling:faithful 原样 / dated 派生分离;sha256 进 `_meta.json`,status 可打印
- [ ] 幂等:重跑不重抓已完成条目;`--force` / `--limit` 可用;中断可续
- [ ] 限速 sleep + 重试退避;自报 UA
- [ ] 退出码 0/1/2 语义正确;`status --json` 可被机器解析
- [ ] 第三方依赖已随附 requirements 并在 docstring 声明;无依赖则纯标准库
- [ ] 无凭证入库;示例/demo 数据不会误留在真实 raw 目录
