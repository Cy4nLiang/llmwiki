#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_notes — push 型 inbox 适配器(开箱即用,随框架发布)

服务捕获协议(W-CAP-1)的投递口:宿主会话把值得留底的踩坑/约定/决策直投
`raw/inbox/<date>-<slug>.md`(frontmatter: title / date / kind),投递 ≠ 整合 ——
本工具只做**盘点与登记**,整合等下次 sync 报 pending 后由 agent 走 light 档 ingest。

push 型免 discover/fetch(CONTRACT §1/§2):sync 对 push 管线不调用适配器,
pending 由目录 diff 成立。本工具提供:

    python3 tools/adapters/local_notes.py status   [--root DIR] [--json] [--pipeline NAME]
        列 raw 目录内容文件,校验最小 frontmatter(title/date/kind):缺失项逐条报出
        但**绝不改文件**(raw 不可变,W-ARCH-1);kind 不在管线 source_kinds 枚举时给警告。

    python3 tools/adapters/local_notes.py register [--root DIR] [--json] [--pipeline NAME]
        把**合格**文件(三必填齐 + 日期格式对)登记进 state/<pipeline>.manifest.json,
        幂等:重跑不产生变化;不合格文件列为 skipped(修好 frontmatter 后重跑)。

管线选择:--pipeline 指名;缺省取 config `pipelines[]` 中第一条 kind=push 的管线。
退出码:0 = 全部合格;1 = 存在不合格文件(或台账指向的文件缺失);2 = 用法/配置错误。
依赖:纯 Python 标准库;frontmatter/config 解析单源复用实例 tools/lib/fm.py。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

CONTENT_EXTS = {".md", ".txt"}
REQUIRED_FM = ("title", "date", "kind")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _import_fm(root: Path):
    """单源复用实例的 tools/lib/fm.py(frozen 拷贝,处处存在)。"""
    for cand in (root / "tools", Path(__file__).resolve().parent.parent):
        if (cand / "lib" / "fm.py").is_file():
            sys.path.insert(0, str(cand))
            break
    try:
        from lib.fm import load_config, parse_frontmatter  # noqa: PLC0415
        return load_config, parse_frontmatter
    except ImportError as e:
        print("错误: 找不到 tools/lib/fm.py —— --root 应指向 llmwiki 实例根:%s" % e,
              file=sys.stderr)
        sys.exit(2)


def _pick_pipeline(cfg: dict, name: str | None) -> dict:
    pushes = [p for p in cfg["pipelines"] if p["kind"] == "push"]
    if name:
        hit = [p for p in cfg["pipelines"] if p["name"] == name]
        if not hit:
            print("错误: --pipeline=%s 不在管线注册表" % name, file=sys.stderr)
            sys.exit(2)
        if hit[0]["kind"] != "push":
            print("错误: 管线 %s 是 %s 型,本工具只服务 push 型"
                  % (name, hit[0]["kind"]), file=sys.stderr)
            sys.exit(2)
        return hit[0]
    if not pushes:
        print("错误: config 中没有 kind=push 的管线(pipelines[])", file=sys.stderr)
        sys.exit(2)
    return pushes[0]


def _content_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.is_dir():
        return []
    return [p for p in sorted(raw_dir.iterdir())
            if p.is_file() and p.suffix.lower() in CONTENT_EXTS
            and not p.name.startswith("_") and not p.stem.endswith(".dated")]


def _inspect(root: Path, pl: dict, parse_frontmatter) -> list[dict]:
    """逐文件校验最小 frontmatter;只读不写(W-ARCH-1)。"""
    kinds = pl.get("source_kinds") or []
    out = []
    for p in _content_files(root / pl["raw_dir"]):
        try:
            meta, _ = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        except OSError as e:
            meta = {}
            missing_note = "读文件失败:%s" % e
        else:
            missing_note = None
        missing = [k for k in REQUIRED_FM
                   if not (isinstance(meta.get(k), str) and meta.get(k).strip())]
        warnings = []
        d = meta.get("date")
        if "date" not in missing and isinstance(d, str) and not DATE_RE.match(d.strip()):
            missing.append("date(格式须 YYYY-MM-DD,得到 %r)" % d)
        k = meta.get("kind")
        if kinds and isinstance(k, str) and k.strip() and k.strip() not in kinds:
            warnings.append("kind=%s 不在管线 source_kinds 枚举 %s(仅警告)"
                            % (k.strip(), "|".join(kinds)))
        if missing_note:
            missing.append(missing_note)
        out.append({
            "raw_file": str(p.relative_to(root)),
            "slug": p.stem,
            "title": (meta.get("title") or "").strip() or None,
            "date": (meta.get("date") or "").strip() or None,
            "kind": (meta.get("kind") or "").strip() or None,
            "qualified": not missing,
            "missing": missing,
            "warnings": warnings,
        })
    return out


def _manifest_path(root: Path, pl: dict) -> Path:
    return root / "state" / ("%s.manifest.json" % pl["name"])


