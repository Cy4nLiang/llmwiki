#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lib.wikigraph — wikilink 图谱(边表/反链)与派生物判定的单源(仅 Python 标准库)。

site/agent/graph.json 由 build_site 派生、wiki/backlinks.md 由 build_index 派生,均经本模块;
lint_wiki 亦复用 resolve_slug / is_derived,消除第二份 slug 解析实现(W-IDX-4,单源原则)。

**只做确定性 wikilink 解析**(命中页 slug 或按子目录前缀补全),不做任何语义/推断边——
拒绝清单明列(spec §2 不做语义推断边)。节点/边全按 slug 定序,产物逐字节可复现。
"""
from __future__ import annotations

from pathlib import Path

try:
    from . import fm  # 包式导入(build_site 的 `from lib import …` 风格)
except ImportError:  # pragma: no cover — sys.path 直插 lib 目录风格(lint_wiki 同款)
    import fm

__all__ = ["GRAPH_FORMAT", "SUBDIRS", "backlinks", "build_graph", "is_derived", "resolve_slug"]

GRAPH_FORMAT = "llmwiki-graph/1"
# 子目录前缀补全用(与 lint_wiki.SUBDIRS 同集合;此处为图谱侧单源)
SUBDIRS = ("sources", "entities", "concepts", "syntheses", "queries")


def is_derived(slug: str) -> bool:
    """派生物判定(W-IDX-1 单源):其链接不计有机入链、不吃页面预算、须带 generated 标记。

    覆盖 contradictions / backlinks / index*(index.md、index-sources-*.md)。
    lint_wiki 的 derived 集合、build_index.contradiction_lines 的豁免、本模块建图的源页跳过
    统一走本函数——新增派生物只改这一处判定(逐文件点名制的收敛点)。
    """
    return slug == "contradictions" or slug == "backlinks" or slug.startswith("index")


def fm_slugs(meta: dict, key: str) -> list:
    """frontmatter 多值 slug 取值(W-ING-5 lineage 字段的单源解析口径)。

    str → [str];list → 原样(逐项 strip、丢空)。简易 YAML 只认标量与**单行** `[a, b]`,
    换行 `- a` 块写法会被 fm 解析成空串——调用方据此报「值为空」提示。
    刻意不做「取首元素」:那会静默丢掉第 2+ 个目标。lint 与 build_index 共用本函数,
    禁第二份实现(W-IDX-4 同款单源纪律)。
    """
    v = meta.get(key)
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip() if v is not None else ""
    return [s] if s else []


def resolve_slug(target: str, page_set: set, subdirs=SUBDIRS):
    """wikilink 目标 → 页 slug:命中 page_set 直取;无斜杠则按子目录前缀补全;无则 None。

    与 lint_wiki 旧内嵌 resolves() 同口径(本函数即其下沉单源)。跨实例 [[alias::slug]]
    (含 `::`)由调用方先分流,不传进本函数。
    """
    if target in page_set:
        return target
    if "/" not in target:
        for d in subdirs:
            cand = "%s/%s" % (d, target)
            if cand in page_set:
                return cand
    return None


def build_graph(wiki_dir) -> dict:
    """扫全库 → {format, n_nodes, n_edges, nodes, edges}(确定性,JSON 可序列化)。

    节点 = 非派生、非 log 页(真实知识节点;派生物是自动生成的链接农场,log 是流水账);
    边 = 节点间**解析成功的有机 wikilink**——跳过 peer(::)/断链/自链,每条 (from,to) 取
    首次出现行号。edges 按 (from,to) 升序,nodes 按 slug 升序。断链归 lint 报,本模块不管。
    """
    wiki = Path(wiki_dir)
    if not wiki.is_dir():
        return {"format": GRAPH_FORMAT, "n_nodes": 0, "n_edges": 0, "nodes": [], "edges": []}
    all_md = sorted(wiki.rglob("*.md"))
    page_set = {p.relative_to(wiki).as_posix()[:-3] for p in all_md}
    nodes = sorted(s for s in page_set if s != "log" and not is_derived(s))
    first_line = {}  # (from, to) -> 最小行号(同一对多次链接取首现)
    for p in all_md:
        rel = p.relative_to(wiki).as_posix()[:-3]
        if rel == "log" or is_derived(rel):
            continue  # log/派生物的出链不入图
        for target, _display, line in fm.iter_wikilinks(p.read_text(encoding="utf-8"), skip_code=True):
            if "::" in target:
                continue  # 跨实例引用(W-XRF-1)不入本图
            hit = resolve_slug(target, page_set)
            if hit is None or hit == rel or hit == "log" or is_derived(hit):
                continue  # 断链(lint 报)/自链/指向 log 或派生物的边不入图——
                # 后者还保证确定性:派生页(index/backlinks)是 build 中途才生成的,
                # 若允许指向它们的边,graph 会随 build 顺序漂移(非幂等)
            key = (rel, hit)
            if key not in first_line or line < first_line[key]:
                first_line[key] = line
    edges = [{"from": f, "to": t, "line": ln} for (f, t), ln in sorted(first_line.items())]
    return {"format": GRAPH_FORMAT, "n_nodes": len(nodes), "n_edges": len(edges),
            "nodes": nodes, "edges": edges}


def backlinks(graph: dict) -> dict:
    """图 → {目标页 slug: [来源页 slug 排序去重]}(仅含有反链的页,按目标页升序)。"""
    bl = {}
    for e in graph.get("edges", []):
        bl.setdefault(e["to"], set()).add(e["from"])
    return {k: sorted(v) for k, v in sorted(bl.items())}


if __name__ == "__main__":  # python3 tools/lib/wikigraph.py — 零依赖冒烟自检
    assert is_derived("index") and is_derived("index-sources-app") and is_derived("backlinks")
    assert is_derived("contradictions") and not is_derived("concepts/foo")
    _ps = {"concepts/greeting", "sources/adr", "overview"}
    assert resolve_slug("concepts/greeting", _ps) == "concepts/greeting"
    assert resolve_slug("greeting", _ps) == "concepts/greeting"  # 前缀补全
    assert resolve_slug("nope", _ps) is None
    # 建图/反链纯函数自检(不落盘)
    _g = {"edges": [{"from": "a", "to": "b", "line": 3}, {"from": "c", "to": "b", "line": 1}]}
    assert backlinks(_g) == {"b": ["a", "c"]}
    print("wikigraph self-check OK")
