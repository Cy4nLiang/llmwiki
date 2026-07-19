#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki eval_retrieval — golden 回归集的检索命中打分器(ID-based,零 LLM,确定性)。

移植自参考实例 newpj4 tools/eval_retrieval.py(2026-07-19,M2);加权 P/R 打分逻辑逐字
保持,路径全部参数化(--root / --golden)。把「agent 读得准不准」变成可回归的数字(Spec §11)。

■ golden 文件(默认 <root>/evals/golden.jsonl,--golden 覆盖)每行一个 JSON 对象:
    {"qid": "...", "type": "single-hop|multi-hop|comparison|aggregation|timeline|
     exact-verbatim|unanswerable|route", "question": "...",
     "golden": {"<wiki 相对 slug>": 2|1, ...}, "answer_keys": ["...", ...]}
  分级语义:2 = 必读页(应被打开),1 = 有帮助页(打开算加分,权重为 2 级页的一半)。
  golden 为空 {} = unanswerable 诚实探针:不评检索,只回传 answer 供人工核对(W-QRY-3)。
  注:题型 6+1+路由题的 schema 机检收敛属 M3;本工具对 type 字段只透传不校验。

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
    python3 tools/eval_retrieval.py --export-qrels [--qrels-out PATH]   # BEIR 兼容导出
  相对路径(run / --golden / --qrels-out)一律按 --root 解析;--root 默认 cwd。

退出码:0 = 打分完成且无漏必读、无缺题;1 = 存在漏必读 / run 缺题 / 数据行解析失败;
        2 = 用法或配置错误(路径不存在、参数缺失等)。
"""
from __future__ import annotations

import argparse
import json
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


def score(golden_rows: list[dict], run_rows: list[dict]) -> tuple[list[dict], dict]:
    """加权 P/R 打分(逻辑与参考实例 newpj4 逐字一致)。返回 (per_question, summary)。"""
    golden = {g["qid"]: g for g in golden_rows}
    runs = {r["qid"]: r for r in run_rows}
    per_q: list[dict] = []
    tot_p = tot_r = 0.0
    n = problems = 0
    for qid, g in golden.items():
        gold = {norm(k): v for k, v in g.get("golden", {}).items()}
        r = runs.get(qid)
        if r is None:
            per_q.append({"qid": qid, "status": "missing-run"})
            problems += 1
            continue
        read = {norm(p) for p in r.get("files_read", [])}
        if not gold:
            # unanswerable 诚实探针(W-QRY-3):不评检索,只提示人工核对 answer
            per_q.append({"qid": qid, "status": "unanswerable",
                          "answer": r.get("answer", "")[:120]})
            continue
        must = {s for s, v in gold.items() if v == 2}
        helpful = {s for s, v in gold.items() if v == 1}
        denom = len(must) + 0.5 * len(helpful)
        rec = (len(read & must) + 0.5 * len(read & helpful)) / denom if denom else 0.0
        wiki_read = {p for p in read if not p.startswith("raw/")} or read
        prec = len(read & set(gold)) / len(wiki_read) if wiki_read else 0.0
        tot_p += prec
        tot_r += rec
        n += 1
        miss = sorted(must - read)
        if miss:
            problems += 1
        per_q.append({"qid": qid, "status": "scored",
                      "precision": round(prec, 4), "recall": round(rec, 4),
                      "miss_must": miss,
                      "extra_read": sorted(wiki_read - set(gold))})
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
            print("%-34s   n/a   n/a  [unanswerable] 人工核对诚实性:%s" % (qid, q["answer"][:60]))
        else:
            detail = ("漏必读:%s" % q["miss_must"]) if q["miss_must"] else "✓"
            if q["extra_read"]:
                detail += " 多读:%s" % q["extra_read"][:3]
            print("%-34s %5.2f %5.2f  %s" % (qid, q["precision"], q["recall"], detail))
    if summary["n"]:
        print("\n均值(不含 unanswerable): precision %.3f  recall %.3f  (n=%d)"
              % (summary["precision"], summary["recall"], summary["n"]))
    if summary["problem_q"]:
        print("发现问题: %d 题存在漏必读或 run 缺失 → exit 1" % summary["problem_q"])


def export_qrels(golden_rows: list[dict], out: Path) -> None:
    """BEIR 兼容 qrels(qid<TAB>docid<TAB>rel);slug 保持 golden 原样不归一。
    默认写 <root>/state/(工具写入白名单 W-ARCH-2:raw/+site/+state/;qrels 为
    纯派生物可随时重导,故不像参考实例那样落 evals/——那属实例数据目录)。"""
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

    golden_path = resolve(root, args.golden) if args.golden else root / "evals" / "golden.jsonl"
    if not golden_path.is_file():
        print("错误: golden 不存在:%s(用 --golden 指定)" % golden_path, file=sys.stderr)
        return 2
    golden_rows, golden_errs = load_jsonl(golden_path)
    for msg in golden_errs:
        print("警告: %s" % msg, file=sys.stderr)

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
