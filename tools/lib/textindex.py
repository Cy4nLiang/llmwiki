#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lib.textindex — 排名检索索引的构建/查询单源(仅 Python 标准库)。

site/agent/search-index.json 由 build_site.py 经本模块派生(W-IDX-1 一切汇总皆派生;
规则登记 W-IDX-3);tools/search.py 查询侧复用本模块打分——构建与查询共享同一份
tokenize/BM25 实现,防止两份口径漂移。

设计要点:
  - tokenize:CJK 连续段切 bigram(单字成段保留 unigram),其余按 [a-z0-9]+ 小写切词;
    CJK 判界与 fm.est_tokens 一致(U+4E00..U+9FFF,自检有行为钉子),中英混排各走各的通道。
  - 字段加权词频:title/aliases ×3、description ×2、标题行 ×1.5、正文 ×1
    (aliases 是双语检索锚点,与 title 同权)。**字段互斥**:标题行只计入 headings,
    body 剔除标题行——否则标题词有效权重 1.5+1.0=2.5 会反超 description 的 2.0,
    颠倒 spec 的字段排序。
  - BM25:k1=1.5、b=0.75(常量,不进 config);idf = ln((N-df+0.5)/(df+0.5)+1) 恒非负。
  - 产物形状(体积敏感,格式 v1 定形前裁决):postings 不重复 slug——
    {term: [[doc_id, weight], ...]}(doc_id = doc_order 下标,条目按 doc_id 升序);
    600 页量级实测 slug 键版 ~20MB → 数组版 ~3MB。doc_order 为 slug 升序定序表。
  - 确定性:doc_order/docs 定序 + postings 数组升序 + JSON sort_keys;分数 round(6)
    后按 (score 降序, slug 升序) tie-break;不写时间戳。
  - 覆盖面:wiki 根页(_map/overview/followups 等)+ 五子目录;排除 log 与派生物
    (index* 是工具链保留命名空间,与 lint_wiki 的 derived 谓词同口径;
    contradictions/backlinks 同理——backlinks 为 W-IDX-4 预留)。

