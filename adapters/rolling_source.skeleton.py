#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rolling_source.skeleton — rolling 型采集适配器骨架(蒸馏自参考实例 newpj4 的 cc_changelog.py)

rolling 源 = 一份**滚动文档**(CHANGELOG、团队规范、runbook 总纲):每次 fetch 对
faithful 快照**同名整体覆盖**(历史由 git 承载),并派生 dated 视图 —— 这是与 pull 型
「逐篇累加」的本质区别。合同面(adapters/CONTRACT.md §6):
  - faithful 快照 = 上游原样拷贝(不注 frontmatter、不清洗):raw/<dir>/<DOC_SLUG>.md;
  - dated 派生 = 纯变换的注日期/注版本视图:raw/<dir>/<DOC_SLUG>.dated.md(不算内容文件);
  - 抓取元信息(fetched_at / source_url / sha256 / 版本计数)写 raw/<dir>/_meta.json;
  - manifest 台账 state/<pipeline>.manifest.json 只有一条 item(该文档本身);
  - pending 判定:快照 sha256 vs 源页 frontmatter `rolling_digest`(CONTRACT §6.3);
    digest 变化 → agent 走「刷新滚动源页」特例(变化记「演进」,W-ING-3)。

使用步骤:拷成 tools/adapters/<name>.py → 改常量区 → 实现 fetch_snapshot()
(与可选的 derive_dated() 辅助数据)→ pipelines[] 注册。未实现前的假数据示范:
    python3 rolling_source.skeleton.py fetch  --demo --root <实例根>
    python3 rolling_source.skeleton.py status --root <实例根> [--json]

依赖:纯 Python 标准库。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# ── 适配器常量(TODO: 拷贝后逐项改;须与 wiki.config.json 对齐)─────────────
PIPELINE = "example-rolling"          # = pipelines[].name
RAW_SUBDIR = "raw/example-rolling"    # = pipelines[].raw_dir
PREFIX = "roll-"                      # = pipelines[].prefix(源页名 <PREFIX><DOC_SLUG>.md)
DOC_SLUG = "example-handbook"         # faithful 快照文件名 <DOC_SLUG>.md
DOC_TITLE = "Example Handbook"
SOURCE_URL = "https://example.com/handbook/raw.md"   # TODO: 上游原文 URL
UA = "llmwiki-adapter/%s (+https://github.com/you/yourwiki) python-urllib" % PIPELINE
TIMEOUT = 30
RETRIES = 3

# 滚动文档里的「版本标题」样式(dated 派生用;不适用就留 None)
VERSION_RE = re.compile(r"^##\s+(\d+\.\d+\.\d+\S*)\s*$")

DEMO_SNAPSHOT = """# Example Handbook

## 1.1.0

- Added: 第二个演示版本(--demo 注入)

## 1.0.0

- Initial: 第一个演示版本
"""


# ── 通用件 ────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


def today() -> str:
    return date.today().isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_get(url: str) -> str:
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            log("  retry %d/%d: %s" % (attempt, RETRIES, e))
            time.sleep(1.0 * attempt)
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (RETRIES, url, last))


def paths(root: Path) -> dict:
    raw_dir = root / RAW_SUBDIR
    return {
        "raw_dir": raw_dir,
        "faithful": raw_dir / ("%s.md" % DOC_SLUG),
        "dated": raw_dir / ("%s.dated.md" % DOC_SLUG),
        "meta": raw_dir / "_meta.json",
        "manifest": root / "state" / ("%s.manifest.json" % PIPELINE),
    }


def save_manifest(root: Path, item: dict) -> None:
    """单条 item 的台账;写 state/tmp/ 后原子替换(CONTRACT §3/§4)。"""
    m = {"pipeline": PIPELINE, "updated": today(), "items": {item["slug"]: item}}
    tmp_dir = root / "state" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / ("%s.manifest.json.tmp" % PIPELINE)
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(paths(root)["manifest"])


# ── 抓取与派生(TODO 区:这里是你要写的全部)──────────────────────────────

def fetch_snapshot() -> str:
    """TODO(作者): 抓上游滚动文档全文,原样返回(faithful:不清洗、不注 frontmatter)。
    参考 newpj4 cc_changelog:一手来源可以是 raw.githubusercontent、导出 API 等。

    示范:
        return http_get(SOURCE_URL)
    """
    raise NotImplementedError(
        "fetch_snapshot() 未实现 —— 见 TODO 注释;先用 `fetch --demo` 体验全链路")


def aux_dates() -> dict[str, str]:
    """TODO(作者,可选): 版本号 → 日期 的辅助映射,供 dated 派生注日期。
    参考 newpj4 cc_changelog:CHANGELOG 自身无日期,用 `npm view <pkg> time --json`
    补齐。没有此类辅助数据就返回 {}(dated 视图仅加生成横幅)。"""
    return {}


def derive_dated(faithful: str, dates: dict[str, str]) -> str:
    """dated 派生 = 纯变换:版本标题 `## X.Y.Z` 注成 `## X.Y.Z — YYYY-MM-DD`,
    并在文件头加生成横幅。faithful 原文永不改动(CONTRACT §6.2)。"""
    out = ["<!-- derived dated view; generated from faithful %s.md; 手编无效,重跑 fetch -->"
           % DOC_SLUG]
    for line in faithful.splitlines():
        m = VERSION_RE.match(line) if VERSION_RE else None
        if m and dates.get(m.group(1)):
            out.append("## %s — %s" % (m.group(1), dates[m.group(1)]))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


