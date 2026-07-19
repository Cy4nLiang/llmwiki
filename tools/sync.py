#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki sync — 管线注册表 orchestrator(采集层单一入口,框架版,frozen)

对应 W-ARCH-2:本工具只**调度**采集与派生重建,自身只读 wiki/,写入发生在:
  - 各管线 adapter(只写 raw/<dir>/ + state/,契约见 adapters/CONTRACT.md);
  - build_site.py / build_index.py(site/ + W-IDX-1 声明的 wiki 内派生物)。
真正的 ingest(写 wiki/ 源页与聚合页)是 agent 的活,本 CLI 不碰。

与参考实例 newpj4 的 tools/sync.py 同骨架,但**去三管线硬编码**:管线来自
wiki.config.json `pipelines[]`(pull / push / rolling 三型,契约见 adapters/CONTRACT.md)。

用法
----
    python3 tools/sync.py [sync] [--root DIR] [--only NAME] [--no-fetch] [--no-build] [--json]
        逐管线采集:pull/rolling 依 config `adapter` 字段跑
        `python3 <adapter> discover --root <root>` 与 `fetch --root <root>`
        (缺 adapter 声明/文件 → 警告跳过);push 型免抓取。
        然后 build_site.py + build_index.py 重建派生物,跑 lint --manifest
        (W-UPG-1 常跑),最后打印分管线 pending 积压与分档建议。

    python3 tools/sync.py status  [--root DIR] [--json]     # 零网络:分管线库存/源页/pending
    python3 tools/sync.py pending [--root DIR] [--json]     # 零网络:只打印待 ingest 清单

pending 判定(持久重算,不依赖一次性台账;详细约定见 adapters/CONTRACT.md §6)
----------------------------------------------------------------------
  - pull / push:raw_dir 顶层内容文件(*.md / *.txt,排除 `_` 开头与 `*.dated.*`
    派生件)其期望源页 `wiki/sources/<prefix><stem>.md` 不存在 → pending;
  - rolling:快照 sha256 与源页 frontmatter `rolling_digest` 不一致(或源页
    缺失 / 缺 digest 字段)→ pending(reason = digest-changed | no-source-page | no-digest)。

分档建议:读 raw 文件 frontmatter `kind:`(或 `source_kind:`),经 config
`ingest_tiers.by_source_kind` 映射到 full|light;缺失时回退管线唯一 source_kind,
再回退 `ingest_tiers.default`。仅是建议,用户可逐篇覆盖(W-ING-1 下限随档)。

退出码
------
  0 = 同步/查询完成(pending 积压属正常待办状态,不算问题)
  1 = 某管线 adapter 抓取失败,或派生重建(build_site/build_index)失败
  2 = 用法或配置错误(config 非法、--only 指了不存在的管线、lib/fm 缺失)
lint --manifest 的发现(fork 警告等)打印为警告并写入 JSON(lint_ok=false),
不改变退出码 —— 机械同步本身已完成,发现项留给 agent 处置。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
try:
    from lib.fm import load_config, parse_frontmatter  # 单源:builder F1 的 lib/fm.py
except ImportError as e:  # pragma: no cover
    print("错误: 无法导入 tools/lib/fm.py(frontmatter/config 单一实现):%s" % e,
          file=sys.stderr)
    sys.exit(2)

PY = sys.executable
CONTENT_EXTS = {".md", ".txt"}
DIGEST_FIELD = "rolling_digest"
FM_READ_LIMIT = 65536          # 读 raw 文件头部提取 frontmatter 的上限(字符)
PREVIEW_N = 40                 # 终端 pending 预览条数上限


# ── 基础 ──────────────────────────────────────────────────────────────────

def _die(code: int, msg: str) -> None:
    print("错误: %s" % msg, file=sys.stderr)
    sys.exit(code)


def _say(quiet: bool, msg: str) -> None:
    """人读诊断:--json 模式下走 stderr,保证 stdout 只有纯 JSON。"""
    print(msg, file=sys.stderr if quiet else sys.stdout)


