#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki init_render — 确定性渲染器(M1,仅 Python 标准库)

用法:
    python3 tools/init_render.py --config <wiki.config.json> --target <dir> [--date YYYY-MM-DD] [--force]

职责(Spec §9 greenfield / PRD F8):
  1. 读 config → 手写校验(必填/类型/枚举/模式;错误信息带字段路径;零第三方依赖);
  2. 计算全部槽位值(注册表 SLOT_REGISTRY;模板私造槽位 = 硬错误);
  3. 条件模块块 <!--BEGIN:key--> … <!--END:key-->(key ∈ multi_facet / rolling_source / peers):
     条件满足去标记留内容,不满足整块删除;
  4. 渲染模板 → 实例;frozen 件(tools/ schema/)原样拷贝(W-UPG-1);
  5. 实例骨架目录、AGENTS.md symlink(失败降级硬拷贝并提醒)、framework/{VERSION,base/} 模板快照、
     wiki/log.md 首条 bootstrap(W-LOG-1);
  6. 任何 <SLOT: 残留 → 硬报错退出非 0;已存在文件无 --force 逐个跳过并列出(adopt 友好)。

确定性保证:同 config + 同 --date + 同模板 ⇒ 两次渲染产物逐字节相同(agent 只填值,不写正文)。
模板根解析:优先脚本所在框架仓库(tools/..);实例内重渲染时回退 framework/base/ 模板快照。
单源导出:compute_conds / stamp_dates / snapshot_manifest 为模块级函数,upgrade.py 双版本
加载本模块后直接复用——三处口径以本文件为单源,勿改回 main 内联。
"""

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量与注册表

SLOT_REGISTRY = (
    "domain.name", "domain.description", "lang.clause", "trust.clause",
    "pipelines.table", "pipelines.raw_dirs", "source.naming_rules", "source.kind_enum",
    "facets.fields", "facets.badges",
    "budgets.page_tokens", "budgets.map_lines", "budgets.boot_tokens",
    "ingest.tier_rules", "typology.table", "staleness.rules",
    "peers.list", "tools.cmds", "framework.version",
)
COND_KEYS = ("multi_facet", "rolling_source", "peers")

LANG_ENUM = ("zh", "en")
TRUST_ENUM = ("internal-authoritative", "official-biased", "needs-verification")
KIND_ENUM = ("pull", "push", "rolling")
TIER_ENUM = ("full", "light")
PROFILE_ENUM = ("cjk", "latin")
PAGE_TYPES = ("source", "entity", "concept", "synthesis", "query")
TOP_KEYS = {"$schema", "framework_version", "domain", "facets", "pipelines", "budgets",
            "ingest_tiers", "typology_map", "staleness", "peers", "x-extensions"}

SLOT_RE = re.compile(r"<SLOT:([A-Za-z0-9_.]+)>")
BEGIN_RE = re.compile(r"^\s*<!--BEGIN:([A-Za-z0-9_]+)-->\s*$")
END_RE = re.compile(r"^\s*<!--END:([A-Za-z0-9_]+)-->\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-.+][0-9A-Za-z.-]+)?$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
KINDNAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PREFIX_RE = re.compile(r"^[a-z0-9-]*$")
RAWDIR_RE = re.compile(r"^raw/[A-Za-z0-9._/-]+$")
DUR_RE = re.compile(r"^\d+d$")

# lang / trust_posture 枚举 → 契约固定文案(封闭映射,Spec §2)
LANG_CLAUSES = {
    "zh": "默认用户交互语言:**中文**。源引用保留原文不译;技术术语可保留英文。高频页 `aliases` 必须中英双语(检索锚点)。",
    "en": "Default user-facing language: **English**. Quote sources verbatim; keep technical terms in their original language. High-traffic pages must carry bilingual `aliases` (retrieval anchors).",
}
TRUST_CLAUSES = {
    "internal-authoritative": "内部一手材料 = 权威来源:如实收录,无需第三方验证;口径冲突时以更新的内部决策为准并标「演进」(W-ING-3)。",
    "official-biased": "官方一手来源 = 权威但有立场:营销口径去夸张化;数字/日期/价格如实记录并标注「官方声明,未必第三方验证」。",
    "needs-verification": "来源默认待验证:关键数字/结论进聚合页前须交叉验证;未验证事实显式标注并记 followups「待验证」(W-LOG-2)。",
}


def _fmt(v):
    return json.dumps(v, ensure_ascii=False)


# ---------------------------------------------------------------- config 校验(手写,单源;lint --check-config 复用)

def validate_config(cfg):
    """返回 (errors, warnings),条目均带字段路径。"""
    errors, warnings = [], []
    err = lambda path, msg: errors.append("%s: %s" % (path, msg))
    warn = lambda path, msg: warnings.append("%s: %s" % (path, msg))

    if not isinstance(cfg, dict):
        return ["<root>: 顶层必须是 JSON object"], []

    for k in cfg:
        if k not in TOP_KEYS and not k.startswith("x-"):
            err(k, "未知字段(自由扩展请用 x- 前缀)")

    fv = cfg.get("framework_version")
    if fv is None:
        err("framework_version", "必填")
    elif not isinstance(fv, str) or not SEMVER_RE.match(fv):
        err("framework_version", "须为语义版本字符串(如 \"1.0.0\"),得到 %s" % _fmt(fv))

    sc = cfg.get("$schema")
    if sc is not None and not isinstance(sc, str):
        err("$schema", "须为字符串")

    # --- domain
    dom = cfg.get("domain")
    if dom is None:
        err("domain", "必填")
    elif not isinstance(dom, dict):
        err("domain", "须为 object")
    else:
        for k in dom:
            if k not in {"name", "description", "lang", "trust_posture"} and not k.startswith("x-"):
                err("domain.%s" % k, "未知字段")
        name = dom.get("name")
        if name is None:
            err("domain.name", "必填")
        elif not isinstance(name, str) or not SLUG_RE.match(name):
            err("domain.name", "须为 ASCII slug(^[a-z0-9][a-z0-9_-]*$),得到 %s" % _fmt(name))
        desc = dom.get("description")
        if desc is None:
            err("domain.description", "必填")
        elif not isinstance(desc, str) or not desc.strip():
            err("domain.description", "须为非空字符串")
        lang = dom.get("lang")
        if lang is None:
            err("domain.lang", "必填")
        elif lang not in LANG_ENUM:
            err("domain.lang", "值 %s 不在枚举 %s" % (_fmt(lang), "|".join(LANG_ENUM)))
        tp = dom.get("trust_posture")
        if tp is None:
            err("domain.trust_posture", "必填")
        elif tp not in TRUST_ENUM:
            err("domain.trust_posture", "值 %s 不在枚举 %s" % (_fmt(tp), "|".join(TRUST_ENUM)))

    # --- facets
    facets = cfg.get("facets", [])
    if not isinstance(facets, list):
        err("facets", "须为数组")
    else:
        fkeys = set()
        for i, f in enumerate(facets):
            p = "facets[%d]" % i
            if not isinstance(f, dict):
                err(p, "须为 object")
                continue
            for k in f:
                if k not in {"key", "values", "shard_index", "badges"} and not k.startswith("x-"):
                    err("%s.%s" % (p, k), "未知字段")
            key = f.get("key")
            if key is None:
                err("%s.key" % p, "必填")
            elif not isinstance(key, str) or not SLUG_RE.match(key):
                err("%s.key" % p, "须为 slug,得到 %s" % _fmt(key))
            elif key in fkeys:
                err("%s.key" % p, "facet key 重复:%s" % _fmt(key))
            else:
                fkeys.add(key)
            vals = f.get("values")
            if vals is None:
                err("%s.values" % p, "必填")
            elif not isinstance(vals, list) or not vals or not all(isinstance(v, str) and v for v in vals):
                err("%s.values" % p, "须为非空字符串数组")
            elif len(set(vals)) != len(vals):
                err("%s.values" % p, "取值重复")
            si = f.get("shard_index")
            if si is not None and not isinstance(si, bool):
                err("%s.shard_index" % p, "须为布尔")
            badges = f.get("badges")
            if badges is not None:
                if not isinstance(badges, dict) or not all(isinstance(v, str) for v in badges.values()):
                    err("%s.badges" % p, "须为 object(值→徽章字符串)")
                elif isinstance(vals, list):
                    for bk in badges:
                        if bk not in vals and bk != "cross":
                            warn("%s.badges.%s" % (p, bk), "徽章键不在 values(特殊键 cross 除外)")

    # --- pipelines
    pls = cfg.get("pipelines")
    all_kinds = []
    if pls is None:
        err("pipelines", "必填")
    elif not isinstance(pls, list) or not pls:
        err("pipelines", "须为非空数组")
    else:
        names, raw_dirs = set(), set()
        for i, pl in enumerate(pls):
            p = "pipelines[%d]" % i
            if not isinstance(pl, dict):
                err(p, "须为 object")
                continue
            for k in pl:
                if k not in {"name", "kind", "raw_dir", "prefix", "adapter", "source_kinds"} and not k.startswith("x-"):
                    err("%s.%s" % (p, k), "未知字段")
            nm = pl.get("name")
            if nm is None:
                err("%s.name" % p, "必填")
            elif not isinstance(nm, str) or not SLUG_RE.match(nm):
                err("%s.name" % p, "须为 slug,得到 %s" % _fmt(nm))
            elif nm in names:
                err("%s.name" % p, "管线名重复:%s" % _fmt(nm))
            else:
                names.add(nm)
            kd = pl.get("kind")
            if kd is None:
                err("%s.kind" % p, "必填")
            elif kd not in KIND_ENUM:
                err("%s.kind" % p, "值 %s 不在枚举 pull|push|rolling" % _fmt(kd))
            rd = pl.get("raw_dir")
            if rd is None:
                err("%s.raw_dir" % p, "必填")
            elif not isinstance(rd, str) or not RAWDIR_RE.match(rd):
                err("%s.raw_dir" % p, "须位于 raw/ 下(^raw/…,W-ARCH-1),得到 %s" % _fmt(rd))
            else:
                if rd in raw_dirs:
                    warn("%s.raw_dir" % p, "多条管线共用 %s,pending 计算可能互相干扰" % _fmt(rd))
                raw_dirs.add(rd)
            pf = pl.get("prefix")
            if pf is not None and (not isinstance(pf, str) or not PREFIX_RE.match(pf)):
                err("%s.prefix" % p, "须匹配 ^[a-z0-9-]*$,得到 %s" % _fmt(pf))
            ad = pl.get("adapter")
            if ad is not None and (not isinstance(ad, str) or not ad.strip()):
                err("%s.adapter" % p, "须为非空字符串路径,或哨兵字面量 \"manual\"")
            # adapter="manual" 哨兵:人工投放快照/文件进 raw_dir,合法且免适配器
            # (sync 跳过抓取不告警,契约见 adapters/CONTRACT.md「manual 哨兵」);
            # 仍未声明 adapter 字段的 pull/rolling 保留下方警告。
            if ad is None and kd in ("pull", "rolling"):
                warn("%s.adapter" % p, "%s 型管线未声明适配器:sync 将跳过该管线(契约见 adapters/CONTRACT.md)" % kd)
            sk = pl.get("source_kinds")
            if sk is not None:
                if not isinstance(sk, list) or not all(isinstance(v, str) and KINDNAME_RE.match(v) for v in sk):
                    err("%s.source_kinds" % p, "须为字符串数组,元素匹配 ^[a-z0-9][a-z0-9-]*$")
                else:
                    dups = sorted({v for v in sk if sk.count(v) > 1})
                    if dups:
                        err("%s.source_kinds" % p, "重复项:%s" % ",".join(dups))
                    all_kinds += sk

    # --- budgets
    b = cfg.get("budgets")
    if b is not None:
        if not isinstance(b, dict):
            err("budgets", "须为 object")
        else:
            for k, v in b.items():
                if k == "est_tokens_profile":
                    if v not in PROFILE_ENUM:
                        err("budgets.%s" % k, "值 %s 不在枚举 cjk|latin" % _fmt(v))
                elif k in {"page_tokens", "map_lines", "boot_tokens", "raw_slice_tokens"}:
                    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                        err("budgets.%s" % k, "须为正整数,得到 %s" % _fmt(v))
                elif not k.startswith("x-"):
                    err("budgets.%s" % k, "未知字段")

    # --- ingest_tiers
    t = cfg.get("ingest_tiers")
    if t is not None:
        if not isinstance(t, dict):
            err("ingest_tiers", "须为 object")
        else:
            for k in t:
                if k not in {"default", "by_source_kind", "min_touch"} and not k.startswith("x-"):
                    err("ingest_tiers.%s" % k, "未知字段")
            dv = t.get("default")
            if dv is not None and dv not in TIER_ENUM:
                err("ingest_tiers.default", "值 %s 不在枚举 full|light" % _fmt(dv))
            bsk = t.get("by_source_kind")
            if bsk is not None:
                if not isinstance(bsk, dict):
                    err("ingest_tiers.by_source_kind", "须为 object")
                else:
                    for k, v in bsk.items():
                        if v not in TIER_ENUM:
                            err("ingest_tiers.by_source_kind.%s" % k, "值 %s 不在枚举 full|light" % _fmt(v))
                        if all_kinds and k not in all_kinds:
                            warn("ingest_tiers.by_source_kind.%s" % k, "该 source_kind 未在任何 pipelines[].source_kinds 声明")
            mt = t.get("min_touch")
            if mt is not None:
                if not isinstance(mt, dict):
                    err("ingest_tiers.min_touch", "须为 object")
                else:
                    for k, v in mt.items():
                        if k not in TIER_ENUM:
                            err("ingest_tiers.min_touch.%s" % k, "键只允许 full|light")
                        elif not isinstance(v, int) or isinstance(v, bool) or v < 0:
                            err("ingest_tiers.min_touch.%s" % k, "须为非负整数,得到 %s" % _fmt(v))

    # --- typology_map
    tm = cfg.get("typology_map")
    if tm is not None:
        if not isinstance(tm, dict):
            err("typology_map", "须为 object")
        else:
            for k, v in tm.items():
                if k not in PAGE_TYPES:
                    err("typology_map.%s" % k, "键只允许 %s(类型名 frozen)" % "|".join(PAGE_TYPES))
                elif not isinstance(v, str) or not v.strip():
                    err("typology_map.%s" % k, "须为非空字符串")

    # --- staleness
    st = cfg.get("staleness")
    if st is not None:
        if not isinstance(st, dict):
            err("staleness", "须为 object")
        else:
            for k in st:
                if k != "by_source_kind" and not k.startswith("x-"):
                    err("staleness.%s" % k, "未知字段")
            sb = st.get("by_source_kind")
            if sb is not None:
                if not isinstance(sb, dict):
                    err("staleness.by_source_kind", "须为 object")
                else:
                    for k, v in sb.items():
                        if not isinstance(v, str) or not DUR_RE.match(v):
                            err("staleness.by_source_kind.%s" % k, "须为天数窗口(如 \"180d\"),得到 %s" % _fmt(v))
                        if all_kinds and k not in all_kinds:
                            warn("staleness.by_source_kind.%s" % k, "该 source_kind 未在任何 pipelines[].source_kinds 声明")

    # --- peers
    prs = cfg.get("peers")
    if prs is not None:
        if not isinstance(prs, list):
            err("peers", "须为数组")
        else:
            aliases = set()
            for i, pr in enumerate(prs):
                p = "peers[%d]" % i
                if not isinstance(pr, dict):
                    err(p, "须为 object")
                    continue
                for k in pr:
                    if k not in {"alias", "path"} and not k.startswith("x-"):
                        err("%s.%s" % (p, k), "未知字段")
                al = pr.get("alias")
                if al is None:
                    err("%s.alias" % p, "必填")
                elif not isinstance(al, str) or not SLUG_RE.match(al):
                    err("%s.alias" % p, "须为 slug,得到 %s" % _fmt(al))
                elif al in aliases:
                    err("%s.alias" % p, "alias 重复:%s" % _fmt(al))
                else:
                    aliases.add(al)
                pth = pr.get("path")
                if pth is None:
                    err("%s.path" % p, "必填")
                elif not isinstance(pth, str) or not pth.strip():
                    err("%s.path" % p, "须为非空本机路径(不入发布物,W-XRF-1/W-SEC-2)")

    xe = cfg.get("x-extensions")
    if xe is not None and not isinstance(xe, dict):
        err("x-extensions", "须为 object")

    return errors, warnings


def apply_defaults(cfg):
    """校验通过后补缺省值;返回深拷贝,不改原对象。"""
    out = json.loads(json.dumps(cfg))
    out.setdefault("facets", [])
    out.setdefault("peers", [])
    b = out.setdefault("budgets", {})
    b.setdefault("page_tokens", 8000)
    b.setdefault("map_lines", 100)
    b.setdefault("boot_tokens", 4000)
    b.setdefault("raw_slice_tokens", 1200)
    b.setdefault("est_tokens_profile", "cjk" if out["domain"]["lang"] == "zh" else "latin")
    t = out.setdefault("ingest_tiers", {})
    t.setdefault("default", "full")
    t.setdefault("by_source_kind", {})
    mt = t.setdefault("min_touch", {})
    mt.setdefault("full", 5)
    mt.setdefault("light", 1)
    out.setdefault("typology_map", {})
    st = out.setdefault("staleness", {})
    st.setdefault("by_source_kind", {})
    for p in out["pipelines"]:
        p.setdefault("prefix", "")
        p.setdefault("source_kinds", [])
    out.setdefault("x-extensions", {})
    return out


# ---------------------------------------------------------------- 槽位计算

def compute_slots(cfg, fw_version):
    d = cfg["domain"]
    pipelines = cfg["pipelines"]
    slots = {}
    slots["domain.name"] = d["name"]
    slots["domain.description"] = d["description"]
    slots["lang.clause"] = LANG_CLAUSES[d["lang"]]
    slots["trust.clause"] = TRUST_CLAUSES[d["trust_posture"]]
    slots["framework.version"] = fw_version

    # pipelines.table
    rows = ["| 管线 | 类型 | raw 目录 | 前缀 | source_kinds | 适配器 |",
            "|---|---|---|---|---|---|"]
    for p in pipelines:
        kinds = "、".join(p["source_kinds"]) if p["source_kinds"] else "—"
        prefix = "`%s`" % p["prefix"] if p["prefix"] else "—"
        if p.get("adapter") == "manual":
            adapter = "manual(人工投放,免适配器)"
        elif p.get("adapter"):
            adapter = "`%s`" % p["adapter"]
        elif p["kind"] == "push":
            adapter = "—(直投,免适配器)"
        else:
            adapter = "待接入(见 adapters/CONTRACT.md)"
        rows.append("| %s | %s | `%s/` | %s | %s | %s |"
                    % (p["name"], p["kind"], p["raw_dir"], prefix, kinds, adapter))
    slots["pipelines.table"] = "\n".join(rows)
    slots["pipelines.raw_dirs"] = "、".join("`%s/`" % p["raw_dir"] for p in pipelines)

    # source.naming_rules(单行短语:模板既有own-line也有句中/表格内用法)
    parts = []
    for p in pipelines:
        pat = "%s<date>-<slug>.md" % p["prefix"]
        if p["kind"] == "rolling":
            parts.append("**%s**(rolling)前缀 `%s`:快照整体覆盖落 `%s/`,一份源页代表整份滚动源(变化记「演进」)"
                         % (p["name"], p["prefix"] or "无", p["raw_dir"]))
        else:
            parts.append("**%s**(%s)`%s/%s`,源页 `wiki/sources/%s` 同名对齐"
                         % (p["name"], p["kind"], p["raw_dir"], pat, pat))
    slots["source.naming_rules"] = ";".join(parts)

    # source.kind_enum(全管线并集,保序去重)
    seen = []
    for p in pipelines:
        for k in p["source_kinds"]:
            if k not in seen:
                seen.append(k)
    slots["source.kind_enum"] = " | ".join(seen) if seen else \
        "(未声明——按需在 config `pipelines[].source_kinds` 补充)"

    # facets.fields / facets.badges(仅 multi_facet 模块内使用;facets 为空时块整体被删)
    # fields 取 YAML 字段行形态(源页骨架示例内直接成行);badges 取单行短语(句中嵌入)
    if cfg["facets"]:
        f_lines, b_parts = [], []
        for f in cfg["facets"]:
            f_lines.append("%s: %s" % (f["key"], " | ".join(f["values"])))
            badges = f.get("badges") or {}
            if badges:
                pairs = ",".join("%s → %s" % (k, v) for k, v in badges.items())
                b_parts.append(pairs if len(cfg["facets"]) == 1 else "%s(%s)" % (f["key"], pairs))
        slots["facets.fields"] = "\n".join(f_lines)
        slots["facets.badges"] = ";".join(b_parts) if b_parts else "(未配置徽章)"
    else:
        slots["facets.fields"] = ""
        slots["facets.badges"] = ""

    # budgets
    b = cfg["budgets"]
    slots["budgets.page_tokens"] = str(b["page_tokens"])
    slots["budgets.map_lines"] = str(b["map_lines"])
    slots["budgets.boot_tokens"] = str(b["boot_tokens"])

    # ingest.tier_rules(单行短语:模板有句中/表格内用法)
    t = cfg["ingest_tiers"]
    mt = t["min_touch"]
    light_kinds = sorted(k for k, v in t["by_source_kind"].items() if v == "light")
    full_kinds = sorted(k for k, v in t["by_source_kind"].items() if v == "full")
    tl = ["默认 **%s**(touch ≥ %d)" % (t["default"], mt[t["default"]])]
    if light_kinds:
        tl.append("light 档(touch ≥ %d,必须记 followups「待晋升」):%s"
                  % (mt["light"], "、".join("`%s`" % k for k in light_kinds)))
    if full_kinds:
        tl.append("显式 full 档(touch ≥ %d):%s"
                  % (mt["full"], "、".join("`%s`" % k for k in full_kinds)))
    tl.append("light 页 rule-of-three 达标时晋升 full")
    slots["ingest.tier_rules"] = ";".join(tl)

    # typology.table
    tm = cfg["typology_map"]
    if tm:
        rows = ["| 类型 | 本库语义 |", "|---|---|"]
        for k in PAGE_TYPES:
            if k in tm:
                rows.append("| %s | %s |" % (k, tm[k]))
        slots["typology.table"] = "\n".join(rows)
    else:
        slots["typology.table"] = "(config `typology_map` 未声明,沿用框架通用五类语义;canonical 映射表见框架 Spec §4.1)"

    # staleness.rules(单行名词短语:模板有句中用法)
    sb = cfg["staleness"]["by_source_kind"]
    if sb:
        slots["staleness.rules"] = "、".join("`%s` %s" % (k, v) for k, v in sb.items())
    else:
        slots["staleness.rules"] = "(未声明时效窗口;如需,填 config `staleness.by_source_kind`)"

    # peers.list(仅 peers 模块内使用;单行且不含裸竖线——模板有表格单元格用法)
    if cfg["peers"]:
        slots["peers.list"] = ";".join(
            "`%s` → `%s`(语法 `[[%s::<path/to/slug>]]`)" % (p["alias"], p["path"], p["alias"])
            for p in cfg["peers"])
    else:
        slots["peers.list"] = ""

    # tools.cmds(未落位工具按文件存在性标注里程碑,防契约指向不存在的命令)
    _tdir = Path(__file__).resolve().parent
    def _m2(*names):
        return "" if all((_tdir / n).exists() for n in names) else "(M2 待交付)"
    _contract = "adapters/CONTRACT.md" + ("" if (_tdir.parent / "adapters" / "CONTRACT.md").exists() else "(M2 提供)")
    cmds = [
        "- `python3 tools/sync.py`:跑全部管线采集 + 打印待 ingest 积压" + _m2("sync.py"),
        "- `python3 tools/sync.py status`:不联网看积压" + _m2("sync.py"),
        "- `python3 tools/build_site.py && python3 tools/build_index.py`:索引派生(内容/description 变更后必跑,W-IDX-1)" + _m2("build_site.py", "build_index.py"),
        "- `python3 tools/search.py \"关键词\"`:BM25 排名检索(关键词不确定时补 grep;W-IDX-3)" + _m2("search.py"),
        "- `python3 tools/bootstrap_scan.py`:冷启动只读扫宿主 repo 产 ingest 候选(候选≠投递,W-CAP-1)" + _m2("bootstrap_scan.py"),
        "- `python3 tools/lint_wiki.py`:完整机械 lint(断链/预算/新鲜度/staleness;`--manifest` 校验 frozen,W-UPG-1)",
        "- `python3 tools/eval_retrieval.py evals/golden.jsonl`:golden 回归(W-UPG-2)" + _m2("eval_retrieval.py"),
        "- `python3 tools/init_render.py --config wiki.config.json --target .`:补渲染/升级(已存在文件默认跳过)",
    ]
    for p in pipelines:
        if p.get("adapter") and p["adapter"] != "manual":   # manual 哨兵无脚本,不列命令
            cmds.append("- 管线 `%s` 适配器:`%s`(discover/fetch/status,契约见 %s)"
                        % (p["name"], p["adapter"], _contract))
    slots["tools.cmds"] = "\n".join(cmds)

    assert set(slots) == set(SLOT_REGISTRY), "槽位实现与注册表不一致"
    return slots


def compute_conds(cfg):
    """条件模块开关(config 派生;单源函数,upgrade.py import 复用)。"""
    return {
        "multi_facet": bool(cfg["facets"]),
        "rolling_source": any(p["kind"] == "rolling" for p in cfg["pipelines"]),
        "peers": bool(cfg["peers"]),
    }


# ---------------------------------------------------------------- 渲染引擎

def render_text(text, slots, conds, src):
    """条件模块块 + 槽位替换;返回 (out_text, errors)。"""
    errors = []
    out_lines = []
    stack = []  # [(key, keep)]
    for i, line in enumerate(text.splitlines(), 1):
        mb = BEGIN_RE.match(line)
        if mb:
            key = mb.group(1)
            if key not in conds:
                errors.append("%s:%d: 未知条件模块 key「%s」(允许:%s)" % (src, i, key, "/".join(COND_KEYS)))
                stack.append((key, False))
            else:
                stack.append((key, conds[key]))
            continue
        me = END_RE.match(line)
        if me:
            key = me.group(1)
            if not stack:
                errors.append("%s:%d: 孤立 <!--END:%s-->(无对应 BEGIN)" % (src, i, key))
            else:
                open_key, _ = stack.pop()
                if open_key != key:
                    errors.append("%s:%d: <!--END:%s--> 与 <!--BEGIN:%s--> 不匹配" % (src, i, key, open_key))
            continue
        if any(not keep for _, keep in stack):
            continue

        hit_unknown = []

        def _sub(m):
            k = m.group(1)
            if k in slots:
                return slots[k]
            hit_unknown.append(k)
            return m.group(0)

        new_line = SLOT_RE.sub(_sub, line)
        for k in hit_unknown:
            errors.append("%s:%d: 未知槽位 <SLOT:%s>(不在注册表)" % (src, i, k))
        if "<SLOT:" in new_line and not hit_unknown:
            errors.append("%s:%d: 槽位语法残留(key 非法或书写不完整): %s" % (src, i, new_line.strip()[:100]))
        out_lines.append(new_line)
    if stack:
        errors.append("%s: 未闭合的条件块 BEGIN:%s" % (src, ",".join(k for k, _ in stack)))
    return "\n".join(out_lines) + "\n", errors


# ---------------------------------------------------------------- 单源后处理(upgrade.py import 复用)

def stamp_dates(rendered, date):
    """wiki 页日期打戳(渲染后处理;单源函数,upgrade.py import 复用):
      a) wiki/log.md:删 bootstrap 指引注释(模板内「替换日期后删除本注释」类,渲染时代为
         执行);bootstrap 首条日期占位 [YYYY-MM-DD] → [date];
      b) 其余 wiki/*.md:frontmatter 区 created/updated 的 YYYY-MM-DD 占位 → date(W-PAGE-4)。
    rendered: [(rel, text), ...] → 返回同序新列表;非 wiki 项原样透传。"""
    out_list = []
    for rel, out in rendered:
        if rel == "wiki/log.md":
            lines = []
            for ln in out.splitlines():
                if re.match(r"^\s*<!--.*bootstrap.*-->\s*$", ln):
                    continue
                if ln.startswith("## [YYYY-MM-DD] bootstrap"):
                    ln = ln.replace("[YYYY-MM-DD]", "[%s]" % date, 1)
                lines.append(ln)
            out = "\n".join(lines) + "\n"
        elif rel.startswith("wiki/"):
            lines, in_fm, fm_seen = out.splitlines(), False, 0
            for i, ln in enumerate(lines):
                if ln.strip() == "---":
                    fm_seen += 1
                    in_fm = fm_seen == 1
                    if fm_seen >= 2:
                        break
                elif in_fm and re.match(r"^(created|updated):\s*YYYY-MM-DD\s*$", ln):
                    lines[i] = ln.split(":")[0] + ": " + date
            out = "\n".join(lines) + ("\n" if out.endswith("\n") else "")
        out_list.append((rel, out))
    return out_list


def snapshot_manifest(mf_path, target):
    """实例 MANIFEST 快照:按实例实际持有过滤(单源函数,upgrade.py import 复用)。
    读框架 MANIFEST(mf_path),滤掉 target 下不存在路径的条目——未拷入实例的框架文件
    不该出现在实例的 hash 契约里;保留 dict 外形,indent=1。
    返回落盘 JSON 字符串;读取/解析失败或结构异常(files 非数组)返回 None,
    调用方回退为原样拷贝。"""
    try:
        data = json.loads(Path(mf_path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    entries = data.get("files", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return None
    target = Path(target)
    kept = [e for e in entries if (target / e.get("path", "")).exists()]
    if isinstance(data, dict) and "files" in data:
        data = dict(data, files=kept)
    else:
        data = kept
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


# ---------------------------------------------------------------- 渲染计划(模板枚举)

def _out_name(name):
    return name.replace(".template.md", ".md")


def build_plan(tpl_root):
    """返回 (plan, missing):plan = [(src Path, out_rel str)];missing = 缺失模板清单。"""
    plan, missing = [], []

    claude = tpl_root / "CLAUDE.template.md"
    if claude.is_file():
        plan.append((claude, "CLAUDE.md"))
    else:
        missing.append("%s(契约模板,必需)" % claude)

    rules = tpl_root / ".claude" / "rules"
    rmds = sorted(rules.glob("*.md")) if rules.is_dir() else []
    if rmds:
        plan += [(p, ".claude/rules/%s" % _out_name(p.name)) for p in rmds]
    else:
        missing.append("%s/*.md(页面规则模板:source-page / aggregate-pages)" % rules)

    agent = tpl_root / ".claude" / "agents" / "wiki-reader.template.md"
    if agent.is_file():
        plan.append((agent, ".claude/agents/wiki-reader.md"))
    else:
        missing.append("%s(只读检索 subagent 模板)" % agent)

    wtpl = tpl_root / "templates" / "wiki"
    wmds = sorted(wtpl.glob("*.md")) if wtpl.is_dir() else []
    if wmds:
        plan += [(p, "wiki/%s" % _out_name(p.name)) for p in wmds]
    else:
        missing.append("%s/*.md(wiki 骨架模板:_map/overview/log/followups/contradictions)" % wtpl)

    stpl = tpl_root / "templates" / "skills"
    entries = sorted(stpl.iterdir()) if stpl.is_dir() else []
    got_skill = False
    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            for f in sorted(entry.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    rel = f.relative_to(entry).as_posix().replace(".template.md", ".md")
                    plan.append((f, ".claude/skills/%s/%s" % (entry.name, rel)))
                    got_skill = True
        elif entry.suffix == ".md":
            stem = entry.name[:-3]
            if stem.endswith(".template"):
                stem = stem[:-len(".template")]
            plan.append((entry, ".claude/skills/%s/SKILL.md" % stem))
            got_skill = True
    if not got_skill:
        missing.append("%s/(实例本地工作流 skills 模板:wiki-ingest/query/lint/sync)" % stpl)

    return plan, missing


# ---------------------------------------------------------------- 写入器(--force / 跳过记账)

class Writer:
    def __init__(self, target, force):
        self.target = Path(target)
        self.force = force
        self.written = []
        self.skipped = []

    def _prep(self, rel):
        dst = self.target / rel
        if dst.exists() or dst.is_symlink():
            if not self.force:
                self.skipped.append(rel)
                return None
            if dst.is_dir():
                raise SystemExit("目标 %s 是目录,无法覆盖" % dst)
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        return dst

    def write_text(self, rel, content):
        dst = self._prep(rel)
        if dst is None:
            return False
        dst.write_text(content, encoding="utf-8")
        self.written.append(rel)
        return True

    def copy(self, rel, src):
        dst = self.target / rel
        try:
            if dst.exists() and os.path.samefile(str(src), str(dst)):
                self.skipped.append(rel + "(与源为同一文件)")
                return False
        except OSError:
            pass
        dst = self._prep(rel)
        if dst is None:
            return False
        shutil.copyfile(str(src), str(dst))
        self.written.append(rel)
        return True


def copy_tree(writer, src_dir, rel_prefix, skip_dirs=()):
    if not src_dir.is_dir():
        return False
    for root, dirs, files in os.walk(str(src_dir)):
        dirs[:] = sorted(d for d in dirs if d not in {"__pycache__", ".git"} and d not in skip_dirs)
        for f in sorted(files):
            if f.endswith(".pyc") or f == ".DS_Store":
                continue
            sp = Path(root) / f
            rel = "%s/%s" % (rel_prefix, sp.relative_to(src_dir).as_posix())
            writer.copy(rel, sp)
    return True


# ---------------------------------------------------------------- 主流程

def _die(code, *msgs):
    for m in msgs:
        print(m, file=sys.stderr)
    raise SystemExit(code)


def main(argv=None):
    ap = argparse.ArgumentParser(description="llmwiki 确定性渲染器(M1)")
    ap.add_argument("--config", required=True, help="wiki.config.json 路径")
    ap.add_argument("--target", required=True, help="实例目标目录")
    ap.add_argument("--date", default=None, help="bootstrap 日期 YYYY-MM-DD(缺省今天;固定它可获得可复现产物)")
    ap.add_argument("--force", action="store_true", help="覆盖已存在文件(缺省逐个跳过并列出)")
    args = ap.parse_args(argv)

    date = args.date or _dt.date.today().isoformat()
    if not DATE_RE.match(date):
        _die(2, "错误: --date 须为 YYYY-MM-DD,得到 %r" % date)

    here = Path(__file__).resolve()
    fw_root = here.parent.parent  # tools/..
    if (fw_root / "CLAUDE.template.md").is_file():
        tpl_root = fw_root
    elif (fw_root / "framework" / "base" / "CLAUDE.template.md").is_file():
        tpl_root = fw_root / "framework" / "base"  # 实例内重渲染:用模板快照
    else:
        tpl_root = fw_root  # 交给 preflight 统一报缺

    warnings, notes = [], []

    # --- config 载入 + 校验
    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        _die(2, "错误: config 不存在:%s" % cfg_path)
    try:
        cfg_raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _die(2, "错误: config 不是合法 JSON(%s:%s:%s)" % (cfg_path, e.lineno, e.msg))
    errors, vwarns = validate_config(cfg_raw)
    warnings += ["config %s" % w for w in vwarns]
    if errors:
        _die(2, "config 校验失败(%d 处):" % len(errors), *["  - %s" % e for e in errors])
    cfg = apply_defaults(cfg_raw)

    # --- framework VERSION
    version_file = fw_root / "framework" / "VERSION"
    if version_file.is_file():
        fw_version = version_file.read_text(encoding="utf-8").strip() or "0.0.0-dev"
    else:
        fw_version = "0.0.0-dev"
        warnings.append("framework/VERSION 缺失(%s),暂用 %s" % (version_file, fw_version))
    if cfg["framework_version"] != fw_version:
        warnings.append("config framework_version=%s 与框架 VERSION=%s 不一致(升级请走 /wiki-upgrade)"
                        % (cfg["framework_version"], fw_version))

    # --- 目标合法性
    target = Path(args.target).resolve()
    if target == fw_root.resolve() or target == tpl_root.resolve():
        _die(2, "错误: --target 不能是框架仓库本身(%s)" % target)

    # --- preflight:模板齐备性(缺失即清晰报错退出,不写任何文件)
    plan, missing = build_plan(tpl_root)
    if missing:
        _die(2,
             "框架模板缺失,无法渲染(模板根:%s):" % tpl_root,
             *["  - %s" % m for m in missing],
             "提示: 请在完整的框架仓库内运行,或先补齐上述模板。未写入任何文件。")

    # --- 槽位与条件
    slots = compute_slots(cfg, fw_version)
    conds = compute_conds(cfg)

    # --- 两阶段:先全部渲染进内存,收齐错误;有错则零写入退出
    rendered, copies, render_errors = [], [], []
    for src, rel in plan:
        if src.suffix == ".md":
            out, errs = render_text(src.read_text(encoding="utf-8"), slots, conds,
                                    str(src.relative_to(tpl_root)))
            render_errors += errs
            rendered.append((rel, out))
        else:
            copies.append((rel, src))  # skills 附属非 md 文件原样拷贝
    if render_errors:
        _die(1,
             "渲染失败(%d 处槽位/模块错误),未写入任何文件:" % len(render_errors),
             *["  - %s" % e for e in render_errors])

    # wiki 页日期打戳:log 模板 bootstrap 占位条目 + meta 页 frontmatter created/updated
    # 占位 → --date(细则见 stamp_dates;单源函数,upgrade.py import 复用)
    rendered = stamp_dates(rendered, date)

    # --- 提交阶段
    w = Writer(target, args.force)
    target.mkdir(parents=True, exist_ok=True)

    scaffold = ["raw", "state", "state/tmp", "site", "evals", "_attic", "tools/adapters",
                "wiki/sources", "wiki/entities", "wiki/concepts", "wiki/syntheses", "wiki/queries",
                ".claude/rules", ".claude/agents", ".claude/skills"]
    scaffold += [p["raw_dir"] for p in cfg["pipelines"]]
    for d in scaffold:
        (target / d).mkdir(parents=True, exist_ok=True)

    for rel, content in rendered:
        w.write_text(rel, content)
    for rel, src in copies:
        w.copy(rel, src)

    # AGENTS.md symlink(失败降级硬拷贝)
    agents = target / "AGENTS.md"
    if agents.exists() or agents.is_symlink():
        if args.force:
            agents.unlink()
        else:
            w.skipped.append("AGENTS.md")
    if not (agents.exists() or agents.is_symlink()):
        try:
            os.symlink("CLAUDE.md", str(agents))
            notes.append("AGENTS.md → CLAUDE.md(symlink)")
        except OSError as e:
            try:
                shutil.copyfile(str(target / "CLAUDE.md"), str(agents))
                notes.append("AGENTS.md symlink 失败(%s):已降级为硬拷贝——CLAUDE.md 变更后需重拷,lint 会校验两者一致" % e)
            except OSError as e2:
                warnings.append("AGENTS.md 创建失败:%s" % e2)

    # frozen 拷贝:tools/ 与 schema/(W-UPG-1;实例改动 = fork)
    if not copy_tree(w, fw_root / "tools", "tools", skip_dirs=("adapters",)):
        warnings.append("框架 tools/ 缺失,跳过拷贝")
    if not copy_tree(w, fw_root / "schema", "schema"):
        warnings.append("框架 schema/ 缺失,跳过拷贝")
    if not copy_tree(w, fw_root / "adapters", "adapters"):
        warnings.append("框架 adapters/ 缺失,跳过拷贝(CONTRACT/local_notes/skeleton 不可用)")
    # design-docs 是开发过程文档,不属框架分发面(与 gen_manifest EXCLUDE 同名同口径)
    if not copy_tree(w, fw_root / "docs", "docs", skip_dirs=("design-docs",)):
        warnings.append("框架 docs/ 缺失,跳过拷贝(skills 内 docs/ 指针将悬空)")

    # config 落位 + framework/{VERSION,base/} 快照(升级三方合并的 base)
    w.copy("wiki.config.json", cfg_path)
    w.write_text("framework/VERSION", fw_version + "\n")
    _mf = fw_root / "framework" / "MANIFEST.json"
    if _mf.exists():
        # 快照只保留实例实际持有的条目(细则见 snapshot_manifest;单源函数,upgrade.py 复用)
        _snap = snapshot_manifest(_mf, target)
        if _snap is not None:
            w.write_text("framework/MANIFEST.json", _snap)
        else:
            w.copy("framework/MANIFEST.json", _mf)
    else:
        warnings.append("框架 MANIFEST.json 缺失,实例未落快照(升级 hash 校验依赖,见 gen_manifest.py)")
    for src in sorted({src for src, _ in plan}):
        w.copy("framework/base/%s" % src.relative_to(tpl_root).as_posix(), src)

    # .gitignore 最小默认(W-SEC-2)
    w.write_text(".gitignore",
                 "# llmwiki 实例默认(W-SEC-2:state/ 与凭证不入库)\n"
                 "state/\n*.env\n.env.*\n__pycache__/\n.DS_Store\n")

    # wiki/log.md 首条 bootstrap(W-LOG-1;幂等:已有 bootstrap 不重复)
    log_path = target / "wiki" / "log.md"
    boot_line = ("## [%s] bootstrap | init_render domain=%s framework=%s pipelines=%s"
                 % (date, cfg["domain"]["name"], fw_version,
                    ",".join(p["name"] for p in cfg["pipelines"])))
    boot_body = ("- rendered: CLAUDE.md + .claude/{rules,agents,skills} + wiki 骨架;"
                 "tools/ 与 schema/ 为 frozen 拷贝(W-UPG-1)\n"
                 "- next: 接入首批内容;约 10 源后回填 _map 档位表/决策表并建 evals/golden.jsonl 基线\n")
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("# log(append-only,格式见 W-LOG-1)\n\n%s\n%s" % (boot_line, boot_body),
                            encoding="utf-8")
        w.written.append("wiki/log.md")
    else:
        txt = log_path.read_text(encoding="utf-8")
        if "] bootstrap | " not in txt:
            with open(str(log_path), "a", encoding="utf-8") as fh:
                if not txt.endswith("\n"):
                    fh.write("\n")
                fh.write("\n%s\n%s" % (boot_line, boot_body))
            notes.append("wiki/log.md 已追加 bootstrap 条目(append-only)")

    # 空脚手架目录补 .gitkeep(空目录不入 git)
    keep_dirs = [p["raw_dir"] for p in cfg["pipelines"]] + \
                ["state/tmp", "site", "evals", "_attic", "tools/adapters",
                 "wiki/sources", "wiki/entities", "wiki/concepts", "wiki/syntheses", "wiki/queries"]
    kept = 0
    for d in keep_dirs:
        dd = target / d
        if dd.is_dir() and not any(dd.iterdir()):
            (dd / ".gitkeep").write_text("", encoding="utf-8")
            kept += 1

    # --- 汇总输出
    print("== init_render 完成 ==")
    print("domain: %s | framework: %s | date: %s | target: %s"
          % (cfg["domain"]["name"], fw_version, date, target))
    print("装载模块: %s" % (", ".join(k for k in COND_KEYS if conds[k]) or "(无)"))
    print("写入 %d 个文件;.gitkeep %d 个" % (len(w.written), kept))
    if w.skipped:
        print("跳过 %d 个已存在文件(adopt 友好;--force 可覆盖):" % len(w.skipped))
        for s in w.skipped:
            print("  - %s" % s)
    for n in notes:
        print("提示: %s" % n)
    for wn in warnings:
        print("警告: %s" % wn)
    push = [p for p in cfg["pipelines"] if p["kind"] == "push"]
    print("提示: config 已拷入 <target>/wiki.config.json,--config 所指源文件可删或另存。")
    print("\n下一步:")
    print("  1. cd %s" % target)
    print("  2. python3 tools/lint_wiki.py --check-slots --target .    # 渲染验收(0 残留)")
    print("  3. python3 tools/build_site.py && python3 tools/build_index.py    # 先建空索引(W-IDX-1)")
    if push:
        print("  4. 首条知识入库:投递 %s/<date>-<slug>.md(frontmatter: title/date/kind ∈ %s)"
              % (push[0]["raw_dir"], "|".join(push[0]["source_kinds"]) or "…"))
    else:
        print("  4. 接入适配器后 python3 tools/sync.py 抓首批源(契约见 adapters/CONTRACT.md)")
    print("  5. python3 tools/lint_wiki.py --check-config wiki.config.json    # config 复检")
    print("  6. 首批 ~10 源后:回填 wiki/_map.md 档位表/决策表页名,写 overview 首版,建 evals/golden.jsonl 基线")
    return 0


if __name__ == "__main__":
    sys.exit(main())
