#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki eval_compare — 多方案(arm@tree)在同一 golden 上的横评对照表。

移植自参考实例 newpj4 tools/eval_compare.py(2026-07-19,M2);打分与记账逻辑保持,
硬编码全部参数化:golden 走 --golden/--root;RAW_SLICE 与 est_tokens profile **逐树**
读取该树 wiki.config.json 的 budgets(统一经 lib/fm.load_config 单源载入)。
W-UPG-2 升级门禁(P/R 与 tok/题不回退)的横评工具;回退与否由调用方对照基线裁决。

■ 记账口径(勿改;Spec §11 评测协议的成本基线):
  - token 成本按 **arm 对应内容树内文件的实际体量** 客观重算,**不采信 agent 自报**;
  - **grep 命中不算 read**:files_read 只记 agent 真正 Read 打开过的文件
    (W-LNT-1「大文件 grep-only」协议红利得以量化的前提);
  - raw/ 文件按「锚定切片」flat 计费 = 该树 config `budgets.raw_slice_tokens`(缺省 1200)
    —— 协议规定 raw 不整读,故不按全文体量计;
  - wiki 页按全文 est_tokens 计,profile = 该树 config `budgets.est_tokens_profile`(缺省 cjk);
  - 每题内同一文件去重计一次。

■ arm 规格:<name>=<run.jsonl>@<tree>,可给多个:
    python3 tools/eval_compare.py \\
        base=evals/runs/a.jsonl@/path/to/main R3=evals/runs/b.jsonl@/path/to/worktree \\
        --root /path/to/instance
  run/tree 相对路径按 cwd 解析(tree 是「另一棵树」,不隶属 --root;建议给绝对路径);
  tree 无 wiki.config.json(如对未迁移参考实例 newpj4 只读对照,Spec §15)时按缺省
  预算记账并打印提示。--golden 相对路径按 --root 解析。

■ run 文件格式与 eval_retrieval.py 相同(与参考实例 newpj4 的 run 文件格式兼容):
    {"qid": "...", "files_read": ["concepts/mcp", "raw/xx/yy.md", ...], "answer": "..."}
  golden 每行:{"qid", "type", "question", "golden": {"<slug>": 2|1}, "answer_keys": [...]}
  (2=必读,1=有帮助权重 0.5;golden 空 {} = unanswerable 诚实探针)。

退出码:0 = 对照表产出成功(不做基线判定,W-UPG-2 的回退裁决由调用方执行);
        1 = 数据行解析失败;2 = 用法 / 路径 / 配置错误。
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

# 树内无 config 时的缺省记账参数(与 wiki.config schema 默认值一致;参考实例 newpj4 为 zh→cjk)
DEFAULT_RAW_SLICE_TOK = 1200
DEFAULT_PROFILE = "cjk"


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


def tree_budgets(tree: Path) -> tuple[int, str, str | None]:
    """逐树读记账参数:统一走 lib/fm.load_config(经 init_render 校验+默认值,单源)。
    树无 wiki.config.json(未迁移树只读对照)→ 回退缺省值,返回第三元为提示文本。"""
    try:
        cfg = fm.load_config(tree)
        b = cfg.get("budgets") or {}
        return (int(b.get("raw_slice_tokens", DEFAULT_RAW_SLICE_TOK)),
                str(b.get("est_tokens_profile", DEFAULT_PROFILE)), None)
    except Exception as e:
        note = ("%s: wiki.config.json 不可用(%s);按缺省 raw_slice=%d / profile=%s 记账"
                % (tree, e, DEFAULT_RAW_SLICE_TOK, DEFAULT_PROFILE))
        return DEFAULT_RAW_SLICE_TOK, DEFAULT_PROFILE, note


def file_tokens(tree: Path, slug: str, raw_slice_tok: int, profile: str,
                cache: dict, missing: set) -> int:
    """单文件 token 成本:按树内文件实际体量客观重算(不采信 agent 自报)。
    raw/ 按锚定切片 flat 计费(协议规定不整读);wiki 页按全文 est_tokens。"""
    if slug in cache:
        return cache[slug]
    if slug.startswith("raw/"):
        tok = raw_slice_tok
    else:
        f = tree / "wiki" / (slug + ".md")
        if f.is_file():
            tok = fm.est_tokens(f.read_text(encoding="utf-8"), profile)
        else:
            tok = 0  # 树内缺页:计 0 并记入 missing(横评时留意树间页面覆盖差异)
            missing.add(slug)
    cache[slug] = tok
    return tok


