# Claude Code hooks(可选:自动捕获 + 启动提醒)

> 框架文档(frozen,domain 无关;随 framework v1.3.0 加入,2026-07-25)。
>
> `extras/hooks/` 的两个脚本把 llmwiki 的两条手动纪律接到 **Claude Code hooks** 上,零口头成本:
> - **boot_reminder.py**(`SessionStart`)——新会话自动提醒 agent「先读 `wiki/_map.md`」(启动阅读协议);
> - **capture_draft.py**(`SessionEnd`/`Stop`)——会话收尾自动在 `raw/inbox/` 投递一份 `kind: draft`
>   占位草稿,让 W-CAP-1 检查点不被遗忘(**投递 ≠ 整合**:草稿是 stub,由你/下次 agent 填或删)。
>
> 两者都是 **opt-in**:不配置就完全不触发。都是 extras 可选层——不进核心依赖面,删掉不影响任何核心承诺。

## 前提

- `extras/` **不随实例分发**(init_render 不拷 extras)。用法:从框架 checkout 里直接跑,靠
  `--root` 或环境变量 `LLMWIKI_ROOT` 指向你的实例根。
- 脚本纯 Python 标准库,`exit 恒 0`——hook 出错绝不打断会话;非 llmwiki 实例时静默无操作。

## 配置(`.claude/settings.json` 片段)

把 `<框架路径>` 换成你 checkout llmwiki 的绝对路径,`<实例根>` 换成实例根绝对路径。
(hook I/O 契约以你的 Claude Code 版本为准——脚本对 stdin 的 hook JSON 是**尽力解析**,
只用 `cwd`/`session_id` 且都可被 `--root`/`--session-id` 覆盖,不硬依赖具体字段。)

```json
{
  "env": { "LLMWIKI_ROOT": "<实例根>" },
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
          "command": "python3 <框架路径>/extras/hooks/boot_reminder.py" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command",
          "command": "python3 <框架路径>/extras/hooks/capture_draft.py" } ] }
    ]
  }
}
```

- 用 `LLMWIKI_ROOT` 定位实例最省事;也可改成 `... capture_draft.py --root <实例根>`。
- capture_draft 草稿投递到默认 `raw/inbox/`(标准 push 管线)。若你的实例把 push 管线 `raw_dir`
  配成了非默认目录,草稿仍落 `raw/inbox/` 而 sync 扫描该管线的自定义 raw_dir——两者一致才会被报
  pending;非默认 raw_dir 的实例请把草稿目录对齐(或保持默认 `raw/inbox/`)。
- 想用 `SessionEnd` 而非 `Stop` 亦可(二者都在会话收尾;`Stop` 每次回合结束触发,capture_draft
  **按 session 幂等**,同一会话只投递一次,不会刷屏)。

## 行为

| 脚本 | 事件 | 做什么 | 不做什么 |
|---|---|---|---|
| boot_reminder | SessionStart | 输出 `additionalContext`:提醒先读 `_map`、走决策表、exact-match、W-CAP-1 收尾检查点 | 不写文件、不改状态 |
| capture_draft | SessionEnd/Stop | 在 `raw/inbox/<date>-session-draft-<sid>.md` 投递 `kind: draft` 占位草稿(同 session 幂等) | **绝不写 `wiki/`**、不总结会话、不替 agent 整合 |

草稿正文是一段检查点模板:填入本次值得留底的踩坑/约定/决策(填好改 `kind` 为
adr/pitfall/decision/howto),**没有则删除本文件**。下次 `sync` 会把未整合的草稿报成 pending。

## 人工 e2e 验收清单

1. 配好 settings.json,新开一个 Claude Code 会话在实例目录——起始上下文应含「先读 _map」提醒。
2. 会话结束后,`ls <实例根>/raw/inbox/` 应出现 `*-session-draft-*.md`,`kind: draft`,`wiki/` 无新增。
3. `python3 <框架>/tools/sync.py status --root <实例根>` 的 pending 计数 +1(草稿被报为待整合)。
4. 同一会话多次触发 `Stop`:草稿只投递一份(幂等)。
5. 在非 llmwiki 目录触发:脚本静默 exit 0,无任何文件/输出。
6. 删除草稿或填入内容并 ingest 后,pending 归零。

CI 对两脚本做机械冒烟(`tests/run_ci.py` phase_extras):草稿投递 + kind:draft + sync pending +1 +
boot 输出合法 JSON + 非实例静默。宿主行为(真会话触发)靠上面人工清单。