# ── 子命令 ────────────────────────────────────────────────────────────────

def cmd_discover(args) -> int:
    """rolling 的 discover 是轻量新鲜度检查(可选实现):比对远端与本地快照是否有差,
    只打印不落盘。TODO(作者): 有条件时用 ETag/Last-Modified/HEAD 少抓全文。
    未实现时为 no-op(exit 0)—— sync 对 rolling 管线也会调用 discover,必须能空转。"""
    P = paths(Path(args.root).resolve())
    if not P["faithful"].exists():
        log("discover: 尚无本地快照 —— 直接跑 fetch")
        return 0
    log("discover: rolling 源以 fetch 整体覆盖为准(TODO: 可实现远端新鲜度预检)")
    return 0


def cmd_fetch(args) -> int:
    root = Path(args.root).resolve()
    P = paths(root)
    P["raw_dir"].mkdir(parents=True, exist_ok=True)
    if args.demo:
        text = DEMO_SNAPSHOT
        dates = {"1.1.0": "2026-07-15", "1.0.0": "2026-07-01"}
        log("fetch: --demo 使用演示快照")
    else:
        try:
            text = fetch_snapshot()
        except NotImplementedError as e:
            log("fetch: %s" % e)
            return 0  # 骨架未实现不算失败;真实现里抓取硬失败应 return 1
        except RuntimeError as e:
            log("fetch: 失败:%s" % e)
            return 1
        dates = aux_dates()

    # 1) faithful 同名整体覆盖(唯一被允许的 raw 覆写,历史由 git 承载)
    P["faithful"].write_text(text, encoding="utf-8")
    digest = sha256_text(text)
    versions = VERSION_RE and [m.group(1) for line in text.splitlines()
                               if (m := VERSION_RE.match(line))] or []
    log("  -> %s (%d chars, %d versions)"
        % (P["faithful"].relative_to(root), len(text), len(versions)))

    # 2) dated 派生(纯变换,不算内容文件)
    P["dated"].write_text(derive_dated(text, dates), encoding="utf-8")
    log("  -> %s (dated 派生视图)" % P["dated"].relative_to(root))

    # 3) _meta.json:抓取元信息 + sha256(pending 判定的 digest 权威记录)
    meta = {
        "fetched_at": today(), "source_url": SOURCE_URL, "sha256": digest,
        "chars": len(text), "versions": len(versions),
        "latest_version": versions[0] if versions else None,
    }
    P["meta"].write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log("  -> %s" % P["meta"].relative_to(root))

    # 4) manifest 台账(单条 item;六必填字段见 CONTRACT §4)
    save_manifest(root, {
        "slug": DOC_SLUG, "url": SOURCE_URL, "title": DOC_TITLE,
        "date": today(), "fetched": today(),
        "raw_file": str(P["faithful"].relative_to(root)), "sha256": digest,
    })
    log("fetch: done. sha256=%s…(源页 frontmatter rolling_digest 与之比对)" % digest[:16])
    return 0


def cmd_status(args) -> int:
    root = Path(args.root).resolve()
    P = paths(root)
    if not P["faithful"].exists():
        log("status: 尚无快照 —— 先跑 fetch(或 fetch --demo)")
        return 1
    meta = json.loads(P["meta"].read_text(encoding="utf-8")) if P["meta"].exists() else {}
    digest = sha256_text(P["faithful"].read_text(encoding="utf-8"))
    source_page = root / "wiki" / "sources" / ("%s%s.md" % (PREFIX, DOC_SLUG))
    result = {"ok": True, "pipeline": PIPELINE, "doc": DOC_SLUG,
              "fetched_at": meta.get("fetched_at"),
              "latest_version": meta.get("latest_version"),
              "sha256": digest,
              "expected_source": str(source_page.relative_to(root))}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        log("pipeline %s · 快照 %s" % (PIPELINE, P["faithful"].relative_to(root)))
        log("  fetched_at:      %s" % meta.get("fetched_at"))
        log("  latest_version:  %s" % meta.get("latest_version"))
        log("  sha256:          %s" % digest)
        log("  期望源页:        %s(其 frontmatter rolling_digest 应与上行一致,"
            "允许 ≥12 位前缀;不一致即 pending)" % result["expected_source"])
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="rolling 型采集适配器骨架(契约见 adapters/CONTRACT.md §6)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover", parents=[common], help="轻量新鲜度预检(可 no-op)")
    f = sub.add_parser("fetch", parents=[common],
                       help="整体覆盖 faithful + 派生 dated + 记 _meta/manifest")
    f.add_argument("--demo", action="store_true", help="用演示快照体验全链路")
    s = sub.add_parser("status", parents=[common], help="零网络:快照信息 + sha256")
    s.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root)
    if not (root / "wiki.config.json").is_file():
        print("错误: --root 未指向实例根(找不到 wiki.config.json):%s" % root.resolve(),
              file=sys.stderr)
        return 2
    return {"discover": cmd_discover, "fetch": cmd_fetch, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
