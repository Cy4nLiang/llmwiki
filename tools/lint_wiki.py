#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lint_wiki — M1 精简版(仅 Python 标准库)

M1 只提供两个检查;完整机械 lint(断链 W-PAGE-3 / 页面预算 W-PAGE-1 / _map 预算 W-LNT-2 /
log 格式 W-LOG-1 / MANIFEST hash W-UPG-1 / staleness「过期未核实」/ light 占比告警等)于 M2 移植。

用法:
    python3 tools/lint_wiki.py --check-slots --target <dir>
        扫描实例内全部 .md 的 <SLOT: 与 <!--BEGIN: / <!--END: 残留(渲染验收,报 文件:行号);
        排除 framework/base/(模板快照本该含槽位)、raw/(不可信输入且从不经渲染,W-SEC-1)、
        state/ site/ _attic/ .git 等;任何残留 → exit 1。
        注:若某页需要示范槽位语法本身,请写成反引号内断开形式(如 `<SLOT :key>`)以免误报。

    python3 tools/lint_wiki.py --check-config <path>
        校验 wiki.config.json;校验器单源复用 tools/init_render.py(手写实现,零第三方依赖)。

两个检查可同时给出;任一有发现 → exit 1;用法/IO 错误 → exit 2。
"""

import argparse
import json
import sys
from pathlib import Path

# 单源:校验器住在 init_render.py(同目录导入)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import init_render as _ir
except ImportError as e:  # pragma: no cover
    print("错误: 无法导入同目录 init_render.py(校验器单源所在):%s" % e, file=sys.stderr)
    sys.exit(2)

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "state", "site", "_attic", "raw"}
MARKERS = ("<SLOT:", "<!--BEGIN:", "<!--END:")


def check_slots(target):
    """返回残留清单 ['相对路径:行号: 行内容', ...]。"""
    target = Path(target).resolve()
    findings = []
    for path in sorted(target.rglob("*.md")):
        rel = path.relative_to(target)
        parts = rel.parts
        if any(p in EXCLUDE_DIRS for p in parts[:-1]):
            continue
        if len(parts) >= 2 and parts[0] == "framework" and parts[1] == "base":
            continue  # 模板快照:槽位是设计使然
        if path.is_symlink():
            continue  # AGENTS.md → CLAUDE.md 之类,避免同一内容双报
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if any(m in line for m in MARKERS):
                findings.append("%s:%d: %s" % (rel.as_posix(), i, line.strip()[:100]))
    return findings


def check_config(path):
    """返回 (errors, warnings);config 读不了/非 JSON 时以单条 error 表达。"""
    p = Path(path)
    if not p.is_file():
        return ["%s: 文件不存在" % p], []
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ["%s:%d: 不是合法 JSON:%s" % (p, e.lineno, e.msg)], []
    return _ir.validate_config(cfg)


def main(argv=None):
    ap = argparse.ArgumentParser(description="llmwiki 机械 lint(M1 精简版)")
    ap.add_argument("--check-slots", action="store_true", help="扫描渲染残留(需配 --target)")
    ap.add_argument("--target", default=None, help="实例根目录(--check-slots 用)")
    ap.add_argument("--check-config", default=None, metavar="PATH", help="校验 wiki.config.json")
    args = ap.parse_args(argv)

    if not args.check_slots and not args.check_config:
        ap.print_help()
        return 2

    failed = False

    if args.check_slots:
        if not args.target:
            print("错误: --check-slots 需要 --target <dir>", file=sys.stderr)
            return 2
        if not Path(args.target).is_dir():
            print("错误: target 目录不存在:%s" % args.target, file=sys.stderr)
            return 2
        findings = check_slots(args.target)
        if findings:
            failed = True
            print("check-slots: %d 处残留(渲染未完成或模板私造槽位):" % len(findings))
            for f in findings:
                print("  - %s" % f)
        else:
            print("check-slots: OK(0 残留)")

    if args.check_config:
        errors, warns = check_config(args.check_config)
        for w in warns:
            print("check-config 警告: %s" % w)
        if errors:
            failed = True
            print("check-config: %d 处错误:" % len(errors))
            for e in errors:
                print("  - %s" % e)
        else:
            print("check-config: OK(%s)" % args.check_config)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