def score_arm(golden_rows: list[dict], run_rows: list[dict], tree: Path,
              raw_slice_tok: int, profile: str) -> dict:
    """P/R 打分逻辑与参考实例 newpj4 逐字一致;token 记账见 file_tokens。"""
    golden = {g["qid"]: g for g in golden_rows}
    runs = {r["qid"]: r for r in run_rows}
    tot_p = tot_r = tok_all = 0.0
    n = miss_must = 0
    honest: list[tuple[str, bool]] = []
    per_q_tok: dict[str, int] = {}
    cache: dict = {}
    missing: set = set()
    for qid, g in golden.items():
        r = runs.get(qid)
        if r is None:
            continue
        read = [norm(p) for p in r.get("files_read", [])]
        # 每题内同一文件去重计一次(dict.fromkeys 保序去重)
        per_q_tok[qid] = sum(file_tokens(tree, s, raw_slice_tok, profile, cache, missing)
                             for s in dict.fromkeys(read))
        tok_all += per_q_tok[qid]
        gold = {norm(k): v for k, v in g.get("golden", {}).items()}
        if not gold:
            # unanswerable 诚实探针:粗启发式(答案含「未收录」/"not");
            # 逐题精核走 eval_retrieval 的 per-question 输出人工复查
            ans = r.get("answer", "")
            honest.append((qid, "未收录" in ans or "not" in ans.lower()))
            continue
        must = {s for s, v in gold.items() if v == 2}
        helpful = {s for s, v in gold.items() if v == 1}
        rset = set(read)
        denom = len(must) + 0.5 * len(helpful)
        rec = (len(rset & must) + 0.5 * len(rset & helpful)) / denom if denom else 0.0
        wiki_read = {p for p in rset if not p.startswith("raw/")} or rset
        prec = len(rset & set(gold)) / len(wiki_read) if wiki_read else 0.0
        tot_p += prec
        tot_r += rec
        n += 1
        if must - rset:
            miss_must += 1
    return {
        "n": n,
        "precision": round(tot_p / n, 4) if n else 0.0,
        "recall": round(tot_r / n, 4) if n else 0.0,
        "miss_must_q": miss_must,
        "honest_pass": sum(1 for _, ok in honest if ok),
        "honest_n": len(honest),
        "tok_per_q": round(tok_all / max(1, len(per_q_tok)), 1),
        "tok_worst": max(per_q_tok.values()) if per_q_tok else 0,
        "per_q_tok": per_q_tok,
        "missing_files": sorted(missing),
        "raw_slice_tokens": raw_slice_tok,
        "est_tokens_profile": profile,
    }


def print_table(rows: list[tuple[str, dict]], notes: list[str]) -> None:
    print("%-12s %6s %6s %6s %5s %9s %9s"
          % ("arm", "prec", "rec", "漏必读题", "诚实", "均tok/题", "最差题tok"))
    for name, s in rows:
        print("%-12s %6.3f %6.3f %6d %5s %9.0f %9.0f"
              % (name, s["precision"], s["recall"], s["miss_must_q"],
                 "%d/%d" % (s["honest_pass"], s["honest_n"]),
                 s["tok_per_q"], s["tok_worst"]))
    print("\n记账基线(逐树 config):")
    for name, s in rows:
        print("  %-12s tree=%s  raw_slice=%d  profile=%s"
              % (name, s["tree"], s["raw_slice_tokens"], s["est_tokens_profile"]))
    if len(rows) > 1:
        qids = sorted(set().union(*(s["per_q_tok"] for _, s in rows)))
        print("\n逐题 token(去重文件计;grep 不计入):")
        print("qid".ljust(34) + "".join("%10s" % name for name, _ in rows))
        for q in qids:
            print(q.ljust(34) + "".join("%10.0f" % s["per_q_tok"].get(q, 0) for _, s in rows))
    if notes:
        print()
        for msg in notes:
            print("提示: %s" % msg)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="arm@tree 多方案横评:token 成本按各树文件实际体量客观重算(详见文件头注)")
    ap.add_argument("arms", nargs="+", metavar="NAME=RUN@TREE",
                    help="如 R3=evals/runs/x.jsonl@/path/to/worktree(run/tree 相对路径按 cwd 解析)")
    ap.add_argument("--root", default=".",
                    help="实例根(默认 cwd):--golden 相对路径的解析基准")
    ap.add_argument("--golden", default=None,
                    help="golden jsonl(默认 <root>/evals/golden.jsonl)")
    ap.add_argument("--json", dest="as_json", action="store_true", help="机器可读 JSON 输出")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("错误: --root 不是目录:%s" % root, file=sys.stderr)
        return 2
    if args.golden:
        g = Path(args.golden).expanduser()
        golden_path = g if g.is_absolute() else root / g
    else:
        golden_path = root / "evals" / "golden.jsonl"
    if not golden_path.is_file():
        print("错误: golden 不存在:%s(用 --golden 指定)" % golden_path, file=sys.stderr)
        return 2
    golden_rows, data_errs = load_jsonl(golden_path)

    specs: list[tuple[str, Path, Path]] = []
    for spec in args.arms:
        if "=" not in spec or "@" not in spec.split("=", 1)[1]:
            print("错误: arm 规格应为 NAME=RUN@TREE,得到:%s" % spec, file=sys.stderr)
            return 2
        name, rest = spec.split("=", 1)
        run_s, tree_s = rest.rsplit("@", 1)
        run_p = Path(run_s).expanduser()
        tree_p = Path(tree_s).expanduser().resolve()
        if not run_p.is_file():
            print("错误: arm %s 的 run 文件不存在:%s" % (name, run_p), file=sys.stderr)
            return 2
        if not tree_p.is_dir():
            print("错误: arm %s 的 tree 不是目录:%s" % (name, tree_p), file=sys.stderr)
            return 2
        specs.append((name, run_p, tree_p))

    notes: list[str] = []
    rows: list[tuple[str, dict]] = []
    for name, run_p, tree_p in specs:
        raw_slice_tok, profile, note = tree_budgets(tree_p)
        if note:
            notes.append(note)
        run_rows, errs = load_jsonl(run_p)
        data_errs.extend(errs)
        s = score_arm(golden_rows, run_rows, tree_p, raw_slice_tok, profile)
        s["run"] = str(run_p)
        s["tree"] = str(tree_p)
        if s["missing_files"]:
            notes.append("arm %s: %d 个 files_read 在树内缺页(计 0 tok):%s"
                         % (name, len(s["missing_files"]), s["missing_files"][:5]))
        rows.append((name, s))

    if args.as_json:
        print(json.dumps({"golden": str(golden_path),
                          "arms": [dict(s, name=name) for name, s in rows],
                          "notes": notes, "data_errors": data_errs},
                         ensure_ascii=False, indent=2))
        return 1 if data_errs else 0
    print_table(rows, notes)
    for msg in data_errs:
        print("警告: %s" % msg, file=sys.stderr)
    return 1 if data_errs else 0


if __name__ == "__main__":
    sys.exit(main())
