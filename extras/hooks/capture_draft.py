#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki extras/hooks/capture_draft.py — 会话收尾捕获草稿 hook(可选;仅标准库)。

【extras 声明】可选组件(不进核心依赖面;删除不影响任何核心承诺)。这是 **Claude Code
SessionEnd/Stop hook** 的实现:会话收尾时在 `raw/inbox/` 起草一份 `kind: draft` 占位草稿,
让 W-CAP-1 的「会话收尾检查点」不被遗忘——下次 `sync` 会把它报成 pending,提示整合。
配置方式(哪个 hook 事件、settings.json 片段)见 `docs/hooks.md`。

**严格遵守 W-CAP-1「投递 ≠ 整合」**:本 hook 只**投递**一份 stub(占位草稿),绝不写
`wiki/`、绝不替 agent 整合、绝不总结会话(纯脚本无 LLM)。草稿正文是一段检查点模板,
由用户/下次 agent 填入真正内容或删除。**opt-in**:用户不配置就完全不触发。

幂等:同一 session 的草稿已存在则跳过(不覆盖可能已填的内容)。exit 恒 0——hook 出错
不应打断会话(不是实例、无法定位根、写失败,一律静默 exit 0)。

实例根定位优先级:`--root` > 环境变量 `LLMWIKI_ROOT` > hook payload 的 `cwd`。
读 stdin 的 hook JSON 是**尽力解析**(坏 JSON/空 stdin → {}),不硬依赖具体字段。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path


def _read_payload() -> dict:
    """尽力读 stdin 的 Claude Code hook JSON;非 JSON/空/无 stdin 一律返回 {}。"""
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    except (OSError, ValueError):
        return {}
    try:
        obj = json.loads(raw) if raw.strip() else {}
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_root(args, payload: dict):
    for cand in (args.root, os.environ.get("LLMWIKI_ROOT"), payload.get("cwd")):
        if not isinstance(cand, str) or not cand:   # cwd 来自不可信 stdin,非字符串也当无(不崩会话)
            continue
        p = Path(cand).expanduser()
        # 有效 llmwiki 实例:含 config 且有 inbox 投递点(否则不是本框架实例)
        if (p / "wiki.config.json").is_file() and (p / "raw" / "inbox").is_dir():
            return p
    return None


_TEMPLATE = """---
title: 会话收尾草稿 %s
date: %s
kind: draft
---

<!-- W-CAP-1 会话收尾检查点(本文件由 capture_draft hook 投递;投递 ≠ 整合)。
     下面按需填入本次会话值得留底的**踩坑 / 约定 / 决策**;没有则**删除本文件**。
     填好后:改 kind 为 adr|pitfall|decision|howto,下次 sync 会报 pending → 走 light 档 ingest。 -->

## 本次值得留底的

- (踩坑 / 约定 / 决策 —— 一条一行;无则删除本文件)
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Claude Code SessionEnd/Stop hook:会话收尾在 raw/inbox 起草 kind:draft 占位草稿"
                    "(W-CAP-1 投递≠整合;配置见 docs/hooks.md)")
    ap.add_argument("--root", default=None, help="实例根(优先级最高;否则用 $LLMWIKI_ROOT / hook cwd)")
    ap.add_argument("--date", default=None, help="草稿日期(默认今天;测试用)")
    ap.add_argument("--session-id", default=None, help="会话 id(默认取 hook payload;测试用)")
    ap.add_argument("--json", action="store_true", help="机器输出(结构化结果)")
    try:
        args, _ = ap.parse_known_args(argv)   # 容忍未知参数(误配 / 未来 CC 追加参数)
    except SystemExit:
        return 0   # argparse 任何 usage 错(缺值等)与 --help 都归 0:hook 绝不非 0 退出打断会话

    payload = _read_payload()
    root = _resolve_root(args, payload)
    result = {"ok": True, "drafted": None, "reason": None}

    def out(reason, drafted=None):
        result["reason"], result["drafted"] = reason, drafted
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif drafted:
            print("capture_draft: 已投递会话草稿 %s(W-CAP-1;下次 sync 报 pending)" % drafted,
                  file=sys.stderr)
        return 0   # 恒 0:hook 不打断会话

    if root is None:
        return out("非 llmwiki 实例或无法定位根(静默跳过)")
    sid = (args.session_id or payload.get("session_id") or "session")
    sid = "".join(c for c in str(sid) if c.isalnum() or c in "-_")[:12] or "session"  # [:12] 降碰撞
    date = args.date or datetime.date.today().isoformat()
    draft = root / "raw" / "inbox" / ("%s-session-draft-%s.md" % (date, sid))
    if draft.exists():
        return out("本 session 草稿已存在(幂等跳过):%s" % draft.name)
    try:
        draft.write_text(_TEMPLATE % (sid, date), encoding="utf-8")
    except OSError as e:
        result["ok"] = False
        return out("写草稿失败(静默跳过):%s" % e)
    return out("drafted", draft.relative_to(root).as_posix())


if __name__ == "__main__":
    sys.exit(main())
