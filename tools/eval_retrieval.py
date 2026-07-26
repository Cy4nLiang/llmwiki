#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki eval_retrieval — golden 回归集的检索命中打分器(ID-based,零 LLM,确定性)。

移植自参考实例 newpj4 tools/eval_retrieval.py(2026-07-19,M2);加权 P/R 打分逻辑逐字
保持,路径全部参数化(--root / --golden)。把「agent 读得准不准」变成可回归的数字(Spec §11)。

■ golden 文件(默认 <root>/evals/golden.jsonl,--golden 覆盖)每行一个 JSON 对象:
    {"qid": "...", "type": "single-hop|multi-hop|comparison|aggregation|timeline|
     exact-verbatim|unanswerable|route", "question": "...",
     "golden": {"<wiki 相对 slug>": 2|1, ...},
     "golden_groups": [{"weight": 2|1, "pages": ["<slug>", ...]}, ...]  # 可选,any-of 组
     "answer_keys": ["...", ...]}
  分级语义:2 = 必读页(应被打开),1 = 有帮助页(打开算加分,权重为 2 级页的一半)。
  any-of 组(golden_groups,2026-07-20):组语义 =「同一信息的多条获取路径,任一命中即满」——
  files_read ∩ 组 pages ≠ ∅ 记该组满权一次;recall 分母 = Σ单点权重 + Σ组权重;precision 对
  golden 单点或任一组成员均计 useful。组约束(违规 = 结构错误 exit 2):weight ∈ 2|1、
  pages 归一后 ≥2 页且互不重复、组页不得与 golden 单点重复、unanswerable 题禁止有组。
  无组的存量 golden 打分逐位不变(向后兼容;newpj4 存量 16 题对拍复证)。
  规范文档 = evals/golden.schema.json(M3):载入时按其手写校验——结构错误(缺必填/类型不符/
  golden 值非 1|2/unanswerable 带非空 golden 或非空 golden_groups/组约束违规/qid 重复)
  → exit 2;未知 type 经别名映射(exact-version→exact-verbatim、how-do-I→single-hop、
  route-entry→route)后仍未知 → warning 不阻断,按普通检索题打分。--check-golden <path>
  只校验不打分(exit 0 干净 / 1 有 warning / 2 结构错误)。

■ unanswerable 诚实探针(golden 空 {},W-QRY-3):
  判定改 answer_keys 锚点匹配——golden 的 answer_keys 收敛为「未收录声明」锚点关键词
  (如 "未收录";schema 约定 ≤20 字符),answer 含任一锚点(大小写不敏感子串)即判诚实;
  超长整句不算可用锚点(存量句式写法,--check-golden 会 warning)。无可用锚点时回退 M2
  遗留粗启发式(answer 含「未收录」或 "not",与 eval_compare 同款)并在结果中标注
  honest_method="heuristic"。判不诚实计入 problem_q → exit 1。

■ route 题型打分语义:与普通题完全相同(files_read 含 golden 页即命中),无特殊分支;
  其特殊性只在出题面——golden 指向 _map 决策表入口应路由到的页 / 应被 description 选中的页,
  回归 W-PAGE-2 description 触发质量。逐型出题要点见 evals/question-types.md。

■ run 文件(每行一题;与参考实例 newpj4 的 run 文件格式兼容):
    {"qid": "...", "files_read": ["concepts/mcp", "raw/xx/yy.md", ...], "answer": "..."}
  - files_read = agent 实际 Read 打开的路径,wiki 相对写法("wiki/" 前缀与 ".md" 后缀
    归一后等价;raw/ 路径保留前缀原样)。**grep 命中不算 read** —— 记账口径,
    W-LNT-1「大文件 grep-only」协议红利得以量化的前提。
  - answer = agent 最终回答文本(诚实探针核对用)。

■ 指标(与参考实例逐字一致):
    recall    = (|命中必读| + 0.5·|命中有帮助|) / (|必读| + 0.5·|有帮助|)
    precision = |read ∩ golden| / |wiki_read|
                (wiki_read = read 去掉 raw/ 路径;全为 raw 时退化为整个 read——
                 raw 锚定切片是协议允许的动作,不按「多读」惩罚)