def _load_cfg(root: Path) -> dict:
    try:
        return load_config(root)
    except SystemExit:
        raise
    except FileNotFoundError as e:
        _die(2, "找不到 wiki.config.json(root=%s):%s" % (root, e))
    except Exception as e:  # noqa: BLE001 — load_config 的报错形态由 lib/fm 决定
        _die(2, "config 载入失败:%s" % e)
    raise AssertionError  # unreachable


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _head_meta(path: Path) -> dict:
    """只读文件头部提取 frontmatter meta(raw 可能很大,不整读)。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            head = f.read(FM_READ_LIMIT)
    except OSError:
        return {}
    meta, _ = parse_frontmatter(head)
    return meta


def _content_files(raw_dir: Path) -> list[Path]:
    """管线 raw_dir 顶层内容文件(pending 计算的分母;约定见 CONTRACT §6):
    *.md / *.txt;排除 `_` 开头(元数据,如 _meta.json 同类)与 `*.dated.*`
    派生件(rolling 的 dated 视图);子目录(assets/ 等)不参与。"""
    if not raw_dir.is_dir():
        return []
    out = []
    for p in sorted(raw_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in CONTENT_EXTS:
            continue
        if p.name.startswith("_"):
            continue
        if p.stem.endswith(".dated"):    # foo.dated.md → stem "foo.dated"
            continue
        out.append(p)
    return out


def _digest_matches(declared, actual: str) -> bool:
    """源页 rolling_digest vs 快照 sha256。允许 `sha256:` 前缀与 ≥12 位十六进制
    前缀缩写(约定见 CONTRACT §6.3)。"""
    if not isinstance(declared, str):
        return False
    d = declared.strip().lower()
    if d.startswith("sha256:"):
        d = d[len("sha256:"):]
    if not d:
        return False
    if len(d) < 12:
        return False
    return actual.lower() == d or actual.lower().startswith(d)


# ── 分档建议 ──────────────────────────────────────────────────────────────

def _source_kind_of(raw_path: Path, pl: dict) -> str | None:
    meta = _head_meta(raw_path)
    kind = meta.get("kind") or meta.get("source_kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()
    sks = pl.get("source_kinds") or []
    if len(sks) == 1:
        return sks[0]
    return None


def _suggest_tier(kind: str | None, tiers: dict) -> str:
    if kind and kind in tiers.get("by_source_kind", {}):
        return tiers["by_source_kind"][kind]
    return tiers.get("default", "full")


# ── pending 计算(status / pending / sync 共用;serve 等下游也可 import)──

def pipeline_pending(root: Path, pl: dict, tiers: dict) -> dict:
    """单管线库存 + pending。返回
    {name, kind, raw_dir, prefix, adapter, raw_count, ingested_count,
     pending_count, pending: [{raw_file, expected_source, source_kind, tier, reason}]}"""
    raw_dir = root / pl["raw_dir"]
    prefix = pl.get("prefix") or ""
    sources_dir = root / "wiki" / "sources"
    files = _content_files(raw_dir)
    pending: list[dict] = []
    ingested = 0
    for p in files:
        expected = sources_dir / ("%s%s.md" % (prefix, p.stem))
        reason = None
        if not expected.exists():
            reason = "no-source-page"
        elif pl["kind"] == "rolling":
            meta = _head_meta(expected)
            declared = meta.get(DIGEST_FIELD)
            if declared is None:
                reason = "no-digest"
            elif not _digest_matches(declared, _sha256(p)):
                reason = "digest-changed"
        if reason is None:
            ingested += 1
            continue
        kind = _source_kind_of(p, pl)
        pending.append({
            "pipeline": pl["name"],
            "raw_file": str(p.relative_to(root)),
            "expected_source": "wiki/sources/%s%s.md" % (prefix, p.stem),
            "source_kind": kind,
            "tier": _suggest_tier(kind, tiers),
            "reason": reason,
        })
    pending.sort(key=lambda x: x["raw_file"], reverse=True)
    return {"name": pl["name"], "kind": pl["kind"], "raw_dir": pl["raw_dir"],
            "prefix": prefix, "adapter": pl.get("adapter"),
            "raw_count": len(files), "ingested_count": ingested,
            "pending_count": len(pending), "pending": pending}


def all_pending(root: Path, cfg: dict, only: str | None = None) -> list[dict]:
    pls = cfg["pipelines"]
    if only is not None:
        pls = [p for p in pls if p["name"] == only]
    tiers = cfg.get("ingest_tiers", {})
    return [pipeline_pending(root, pl, tiers) for pl in pls]


# ── 子进程封装 ────────────────────────────────────────────────────────────

def _run(cmd: list[str], root: Path, label: str, timeout: int = 3600,
         quiet: bool = False) -> tuple[int | None, str]:
    """跑一个子命令,捕获输出回传尾部日志。返回 (returncode, tail);异常时 rc=None。"""
    if not quiet:
        print("  → %s: %s" % (label, " ".join(cmd[1:] if cmd[0] == PY else cmd)))
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                           timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, "%s: %s" % (e.__class__.__name__, e)
    tail = (r.stdout or "")[-1200:]
    if r.stderr and r.stderr.strip():
        tail += "\n[stderr] " + r.stderr.strip()[-600:]
    return r.returncode, tail.strip()


# ── 采集阶段 ──────────────────────────────────────────────────────────────

def fetch_pipeline(root: Path, pl: dict, quiet: bool) -> dict:
    """按契约驱动单管线采集。push 免抓取;pull/rolling 跑 adapter discover+fetch。"""
    name, kind = pl["name"], pl["kind"]
    res: dict = {"name": name, "kind": kind, "ran": False, "ok": True}
    if kind == "push":
        res["skipped"] = "push 型:人/CI 直投 raw,免抓取"
        return res
    adapter = pl.get("adapter")
    if not adapter:
        res["skipped"] = "未声明 adapter(config pipelines[].adapter)→ 跳过"
        res["warning"] = True
        return res
    apath = (root / adapter).resolve()
    if not apath.is_file():
        res["skipped"] = "adapter 文件不存在:%s → 跳过" % adapter
        res["warning"] = True
        return res
    res["ran"] = True
    logs = []
    for sub, tmo in (("discover", 900), ("fetch", 3600)):
        rc, tail = _run([PY, str(apath), sub, "--root", str(root)],
                        root, "%s %s" % (name, sub), timeout=tmo, quiet=quiet)
        res["%s_rc" % sub] = rc
        logs.append(tail)
        if rc != 0:
            res["ok"] = False
            _say(quiet, "    ✗ %s %s 失败(rc=%s)" % (name, sub, rc))
            if tail:
                _say(quiet, "      " + "\n      ".join(tail.splitlines()[-8:]))
            break
    res["log"] = "\n".join(x for x in logs if x)
    return res


# ── 派生重建 + lint ───────────────────────────────────────────────────────

def rebuild_derived(root: Path, quiet: bool) -> dict:
    """build_site.py + build_index.py(W-IDX-1/W-IDX-2:人读 index 与机器 jsonl
    同一次 build 产出)。工具未就位(并行开发期)→ 警告跳过,不算失败。"""
    out: dict = {"ok": True}
    for tool in ("build_site.py", "build_index.py"):
        tpath = TOOLS_DIR / tool
        if not tpath.is_file():
            out[tool] = {"rc": None, "skipped": "工具未就位"}
            _say(quiet, "  (%s 未就位,跳过)" % tool)
            continue
        rc, tail = _run([PY, str(tpath), "--root", str(root)], root,
                        tool.replace(".py", ""), timeout=600, quiet=quiet)
        out[tool] = {"rc": rc}
        if rc != 0:
            out["ok"] = False
            _say(quiet, "    ✗ %s 失败(rc=%s)" % (tool, rc))
            if tail:
                _say(quiet, "      " + "\n      ".join(tail.splitlines()[-8:]))
    return out


def run_manifest_lint(root: Path, quiet: bool) -> dict:
    """lint --manifest(W-UPG-1 常跑:frozen 文件 hash 校验,fork 警告)。
    exit 0 = 干净;1 = 有发现(警告呈现,不阻断);2 = 该 lint 版本不支持
    --manifest(M1 精简版)→ 视为不可用。"""
    lint = TOOLS_DIR / "lint_wiki.py"
    if not lint.is_file():
        return {"available": False, "note": "lint_wiki.py 未就位"}
    rc, tail = _run([PY, str(lint), "--manifest", "--root", str(root)], root,
                    "lint --manifest", timeout=300, quiet=quiet)
    if rc == 0:
        return {"available": True, "lint_ok": True}
    if rc == 1:
        _say(quiet, "  ⚠️ lint --manifest 有发现(W-UPG-1 fork 警告等)——"
                    "跑 python3 tools/lint_wiki.py --manifest 看明细")
        if tail:
            _say(quiet, "      " + "\n      ".join(tail.splitlines()[-8:]))
        return {"available": True, "lint_ok": False, "tail": tail}
    return {"available": False, "rc": rc,
            "note": "lint --manifest 不可用(rc=%s;或为 M1 精简版 lint)" % rc}


# ── 报告 ──────────────────────────────────────────────────────────────────

def _print_pipeline_pending(st: dict) -> None:
    extra = ""
    if st["kind"] == "rolling" and st["pending"]:
        extra = "(" + " · ".join(sorted({p["reason"] for p in st["pending"]})) + ")"
    print("  管线 %-12s(%-7s):raw 库存 %d · 已 ingest %d · pending %d %s"
          % (st["name"], st["kind"], st["raw_count"], st["ingested_count"],
             st["pending_count"], extra))


def _print_pending_list(stats: list[dict], limit: int = PREVIEW_N) -> None:
    flat = [p for st in stats for p in st["pending"]]
    if not flat:
        print("  ✅ 没有待 ingest —— wiki 已覆盖所有已采集内容。")
        return
    shown = 0
    for st in stats:
        for p in st["pending"]:
            if shown >= limit:
                print("    … 还有 %d 条(--json 看全量)" % (len(flat) - shown))
                return
            kind = p["source_kind"] or "?"
            print("    [%-10s] %s  →  %s  [%s→%s]%s"
                  % (p["pipeline"], p["raw_file"], p["expected_source"],
                     kind, p["tier"],
                     "" if p["reason"] == "no-source-page" else "  (%s)" % p["reason"]))
            shown += 1


def _print_next_step(stats: list[dict]) -> None:
    total = sum(st["pending_count"] for st in stats)
    if not total:
        return
    light = sum(1 for st in stats for p in st["pending"] if p["tier"] == "light")
    print("\n" + "─" * 60)
    print("  下一步(agent / 在会话里继续):")
    print("    pending 共 %d 篇(建议 light %d / full %d)。"
          % (total, light, total - light))
    print("    ≤3 篇逐篇走 wiki-ingest;≥10 篇走 bulk map-reduce(W-ING-2);")
    print("    light 档必记 followups「待晋升」(W-ING-1);rolling 刷新走滚动源特例,"
          "变化记「演进」(W-ING-3)。")


# ── 子命令 ────────────────────────────────────────────────────────────────

def _select_only(cfg: dict, only: str | None) -> None:
    if only is None:
        return
    names = [p["name"] for p in cfg["pipelines"]]
    if only not in names:
        _die(2, "--only=%s 不在管线注册表(可选:%s)" % (only, ", ".join(names)))


def cmd_sync(args) -> tuple[dict, int]:
    root = Path(args.root).resolve()
    cfg = _load_cfg(root)
    _select_only(cfg, args.only)
    pls = cfg["pipelines"] if args.only is None else \
        [p for p in cfg["pipelines"] if p["name"] == args.only]

    quiet = args.json
    if not quiet:
        print("=" * 60)
        print("  llmwiki sync — 管线注册表同步(采集层;不碰 wiki/)")
        print("  root=%s · %d 管线%s" % (root, len(pls),
              "(--only=%s)" % args.only if args.only else ""))
        print("=" * 60)

    result: dict = {"ok": True, "root": str(root), "date": date.today().isoformat(),
                    "fetch": [], "build": None, "lint": None}

    # 1) 逐管线采集
    if args.no_fetch:
        if not quiet:
            print("\n[fetch] --no-fetch:跳过采集阶段")
    else:
        for i, pl in enumerate(pls, 1):
            if not quiet:
                print("\n[%d/%d] 管线 %s(%s)…" % (i, len(pls), pl["name"], pl["kind"]))
            r = fetch_pipeline(root, pl, quiet)
            if r.get("skipped") and not quiet:
                mark = "⚠️ " if r.get("warning") else ""
                print("      %s%s" % (mark, r["skipped"]))
            result["fetch"].append(r)
            if not r["ok"]:
                result["ok"] = False

    # 2) 派生重建(W-IDX-1/W-IDX-2)
    if not args.no_build:
        if not quiet:
            print("\n[site] 重建派生物 …")
        result["build"] = rebuild_derived(root, quiet)
        if not result["build"]["ok"]:
            result["ok"] = False

    # 3) lint --manifest(W-UPG-1 常跑;发现≠失败)
    if not quiet:
        print("\n[lint] W-UPG-1 manifest 校验 …")
    result["lint"] = run_manifest_lint(root, quiet)

    # 4) pending 报告 + 分档建议
    stats = all_pending(root, cfg, args.only)
    result["pipelines"] = stats
    result["pending_total"] = sum(st["pending_count"] for st in stats)
    if not quiet:
        print("\n" + "=" * 60)
        print("  待 ingest 积压 / pending(持久重算)")
        print("=" * 60)
        for st in stats:
            _print_pipeline_pending(st)
        print()
        _print_pending_list(stats)
        _print_next_step(stats)
    return result, (0 if result["ok"] else 1)


def cmd_status(args) -> tuple[dict, int]:
    root = Path(args.root).resolve()
    cfg = _load_cfg(root)
    _select_only(cfg, getattr(args, "only", None))
    stats = all_pending(root, cfg, getattr(args, "only", None))
    result = {"ok": True, "root": str(root), "pipelines": stats,
              "pending_total": sum(st["pending_count"] for st in stats)}
    if not args.json:
        print("=" * 60)
        print("  状态 / status(零网络)· root=%s" % root)
        print("=" * 60)
        for st in stats:
            _print_pipeline_pending(st)
            for p in st["pending"][:5]:
                print("      · %s  [%s→%s]" % (p["raw_file"],
                      p["source_kind"] or "?", p["tier"]))
            if st["pending_count"] > 5:
                print("      … 还有 %d 条" % (st["pending_count"] - 5))
    return result, 0


def cmd_pending(args) -> tuple[dict, int]:
    root = Path(args.root).resolve()
    cfg = _load_cfg(root)
    _select_only(cfg, getattr(args, "only", None))
    stats = all_pending(root, cfg, getattr(args, "only", None))
    flat = [p for st in stats for p in st["pending"]]
    result = {"ok": True, "root": str(root), "pending": flat,
              "pending_total": len(flat)}
    if not args.json:
        _print_pending_list(stats)
        _print_next_step(stats)
    return result, 0


# ── CLI ──────────────────────────────────────────────────────────────────

KNOWN_CMDS = {"sync", "status", "pending"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sync.py",
        description="llmwiki — 管线注册表同步(采集层 CLI;管线来自 wiki.config.json)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="机器可读输出(给 agent 解析)")
    common.add_argument("--only", default=None, metavar="NAME",
                        help="只处理这一条管线(config pipelines[].name)")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("sync", parents=[common],
                       help="逐管线采集 + 派生重建 + lint --manifest + pending 报告(默认)")
    s.add_argument("--no-fetch", action="store_true", help="跳过采集阶段(仍重建/体检/报积压)")
    s.add_argument("--no-build", action="store_true", help="跳过派生重建")
    sub.add_parser("status", parents=[common], help="零网络:分管线库存/源页/pending")
    sub.add_parser("pending", parents=[common], help="零网络:只打印待 ingest 清单")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 无子命令时默认 sync(全局旗标归到 sync 下);裸 -h/--help 留给顶层列出子命令
    if not any(tok in KNOWN_CMDS for tok in argv) and not ({"-h", "--help"} & set(argv)):
        argv = ["sync", *argv]
    args = build_parser().parse_args(argv)
    args.json = getattr(args, "json", False)
    dispatch = {"sync": cmd_sync, "status": cmd_status, "pending": cmd_pending}
    result, rc = dispatch[args.cmd](args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
