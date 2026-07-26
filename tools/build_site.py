#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki build_site — 站点数据 + agent 机器索引派生(M2,仅 Python 标准库)

从实例的管线 manifest 与 wiki/ 各页 frontmatter 聚合,同一次 build 产出双轨(W-IDX-2):
  site/data.json                  阅读器数据(字段尽量与参考实例 newpj4 兼容)
  site/agent/sources.jsonl        来源机器索引(每行一条,含 page_tokens 预估)
  site/agent/pages.jsonl          聚合页 + 查询页机器索引(每行一条,含 tokens 预估)
  site/agent/search-index.json    排名检索索引(BM25;W-IDX-3,构建/查询单源 = lib/textindex,
                                  tools/search.py 消费;覆盖 wiki 根页+五子目录全文)
  site/agent/graph.json           链接图谱(W-IDX-4;lib/wikigraph 确定性 wikilink 边表,
                                  节点=非派生非 log 页;供社区/中心/孤立分析,不做语义推断边)

数据来源(全部 config 驱动,移植自参考实例 newpj4 tools/build_site.py 并去 domain 化):
  - 每条管线优先读 state/<name>.manifest.json(fetcher 契约§7:slug/url/title/date/fetched/raw_file);
  - 缺 manifest 的 push 管线从 raw 目录 frontmatter 直读(直投/CI 免适配器);
  - 缺 manifest 的 rolling 管线从 wiki/sources/ 内 raw_file 指向该管线 raw_dir 的源页反推
    (newpj4 changelog 特例的通用化;faithful 快照存在 <stem>.dated.md 派生时优先展示后者);
  - 缺 manifest 的 pull 管线跳过并告警(适配器尚未运行)。

与 newpj4 的去 domain 化差异:
  - CLUSTERS/KIND_LABEL 中文标签/raw/blog_zn 双语路径/单管线 manifest 假设全部删除;
  - source_kind 标签 = config 枚举原文(kind_label 恒等映射,阅读器直接显示枚举值);
  - **cluster 属实例可选约定,v1 不入框架**:产出不含 cluster 字段
    (实例要用 → tags 约定 + x-extensions 自行扩展,勿改本 frozen 工具);
  - vendor 硬编码由 config `facets[]` 泛化:每个 facet key 直接成为条目字段
    (值优先取页面 frontmatter `<key>:`,聚合页退回 tags 约定 `cross-<key>` / `<key>-<value>`);
  - file_zh/title_zh 保留为双语槽位(extras/i18n_link 增强填充;核心默认 None/"")。

确定性(可复现构建):articles 按 date 降序、同日按 src_slug 升序;wiki 页按文件名;
计数字典按键排序;不写时间戳(data.json "generated" 恒为 "");内容未变不重写(mtime 不污染)。

写入边界(W-ARCH-2):只写 site/;只读 wiki.config.json、state/、raw/、wiki/。

用法:
    python3 tools/build_site.py [--root <实例根>] [--json]
退出码:0 = OK;1 = 发现问题(manifest 损坏/结构不识别等);2 = 配置与用法错误。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import fm  # noqa: E402(钉死单源:frontmatter/est_tokens/config 载入)
from lib import textindex  # noqa: E402(检索索引构建/查询单源,W-IDX-3)
from lib import wikigraph  # noqa: E402(图谱/派生物判定单源,W-IDX-4)

WIKI_KINDS = ("syntheses", "concepts", "entities", "queries")
# TL;DR 节:框架冻结骨架段名「## 一句话摘要 / TL;DR」(W-ING-4);容忍任一写法
_TLDR_RE = re.compile(r"^##[^\n]*(?:TL;DR|一句话摘要)[^\n]*\n(.+?)(?=\n#|\Z)",
                      re.S | re.M | re.I)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

_ARTICLE_RESERVED = {"src_slug", "slug", "pipeline", "file_en", "file_zh", "title_en",
                     "title_zh", "date", "year", "description", "authors", "source_kind",
                     "tldr", "chars", "url", "wiki_source"}
_PAGE_RESERVED = {"slug", "file", "title", "summary", "status", "tokens"}


# ---------------------------------------------------------------- 小工具

def clean(s) -> str:
    return html.unescape(s or "").strip()


def _scalar(v) -> str:
    """frontmatter/manifest 值 → 标量字符串(列表取首项;None → "")。"""
    if v is None:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v).strip()


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return [clean(str(x)) for x in v if clean(str(x))]
    s = clean(str(v))
    return [s] if s else []


def _first(*vals) -> str:
    for v in vals:
        s = _scalar(v)
        if s:
            return s
    return ""