用法:
    python3 tools/eval_retrieval.py <run.jsonl> [--root DIR] [--golden PATH] [--json]
    python3 tools/eval_retrieval.py --check-golden evals/golden.jsonl [--json]  # 只校验不打分
    python3 tools/eval_retrieval.py --export-qrels [--qrels-out PATH]   # BEIR 兼容导出
  相对路径(run / --golden / --check-golden / --qrels-out)一律按 --root 解析;--root 默认 cwd。

退出码:0 = 打分完成且无漏必读、无缺题、诚实探针全过(--check-golden:校验干净);
        1 = 存在漏必读 / run 缺题 / 诚实探针未过 / 数据行解析失败(--check-golden:仅 warning);
        2 = 用法或配置错误(路径不存在、参数缺失、golden 结构错误)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# lib/fm.py = frontmatter/est_tokens/config 单一实现;同目录 sys.path 导入(与 lint_wiki.py 同款)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib import fm
except ImportError as e:  # pragma: no cover
    print("错误: 无法导入 tools/lib/fm.py(config/est_tokens 单一实现):%s" % e, file=sys.stderr)
    sys.exit(2)


def norm(p: str) -> str:
    """路径归一:去 wiki/ 前缀;非 raw/ 路径去 .md 后缀 —— 使 run 与 golden 的写法等价。"""
    p = p.strip().removeprefix("wiki/")
    return p[:-3] if p.endswith(".md") and not p.startswith("raw/") else p


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    """逐行读 jsonl;坏行跳过并记录(不让单行毒化整跑)。返回 (rows, errors)。"""
    rows: list[dict] = []
    errors: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append("%s:%d: JSON 解析失败:%s" % (path, i, e.msg))
    return rows, errors


# ------------------------------------------------------- golden schema 校验(M3)
# 规范文档 = evals/golden.schema.json;此处为其手写实现(仅标准库,不引 JSON Schema 引擎)。
# 执行口径与 schema 头注一致:结构错误 → exit 2;未知 type(经别名映射后)/ 未知字段 → warning。

CANONICAL_TYPES = ("single-hop", "multi-hop", "comparison", "aggregation",
                   "timeline", "exact-verbatim", "keyword-miss", "unanswerable", "route")
# 别名映射(schema x-alias-map 同源):exact-version = 参考实例 newpj4 存量;
# how-do-I = hello-wiki 夹具存量(queries 缓存单跳);route-entry = route 早期草案名。
TYPE_ALIASES = {"exact-version": "exact-verbatim", "how-do-I": "single-hop",
                "how-do-i": "single-hop", "route-entry": "route"}
KNOWN_FIELDS = {"qid", "type", "question", "golden", "golden_groups", "answer_keys", "notes"}
GROUP_FIELDS = {"weight", "pages"}  # any-of 组条目的已知字段(schema golden_groups.items)
UNANSWERABLE_KEY_MAXLEN = 20  # 诚实探针锚点长度上限(schema 同值);超长疑似整句,锚点匹配必失


def canon_type(t) -> str:
    """type 归一:别名映射到规范题型;未知原样返回(调用方判 warning)。"""
    return TYPE_ALIASES.get(t, t) if isinstance(t, str) else ""


def norm_groups(row: dict) -> list[dict]:
    """提取并归一 any-of 组:[{"weight": 2|1, "pages": [norm 后路径, ...]}, ...]。
    只做形状宽容提取(打分用);合法性裁决归 validate_golden(结构错误 → exit 2,
    打分主流程在校验门之后,故此处见到的数据已保证合法)。"""
    out = []
    raw = row.get("golden_groups")
    if not isinstance(raw, list):
        return out
    for grp in raw:
        if not isinstance(grp, dict):
            continue
        pages = grp.get("pages")
        out.append({"weight": grp.get("weight"),
                    "pages": [norm(p) for p in pages if isinstance(p, str)]
                    if isinstance(pages, list) else []})
    return out


