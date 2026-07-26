#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki search — 排名检索 CLI(BM25;仅 Python 标准库,W-IDX-3)。

消费 `site/agent/search-index.json`(由 build_site 经 lib/textindex 派生),对查询词
出 BM25 top-k;打分逻辑复用 lib/textindex(构建/查询单源,防口径漂移)。用于"关键词
不确定 / 想要跨库排名候选"——grep 精确命中不了时的补充入口(见 `wiki/_map.md` 决策表)。

装载层是格式/形状校验的责任方(设计裁决:textindex.search() 契约自限于 build_index
产物,不重复防御):索引缺失 / 版本漂移 / 手编损坏 → 清晰报错 exit 2,不以裸异常暴露。

用法:
    python3 tools/search.py <关键词...> [--root DIR] [-k N] [--json]
输出:人读为对齐表(slug / 分值 / ~token / 分诊摘要);--json 为 {query,k,count,hits[]}。
退出码:0 = 查询成功(含零命中——未收录是诚实结果,非错误);2 = 索引不可用 / 用法错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import textindex  # noqa: E402(检索构建/查询单源,W-IDX-3)

_INDEX_REL = "site/agent/search-index.json"
_DESC_MAX = 70  # 人读表分诊摘要截断(仅显示;不影响 --json 全文)


class SearchIndexError(Exception):
    """检索索引不可用(缺失/版本漂移/结构损坏);调用方捕获后 exit 2。"""


def load_index(path: Path) -> dict:
    """载入并校验 search-index.json 顶层形状;不符抛 SearchIndexError(清晰信息,调用方 exit 2)。

    校验层次:存在 → 合法 JSON → 顶层对象 → format 匹配当前版本 → 顶层键(n_docs/docs/
    postings/doc_order)类型齐备。**只校验顶层**——深层遍历 postings/docs 是 O(索引体积) 二次
    扫描、不划算;内层任意手编损坏(postings 条目畸形 / doc_id 越界 / docs 记录非 dict /
    数值字段畸形等)由 main() 对 search() 的广捕兜底转成 exit 2(见下)。两道合起来兑现头注契约
    "手编损坏 → 清晰报错,不以裸异常暴露"。
    """
    if not path.is_file():
        raise SearchIndexError(
            "检索索引不存在:%s —— 先跑 `python3 tools/build_site.py`" % path)
    try:
        idx = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise SearchIndexError("检索索引读取失败:%s(%s)" % (path, e))
    except json.JSONDecodeError as e:
        raise SearchIndexError("检索索引不是合法 JSON:%s(:%d %s)" % (path, e.lineno, e.msg))
    if not isinstance(idx, dict):
        raise SearchIndexError("检索索引结构错误:顶层非对象:%s" % path)
    fmt = idx.get("format")
    if fmt != textindex.INDEX_FORMAT:
        raise SearchIndexError(
            "检索索引版本不符:期望 %r 得到 %r —— 重跑 `python3 tools/build_site.py` 重建(%s)"
            % (textindex.INDEX_FORMAT, fmt, path))
    for key, typ in (("n_docs", int), ("docs", dict), ("postings", dict), ("doc_order", list)):
        v = idx.get(key)
        if not isinstance(v, typ) or isinstance(v, bool):  # bool 是 int 子类,单列排除
            raise SearchIndexError(
                "检索索引形状错误:字段 %s 缺失或类型非 %s(%s;疑手编或版本漂移)"
                % (key, typ.__name__, path))
    return idx


def print_human(hits: list, query: str) -> None:
    if not hits:
        print("(无命中:%r —— 换关键词,或按 _map 降级链 grep raw/)" % query)
        return
    print("%-40s %7s %7s  %s" % ("slug", "score", "~tok", "description(分诊)"))
    for h in hits:
        desc = " ".join((h.get("description") or h.get("title") or "").split())
        if len(desc) > _DESC_MAX:
            desc = desc[:_DESC_MAX].rstrip() + "…"
        tok = h.get("tokens")
        print("%-40s %7.3f %7s  %s"
              % (h["slug"], h["score"], tok if isinstance(tok, int) else "?", desc))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki 排名检索(BM25;消费 site/agent/search-index.json,W-IDX-3)")
    ap.add_argument("query", nargs="+", help="检索词(可多个,空格分隔;中文直接写)")
    ap.add_argument("--root", default=".", help="实例根目录(含 site/;默认 cwd)")
    ap.add_argument("-k", "--k", type=int, default=8, help="返回前 k 条(默认 8)")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="机器输出:stdout 打 JSON {query,k,count,hits[]}")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("错误: --root 不是目录:%s" % root, file=sys.stderr)
        return 2
    if args.k < 1:
        print("错误: -k 必须 ≥ 1(得到 %d)" % args.k, file=sys.stderr)
        return 2

    try:
        index = load_index(root / _INDEX_REL)
    except SearchIndexError as e:
        print("错误: %s" % e, file=sys.stderr)
        return 2

    query = " ".join(args.query)
    try:
        hits = textindex.search(index, query, args.k)
    except Exception as e:  # noqa: BLE001 — 见下:开放式手编损坏不可枚举,故广捕
        # load_index 只校验顶层;postings/docs 记录/数值字段(k1/b/权重)等任意内层手编损坏,
        # 会在 search() 遍历时以多类异常抛出(IndexError/ValueError/TypeError/AttributeError/
        # ZeroDivisionError…)。入参本质是"任意磁盘垃圾",逐类枚举是打地鼠,故广捕转 exit 2,
        # 兑现头注契约"手编损坏 → 清晰报错,不以裸异常暴露"。合法索引上的真逻辑 bug 不会被掩盖:
        # CI 的 search 冒烟用真实索引断言命中 + 确定性,真 bug 会令 rc≠0 而变红。
        print("错误: 检索索引处理失败(疑内层损坏或版本不兼容;%s: %s)—— "
              "重跑 `python3 tools/build_site.py` 重建(%s)"
              % (type(e).__name__, e, root / _INDEX_REL), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps({"query": query, "k": args.k, "count": len(hits), "hits": hits},
                         ensure_ascii=False, indent=1))
    else:
        print_human(hits, query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
