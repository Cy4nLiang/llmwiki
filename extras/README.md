# extras — 可选组件(随框架交付,不进核心依赖面)

> 〔D7 终裁〕本目录是框架的**可选增强层**:随框架仓库交付、`gen_manifest` 归 frozen 档做
> hash 追踪(改 = 显式 fork,W-UPG-1),但**不进核心依赖面**——`tools/` 七件套与四个
> 工作流(ingest / query / lint / sync)对本目录零依赖,评测协议也不覆盖它;删掉整个
> `extras/` 不影响任何核心承诺。`init_render` 不把 extras 拷进实例:要用就从框架
> checkout 直接 `--root` 指向实例运行,或手工拷入实例后运行。
>
> 两个组件都遵守框架 CLI 约定:`--root` 定位实例;exit 0 OK / 1 有发现或文件级失败 /
> 2 配置用法错;机器输出 `--json`(serve 是常驻服务,无 --json)。仅 Python 标准库。

## serve.py — 本地阅读器 + action API

```bash
python3 extras/serve.py --root <实例根> [--port 8787] [--no-browser]
```

浏览器打开 `http://localhost:8787/`:读 `site/data.json` 渲染来源列表(搜索 / 管线 /
source_kind / 年份筛选)、wiki 聚合页目录与详情视图(极简 markdown 渲染)。参考实例
newpj4 版的 vendor/cluster 特化已全部泛化:**筛选面由 config `facets[]` / `pipelines[]`
驱动**,无 facet 的实例自动隐藏对应筛选;`file_zh` 槽位有值时详情页出现配对语言按钮
(由 i18n_link 回填,见下)。

### 边界:机械动作 HTTP,LLM 动作 Copy-as-Prompt

这是本组件从参考实例继承的核心设计,对应 W-ARCH-2 双写入者分权:

| 类别 | 动作 | 执行方式 |
|---|---|---|
| 机械(工具的活) | `GET /api/status`、`GET /api/pending` | subprocess 调 `tools/sync.py status/pending --json`(单源,不复制判定逻辑) |
| 机械 | `POST /api/lint` | subprocess 调 `tools/lint_wiki.py --json`(exit 1 = 有发现,报告照常回传) |
| 机械 | `POST /api/fetch[?only=NAME]` | subprocess 调 `tools/sync.py sync --json`,走管线注册表:声明 adapter 的 pull/rolling 管线跑 discover/fetch;push(人/CI 直投)与未声明 adapter 的管线在 `fetch[].skipped` 里返回说明 |
| LLM(agent 的活) | ingest 积压 / 语义 lint / 查询 | **不经 HTTP 执行**——UI 只把积压清单与 W-* 规则要点编译成可拷贝的 prompt,粘回 Claude Code 会话 |

安全:仅绑定 `127.0.0.1`;静态文件只暴露 `/site` `/raw` `/wiki` 三前缀(`wiki.config.json`
的 peers 本机路径、`state/` 等一概不暴露,W-SEC-2 同源考量);UI 单文件内嵌,零外部资源。

### 何时不需要 serve.py

- **agent 会话本身就是入口**:核心阅读协议(`_map` 路由 + grep 配方 + `site/agent/*.jsonl`)
  面向 agent 设计,人只在想「翻着看」时才需要网页;
- 机器检索走 `site/agent/pages.jsonl` / `sources.jsonl` 更便宜,不需要起服务;
- CI / headless 环境:全部机械动作有等价 CLI(`sync.py` / `lint_wiki.py`),API 只是薄封装;
- 多人共享阅读:出界(实例定位单人 + agent,本服务故意只听 localhost)。

## i18n_link.py — raw 语言对切换横幅(bilingual_link 泛化)

```bash
python3 extras/i18n_link.py --root <实例根> [--dry-run] [--strip] [--no-patch-site] [--json]
```

在 raw 语言对文件间注入幂等的切换横幅(一行 blockquote,尾缀唯一 marker
`llmwiki:i18n-switch` 注释),供 Obsidian 等阅读器双向跳转;并默认回填
`site/data.json` 的 `file_zh` / `title_zh` 双语槽位(build_site 明示由本组件填充;
data.json 每次 build 会重建,重建后需重跑本工具)。

### 配置(config 驱动;无该配置时报「未配置」exit 2)

```json
"x-extensions": {
  "i18n": {
    "pairs": [
      { "src_dir": "raw/blog", "dst_dir": "raw/blog_zn", "suffix": "",
        "src_label": "English", "dst_label": "中文" }
    ]
  }
}
```

配对约定 `src_dir/<stem>.md ↔ dst_dir/<stem><suffix>.md`,仅两侧都存在的对注入;
同目录后缀式(`foo.md ↔ foo.zh.md`)用 `src_dir == dst_dir` + `suffix: ".zh"`;
label 缺省取目录名。两目录必须在 `raw/` 下。

### W-ARCH-1 例外声明(为什么允许写 raw/)

「raw/ 不可变」是 frozen 不变式;本工具是 Spec §1.1 extras 条目**显式豁免**的 raw 增强,
豁免以三个条件为界:

1. **marker 内内容不算源文本**:只注入/剥离带唯一 marker 的一行横幅;事实裁决
   (raw wins)、引用与针对 raw 的 grep 语义都不应把横幅行当源内容;
2. **幂等 + 可撤销**:重跑先剥后插、内容未变不重写;`--strip` 一键剥离全部横幅,
   raw 回到未增强状态(豁免的退出机制);
3. **rolling 管线的 raw_dir 禁止入语言对**(工具校验后拒绝,exit 2):注入会改变快照
   sha256,把 `rolling_digest` 判新搅成永久 pending。

### 何时不需要 i18n_link.py

- 单语料库(绝大多数实例):没有语言对就没有横幅,连配置都不用写;
- 翻译覆盖零散且无人维护:横幅只对「两侧都存在」的对注入,覆盖率太低时价值有限;
- raw 阅读全靠 agent(不用 Obsidian 等人读工具):agent 检索走 wiki 层与 jsonl 索引,
  用不到 raw 内的导航横幅;
- 语料在 rolling 管线里:被本工具明确拒绝(见上)。

---

2026-07-19 · 两组件均泛化自参考实例 newpj4(`tools/serve.py` / `tools/bilingual_link.py`),
含其实测教训(iCloud dataless 文件防呆)。问题走框架 issue;好的扩展按回流通道提 PR(MINOR)。
