# MCP server(可选:让非 skills 宿主消费同一座 wiki)

> 框架文档(frozen,domain 无关;随 framework v1.4.0 加入,2026-07-26)。
>
> `extras/mcp_server.py` 把实例暴露成一个 **MCP stdio server**(JSON-RPC 2.0,纯 Python 标准库)。
> 一级宿主 Claude Code 走 skills 就够了——本组件是给 **Claude Desktop / Cursor / Windsurf 等
> 非 skills 宿主**用的通用接口(R7)。
>
> **opt-in**:不注册就完全不存在。extras 可选层——不进核心依赖面,删掉不影响任何核心承诺。

## 前提

- `extras/` **不随实例分发**(init_render 不拷 extras)。用法:从框架 checkout 里直接跑,靠 `--root` 指向你的实例根。
- 纯标准库,零网络监听(stdio 管道,不开端口)。
- 检索工具依赖派生索引:先在实例里跑过 `python3 tools/build_site.py && python3 tools/build_index.py`,否则 `wiki_search` 会返回「索引未就位」并给出指路。
- 协议版本 **`2025-11-25`**(常量钉死在 `PROTOCOL_VERSION`;客户端请求别的版本时按 MCP 协商规则仍回本值)。

## 工具(4)

| 工具 | 做什么 | 不做什么 |
|---|---|---|
| `wiki_map` | 返回 `wiki/_map.md` 全文 + 「读取档位」节 + token 预算(`map_lines`/`page_tokens`/`boot_tokens`)。**任何检索前先调它** | 不猜路由;不返回页面正文 |
| `wiki_search` | BM25 排名检索,经 subprocess 调 `tools/search.py --json`(检索单源,不复制打分逻辑) | 不做向量/语义检索;精确事实仍应 grep 原文 exact-match(W-QRY-1) |
| `wiki_page` | 按 slug 取页:`mode=tldr\|full`、`max_tokens` 截断;回整页 `est_tokens` + 本次 `returned_est_tokens` + `truncated` | 不解析跨实例 `alias::slug`;slug 只认库内实页(挡路径穿越) |
| `wiki_capture` | 投递草稿到**第一条 push 型管线**的 raw 目录,再调 `adapters/local_notes.py register` 登记台账 | **绝不写 `wiki/`**;不整合(投递 ≠ 整合,W-CAP-1);同名已存在则幂等跳过(raw 不可变,W-ARCH-1) |

`max_tokens` 是**硬承诺**:`returned_est_tokens` 恒 ≤ 你给的值(截断提示语自身的 token 也计入)。`mode=tldr` 走降级链——TL;DR 节 → 首个 `##` 节 → 整 body,并在 `tldr_source` 回报实际来源(聚合页通常没有 TL;DR 段)。

## 宿主注册片段

把 `<框架路径>`、`<实例根>` 换成绝对路径。四个宿主用的都是同一个 `mcpServers` 结构,只有文件位置不同。

```json
{
  "mcpServers": {
    "llmwiki": {
      "command": "python3",
      "args": ["<框架路径>/extras/mcp_server.py", "--root", "<实例根>"]
    }
  }
}
```

| 宿主 | 配置文件 |
|---|---|
| **Claude Code** | 项目级 `.mcp.json`(仓库根)或用 `claude mcp add llmwiki -- python3 <框架路径>/extras/mcp_server.py --root <实例根>`;`claude mcp list` 查看 |
| **Claude Desktop** | macOS `~/Library/Application Support/Claude/claude_desktop_config.json`;Windows `%APPDATA%\Claude\claude_desktop_config.json` |
| **Cursor** | 全局 `~/.cursor/mcp.json` 或项目级 `.cursor/mcp.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |

改完配置需重启宿主(或按宿主提供的 reload 入口)。凭证类信息本组件一概不需要,别往配置里塞。

## MCP inspector 验证步骤(人工)

官方调试器不需要预装,`npx` 直接拉起(需 Node.js):

```bash
npx @modelcontextprotocol/inspector python3 <框架路径>/extras/mcp_server.py --root <实例根>
```

1. inspector 打开后点 **Connect** —— 应看到握手成功,`serverInfo.name = llmwiki`、版本等于框架 `framework/VERSION`。
2. **Tools** 标签点 **List Tools** —— 应恰好列出 4 个:`wiki_map` / `wiki_search` / `wiki_page` / `wiki_capture`。
3. 调 `wiki_map`(无参数)—— 返回文本里应含 `_map` 正文与 `read_tiers` 字段。
4. 调 `wiki_search`,`query` 填一个你库里确实有的词 —— 返回 `{query, k, count, hits}`,`hits[].slug` 可点回库内页。
   零命中不是错误(未收录是诚实结果);若报「索引未就位」,先跑 build_site + build_index。
5. 调 `wiki_page`,`slug` 填上一步的某个命中、`mode=tldr`、`max_tokens=200` —— 检查 `returned_est_tokens ≤ 200`、`truncated` 与 `tldr_source` 是否合理。
6. 调 `wiki_capture`(`title` + `slug`)—— 应在 push 管线的 raw 目录出现 `<date>-<slug>.md`,`wiki/` **无任何新增**;重复调用同一 slug 应回 `skipped_existing`(幂等)。
7. 收尾:在实例里跑 `python3 tools/sync.py status`,刚投递的草稿应被报为 pending(投递 ≠ 整合)。
8. 断开连接 —— 服务应随 stdin 关闭正常退出(exit 0)。

## 注意

- **stdout 是协议通道**:服务只往 stdout 写 JSON-RPC 帧,一切诊断走 stderr。若你 fork 本文件,别在 stdout 上 `print`,那会当场毁掉握手。
- **工具失败 vs 协议失败分层**:工具执行失败回 `isError: true` 的正常响应(便于宿主自纠),只有未知方法/未知工具/坏参数才回 JSON-RPC `error`(-32601 / -32602)。
- **投递口取自 config**:`wiki_capture` 用**第一条 `kind: push` 管线**的 `raw_dir`,不硬编码 `raw/inbox`——实例改了 `raw_dir` 它跟着走。(注:`extras/hooks/capture_draft.py` 是硬编码 `raw/inbox` 的,两者在默认实例上一致;非默认 `raw_dir` 的实例见 `docs/hooks.md` 的注意项。)
- `kind` 缺省为 `draft`,它通常不在实例的 `source_kinds` 枚举里 → sync 的分档建议会落到 `ingest_tiers.default`。想让草稿走 light 档,调用时显式给一个实例已声明的 kind(如 `pitfall`)。
- 实例没有 push 型管线时 `wiki_capture` 会明确报错并指路(加一条 `kind: push` 管线),不会静默写到别处。
- **入参不合形不静默吞**:`max_tokens`/`k` 传成字符串或非正数时,响应带 `ignored_args`(并回 `max_tokens_applied`),而不是悄悄换成默认值;`title`/`kind` 含换行或起首 `---` 会被**拒收**(frontmatter 逐行解析,换行可注入伪键),`date` 过 fullmatch + 真日历校验。畸形 `params`/`name`回 JSON-RPC `-32602` 且**进程存活**,排在后面的帧不会丢。

CI 只做机械冒烟(`tests/run_ci.py` phase_extras:握手 + `tools/list` 4 工具 + 各工具调用 + 写边界 + 幂等 + 未知工具分层)。真宿主注册与 inspector 交互靠上面的人工清单。
