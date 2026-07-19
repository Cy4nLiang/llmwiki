#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article_fetcher.skeleton — pull 型采集适配器骨架(蒸馏自参考实例 newpj4 的 blog_wiki.py)

合同面(adapters/CONTRACT.md;编写指南 docs/fetcher-contract.md):
  - discover / fetch / status 三子命令分离;--root 必收;
  - manifest 台账 state/<pipeline>.manifest.json(六必填字段;写入经 state/tmp/ 原子替换);
  - raw 文件 = YAML frontmatter + markdown 正文;
  - 幂等可续(已抓跳过 / --force / --limit)、限速退避、自报 UA;
  - 只写 raw/<RAW_SUBDIR>/ + state/;退出码 0/1/2。

使用步骤(详见 docs/fetcher-contract.md):
  1. 拷成 tools/adapters/<name>.py,改「适配器常量」区;
  2. 实现两个 TODO:discover_items()(发现清单)与 fetch_article_body()(抓正文);
  3. wiki.config.json pipelines[] 注册 adapter 字段 → sync 自动接入。

未实现前即可跑通全链路(假数据示范):
    python3 article_fetcher.skeleton.py discover --demo --root <实例根>
    python3 article_fetcher.skeleton.py fetch    --root <实例根>
    python3 article_fetcher.skeleton.py status   --root <实例根> [--json]

依赖:纯 Python 标准库(urllib)。第三方依赖(bs4 等)按 CONTRACT §9 自带声明。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# ── 适配器常量(TODO: 拷贝后逐项改成你的管线;须与 wiki.config.json 对齐)────
PIPELINE = "example-articles"        # = pipelines[].name
RAW_SUBDIR = "raw/example-articles"  # = pipelines[].raw_dir
PREFIX = "ex-"                       # = pipelines[].prefix(只影响 wiki 源页命名,供注释对照)
DEFAULT_KIND = "reference"           # 写进 raw frontmatter kind:(供 sync 分档建议)
LISTING_URL = "https://example.com/blog"          # TODO: 源站清单页/RSS
UA = "llmwiki-adapter/%s (+https://github.com/you/yourwiki) python-urllib" % PIPELINE
DELAY = 1.0                          # 请求间隔秒(限速,CONTRACT §7)
TIMEOUT = 30
RETRIES = 3

# 演示条目(--demo 注入;体验完删掉 raw/state 里的对应产物即可)
DEMO_ITEMS = [
    {"slug": "2026-07-01-demo-hello", "url": "https://example.com/blog/demo-hello",
     "title": "Demo: Hello llmwiki", "date": "2026-07-01"},
    {"slug": "2026-07-15-demo-second", "url": "https://example.com/blog/demo-second",
     "title": "Demo: Second Post", "date": "2026-07-15"},
]


# ── 通用件(一般无需改动)──────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


def today() -> str:
    return date.today().isoformat()


def http_get(url: str) -> str | None:
    """GET 带重试 + 线性退避 + 自报 UA。硬失败返回 None(404 不重试)。"""
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log("    ! %s -> HTTP %s (attempt %d)" % (url, e.code, attempt))
        except (urllib.error.URLError, TimeoutError) as e:
            log("    ! %s -> %s (attempt %d)" % (url, e.__class__.__name__, attempt))
        time.sleep(DELAY * attempt)
    return None


def manifest_path(root: Path) -> Path:
    return root / "state" / ("%s.manifest.json" % PIPELINE)


def load_manifest(root: Path) -> dict:
    p = manifest_path(root)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"pipeline": PIPELINE, "updated": None, "items": {}}


def save_manifest(root: Path, m: dict) -> None:
    """写 state/tmp/ 临时文件后原子替换(CONTRACT §3/§4;抓一条存一次,中断可续)。"""
    m["updated"] = today()
    tmp_dir = root / "state" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / ("%s.manifest.json.tmp" % PIPELINE)
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(manifest_path(root))