def validate_golden(rows: list[dict]) -> tuple[list[str], list[str]]:
    """按 evals/golden.schema.json 手写校验。返回 (errors, warnings);errors 非空 → exit 2。"""
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, 1):
        tag = "golden 第 %d 条" % i
        if not isinstance(row, dict):
            errors.append("%s: 不是 JSON 对象" % tag)
            continue
        qid = row.get("qid")
        if not isinstance(qid, str) or not qid.strip():
            errors.append("%s: qid 缺失或非非空字符串" % tag)
        else:
            tag = "golden[%s]" % qid
            if qid in seen:
                errors.append("%s: qid 重复" % tag)
            seen.add(qid)
            if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", qid):
                warnings.append("%s: qid 不符 ASCII slug 约定(schema pattern)" % tag)
        if not isinstance(row.get("question"), str) or not row.get("question", "").strip():
            errors.append("%s: question 缺失或非非空字符串" % tag)
        t = row.get("type")
        if not isinstance(t, str) or not t.strip():
            errors.append("%s: type 缺失或非字符串" % tag)
            ct = ""
        else:
            ct = canon_type(t)
            if ct not in CANONICAL_TYPES:
                warnings.append("%s: 未知 type %r(经别名映射后仍未知;按普通检索题打分)" % (tag, t))
        gold = row.get("golden")
        if not isinstance(gold, dict):
            errors.append("%s: golden 缺失或非对象" % tag)
            gold = {}
        else:
            for k, v in gold.items():
                if not isinstance(k, str) or not k.strip():
                    errors.append("%s: golden 含非法键 %r" % (tag, k))
                if v not in (1, 2):
                    errors.append("%s: golden[%r] = %r(枚举 2=必读 / 1=有帮助)" % (tag, k, v))
        # any-of 组(golden_groups,可选;约束违规 = 结构错误)
        groups = row.get("golden_groups")
        n_groups = 0                # 合法提取到的组数(跨字段一致性用)
        has_w2_group = False
        if groups is not None:
            if not isinstance(groups, list):
                errors.append("%s: golden_groups 须为数组" % tag)
            else:
                n_groups = len(groups)
                single_keys = {norm(k) for k in gold if isinstance(k, str)}
                seen_group_pages: set = set()
                for j, grp in enumerate(groups, 1):
                    gtag = "%s golden_groups[%d]" % (tag, j)
                    if not isinstance(grp, dict):
                        errors.append("%s: 组须为对象 {weight, pages}" % gtag)
                        continue
                    if grp.get("weight") not in (1, 2):
                        errors.append("%s: weight = %r(枚举 2=必读〔任一路径〕 / 1=有帮助〔任一路径〕)"
                                      % (gtag, grp.get("weight")))
                    elif grp.get("weight") == 2:
                        has_w2_group = True
                    pages = grp.get("pages")
                    pages_bad = (not isinstance(pages, list)
                                 or any(not isinstance(p, str) or not p.strip() for p in pages))
                    if pages_bad:
                        errors.append("%s: pages 须为非空字符串数组" % gtag)
                        pages = [] if not isinstance(pages, list) else \
                            [p for p in pages if isinstance(p, str) and p.strip()]
                    npages = [norm(p) for p in pages]
                    distinct = set(npages)
                    if len(npages) != len(distinct):
                        errors.append("%s: 组内页重复(归一后):%s"
                                      % (gtag, sorted({p for p in distinct
                                                       if npages.count(p) > 1})))
                    if not pages_bad and len(distinct) < 2:
                        errors.append("%s: 组内不足 2 页——any-of 组至少两条获取路径,"
                                      "单页请写回 golden 单点" % gtag)
                    dup = sorted(distinct & single_keys)
                    if dup:
                        errors.append("%s: 组页与 golden 单点重复:%s" % (gtag, dup))
                    cross = sorted(distinct & seen_group_pages)
                    if cross:
                        warnings.append("%s: 页同现于多个组(读一页将同时记满多组权,recall 双计):%s"
                                        % (gtag, cross))
                    seen_group_pages |= distinct
                    for f in grp:
                        if f not in GROUP_FIELDS:
                            warnings.append("%s: 未知字段 %r(schema 外;忽略)" % (gtag, f))
        keys = row.get("answer_keys")
        if keys is None:
            errors.append("%s: answer_keys 缺失(必填;可为空数组)" % tag)
            keys = []
        elif not isinstance(keys, list) or any(not isinstance(k, str) or not k for k in keys):
            errors.append("%s: answer_keys 须为非空字符串数组" % tag)
            keys = []
        for f in row:
            if f not in KNOWN_FIELDS and not str(f).startswith("x-"):
                warnings.append("%s: 未知字段 %r(schema 外;忽略)" % (tag, f))
        # 跨字段一致性(schema allOf if/then)
        if ct == "unanswerable":
            if gold:
                errors.append("%s: unanswerable 题 golden 必须为空对象 {}" % tag)
            if n_groups:
                errors.append("%s: unanswerable 题禁止 golden_groups(诚实探针不评检索)" % tag)
            if not keys:
                warnings.append("%s: unanswerable 题 answer_keys 为空 → 诚实判定回退 M2 启发式" % tag)
            for k in keys:
                if len(k) > UNANSWERABLE_KEY_MAXLEN:
                    warnings.append("%s: unanswerable 锚点 %r 超 %d 字符,疑似整句非锚点关键词,"
                                    "匹配可能误判(schema 约定收敛为「未收录声明」短锚点)"
                                    % (tag, k[:30], UNANSWERABLE_KEY_MAXLEN))
        else:
            if not gold and not n_groups:
                warnings.append("%s: golden 为空但 type 非 unanswerable → 将按诚实探针处理" % tag)
            elif 2 not in gold.values() and not has_w2_group:
                warnings.append("%s: 无 2 级必读页(每题应至少一个 2 级单点或 2 权组)" % tag)
    return errors, warnings


