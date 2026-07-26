#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki extras/hooks/boot_reminder.py — 会话启动提醒 hook(可选;仅标准库)。

【extras 声明】可选组件(不进核心依赖面)。这是 **Claude Code SessionStart hook** 的实现:
新会话启动时,向 agent 注入一条 additionalContext,提醒它按契约先读 `wiki/_map.md` 路由页
再作答(启动阅读协议),并记住 W-CAP-1 会话收尾捕获检查点。配置见 `docs/hooks.md`。

只**追加上下文**,不写任何文件、不改任何状态。exit 恒 0(hook 出错不打断会话);
非 llmwiki 实例时输出空、静默退出。实例根定位:`--root` > `$LLMWIKI_ROOT` > hook cwd。

Claude Code SessionStart hook 约定:stdout 打印
`{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`,
其 additionalContext 会被并入会话起始上下文(以你的 Claude Code 版本为准,见 docs/hooks.md)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REMINDER = (
    "[llmwiki] 本项目挂有 agent-维护的 wiki 知识库。作答前先读 `wiki/_map.md`(路由页,第一读:"
    "读取档位表 / 纠偏区 / 问题类型→入口决策表 / grep 配方 + `python3 tools/search.py \"词\"` "
    "排名检索),按其决策表选最便宜入口;精确事实只认 exact-match 不信参数记忆(W-QRY-1)。"
    "会话收尾检查点(W-CAP-1):本次若产生值得留底的踩坑/约定/决策,投递 `raw/inbox/`(投递≠整合,"
    "不打断当前任务)。"
)


def _read_payload() -> dict:
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
        if (p / "wiki.config.json").is_file() and (p / "wiki" / "_map.md").is_file():
            return p
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Claude Code SessionStart hook:注入「先读 wiki/_map.md」启动提醒"
                    "(配置见 docs/hooks.md)")
    ap.add_argument("--root", default=None, help="实例根(优先;否则 $LLMWIKI_ROOT / hook cwd)")
    try:
        args, _ = ap.parse_known_args(argv)   # 容忍未知参数(误配 / 未来 CC 追加参数)
    except SystemExit:
        return 0   # argparse 任何 usage 错(缺值等)与 --help 都归 0:hook 绝不非 0 退出打断会话

    payload = _read_payload()
    root = _resolve_root(args, payload)
    if root is None:
        return 0   # 非实例:输出空,静默退出(不打断会话)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": _REMINDER}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