def yaml_str(v) -> str:
    return json.dumps(v if v is not None else "", ensure_ascii=False)


def write_raw_article(root: Path, item: dict, body_md: str) -> Path:
    """raw 文件形态(CONTRACT §5):YAML frontmatter + 正文;文件名 = <slug>.md。
    注意 stem 决定源页名 wiki/sources/<PREFIX><stem>.md —— pending 判定靠它对齐。"""
    raw_dir = root / RAW_SUBDIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / ("%s.md" % item["slug"])
    fm = [
        "---",
        "title: %s" % yaml_str(item.get("title") or item["slug"]),
        "slug: %s" % item["slug"],
        "source_url: %s" % (item.get("url") or ""),
        "date_published: %s" % (item.get("date") or ""),
        "date_fetched: %s" % today(),
        "kind: %s" % (item.get("kind") or DEFAULT_KIND),
        "authors: %s" % json.dumps(item.get("authors") or [], ensure_ascii=False),
        "---",
        "",
        "# %s" % (item.get("title") or item["slug"]),
        "",
    ]
    path.write_text("\n".join(fm) + body_md.rstrip() + "\n", encoding="utf-8")
    return path


# ── 抓取实现(两个 TODO:这里是你要写的全部)────────────────────────────────

def discover_items() -> list[dict]:
    """TODO(作者): 抓 LISTING_URL(翻页/RSS),返回条目列表:
        [{"slug": "<date>-<slug>", "url": "...", "title": "...", "date": "YYYY-MM-DD"}, ...]
    要点(参考 newpj4 blog_wiki.discover 的合同面):
      - slug 用 ASCII(小写/数字/连字符),建议带日期前缀保证目录时序;
      - 只发现不抓正文(廉价、可频繁跑);翻页要有安全上限与「连续空页即停」;
      - 返回全量即可,merge 进 manifest 由调用方做(已存在的 slug 不覆盖)。

    示范(伪代码):
        html = http_get(LISTING_URL)
        for m in re.finditer(r'href="/blog/([a-z0-9-]+)"', html): ...
    """
    raise NotImplementedError(
        "discover_items() 未实现 —— 见文件内 TODO 注释;先用 `discover --demo` 体验全链路")


def fetch_article_body(item: dict) -> str | None:
    """TODO(作者): 抓单篇正文,返回 markdown 字符串(失败返回 None)。
    要点(参考 newpj4 blog_wiki.fetch 的合同面):
      - 顺手回填 item["title"] / item["date"] / item["authors"](fetch 后 manifest 必填补齐);
      - 清洗:剥 script/nav/footer 等站点镶边,只留正文;可疑短正文(如 <200 字符)打日志;
      - 非文章页(落地页等)返回 None 并由调用方计 skip,不算失败。

    示范(伪代码):
        html = http_get(item["url"])
        return html_to_markdown(extract_main(html))
    """
    if item["slug"].split("-", 3)[-1].startswith("demo-") or "demo-" in item["slug"]:
        # 假数据示范:让骨架不写一行抓取代码也能端到端跑通
        return ("这是 --demo 注入的假正文,用来演示 raw 文件形态与 manifest 台账。\n\n"
                "- 来源:%s\n- 抓取路径:skeleton demo(与真实路径产物同构,CONTRACT §5)\n"
                % item["url"])
    raise NotImplementedError(
        "fetch_article_body() 未实现 —— 见文件内 TODO 注释")


# ── 子命令 ────────────────────────────────────────────────────────────────

