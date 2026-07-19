#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lint_wiki — 完整机械体检(M2 全量版;仅 Python 标准库)。

三种用法(可并存;M1 旗标 --check-slots / --check-config 行为不变):

    python3 tools/lint_wiki.py [--root DIR] [--json] [--manifest]
        对实例跑完整机械 lint。检查项 × 规则 ID(权威表 framework/RULES.md):
          W-PAGE-3  断链 wikilink(码块/行内码豁免;log.md 豁免)/ 孤儿聚合页 /
                    晋升候选(rule-of-three:断链目标被 ≥2 处引用)
          W-XRF-1   跨实例链接 [[alias::…]] soft 检查:peer 可达查其 site/agent/pages.jsonl;
                    不可达仅 warning 计数,不 fail
          W-PAGE-4  frontmatter 必填与漂移(type 与目录不符;源页附加字段 + config facet 字段)
          W-PAGE-1  页面 token 预算(config budgets.page_tokens;-timeline/-appendix 子页豁免)
          W-LNT-2   _map 行数 ≤ config budgets.map_lines
          W-IDX-1   索引新鲜度(index*/contradictions 派生物 vs frontmatter 重算)+ 生成区标记
          W-IDX-2   人读 index 与机器 jsonl 同 build 产出(site/agent/*.jsonl 存在性,soft)
          W-LNT-3   staleness 过期未核实(config staleness 窗口 vs verified:;
                    操作类 source_kind 无 verified 视为自 created: 起算)
          W-ING-1   准孤儿源页(无聚合页有机入链)/ light 档占比 >50% 告警(ingest_tier: light)
          W-LOG-1   log 行格式抽查(`## [YYYY-MM-DD] <op> | <one-line>`)
          W-ARCH-3  根命名空间白名单(杂物入 _attic/)
          W-SEC-2   state/ 入 .gitignore + config/manifest 凭证样式扫描(soft)
          W-UPG-1   --manifest:对照 framework/MANIFEST.json 校验 frozen 档 sha256,
                    漂移报 fork 警告(有漂移 exit 1,供 sync 常跑路径当场报警)

    python3 tools/lint_wiki.py --check-slots --target <dir>
        扫描实例内全部 .md 的 <SLOT: 与 <!--BEGIN: / <!--END: 残留(渲染验收,报 文件:行号);
        排除 framework/base/(模板快照本该含槽位)、raw/(不可信输入且从不经渲染,W-SEC-1)、
        state/ site/ _attic/ .git 等;任何残留 → exit 1。
        注:若某页需要示范槽位语法本身,请写成反引号内断开形式(如 `<SLOT :key>`)以免误报。

    python3 tools/lint_wiki.py --check-config <path>
        校验 wiki.config.json;校验器单源复用 tools/init_render.py(零第三方依赖)。

exit:0 干净 / 1 有 finding(fail 级,含 --manifest 漂移;soft 项如 W-XRF-1/W-ARCH-3/W-SEC-2
     仅 warning,不改变退出码)/ 2 配置与用法错误。机器输出统一 --json。
语义体检(跨页矛盾、过时声明、mature 空段)仍需 agent 审——本工具只喂机械发现。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 单源:config 校验器住在 init_render.py(同目录导入;M1 行为保持)
_TOOLS = Path(__file__).resolve().parent
for _p in (str(_TOOLS), str(_TOOLS / "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import init_render as _ir
except ImportError as e:  # pragma: no cover
    print("错误: 无法导入同目录 init_render.py(校验器单源所在):%s" % e, file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------- M1 检查(行为不变)

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


# ---------------------------------------------------------------- 完整机械 lint(M2)

SUBDIRS = ("sources", "entities", "concepts", "syntheses", "queries")
TYPE_BY_DIR = {"sources": "source", "entities": "entity", "concepts": "concept",
               "syntheses": "synthesis", "queries": "query"}
REQUIRED_ALL = ("title", "description", "type", "created", "tags", "status")
REQUIRED_SRC = ("source_kind", "raw_file", "date_published", "date_ingested")
META_STEMS = {"index", "overview", "followups", "log", "_map", "contradictions"}
LOG_LINE_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] [a-z][a-z0-9-]* \| .+$")
DUR_RE = re.compile(r"^(\d+)d$")
GEN_MARK_PREFIX = "<!-- generated"
# 根命名空间白名单(W-ARCH-3;Spec §1.2 实例目录 + 常规仓库文件;`.` 开头一律放行)
ROOT_WHITELIST = {"CLAUDE.md", "AGENTS.md", "README.md", "LICENSE", "LICENSE.md", "schema",
                  "wiki.config.json", "framework", "tools", "adapters", "raw",
                  "state", "site", "wiki", "evals", "docs", "_attic"}
ITEM_CAP = 200   # --json 每检查项条目上限
SHOW_CAP = 15    # 文本报告每检查项展示上限


def _s(meta, key):
    v = meta.get(key, "")
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v).strip()


def _tags(meta):
    v = meta.get("tags", [])
    if isinstance(v, list):
        return [str(t).strip() for t in v]
    return [t.strip() for t in str(v).strip("[] ").split(",") if t.strip()]


def _pdate(s):
    try:
        return datetime.date.fromisoformat(str(s).strip())
    except (ValueError, TypeError):
        return None


def _chk(cid, rule, label, severity, items, hint=""):
    return {"id": cid, "rule": rule, "label": label, "severity": severity,
            "count": len(items), "items": items[:ITEM_CAP], "hint": hint}


def run_lint(root: Path, cfg: dict, fmmod, with_manifest: bool = False) -> dict:
    """完整机械 lint;返回 {"ok","errors","warnings","checks","totals"}。"""
    wiki = root / "wiki"
    profile = cfg["budgets"]["est_tokens_profile"]
    facets = cfg.get("facets", [])
    today = datetime.date.today()

    all_md = sorted(wiki.rglob("*.md"))
    page_set = {p.relative_to(wiki).as_posix()[:-3] for p in all_md}
    # 派生物(W-IDX-1):其中的链接不计有机入链,避免索引/汇总把孤儿页"救活"
    derived = {s for s in page_set if s == "contradictions" or s.startswith("index")}

    def resolves(t):
        if t in page_set:
            return t
        if "/" not in t:
            for d in SUBDIRS:
                if "%s/%s" % (d, t) in page_set:
                    return "%s/%s" % (d, t)
        return None

    # ---- W-PAGE-3 断链 + 入链计数;W-XRF-1 peer 链接分流 -----------------
    inbound_organic = Counter()
    broken = Counter()
    broken_where = {}
    peer_links = []   # (alias, slug, src_rel, lineno)
    for p in all_md:
        rel = p.relative_to(wiki).as_posix()[:-3]
        if rel == "log":     # append-only 历史,豁免(W-LOG-1 另查格式)
            continue
        text = p.read_text(encoding="utf-8")
        for target, _display, lineno in fmmod.iter_wikilinks(text, skip_code=True):
            if "::" in target:
                alias, _, slug = target.partition("::")
                peer_links.append((alias.strip(), slug.strip(), rel, lineno))
                continue
            hit = resolves(target)
            if hit:
                if rel not in derived:
                    inbound_organic[hit] += 1
            else:
                broken[target] += 1
                broken_where.setdefault(target, "%s:%d" % (rel, lineno))

    broken_items = ["[[%s]] ×%d  (如 %s)" % (t, c, broken_where[t])
                    for t, c in sorted(broken.items(), key=lambda x: -x[1])]
    promote_items = ["%s (被 %d 处引用)" % (t, c) for t, c in sorted(broken.items())
                     if c >= 2 and re.match(r"^(concepts|entities)/", t)]

    # ---- 孤儿聚合页 / 准孤儿源页 ----------------------------------------
    orphans = sorted(
        s for s in page_set
        if "/" in s and not s.startswith(("sources/", "queries/"))   # queries=缓存层,经索引/grep 发现
        and inbound_organic[s] == 0 and s.split("/")[-1] not in META_STEMS)
    src_pages = [pg for pg in fmmod.iter_pages(wiki, subdirs=("sources",), profile=profile)]
    stub_sources = {pg["rel"] for pg in src_pages if _s(pg["meta"], "status") == "stub"}
    quasi_orphans = sorted(
        s for s in page_set if s.startswith("sources/")
        and inbound_organic[s] == 0 and s not in stub_sources)  # stub=显式接受的未整合态

    # ---- W-PAGE-4 frontmatter 必填与漂移 --------------------------------
    pipelines = cfg.get("pipelines", [])
    fm_missing, fm_drift = [], []
    pages = list(fmmod.iter_pages(wiki, profile=profile))
    for pg in pages:
        rel, meta = pg["rel"], pg["meta"]
        if not meta:
            fm_missing.append("%s: 无 frontmatter" % rel)
            continue
        is_src = rel.startswith("sources/")
        need = list(REQUIRED_ALL)
        if is_src:
            need += list(REQUIRED_SRC) + [f["key"] for f in facets]
        miss = [k for k in need if not _s(meta, k) and not (isinstance(meta.get(k), list) and meta.get(k))]
        if miss:
            fm_missing.append("%s: 缺 %s" % (rel, ", ".join(miss)))
        want_type = TYPE_BY_DIR[rel.split("/")[0]]
        got_type = _s(meta, "type")
        if got_type and got_type != want_type:
            fm_drift.append("%s: type=%s 与目录不符(应为 %s)" % (rel, got_type, want_type))
        if is_src and not _s(meta, "source_url"):
            raw_file = _s(meta, "raw_file")
            kind = next((pl.get("kind") for pl in pipelines
                         if raw_file.startswith(pl.get("raw_dir", "\x00").rstrip("/") + "/")), None)
            if kind in ("pull", "rolling"):
                fm_missing.append("%s: 缺 source_url(%s 型管线来源必填;内生 push 源可省)" % (rel, kind))
            elif kind is None and raw_file:
                fm_drift.append("%s: raw_file=%s 未匹配任何管线 raw_dir(source_url 亦缺)" % (rel, raw_file))

    # ---- W-PAGE-1 页面 token 预算 ---------------------------------------
    budget = cfg["budgets"]["page_tokens"]
    overweight = []
    for p in all_md:
        rel = p.relative_to(wiki).as_posix()[:-3]
        if rel in derived or rel == "log" or rel.endswith(("-timeline", "-appendix")):
            continue  # 派生物/append-only/L3 附录层(锚定/grep 访问)豁免
        tok = fmmod.est_tokens(p.read_text(encoding="utf-8"), profile)
        if tok > budget:
            overweight.append("%s ≈%d tok(预算 %d,拆 -timeline/-appendix 子页)" % (rel, tok, budget))

    # ---- W-LNT-2 _map 行数 ----------------------------------------------
    map_items = []
    map_path = wiki / "_map.md"
    if map_path.is_file():
        n = len(map_path.read_text(encoding="utf-8").splitlines())
        if n > cfg["budgets"]["map_lines"]:
            map_items.append("wiki/_map.md %d 行 > 预算 %d(超限内容下沉契约/子索引,绝不长大)"
                             % (n, cfg["budgets"]["map_lines"]))
    else:
        map_items.append("wiki/_map.md 缺失(agent 路由入口不存在)")

    # ---- W-IDX-1 索引新鲜度 + 生成区标记 --------------------------------
    stale = []
    try:
        import build_index
        agg = build_index.agg_lines(wiki, cfg)
        idx_path = wiki / "index.md"
        idx_text = idx_path.read_text(encoding="utf-8") if idx_path.is_file() else None
        if idx_text is None:
            stale.append("wiki/index.md 缺失 → 跑 python3 tools/build_index.py")
        else:
            for kind, lines in agg.items():
                for line in lines:
                    if line not in idx_text:
                        stale.append("index.md 落后: %s…" % line[:90])
        facet, shards = build_index.source_shards(wiki, cfg)
        for bucket, lines in shards.items():
            name = "index-sources-%s.md" % bucket if bucket else "index-sources.md"
            sp = wiki / name
            if not sp.is_file():
                if lines:
                    stale.append("wiki/%s 缺失 → 跑 python3 tools/build_index.py" % name)
                continue
            stxt = sp.read_text(encoding="utf-8")
            for line in lines:
                if line not in stxt:
                    stale.append("%s 落后: %s…" % (name, line[:90]))
        cpath = wiki / "contradictions.md"
        if cpath.is_file():
            ctxt = cpath.read_text(encoding="utf-8")
            for line in build_index.contradiction_lines(wiki):
                if line not in ctxt:
                    stale.append("contradictions.md 落后: %s…" % line[:90])
        elif build_index.contradiction_lines(wiki):
            stale.append("wiki/contradictions.md 缺失 → 跑 python3 tools/build_index.py")
        # 生成区标记(手编检测的机械近似:派生物必须保留 generated 标记)
        for s in sorted(derived):
            txt = (wiki / (s + ".md")).read_text(encoding="utf-8")
            if GEN_MARK_PREFIX not in txt:
                stale.append("%s.md 缺 `<!-- generated` 标记(疑手工重写;派生物禁手编)" % s)
    except Exception as e:  # noqa: BLE001 — 校验器自身故障降级为单条报告
        stale.append("(无法校验索引新鲜度:%s)" % e)

    # ---- W-LNT-3 staleness 过期未核实 -----------------------------------
    windows = {k: int(DUR_RE.match(v).group(1))
               for k, v in cfg.get("staleness", {}).get("by_source_kind", {}).items()
               if DUR_RE.match(v)}
    stale_pages = []
    for pg in pages:
        sk = _s(pg["meta"], "source_kind")
        if sk not in windows:
            continue
        verified = _s(pg["meta"], "verified")
        base = _pdate(verified) or _pdate(_s(pg["meta"], "created"))
        if base is None:
            stale_pages.append("%s: source_kind=%s 但 verified:/created: 均不可解析" % (pg["rel"], sk))
        elif (today - base).days > windows[sk]:
            stale_pages.append("%s: 过期未核实 — source_kind=%s 窗口 %dd,自%s %s 起已 %d 天"
                               % (pg["rel"], sk, windows[sk],
                                  " verified:" if verified else " created:(无 verified)",
                                  base.isoformat(), (today - base).days))

    # ---- W-ING-1 light 档占比 -------------------------------------------
    light_items = []
    if src_pages:
        n_light = sum(1 for pg in src_pages if _s(pg["meta"], "ingest_tier") == "light")
        if n_light / len(src_pages) > 0.5:
            light_items.append("light 档源页 %d/%d(>50%%)— 剪藏化风险:按 rule-of-three 晋升 full,清 followups 待晋升"
                               % (n_light, len(src_pages)))

    # ---- W-LOG-1 log 行格式 ---------------------------------------------
    log_items = []
    log_path = wiki / "log.md"
    if log_path.is_file():
        for i, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("## ") and not LOG_LINE_RE.match(line):
                log_items.append("log.md:%d: %s" % (i, line[:80]))
    else:
        log_items.append("wiki/log.md 缺失(操作史不存在)")

    # ---- W-ARCH-3 根命名空间白名单 --------------------------------------
    ns_items = sorted(
        e.name + ("/" if e.is_dir() else "")
        for e in root.iterdir()
        if not e.name.startswith(".") and e.name not in ROOT_WHITELIST)

    # ---- W-IDX-2 人机目录同 build(soft:jsonl 存在性)--------------------
    idx2_items = []
    if any("/" in s for s in page_set) and not (root / "site" / "agent" / "pages.jsonl").is_file():
        idx2_items.append("site/agent/pages.jsonl 缺失 — 人读 index 与机器 jsonl 应同一次 build 产出"
                          "(跑 python3 tools/build_site.py)")

    # ---- W-SEC-2 gitignore + 凭证样式扫描(soft)-------------------------
    sec_items = []
    gi = root / ".gitignore"
    if not gi.is_file():
        sec_items.append(".gitignore 缺失(state/、*.env 应入 gitignore)")
    else:
        gi_lines = [ln.strip().rstrip("/") for ln in gi.read_text(encoding="utf-8").splitlines()]
        if "state" not in gi_lines:
            sec_items.append(".gitignore 未含 state/(state 内有适配器 manifest/临时件,禁入仓)")
    cred_re = re.compile(r'"[^"]*(?:api[_-]?key|secret|password|passwd|access[_-]?token)[^"]*"'
                         r'\s*:\s*"[^"]{4,}"', re.I)
    for f in (root / "wiki.config.json", root / "framework" / "MANIFEST.json"):
        if f.is_file() and cred_re.search(f.read_text(encoding="utf-8")):
            sec_items.append("%s: 疑似凭证样式字段 — 凭证只走环境变量,禁落 config/manifest"
                             % f.relative_to(root).as_posix())

    # ---- W-XRF-1 peers soft 检查 ----------------------------------------
    xrf_items = []
    peers = {p["alias"]: Path(str(p["path"])).expanduser() for p in cfg.get("peers", [])}
    seen_alias_warn = set()
    slug_cache = {}
    for alias, slug, src_rel, lineno in peer_links:
        if alias not in peers:
            xrf_items.append("%s:%d: [[%s::%s]] — alias 未在 config peers 声明" % (src_rel, lineno, alias, slug))
            continue
        base = peers[alias]
        if not base.is_dir():
            if alias not in seen_alias_warn:
                seen_alias_warn.add(alias)
                n = sum(1 for a, _s2, _r, _l in peer_links if a == alias)
                xrf_items.append("peer %s 不可达(%s;共 %d 处引用)— soft,不 fail" % (alias, base, n))
            continue
        if alias not in slug_cache:
            slugs = set()
            jp = base / "site" / "agent" / "pages.jsonl"
            if jp.is_file():
                for ln in jp.read_text(encoding="utf-8").splitlines():
                    try:
                        slugs.add(json.loads(ln).get("slug", ""))
                    except json.JSONDecodeError:
                        continue
            else:
                xrf_items.append("peer %s 缺派生索引 site/agent/pages.jsonl(先在对方实例跑 build)" % alias)
            slug_cache[alias] = slugs
        if slug not in slug_cache[alias] and not (base / "wiki" / (slug + ".md")).is_file():
            xrf_items.append("%s:%d: [[%s::%s]] — peer 断链(pages.jsonl 与 wiki/ 均未命中)"
                             % (src_rel, lineno, alias, slug))

    # ---- W-UPG-1 MANIFEST hash(--manifest)------------------------------
    manifest_items = []
    if with_manifest:
        mf = root / "framework" / "MANIFEST.json"
        if not mf.is_file():
            manifest_items.append("framework/MANIFEST.json 缺失,无法校验 frozen 档(W-UPG-1)")
        else:
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                for f in data.get("files", []):
                    if f.get("tier") != "frozen":
                        continue
                    cand = [root / f["path"], root / "framework" / "base" / f["path"]]
                    target = next((c for c in cand if c.is_file()), None)
                    if target is None:
                        manifest_items.append("%s: frozen 档文件缺失(MANIFEST 声明)" % f["path"])
                        continue
                    got = hashlib.sha256(target.read_bytes()).hexdigest()
                    if got != f.get("sha256"):
                        manifest_items.append(
                            "%s: sha256 漂移 → fork 警告:确要改请在 MANIFEST 显式声明 fork,"
                            "否则升级时被覆盖丢失(W-UPG-1)" % f["path"])
            except (json.JSONDecodeError, KeyError) as e:
                manifest_items.append("framework/MANIFEST.json 解析失败:%s" % e)

    checks = [
        _chk("broken_links", "W-PAGE-3", "断链 wikilink / Broken wikilinks", "error", broken_items,
             "链接指向不存在的页。修 slug;单提及目标按 rule-of-three 去链接化,记 followups 待晋升。"),
        _chk("promote", "W-PAGE-3", "晋升候选 / Referenced ≥2 but missing", "warning", promote_items,
             "被多处引用却没有独立页(rule-of-three)—— 值得建页。"),
        _chk("orphans", "W-PAGE-3", "孤儿聚合页 / Orphan aggregate pages", "warning", orphans,
             "无任何有机入链(索引/contradictions 等派生物不算)。补交叉引用或并入相关页。"),
        _chk("quasi_orphan_sources", "W-ING-1", "准孤儿源页 / Sources w/o aggregate inlink", "warning",
             quasi_orphans, "只被索引收录、未被任何聚合页引用 —— ingest 深度不足(剪藏化),补 touch 或标 stub。"),
        _chk("fm_required", "W-PAGE-4", "Frontmatter 必填缺失", "error", fm_missing,
             "title/description/type/created/tags/status;源页另带 source_kind/raw_file/"
             "date_published/date_ingested + config facet 字段。description 是分诊面,每页必填(W-PAGE-2)。"),
        _chk("fm_drift", "W-PAGE-4", "Frontmatter 漂移", "error", fm_drift,
             "type 与所在目录不符 / raw_file 不在任何管线 raw_dir 下。"),
        _chk("overweight", "W-PAGE-1", "超预算页 / Pages over token budget", "warning", overweight,
             "超 budgets.page_tokens 的页应拆「精华主页 + 子页」,主页留指针。"),
        _chk("map_budget", "W-LNT-2", "_map 行数预算", "error", map_items,
             "入口页吃每会话固定预算,超限内容下沉契约或子索引。"),
        _chk("stale_index", "W-IDX-1", "索引新鲜度 / 派生物落后或被手编", "error", stale,
             "跑 python3 tools/build_index.py 重新派生;要改摘要改对应页 description:。"),
        _chk("agent_jsonl", "W-IDX-2", "人机目录同 build(soft)", "warning", idx2_items,
             "index 与 site/agent/*.jsonl 由同一次 build 产出,不允许各自演化。"),
        _chk("staleness", "W-LNT-3", "过期未核实 / Stale operational pages", "warning", stale_pages,
             "stale 的操作性页面是危险品:对着实物核实后 bump verified:,推翻的结论按 W-ING-3 处理。"),
        _chk("light_ratio", "W-ING-1", "light 档占比告警", "warning", light_items,
             "light 档只是延迟整合,不是终点;占比过半说明复利闭环在退化。"),
        _chk("log_format", "W-LOG-1", "log 行格式抽查", "error", log_items,
             "行格式 `## [YYYY-MM-DD] <op> | <one-line>`(ASCII 分隔符);历史条目禁改,只修新增。"),
        _chk("root_namespace", "W-ARCH-3", "根命名空间白名单", "warning", ns_items,
             "根目录只允许契约架构图声明的成员;杂物一律入 _attic/。"),
        _chk("gitignore_creds", "W-SEC-2", "state/.gitignore 与凭证扫描(soft)", "warning", sec_items,
             "凭证只走环境变量;state/、*.env 入 gitignore。"),
        _chk("peer_links", "W-XRF-1", "跨实例链接(soft)", "warning", xrf_items,
             "peer 断链/不可达仅计数,不 fail;peers 路径为本机信息,不入发布物(W-SEC-2)。"),
    ]
    if with_manifest:
        # exit 语义归 error 档(sync 常跑路径靠 rc=1 当场报警,W-UPG-1);措辞仍是 fork 警告
        checks.append(_chk("manifest", "W-UPG-1", "frozen 档 MANIFEST hash 校验(fork 警告)",
                           "error", manifest_items,
                           "frozen 文件禁改;确要改 = 显式声明 fork,此后该文件不随框架覆盖升级。"))

    n_err = sum(c["count"] for c in checks if c["severity"] == "error")
    n_warn = sum(c["count"] for c in checks if c["severity"] == "warning")
    return {"ok": n_err == 0 and n_warn == 0, "errors": n_err, "warnings": n_warn,
            "checks": checks, "totals": {c["id"]: c["count"] for c in checks}}


def print_report(r: dict) -> None:
    print("=" * 56)
    print("  Wiki 机械体检 / mechanical lint(规则 ID 见 framework/RULES.md)")
    print("=" * 56)
    for c in r["checks"]:
        flag = "✅" if c["count"] == 0 else ("🔴" if c["severity"] == "error" else "🟡")
        print("\n%s [%s] %s: %d" % (flag, c["rule"], c["label"], c["count"]))
        for it in c["items"][:SHOW_CAP]:
            print("    · [%s] %s" % (c["rule"], it))
        if c["count"] > SHOW_CAP:
            print("    … 还有 %d 条" % (c["count"] - SHOW_CAP))
        if c["count"] and c["hint"]:
            print("    ↳ %s" % c["hint"])
    print("\n%s(error %d / warning %d;exit 1 仅由 error 级触发,soft 项不 fail)"
          % ("✅ 全部通过" if r["ok"] else "⚠️ 见上", r["errors"], r["warnings"]))
    print("语义体检(跨页矛盾/过时声明/晋升裁决/mature 空段)请按契约 lint 工作流走 agent 审。")


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki 机械 lint(完整版;--check-slots/--check-config 保持 M1 语义)")
    ap.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    ap.add_argument("--json", action="store_true", help="机器输出(结构化)")
    ap.add_argument("--manifest", action="store_true",
                    help="附加 frozen 档 sha256 校验(framework/MANIFEST.json,W-UPG-1)")
    ap.add_argument("--check-slots", action="store_true", help="扫描渲染残留(需配 --target)")
    ap.add_argument("--target", default=None, help="实例根目录(--check-slots 用)")
    ap.add_argument("--check-config", default=None, metavar="PATH", help="校验 wiki.config.json")
    args = ap.parse_args(argv)

    # ---- M1 模式:给了任一 M1 旗标就只跑 M1 检查(行为不变)----
    if args.check_slots or args.check_config:
        failed = False
        m1 = {}

        if args.check_slots:
            if not args.target:
                print("错误: --check-slots 需要 --target <dir>", file=sys.stderr)
                return 2
            if not Path(args.target).is_dir():
                print("错误: target 目录不存在:%s" % args.target, file=sys.stderr)
                return 2
            findings = check_slots(args.target)
            m1["check_slots"] = findings
            if findings:
                failed = True
                print("check-slots: %d 处残留(渲染未完成或模板私造槽位):" % len(findings))
                for f in findings:
                    print("  - %s" % f)
            else:
                print("check-slots: OK(0 残留)")

        if args.check_config:
            errors, warns = check_config(args.check_config)
            m1["check_config"] = {"errors": errors, "warnings": warns}
            for w in warns:
                print("check-config 警告: %s" % w)
            if errors:
                failed = True
                print("check-config: %d 处错误:" % len(errors))
                for e in errors:
                    print("  - %s" % e)
            else:
                print("check-config: OK(%s)" % args.check_config)

        if args.json:
            print(json.dumps({"ok": not failed, **m1}, ensure_ascii=False))
        return 1 if failed else 0

    # ---- 完整机械 lint(默认模式)----
    try:
        import fm as fmmod
    except ImportError as e:
        print("错误: 无法导入 tools/lib/fm.py(钉死 API 所在):%s" % e, file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    try:
        cfg = fmmod.load_config(root)
    except fmmod.ConfigError as e:
        print("配置错误: %s" % e, file=sys.stderr)
        return 2
    if not (root / "wiki").is_dir():
        print("配置错误: %s/wiki 不存在(--root 应指向实例根)" % root, file=sys.stderr)
        return 2

    r = run_lint(root, cfg, fmmod, with_manifest=args.manifest)
    if args.json:
        print(json.dumps({"root": str(root), **r}, ensure_ascii=False))
    else:
        print_report(r)
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
