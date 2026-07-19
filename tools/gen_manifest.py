#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki gen_manifest — 生成 framework/MANIFEST.json(仅 Python 标准库)

MANIFEST 本身是派生物(W-IDX-1):由本工具从框架仓库文件树重算,勿手编;
升级协议以其中 sha256 判定 frozen 漂移(W-UPG-1:frozen 禁改,改 = 显式 fork)。

分档规则(路径首个命中为准;Spec §1.3 三档在框架仓库侧的投影):
  frozen      tools/**、schema/**、docs/**、evals/**、adapters/**(含 CONTRACT*)、extras/**
              —— 机器可检且 domain 无关,升级 hash 校验后整体覆盖
  render-once CLAUDE.template.md、.claude/**、templates/**
              —— 渲染出生的模板源,升级走 base × 现文件 × 新模板三方合并
  meta        README* / LICENSE* / framework/** 及其余未命中路径(示例 config、tests 夹具等)

用法:
    python3 tools/gen_manifest.py [--root <framework_repo>] [--out <path>] [--date YYYY-MM-DD]
缺省 root = 本脚本所在 tools/ 的上级;out = <root>/framework/MANIFEST.json。
确定性:文件按路径排序,不写时间戳(需要落款时显式传 --date)。
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXCLUDE_DIR_NAMES = {".git", "__pycache__", "node_modules", "state", "tests", ".claude/worktrees"}
EXCLUDE_FILE_NAMES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def classify(rel):
    """rel 为 posix 相对路径;返回 frozen | render-once | meta。"""
    if rel.startswith(("tools/", "schema/", "docs/", "evals/")):
        return "frozen"
    if rel.startswith("adapters/"):
        return "frozen"  # CONTRACT* 与 skeleton/local_notes 均为 domain 无关框架件
    if rel.startswith("extras/"):
        return "frozen"
    if rel == "CLAUDE.template.md":
        return "render-once"
    if rel.startswith((".claude/", "templates/")):
        return "render-once"
    if rel.startswith(("README", "LICENSE", "framework/")):
        return "meta"
    return "meta"  # 兜底:wiki.config.example.json、tests/ 夹具等


def sha256_file(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root):
    root = Path(root).resolve()
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if any(p in EXCLUDE_DIR_NAMES for p in parts[:-1]):
            continue
        if path.name in EXCLUDE_FILE_NAMES or path.suffix in EXCLUDE_SUFFIXES:
            continue
        if rel == "framework/MANIFEST.json":
            continue  # 派生物不自证
        entries.append({"path": rel, "tier": classify(rel), "sha256": sha256_file(path)})
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成 framework/MANIFEST.json(派生物,W-IDX-1)")
    ap.add_argument("--root", default=None, help="框架仓库根(缺省:本脚本所在 tools/ 的上级)")
    ap.add_argument("--out", default=None, help="输出路径(缺省:<root>/framework/MANIFEST.json)")
    ap.add_argument("--date", default=None, help="可选落款日期 YYYY-MM-DD(缺省不写,保持产物确定性)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print("错误: root 不存在:%s" % root, file=sys.stderr)
        return 2
    if args.date and not DATE_RE.match(args.date):
        print("错误: --date 须为 YYYY-MM-DD", file=sys.stderr)
        return 2

    version_file = root / "framework" / "VERSION"
    if version_file.is_file():
        fw_version = version_file.read_text(encoding="utf-8").strip() or "0.0.0-dev"
    else:
        fw_version = "0.0.0-dev"
        print("警告: framework/VERSION 缺失,暂记 %s" % fw_version, file=sys.stderr)

    entries = scan(root)
    doc = {
        "_comment": "派生物(W-IDX-1):python3 tools/gen_manifest.py 生成,勿手编;tier 语义见 Spec §1.3",
        "framework_version": fw_version,
        "files": entries,
    }
    if args.date:
        doc["generated"] = args.date

    out = Path(args.out) if args.out else root / "framework" / "MANIFEST.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tiers = {}
    for e in entries:
        tiers[e["tier"]] = tiers.get(e["tier"], 0) + 1
    print("MANIFEST 写入 %s:%d 文件(%s)| framework %s"
          % (out, len(entries),
             ", ".join("%s=%d" % (k, tiers[k]) for k in ("frozen", "render-once", "meta") if k in tiers),
             fw_version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