def cmd_discover(args) -> int:
    root = Path(args.root).resolve()
    m = load_manifest(root)
    items = m["items"]
    before = len(items)
    if args.demo:
        found = DEMO_ITEMS
        log("discover: --demo 注入 %d 条演示条目" % len(found))
    else:
        try:
            found = discover_items()
        except NotImplementedError as e:
            log("discover: %s" % e)
            return 0  # 骨架未实现时不算失败,sync 全链路可先跑通
    new = 0
    for it in found:
        if it["slug"] in items:
            continue  # 幂等:已发现的不覆盖(其 fetched/raw_file 状态要保留)
        items[it["slug"]] = {
            "slug": it["slug"], "url": it.get("url") or "",
            "title": it.get("title"), "date": it.get("date"),
            "fetched": None, "raw_file": None,
            "discovered": today(),
        }
        new += 1
    save_manifest(root, m)
    log("discover: 共 %d 条(新 %d)→ %s"
        % (len(items), new, manifest_path(root).relative_to(root)))
    return 0


def cmd_fetch(args) -> int:
    root = Path(args.root).resolve()
    m = load_manifest(root)
    items = m["items"]
    if not items:
        log("fetch: manifest 为空 —— 先跑 discover")
        return 0
    pending = [a for a in items.values()
               if args.force or not a.get("fetched")
               or not (a.get("raw_file") and (root / a["raw_file"]).exists())]
    pending.sort(key=lambda a: a["slug"])
    if args.limit:
        pending = pending[: args.limit]
    log("fetch: 待抓 %d 条(force=%s,总计 %d)" % (len(pending), args.force, len(items)))
    ok = skipped = failed = 0
    for i, a in enumerate(pending, 1):
        log("  [%d/%d] %s" % (i, len(pending), a["slug"]))
        try:
            body = fetch_article_body(a)
        except NotImplementedError as e:
            log("    -> %s" % e)
            failed += 1
            break  # 未实现属结构性失败,不必逐条重复
        if body is None:
            log("    -> 非文章/无正文,跳过")
            skipped += 1
            time.sleep(DELAY)
            continue
        path = write_raw_article(root, a, body)
        a["fetched"] = today()
        a["raw_file"] = str(path.relative_to(root))
        a["chars"] = len(body)
        save_manifest(root, m)   # 抓一条存一次:中断可续(CONTRACT §7)
        log("    -> %s (%d chars)" % (a["raw_file"], len(body)))
        ok += 1
        time.sleep(DELAY)
    log("fetch: done. ok=%d skip=%d fail=%d" % (ok, skipped, failed))
    return 1 if failed else 0


def cmd_status(args) -> int:
    root = Path(args.root).resolve()
    m = load_manifest(root)
    items = m["items"]
    fetched = [a for a in items.values()
               if a.get("fetched") and a.get("raw_file")
               and (root / a["raw_file"]).exists()]
    missing = [a for a in items.values()
               if a.get("fetched") and not (a.get("raw_file")
               and (root / a["raw_file"]).exists())]
    pend = [a for a in items.values() if not a.get("fetched")]
    result = {"ok": not missing, "pipeline": PIPELINE, "updated": m.get("updated"),
              "discovered": len(items), "fetched": len(fetched),
              "pending_fetch": len(pend),
              "manifest_vs_disk_missing": [a["slug"] for a in missing]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        log("pipeline %s · manifest %s" % (PIPELINE, manifest_path(root)))
        log("  updated:       %s" % m.get("updated"))
        log("  discovered:    %d" % len(items))
        log("  fetched:       %d" % len(fetched))
        log("  pending fetch: %d" % len(pend))
        if missing:
            log("  ⚠️ 台账称已抓但 raw 文件缺失:%s"
                % ", ".join(a["slug"] for a in missing[:10]))
    return 0 if result["ok"] else 1


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="pull 型采集适配器骨架(契约见 adapters/CONTRACT.md)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover", parents=[common], help="发现清单 → manifest(不抓正文)")
    d.add_argument("--demo", action="store_true", help="注入演示条目(体验全链路)")
    f = sub.add_parser("fetch", parents=[common], help="抓 pending → raw/(幂等可续)")
    f.add_argument("--limit", type=int, default=None)
    f.add_argument("--force", action="store_true", help="忽略已抓,全量重抓")
    s = sub.add_parser("status", parents=[common], help="零网络计数")
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