def score(golden_rows: list[dict], run_rows: list[dict]) -> tuple[list[dict], dict]:
    """加权 P/R 打分(P/R 数学与参考实例 newpj4 逐字一致;M3 改动仅限 unanswerable 分支:
    诚实判定自动化 = answer_keys 锚点匹配,空锚点回退旧启发式,不诚实计入 problems)。
    any-of 组(2026-07-20):recall 分母 = Σ单点权重 + Σ组权重,组命中(files_read ∩ pages
    ≠ ∅)记该组满权一次;precision 对单点或任一组成员均计 useful;2 权组全 miss 视同漏必读
    计入 problems。无组的存量 golden 走原公式同一代码路径,打分逐位不变(向后兼容)。"""
    golden = {g["qid"]: g for g in golden_rows}
    runs = {r["qid"]: r for r in run_rows}
    per_q: list[dict] = []
    tot_p = tot_r = 0.0
    n = problems = 0
    for qid, g in golden.items():
        gold = {norm(k): v for k, v in g.get("golden", {}).items()}
        groups = norm_groups(g)
        r = runs.get(qid)
        if r is None:
            per_q.append({"qid": qid, "status": "missing-run"})
            problems += 1
            continue
        read = {norm(p) for p in r.get("files_read", [])}
        if not gold and not groups:
            # unanswerable 诚实探针(W-QRY-3):不评检索,自动判诚实。
            # 首选 answer_keys 锚点匹配(「未收录声明」关键词,大小写不敏感子串);
            # 可用锚点 = 长度 ≤ UNANSWERABLE_KEY_MAXLEN 的键——超长整句(参考实例 newpj4
            # v0.1 存量写法,--check-golden 已 warning)不算锚点,以免制造假阴性;
            # 无可用锚点时回退 M2 遗留粗启发式(与 eval_compare 同款)并标注 —— fallback,
            # 新 golden 应按 schema 收敛锚点,消除启发式误判。
            ans = r.get("answer", "")
            keys = [k for k in g.get("answer_keys", [])
                    if isinstance(k, str) and k.strip()
                    and len(k) <= UNANSWERABLE_KEY_MAXLEN]
            if keys:
                honest = any(k.lower() in ans.lower() for k in keys)
                method = "answer_keys"
            else:
                honest = ("未收录" in ans) or ("not" in ans.lower())
                method = "heuristic"
            if not honest:
                problems += 1
            per_q.append({"qid": qid, "status": "unanswerable",
                          "honest": honest, "honest_method": method,
                          "answer": ans[:120]})
            continue
        must = {s for s, v in gold.items() if v == 2}
        helpful = {s for s, v in gold.items() if v == 1}
        # any-of 组:任一成员命中记满权一次;权重换算与单点同刻度(2→1.0,1→0.5),
        # 故 recall 比值 = (Σ命中单点权 + Σ命中组权) / (Σ单点权 + Σ组权)。
        group_detail: list[dict] = []
        miss_groups: list[list[str]] = []
        grp_hit_w = grp_all_w = 0.0
        for grp in groups:
            hit_pages = sorted(read & set(grp["pages"]))
            w = 0.5 * grp["weight"]
            grp_all_w += w
            if hit_pages:
                grp_hit_w += w
            elif grp["weight"] == 2:
                miss_groups.append(grp["pages"])
            group_detail.append({"weight": grp["weight"], "pages": grp["pages"],
                                 "hit": bool(hit_pages), "hit_pages": hit_pages})
        denom = len(must) + 0.5 * len(helpful) + grp_all_w
        rec = (len(read & must) + 0.5 * len(read & helpful) + grp_hit_w) / denom \
            if denom else 0.0
        wiki_read = {p for p in read if not p.startswith("raw/")} or read
        useful = set(gold) | {p for grp in groups for p in grp["pages"]}
        prec = len(read & useful) / len(wiki_read) if wiki_read else 0.0
        tot_p += prec
        tot_r += rec
        n += 1
        miss = sorted(must - read)
        if miss or miss_groups:
            problems += 1
        item = {"qid": qid, "status": "scored",
                "precision": round(prec, 4), "recall": round(rec, 4),
                "miss_must": miss,
                "extra_read": sorted(wiki_read - useful)}
        if groups:  # 组命中明细只在有组时输出(无组行保持存量形状,逐位不变)
            item["groups"] = group_detail
            item["miss_groups"] = miss_groups
        per_q.append(item)
    summary = {"n": n,
               "precision": round(tot_p / n, 4) if n else 0.0,
               "recall": round(tot_r / n, 4) if n else 0.0,
               "problem_q": problems}
    return per_q, summary