def norm_raw_path(p) -> str:
    """manifest / frontmatter 内 raw 路径归一为实例根相对(剥 ../../ 等前导段)。"""
    s = _scalar(p).replace("\\", "/")
    i = s.find("raw/")
    return s[i:] if i >= 0 else s


def tldr_of(body: str) -> str:
    m = _TLDR_RE.search(body or "")
    if not m:
        return ""
    for ln in m.group(1).splitlines():
        ln = clean(ln)
        if ln:
            return ln
    return ""


def _read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _write_if_changed(path: Path, text: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.write_text(text, encoding="utf-8")
    return True


# ---------------------------------------------------------------- 管线条目收集

def load_manifest_entries(path: Path, problems: list) -> list:
    """宽容读取 manifest:{"articles": {slug: {...}}} / {"articles": [...]} /
    顶层 dict(slug 键)/ 顶层 list 均可;条目缺 slug 时以键补齐。排序确定。"""
    text = _read_text(path)
    if text is None:
        problems.append("manifest 读取失败:%s" % path)
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        problems.append("manifest 不是合法 JSON:%s(:%d %s)" % (path, e.lineno, e.msg))
        return []
    if isinstance(data, dict) and isinstance(data.get("articles"), (dict, list)):
        data = data["articles"]
    if isinstance(data, dict):
        entries = []
        for key in sorted(data):
            e = data[key]
            if isinstance(e, dict):
                e = dict(e)
                e.setdefault("slug", key)
                entries.append(e)
        return entries
    if isinstance(data, list):
        return [dict(e) for e in data if isinstance(e, dict)]
    problems.append("manifest 结构不识别(非 dict/list):%s" % path)
    return []


def scan_push_raw(root: Path, pipeline: dict) -> list:
    """push 管线免 manifest:raw 目录 *.md frontmatter 直读(W-CAP-1:title/date/kind)。"""
    entries = []
    d = root / pipeline["raw_dir"]
    if not d.is_dir():
        return entries
    for f in sorted(d.glob("*.md")):
        text = _read_text(f)
        if text is None:
            continue
        meta, _body = fm.parse_frontmatter(text)
        m = _DATE_RE.search(f.stem)
        entries.append({
            "slug": _first(meta.get("slug")) or f.stem,
            "title": _first(meta.get("title")) or f.stem,
            "date": _first(meta.get("date"), meta.get("date_published")) or (m.group(0) if m else ""),
            "url": _first(meta.get("source_url"), meta.get("url")),
            "raw_file": "%s/%s" % (pipeline["raw_dir"], f.name),
            "fetched": True,
            "kind": _first(meta.get("kind"), meta.get("source_kind")),
            "description": _first(meta.get("description")),
            "authors": _as_list(meta.get("authors")),
            "chars": len(text),
        })
    return entries


def scan_rolling_sources(root: Path, wiki: Path, pipeline: dict) -> list:
    """rolling 管线免 manifest:从 wiki/sources/ 内 raw_file 落在该管线 raw_dir 的源页反推
    (一份源页代表整份滚动源;源页 stem 可与 raw stem 不同,经 wiki_page 显式携带)。"""
    entries = []
    sdir = wiki / "sources"
    if not sdir.is_dir():
        return entries
    prefix = pipeline["raw_dir"].rstrip("/") + "/"
    for f in sorted(sdir.glob("*.md")):
        text = _read_text(f)
        if text is None:
            continue
        meta, _body = fm.parse_frontmatter(text)
        raw_file = norm_raw_path(meta.get("raw_file"))
        if not raw_file.startswith(prefix):
            continue
        entries.append({
            "slug": f.stem,
            "title": _first(meta.get("title")) or f.stem,
            "date": _first(meta.get("date_published"), meta.get("date_ingested")),
            "url": _first(meta.get("source_url")),
            "raw_file": raw_file,
            "fetched": True,
            "kind": _first(meta.get("source_kind")),
            "authors": _as_list(meta.get("authors")),
            "wiki_page": f.stem,
        })
    return entries


# ---------------------------------------------------------------- 文章装配

def make_article(root: Path, wiki: Path, pipeline: dict, e: dict,
                 facets: list, profile: str, page_tokens: dict):
    if not e.get("fetched", True):
        return None
    raw_file = norm_raw_path(e.get("raw_file"))
    if not raw_file:
        return None
    stem = Path(raw_file).name
    stem = stem[:-3] if stem.endswith(".md") else stem
    page_stem = _scalar(e.get("wiki_page")) or stem  # 命名规则:源页与 raw 同名对齐
    src_page = wiki / "sources" / (page_stem + ".md")
    sp_meta, sp_body = {}, ""
    sp_text = _read_text(src_page) if src_page.is_file() else None
    if sp_text is not None:
        sp_meta, sp_body = fm.parse_frontmatter(sp_text)

    file_en = raw_file
    if pipeline["kind"] == "rolling" and raw_file.endswith(".md"):
        dated = raw_file[:-3] + ".dated.md"  # rolling 协议:faithful 快照 / dated 派生分离
        if (root / dated).is_file():
            file_en = dated

    date = _first(e.get("date"), sp_meta.get("date_published"))
    chars = e.get("chars")
    if not isinstance(chars, int) or isinstance(chars, bool):
        raw_text = _read_text(root / raw_file)
        chars = len(raw_text) if raw_text is not None else 0

    wiki_source = "sources/%s" % page_stem if sp_text is not None else None
    art = {
        "src_slug": stem,
        "slug": _first(e.get("slug")) or stem,
        "pipeline": pipeline["name"],
        "file_en": file_en,
        "file_zh": None,   # 双语槽位:extras/i18n_link 增强填充,核心恒 None/""
        "title_en": clean(_first(e.get("title"), sp_meta.get("title"))) or stem,
        "title_zh": "",
        "date": date,
        "year": date[:4] if date else "?",
        "description": clean(_first(e.get("description"))),
        "authors": _as_list(e.get("authors")),
        "source_kind": _first(sp_meta.get("source_kind"), e.get("kind"), e.get("source_kind")),
        "tldr": tldr_of(sp_body),
        "chars": chars,
        "url": _first(e.get("url"), sp_meta.get("source_url")),
        "wiki_source": wiki_source,
    }
    for fc in facets:
        art[fc["key"]] = _first(sp_meta.get(fc["key"]), e.get(fc["key"]))
    if wiki_source and sp_text is not None:
        page_tokens[wiki_source] = fm.est_tokens(sp_text, profile)
    return art


def collect_articles(root: Path, wiki: Path, cfg: dict, profile: str,
                     problems: list, warnings: list):
    facets = cfg["facets"]
    articles, page_tokens = [], {}
    per_pipeline = []  # [(name, kind, origin, count)]
    seen_raw, seen_page = set(), set()
    for p in cfg["pipelines"]:
        mf = root / "state" / ("%s.manifest.json" % p["name"])
        if mf.is_file():
            entries, origin = load_manifest_entries(mf, problems), "manifest"
        elif p["kind"] == "push":
            entries, origin = scan_push_raw(root, p), "raw-frontmatter"
        elif p["kind"] == "rolling":
            entries, origin = scan_rolling_sources(root, wiki, p), "wiki-sources"
        else:
            warnings.append("管线 %s(pull)无 manifest(state/%s.manifest.json),跳过:适配器尚未运行?"
                            % (p["name"], p["name"]))
            per_pipeline.append((p["name"], p["kind"], "skipped", 0))
            continue
        n = 0
        for e in entries:
            art = make_article(root, wiki, p, e, facets, profile, page_tokens)
            if art is None:
                continue
            raw_key, ws = art["file_en"], art["wiki_source"]
            if raw_key in seen_raw or (ws and ws in seen_page):
                warnings.append("管线 %s:条目 %s 与先前管线重复,跳过" % (p["name"], art["src_slug"]))
                continue
            seen_raw.add(raw_key)
            if ws:
                seen_page.add(ws)
            articles.append(art)
            n += 1
        per_pipeline.append((p["name"], p["kind"], origin, n))
    # 确定性排序:date 降序,同日按 src_slug 升序(稳定排序两趟)
    articles.sort(key=lambda a: a["src_slug"])
    articles.sort(key=lambda a: a["date"] or "", reverse=True)
    return articles, page_tokens, per_pipeline


# ---------------------------------------------------------------- wiki 聚合页

def facet_value_of_page(meta: dict, facet: dict) -> str:
    """聚合页分面归属:frontmatter `<key>:` 直取;否则 tags 约定
    `cross-<key>` → "cross",`<key>-<value>` → value;都没有 → ""(不猜默认值)。"""
    key = facet["key"]
    v = _scalar(meta.get(key))
    if v:
        return v
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if ("cross-%s" % key) in tags:
        return "cross"
    for val in facet["values"]:
        if ("%s-%s" % (key, val)) in tags:
            return val
    return ""


def collect_wiki(wiki: Path, cfg: dict, profile: str):
    """{kind: [page,…]} + jsonl 用 token 表。摘要单源 = frontmatter description(W-IDX-1);
    不再回落 index.md 摘要行(newpj4 的 P1 过渡逻辑,框架里 index 本身是派生物)。"""
    out = {k: [] for k in WIKI_KINDS}
    tokens = {}
    for k in WIKI_KINDS:
        for page in fm.iter_pages(wiki, subdirs=(k,), profile=profile):
            meta, stem = page["meta"], Path(page["path"]).stem
            rec = {
                "slug": stem,
                "file": "wiki/%s/%s.md" % (k, stem),
                "title": clean(_first(meta.get("title"))) or stem,
                "summary": clean(_first(meta.get("description"))),
                "status": _first(meta.get("status")),
            }
            for fc in cfg["facets"]:
                rec[fc["key"]] = facet_value_of_page(meta, fc)
            out[k].append(rec)
            tokens[page["rel"]] = page["est_tokens"]
    return out, tokens


# ---------------------------------------------------------------- 汇总装配

def kind_labels(cfg: dict, articles: list) -> dict:
    """source_kind 标签 = 枚举原文(恒等映射):config 声明序在前,库内发现的额外值排序后附。"""
    seen = []
    for p in cfg["pipelines"]:
        for k in p["source_kinds"]:
            if k not in seen:
                seen.append(k)
    extra = sorted({a["source_kind"] for a in articles if a["source_kind"]} - set(seen))
    return {k: k for k in seen + extra}


def build_data(cfg: dict, articles: list, wiki_pages: dict) -> dict:
    facets = [{"key": f["key"], "values": f["values"],
               "shard_index": bool(f.get("shard_index")),
               "badges": f.get("badges") or {}} for f in cfg["facets"]]
    by_facet = {}
    for f in cfg["facets"]:
        c = Counter(a[f["key"]] for a in articles if a.get(f["key"]))
        by_facet[f["key"]] = dict(sorted(c.items()))
    stats = {
        "articles": len(articles),
        "translated": sum(1 for a in articles if a["file_zh"]),
        "concepts": len(wiki_pages["concepts"]),
        "entities": len(wiki_pages["entities"]),
        "syntheses": len(wiki_pages["syntheses"]),
        "queries": len(wiki_pages["queries"]),
        "by_year": dict(sorted(Counter(a["year"] for a in articles).items())),
        "by_kind": dict(sorted(Counter(a["source_kind"] for a in articles
                                       if a["source_kind"]).items())),
        "by_pipeline": dict(sorted(Counter(a["pipeline"] for a in articles).items())),
        "by_facet": by_facet,
    }
    return {
        "generated": "",  # 确定性:不写时间戳(参考实例曾写 manifest.updated)
        "domain": {"name": cfg["domain"]["name"], "description": cfg["domain"]["description"]},
        "kind_label": kind_labels(cfg, articles),
        "facets": facets,
        "pipelines": [{"name": p["name"], "kind": p["kind"], "raw_dir": p["raw_dir"],
                       "prefix": p["prefix"]} for p in cfg["pipelines"]],
        "stats": stats,
        "articles": articles,
        "wiki": wiki_pages,
    }


def build_jsonl(cfg: dict, articles: list, wiki_pages: dict,
                page_tokens: dict, wiki_tokens: dict):
    facet_keys = [f["key"] for f in cfg["facets"]]
    src_lines = []
    for a in articles:
        row = {"slug": a["slug"], "date": a["date"], "pipeline": a["pipeline"],
               "kind": a["source_kind"]}
        for k in facet_keys:
            row[k] = a.get(k, "")
        row.update({
            "title": a["title_en"],
            "tldr": a["tldr"] or a["description"],
            "page": a["wiki_source"] or "",
            "page_tokens": page_tokens.get(a["wiki_source"]) if a["wiki_source"] else None,
        })
        src_lines.append(json.dumps(row, ensure_ascii=False))
    pg_lines = []
    for kind in WIKI_KINDS:
        for e in wiki_pages[kind]:
            rel = "%s/%s" % (kind, e["slug"])
            row = {"slug": rel, "title": e["title"]}
            for k in facet_keys:
                row[k] = e.get(k, "")
            row.update({"status": e["status"], "summary": e["summary"],
                        "tokens": wiki_tokens.get(rel)})
            pg_lines.append(json.dumps(row, ensure_ascii=False))
    return src_lines, pg_lines


# ---------------------------------------------------------------- 主流程

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki build_site — site/data.json + site/agent/*"
                    "(sources/pages.jsonl 与 search-index.json)派生(W-IDX-2/W-IDX-3)")
    ap.add_argument("--root", default=".", help="实例根目录(含 wiki.config.json;默认 cwd)")
    ap.add_argument("--json", action="store_true", help="机器输出:stdout 打 JSON 摘要")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    warnings, problems = [], []
    try:
        cfg = fm.load_config(root, on_warning=warnings.append)
    except fm.ConfigError as e:
        print("错误: %s" % e, file=sys.stderr)
        return 2

    wiki = root / "wiki"
    if not wiki.is_dir():
        warnings.append("wiki/ 目录不存在(%s):按空库构建" % wiki)
    profile = cfg["budgets"]["est_tokens_profile"]

    for fc in cfg["facets"]:  # facet key 与保留字段冲突则忽略该 facet(防字段覆盖)
        if fc["key"] in _ARTICLE_RESERVED or fc["key"] in _PAGE_RESERVED:
            warnings.append("facet key %r 与产出保留字段冲突,该分面不进条目字段" % fc["key"])
    cfg = dict(cfg)
    cfg["facets"] = [f for f in cfg["facets"]
                     if f["key"] not in _ARTICLE_RESERVED and f["key"] not in _PAGE_RESERVED]

    articles, page_tokens, per_pipeline = collect_articles(
        root, wiki, cfg, profile, problems, warnings)
    wiki_pages, wiki_tokens = collect_wiki(wiki, cfg, profile)
    data = build_data(cfg, articles, wiki_pages)
    src_lines, pg_lines = build_jsonl(cfg, articles, wiki_pages, page_tokens, wiki_tokens)
    # 排名检索索引(W-IDX-3):textindex 自扫 wiki(根页+五子目录全文;collect_wiki 只带
    # 四类聚合页 frontmatter,覆盖面不同)。放在任何写盘之前:坏文件在此 fail loud 时,
    # 上一轮 site/ 产物保持完整一致,不留"半新半旧"的窗口。
    search_index = textindex.build_index(textindex.collect_docs(wiki, profile), profile)
    # 链接图谱(W-IDX-4):确定性 wikilink 边表(节点=非派生非 log 页);同样先派生后写盘
    graph = wikigraph.build_graph(wiki)

    site = root / "site"
    agent = site / "agent"
    agent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["site/data.json"] = _write_if_changed(
        site / "data.json", json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    outputs["site/agent/sources.jsonl"] = _write_if_changed(
        agent / "sources.jsonl", ("\n".join(src_lines) + "\n") if src_lines else "")
    outputs["site/agent/pages.jsonl"] = _write_if_changed(
        agent / "pages.jsonl", ("\n".join(pg_lines) + "\n") if pg_lines else "")
    # 机读专用且体积敏感(全文倒排,与人读 data.json 定位不同):紧凑分隔;
    # sort_keys 定序 + 无时间戳,保逐字节确定性
    outputs["site/agent/search-index.json"] = _write_if_changed(
        agent / "search-index.json",
        json.dumps(search_index, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")) + "\n")
    outputs["site/agent/graph.json"] = _write_if_changed(
        agent / "graph.json",
        json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    ok = not problems
    if args.json:
        print(json.dumps({
            "ok": ok,
            "root": str(root),
            "articles": len(articles),
            "pipelines": [{"name": n, "kind": k, "origin": o, "articles": c}
                          for n, k, o, c in per_pipeline],
            "wiki_pages": {k: len(v) for k, v in wiki_pages.items()},
            "rows": {"sources.jsonl": len(src_lines), "pages.jsonl": len(pg_lines)},
            "search": {"docs": search_index["n_docs"],
                       "terms": len(search_index["postings"])},
            "graph": {"nodes": graph["n_nodes"], "edges": graph["n_edges"]},
            "outputs": {k: ("wrote" if v else "unchanged") for k, v in outputs.items()},
            "warnings": warnings,
            "problems": problems,
        }, ensure_ascii=False, indent=1))
    else:
        print("== build_site @ %s ==" % root)
        for n, k, o, c in per_pipeline:
            print("管线 %s(%s,%s):%d 篇" % (n, k, o, c))
        print("articles 共 %d;wiki 页 %s" % (
            len(articles),
            " / ".join("%s %d" % (k, len(v)) for k, v in wiki_pages.items())))
        for path, changed in outputs.items():
            print("%s %s" % (path, "wrote" if changed else "unchanged"))
        print("agent index: sources.jsonl %d rows, pages.jsonl %d rows, "
              "search-index %d docs / %d terms, graph %d nodes / %d edges" %
              (len(src_lines), len(pg_lines), search_index["n_docs"],
               len(search_index["postings"]), graph["n_nodes"], graph["n_edges"]))
        for w in warnings:
            print("警告: %s" % w)
        for p in problems:
            print("问题: %s" % p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