def _load_manifest(root: Path, pl: dict) -> dict:
    p = _manifest_path(root, pl)
    if p.exists():
        m = json.loads(p.read_text(encoding="utf-8"))
        if "articles" not in m and "items" in m:   # 旧容器键兼容:载入即迁移(CONTRACT §4 冻结形状)
            m["articles"] = m.pop("items")
        return m
    return {"pipeline": pl["name"], "updated": None, "articles": {}}


def _save_manifest(root: Path, pl: dict, m: dict) -> None:
    m["updated"] = date.today().isoformat()
    tmp_dir = root / "state" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / ("%s.manifest.json.tmp" % pl["name"])
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_manifest_path(root, pl))


def cmd_status(root, pl, files, m, args) -> int:
    registered = {it.get("raw_file") for it in m["articles"].values()}
    stale = [slug for slug, it in m["articles"].items()
             if it.get("raw_file") and not (root / it["raw_file"]).exists()]
    bad = [f for f in files if not f["qualified"]]
    result = {"ok": not bad and not stale, "pipeline": pl["name"],
              "raw_dir": pl["raw_dir"], "files": files,
              "total": len(files), "qualified": len(files) - len(bad),
              "registered": sum(1 for f in files if f["raw_file"] in registered),
              "manifest_stale": stale}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["ok"] else 1
    print("pipeline %s(push)· %s · 共 %d 件(合格 %d · 已登记 %d)"
          % (pl["name"], pl["raw_dir"], len(files),
             result["qualified"], result["registered"]))
    for f in files:
        mark = "✅" if f["qualified"] else "✗"
        reg = "已登记" if f["raw_file"] in registered else "未登记"
        print("  %s %s  [%s] %s · %s" % (mark, f["raw_file"], f["kind"] or "?",
                                          f["date"] or "?", reg))
        for miss in f["missing"]:
            print("      缺失/非法: %s(修 frontmatter 后重跑;工具不改文件,W-ARCH-1)" % miss)
        for w in f["warnings"]:
            print("      ⚠️ %s" % w)
    if stale:
        print("  ⚠️ 台账指向的文件已不存在(raw 不可变,请核查):%s" % ", ".join(stale))
    if bad:
        print("共 %d 件不合格 —— 最小 frontmatter 为 title/date/kind(W-CAP-1)" % len(bad))
    return 0 if result["ok"] else 1


def cmd_register(root, pl, files, m, args) -> int:
    items = m["articles"]
    added = updated = 0
    skipped = [f for f in files if not f["qualified"]]
    for f in files:
        if not f["qualified"]:
            continue
        entry = {
            "slug": f["slug"],
            "url": "",                       # push 型:url 可空(CONTRACT §4)
            "title": f["title"],
            "date": f["date"],
            "kind": f["kind"],
            "fetched": None,                 # 占位,见下
            "raw_file": f["raw_file"],
        }
        old = items.get(f["slug"])
        if old is None:
            entry["fetched"] = date.today().isoformat()   # 登记日即「入库日」
            items[f["slug"]] = entry
            added += 1
        else:
            entry["fetched"] = old.get("fetched") or date.today().isoformat()
            merged = {**old, **entry}
            if merged != old:
                items[f["slug"]] = merged
                updated += 1
    if added or updated:
        _save_manifest(root, pl, m)
    result = {"ok": not skipped, "pipeline": pl["name"], "added": added,
              "updated": updated, "unchanged": len(files) - len(skipped) - added - updated,
              "skipped": [{"raw_file": f["raw_file"], "missing": f["missing"]}
                          for f in skipped]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print("register: 新登记 %d · 更新 %d · 无变化 %d → %s"
              % (added, updated, result["unchanged"],
                 _manifest_path(root, pl).relative_to(root)))
        for f in skipped:
            print("  ✗ 跳过 %s(缺 %s)—— 修 frontmatter 后重跑;工具不改文件(W-ARCH-1)"
                  % (f["raw_file"], ", ".join(f["missing"])))
        print("提示:投递 ≠ 整合(W-CAP-1)——下次 sync 报 pending 后走 light 档 ingest。")
    return 0 if result["ok"] else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="push 型 inbox 适配器:盘点/校验/登记(契约见 adapters/CONTRACT.md)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    common.add_argument("--json", action="store_true", help="机器可读输出")
    common.add_argument("--pipeline", default=None, metavar="NAME",
                        help="push 管线名(缺省:config 第一条 kind=push)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[common], help="盘点 + frontmatter 校验(只读)")
    sub.add_parser("register", parents=[common], help="登记合格文件进 manifest(幂等)")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "wiki.config.json").is_file():
        print("错误: --root 未指向实例根(找不到 wiki.config.json):%s" % root,
              file=sys.stderr)
        return 2
    load_config, parse_frontmatter = _import_fm(root)
    try:
        cfg = load_config(root)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("错误: config 载入失败:%s" % e, file=sys.stderr)
        return 2
    pl = _pick_pipeline(cfg, args.pipeline)
    files = _inspect(root, pl, parse_frontmatter)
    m = _load_manifest(root, pl)
    return {"status": cmd_status, "register": cmd_register}[args.cmd](root, pl, files, m, args)


if __name__ == "__main__":
    raise SystemExit(main())