def print_human(per_q: list[dict], summary: dict) -> None:
    print("%-34s %5s %5s  detail" % ("qid", "prec", "rec"))
    for q in per_q:
        qid = q["qid"]
        if q["status"] == "missing-run":
            print("%-34s   -     -   (run 缺失)" % qid)
        elif q["status"] == "unanswerable":
            mark = "✓" if q["honest"] else "✗(编造/未声明未收录)"
            via = "锚点" if q["honest_method"] == "answer_keys" else "启发式 fallback"
            print("%-34s   n/a   n/a  [unanswerable] 诚实=%s(%s)answer:%s"
                  % (qid, mark, via, q["answer"][:50]))
        else:
            miss_bits = []
            if q["miss_must"]:
                miss_bits.append("漏必读:%s" % q["miss_must"])
            if q.get("miss_groups"):
                miss_bits.append("漏必读组(任一即可):%s" % q["miss_groups"])
            detail = " ".join(miss_bits) if miss_bits else "✓"
            if q.get("groups"):
                detail += " 组命中:%d/%d" % (sum(1 for gp in q["groups"] if gp["hit"]),
                                             len(q["groups"]))
            if q["extra_read"]:
                detail += " 多读:%s" % q["extra_read"][:3]
            print("%-34s %5.2f %5.2f  %s" % (qid, q["precision"], q["recall"], detail))
    if summary["n"]:
        print("\n均值(不含 unanswerable): precision %.3f  recall %.3f  (n=%d)"
              % (summary["precision"], summary["recall"], summary["n"]))
    if summary["problem_q"]:
        print("发现问题: %d 题存在漏必读 / run 缺失 / 诚实探针未过 → exit 1" % summary["problem_q"])


def export_qrels(golden_rows: list[dict], out: Path) -> None:
    """BEIR 兼容 qrels(qid<TAB>docid<TAB>rel);slug 保持 golden 原样不归一。
    默认写 <root>/state/(工具写入白名单 W-ARCH-2:raw/+site/+state/;qrels 为
    纯派生物可随时重导,故不像参考实例那样落 evals/——那属实例数据目录)。
    注:golden_groups 不导出——BEIR qrels 无 any-of 语义,组页导出会被当独立必读文档
    误读;需要组语义评测请直接用本工具打分。"""
    lines = ["%s\t%s\t%s" % (g["qid"], slug, rel)
             for g in golden_rows for slug, rel in g.get("golden", {}).items()]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("wrote %s(%d qrels)" % (out, len(lines)))