限制(如实声明):单字 CJK 查询词只匹配"独立单字成段"的文本;多字词按 bigram 召回;
拉丁/数字/CJK 之外的文字(假名/谚文/西里尔等)不进索引。
"""
from __future__ import annotations

import math
import re
from pathlib import Path

try:
    from . import fm  # 包式导入(build_site 的 `from lib import …` 风格)
    from . import wikigraph
except ImportError:  # pragma: no cover — sys.path 直插 lib 目录风格(lint_wiki 同款)
    import fm
    import wikigraph

__all__ = ["INDEX_FORMAT", "build_index", "collect_docs", "search", "tokenize"]

INDEX_FORMAT = "llmwiki-search-index/1"
_K1, _B = 1.5, 0.75

# CJK 判界与 fm.est_tokens 一致(U+4E00..U+9FFF):同一份"什么算 CJK"的口径
_CJK_RE = re.compile(r"[一-鿿]+")
_WORD_RE = re.compile(r"[a-z0-9]+")
# ATX 标题严格形(CommonMark):0-3 空格缩进 + 1-6 个 # + 空格或行尾。
# `#tag`(# 后无空格)与 4+ 空格缩进(缩进代码块)都不是标题——避免误判抬权重。
_ATX_RE = re.compile(r" {0,3}#{1,6}(?:\s|$)")

# 字段 → 权重(元组定序,构建确定性;字段互斥语义见模块头注)
_FIELD_WEIGHTS = (("title", 3.0), ("aliases", 3.0), ("description", 2.0),
                  ("headings", 1.5), ("body", 1.0))

# 根页排除:log 是 grep-only 流水账;派生物(index*/contradictions/backlinks)判定
# 走 wikigraph.is_derived 单源(W-IDX-4;新增派生物只改那一处,不在此另立字面量列表)


# ---------------------------------------------------------------- tokenize

def tokenize(text: str) -> list:
    """全文 → 检索词列表(小写;CJK bigram + 拉丁/数字词)。空文本返回 []。"""
    text = (text or "").lower()
    tokens = _WORD_RE.findall(text)
    for run in _CJK_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


def _split_headings(body: str) -> tuple:
    """单趟围栏感知切分:(标题行拼接文本, 剔除标题行后的正文)。

    字段互斥是权重契约的前提(见模块头注)。标题判定用 ATX 严格形(_ATX_RE):
    `#tag`(# 后无空格)与 4+ 空格缩进的 "# …"(缩进代码块)都不算标题,不从正文剔除、
    不抬权重;```围栏内的行整体豁免(围栏识别与 fm.iter_wikilinks 同款)。
    """
    heads, rest = [], []
    fence = False
    for line in (body or "").split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            rest.append(line)
            continue
        if not fence and _ATX_RE.match(line):
            heads.append(line.strip().lstrip("#").strip())
            continue
        rest.append(line)
    return " ".join(heads), "\n".join(rest)


def _scalar_text(v) -> str:
    """frontmatter 值 → 文本(列表按空格拼接;None → "")。"""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


# ---------------------------------------------------------------- 文档收集

def _make_doc(slug: str, page: dict) -> dict:
    meta = page["meta"]
    headings, body_rest = _split_headings(page["body"])
    title = _scalar_text(meta.get("title"))
    description = _scalar_text(meta.get("description"))
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "tokens": page["est_tokens"],
        "fields": {
            "title": title,
            "aliases": _scalar_text(meta.get("aliases")),
            "description": description,
            "headings": headings,
            "body": body_rest,
        },
    }


def collect_docs(wiki_dir, profile: str = "cjk") -> list:
    """收集待索引文档:wiki 根页(排除 log/派生物)+ 五子目录(fm.iter_pages 定序)。

    独立于 build_site.collect_wiki 再扫一遍:后者只覆盖四类聚合页且不带正文,
    检索需要根页与 sources 的全文;页面量级为数百,重读成本可忽略,换取本模块
    自包含(构建/调试/测试都能单独调用)。坏文件(不可解码等)在此 fail loud——
    调用方须保证该失败发生在任何产物写盘之前(build_site 已按此编排)。
    """
    wiki = Path(wiki_dir)
    docs = []
    if not wiki.is_dir():
        return docs
    for f in sorted(wiki.glob("*.md")):
        if f.stem == "log" or wikigraph.is_derived(f.stem):  # 派生物判定单源(W-IDX-4)
            continue
        docs.append(_make_doc(f.stem, fm.read_page(f, profile)))
    for page in fm.iter_pages(wiki, profile=profile):
        docs.append(_make_doc(page["rel"], page))
    return docs


# ---------------------------------------------------------------- 构建

def _weighted_tf(fields: dict) -> dict:
    """字段加权词频:{term: Σ(该字段词频 × 字段权重)}。权重全为 k/2 → 浮点精确。"""
    wtf = {}
    for field, weight in _FIELD_WEIGHTS:
        for tok in tokenize(fields.get(field, "")):
            wtf[tok] = wtf.get(tok, 0.0) + weight
    return wtf


def build_index(docs: list, profile: str = "cjk") -> dict:
    """文档列表 → 索引 dict(JSON 可序列化;调用方负责 sort_keys+紧凑分隔落盘)。

    postings 以 doc_order 下标引用文档而非重复 slug(体积的结构性大头,
    格式 v1 定形前的裁决;600 页量级 ~20MB → ~3MB)。
    """
    raw_postings, doc_table = {}, {}
    total_dl = 0.0
    for d in docs:
        wtf = _weighted_tf(d["fields"])
        dl = sum(wtf.values())
        total_dl += dl
        doc_table[d["slug"]] = {"dl": dl, "title": d["title"],
                                "description": d["description"], "tokens": d["tokens"]}
        for term, w in wtf.items():
            raw_postings.setdefault(term, {})[d["slug"]] = w
    doc_order = sorted(doc_table)
    id_of = {slug: i for i, slug in enumerate(doc_order)}
    postings = {term: sorted([id_of[s], w] for s, w in plist.items())
                for term, plist in raw_postings.items()}
    n = len(doc_table)
    return {
        "format": INDEX_FORMAT,
        "profile": profile,
        "k1": _K1,
        "b": _B,
        "n_docs": n,
        "avgdl": round(total_dl / n, 6) if n else 0.0,
        "doc_order": doc_order,
        "docs": doc_table,
        "postings": postings,
    }


# ---------------------------------------------------------------- 查询

def search(index: dict, query: str, k: int = 8) -> list:
    """BM25 top-k:[{slug, score, title, description, tokens}]。

    契约:index 为 build_index 产物(或其 JSON 回读);格式/形状校验是装载层
    (tools/search.py)的职责,本函数不重复防御。确定性 tie-break:分数 round(6)
    后按 (score 降序, slug 升序)。空库/空查询/全未命中一律返回 []。
    """
    n = index.get("n_docs") or 0
    if n <= 0:
        return []
    postings = index.get("postings") or {}
    docs = index.get("docs") or {}
    doc_order = index.get("doc_order") or []
    k1 = float(index.get("k1", _K1))
    b = float(index.get("b", _B))
    avgdl = float(index.get("avgdl") or 0.0) or 1.0  # 防零:空库已在上方返回

    scores = {}
    for term in sorted(set(tokenize(query))):  # 查询词去重,BM25 qtf=1 简化
        plist = postings.get(term)
        if not plist:
            continue
        df = len(plist)
        idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
        for did, w in plist:
            slug = doc_order[did]
            dl = float(docs.get(slug, {}).get("dl") or 0.0)
            denom = w + k1 * (1.0 - b + b * dl / avgdl)
            scores[slug] = scores.get(slug, 0.0) + idf * w * (k1 + 1.0) / denom

    ranked = sorted(((round(s, 6), slug) for slug, s in scores.items()),
                    key=lambda t: (-t[0], t[1]))
    out = []
    for score, slug in ranked[:max(0, k)]:
        d = docs.get(slug, {})
        out.append({"slug": slug, "score": score, "title": d.get("title", ""),
                    "description": d.get("description", ""), "tokens": d.get("tokens")})
    return out


# ---------------------------------------------------------------- 自检

if __name__ == "__main__":  # python3 tools/lib/textindex.py — 零依赖冒烟自检
    import json as _json

    # tokenize:中英混排/单字段/空
    assert tokenize("BM25检索 Index") == ["bm25", "index", "检索"], tokenize("BM25检索 Index")
    assert tokenize("锁") == ["锁"] and tokenize("乐观锁") == ["乐观", "观锁"]
    assert tokenize("") == []

    # CJK 判界与 fm 同口径的行为钉子(界内两端算 CJK;界外邻字符两侧一致不算)
    assert fm.est_tokens("一") == 1 and tokenize("一") == ["一"]
    assert fm.est_tokens("鿿") == 1 and tokenize("鿿") == ["鿿"]
    assert fm.est_tokens("㐀") == 0 and tokenize("㐀") == []

    # 字段互斥:标题行只进 headings,body 被剔除;ATX 严格(围栏/缩进码块/#tag 都不算标题)
    assert _split_headings("## 概览\n正文行") == ("概览", "正文行")
    assert _split_headings("### 三级")[0] == "三级"
    assert _split_headings("```\n# 注释\n```")[0] == ""
    assert _split_headings("#tag 不是标题")[0] == ""       # # 后无空格
    assert _split_headings("    # 缩进码块非标题")[0] == ""  # 4 空格缩进
    _doc = _make_doc("t", {"meta": {"title": "X"}, "body": "## 概览\n正文", "est_tokens": 1})
    assert _doc["fields"]["headings"] == "概览" and "概览" not in _doc["fields"]["body"]

    # 权重表五值逐一钉死 spec §4 S1(title/aliases 3 > description 2 > headings 1.5 > body 1)
    _only = lambda **f: _weighted_tf({"title": "", "aliases": "", "description": "",
                                      "headings": "", "body": "", **f})  # noqa: E731
    assert _only(title="甲乙")["甲乙"] == 3.0
    assert _only(aliases="甲乙")["甲乙"] == 3.0
    assert _only(description="甲乙")["甲乙"] == 2.0
    assert _only(headings="甲乙")["甲乙"] == 1.5
    assert _only(body="甲乙")["甲乙"] == 1.0

    _docs = [
        {"slug": "concepts/greeting", "title": "问候协议", "description": "打招呼的约定",
         "tokens": 100, "fields": {"title": "问候协议", "aliases": "greeting protocol",
                                   "description": "打招呼的约定", "headings": "", "body": "正文 问候"}},
        {"slug": "concepts/other", "title": "其他", "description": "",
         "tokens": 50, "fields": {"title": "其他", "aliases": "", "description": "",
                                  "headings": "", "body": "无关内容"}},
    ]
    _idx = build_index(_docs)
    assert _idx["n_docs"] == 2 and _idx["format"] == INDEX_FORMAT
    assert _idx["doc_order"] == ["concepts/greeting", "concepts/other"]
    assert all(isinstance(p, list) and len(p[0]) == 2 for p in _idx["postings"].values())
    _hits = search(_idx, "问候 协议")
    assert _hits and _hits[0]["slug"] == "concepts/greeting", _hits
    assert search(_idx, "问候") == search(_idx, "问候"), "同查询必须逐位一致"
    # JSON 落盘回读后打分逐位一致(消费侧 = 回读路径)
    _idx2 = _json.loads(_json.dumps(_idx, ensure_ascii=False, sort_keys=True))
    assert search(_idx2, "问候 协议") == _hits
    assert search(build_index([]), "任意") == []
    print("textindex self-check OK")