def resolve(root: Path, p: str) -> Path:
    q = Path(p).expanduser()
    return q if q.is_absolute() else root / q


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="golden 回归集检索命中打分器(零 LLM,ID-based;详见文件头注)")
    ap.add_argument("run", nargs="?", help="run jsonl 路径(相对路径按 --root 解析)")
    ap.add_argument("--root", default=".",
                    help="实例根(默认 cwd);定位 wiki.config.json 与 evals/golden.jsonl")
    ap.add_argument("--golden", default=None,
                    help="golden jsonl 路径(默认 <root>/evals/golden.jsonl)")
    ap.add_argument("--json", dest="as_json", action="store_true", help="机器可读 JSON 输出")
    ap.add_argument("--check-golden", metavar="PATH", default=None,
                    help="只按 evals/golden.schema.json 校验该 golden 文件,不打分"
                         "(exit 0 干净 / 1 有 warning / 2 结构错误)")
    ap.add_argument("--export-qrels", action="store_true", help="导出 BEIR 兼容 qrels 后退出")
    ap.add_argument("--qrels-out", default=None,
                    help="qrels 输出路径(默认 <root>/state/qrels.tsv,守 W-ARCH-2 白名单)")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("错误: --root 不是目录:%s" % root, file=sys.stderr)
        return 2
    # 统一经 lib/fm.load_config 定位实例 config;ID-based 打分本身不消费 config 值,
    # 载入失败(如对未迁移树打分,Spec §15 只读对照)仅提示不阻断。
    try:
        fm.load_config(root)
    except Exception as e:
        print("提示: %s 下 wiki.config.json 不可用(%s);ID-based 打分不依赖 config,继续。"
              % (root, e), file=sys.stderr)

    if args.check_golden:
        # --check-golden:只校验不打分(规范 = evals/golden.schema.json)
        gp = resolve(root, args.check_golden)
        if not gp.is_file():
            print("错误: golden 不存在:%s" % gp, file=sys.stderr)
            return 2
        rows, parse_errs = load_jsonl(gp)
        errors, warnings = validate_golden(rows)
        errors = parse_errs + errors  # 坏行 = 结构错误同级
        if args.as_json:
            print(json.dumps({"golden": str(gp), "n_questions": len(rows),
                              "errors": errors, "warnings": warnings,
                              "ok": not errors}, ensure_ascii=False, indent=2))
        else:
            for msg in errors:
                print("错误: %s" % msg)
            for msg in warnings:
                print("警告: %s" % msg)
            print("check-golden: %s — %d 题,%d 错误,%d 警告"
                  % (gp, len(rows), len(errors), len(warnings)))
        return 2 if errors else (1 if warnings else 0)

    golden_path = resolve(root, args.golden) if args.golden else root / "evals" / "golden.jsonl"
    if not golden_path.is_file():
        print("错误: golden 不存在:%s(用 --golden 指定)" % golden_path, file=sys.stderr)
        return 2
    golden_rows, golden_errs = load_jsonl(golden_path)
    for msg in golden_errs:
        print("警告: %s" % msg, file=sys.stderr)
    # schema 校验门(M3):结构错误 → exit 2;warning 打印 stderr 不阻断打分
    schema_errs, schema_warns = validate_golden(golden_rows)
    for msg in schema_warns:
        print("警告: %s" % msg, file=sys.stderr)
    if schema_errs:
        for msg in schema_errs:
            print("错误: %s" % msg, file=sys.stderr)
        print("错误: golden 结构校验未过(%d 条;规范见 evals/golden.schema.json,"
              "可先跑 --check-golden)" % len(schema_errs), file=sys.stderr)
        return 2

    if args.export_qrels:
        out = resolve(root, args.qrels_out) if args.qrels_out else root / "state" / "qrels.tsv"
        export_qrels(golden_rows, out)
        return 1 if golden_errs else 0

    if not args.run:
        ap.print_usage(sys.stderr)
        print("错误: 需要 run jsonl 参数(或改用 --export-qrels)", file=sys.stderr)
        return 2
    run_path = resolve(root, args.run)
    if not run_path.is_file():
        print("错误: run 文件不存在:%s" % run_path, file=sys.stderr)
        return 2
    run_rows, run_errs = load_jsonl(run_path)
    for msg in run_errs:
        print("警告: %s" % msg, file=sys.stderr)

    per_q, summary = score(golden_rows, run_rows)
    if args.as_json:
        print(json.dumps({"golden": str(golden_path), "run": str(run_path),
                          "per_question": per_q, "summary": summary},
                         ensure_ascii=False, indent=2))
    else:
        print_human(per_q, summary)
    return 1 if (summary["problem_q"] or golden_errs or run_errs) else 0


if __name__ == "__main__":
    sys.exit(main())
