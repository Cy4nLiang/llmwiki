#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki tests/run_ci.py — hello-wiki 夹具 CI 闭环(唯一入口;仅 Python 标准库)。

夹具:tests/hello-wiki/(合成 domain「hello-wiki 示例项目知识库」,内容全部原创)。
流程(全部产物写系统 tmp,经 tempfile;不写仓库):

  (a) init_render 渲染 config.json → tmp base 实例 → overlay 覆盖注入
      → lint --check-slots(0 残留);
  (b) build_site + build_index → 立即重跑一遍,断言:两工具自报 unchanged/written=[]
      且全部派生产物逐字节相同(确定性/幂等);
  (c) lint_wiki 全量 → 断言 exit 0(夹具即「lint 干净样例」:error 级为 0;
      soft warning 允许,如 W-ARCH-3 对 schema/ 的白名单告警);
      另断言 contradictions.md 恰好派生 1 条(概念页 > ⚠️ 行);
  (d) sync.py status/pending --json → notes 管线 pending==1(reason=no-source-page,
      pitfall→light);guide 管线依 rolling_digest 判定(匹配→0;CI 现场改快照
      →digest-changed;还原→0)。local_notes status/register:4 件全合格、
      register 幂等、台账落 state/notes.manifest.json;
  (e) eval_retrieval 对 evals/runs/scripted.jsonl(手写 run)打分 → 断言
      exit 0 且 summary 等于预期常数 {n:3, precision:0.8333, recall:0.8889};
  (f) config.multifacet.json 变体(peers[0].path 由 CI 现场替换为 base 实例路径)
      重复 (a)-(c),并断言 index-sources-{infra,app}.md 生成、
      peer 互引 lint 为 soft warning(W-XRF-1)不 fail。

退出码:0 = 全部断言通过;1 = 任一断言失败(fail-fast,失败后保留 tmp 便于排查);
        2 = 用法/环境错误(夹具或框架文件缺失)。
用法:python3 tests/run_ci.py [--keep] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

PY = sys.executable
HERE = Path(__file__).resolve().parent          # llmwiki/tests
FW = HERE.parent                                # llmwiki 框架根
FX = HERE / "hello-wiki"                        # 夹具根
DATE = "2026-07-19"                             # 固定渲染日期(确定性)
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

# 手写 run 的确定分数(推导:q1 P=1 R=1;q2 P=1/2 R=1/1.5;q3 P=1 R=1;q4 不计分)
EXPECT_SUMMARY = {"n": 3, "precision": 0.8333, "recall": 0.8889, "problem_q": 0}
PENDING_RAW = "raw/inbox/2026-07-15-pitfall-timezone-greeting.md"
PENDING_SRC = "wiki/sources/2026-07-15-pitfall-timezone-greeting.md"

# lint 中必须为 0 的 error 级检查项(soft/warning 项不在此列)
ZERO_ERROR_CHECKS = ("broken_links", "fm_required", "fm_drift", "map_budget",
                     "stale_index", "log_format")


class CheckFail(Exception):
    pass


class CI:
    """断言记账:通过打 ✓,失败打 ✗ 并 fail-fast(保留 tmp 现场)。"""

    def __init__(self, verbose: bool):
        self.verbose = verbose
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed.append(name)
            print("  ✓ %s" % name)
        else:
            self.failed.append((name, detail))
            print("  ✗ %s" % name)
            if detail:
                print("      %s" % detail.replace("\n", "\n      "))
            raise CheckFail(name)

    def run(self, cmd: list, cwd=None) -> tuple[int, str, str]:
        scmd = [str(c) for c in cmd]
        if self.verbose:
            print("  $ %s" % " ".join(scmd))
        r = subprocess.run(scmd, cwd=cwd, capture_output=True, text=True, env=ENV)
        if self.verbose and r.stdout:
            print("    " + r.stdout.strip().replace("\n", "\n    "))
        return r.returncode, r.stdout, r.stderr

    def run_ok(self, name: str, cmd: list, want_rc: int = 0) -> tuple[str, str]:
        rc, out, err = self.run(cmd)
        self.check("%s → rc=%d" % (name, want_rc), rc == want_rc,
                   "rc=%s\nstdout(tail): %s\nstderr(tail): %s"
                   % (rc, out[-600:], err[-600:]))
        return out, err

    def run_json(self, name: str, cmd: list, want_rc: int = 0) -> dict:
        out, _err = self.run_ok(name, cmd, want_rc)
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            self.check("%s stdout 为纯 JSON" % name, False,
                       "%s;stdout head: %r" % (e, out[:300]))
            raise AssertionError  # unreachable


# ---------------------------------------------------------------- 工具函数

def overlay_inject(dst: Path) -> int:
    """把夹具 overlay/ 整树覆盖注入实例(文件级覆盖,字节保真)。"""
    n = 0
    src_root = FX / "overlay"
    for src in sorted(src_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        d = dst / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(d))
        n += 1
    return n


def derived_paths(inst: Path) -> list[Path]:
    """确定性断言所覆盖的派生产物清单。"""
    fixed = [inst / "site" / "data.json",
             inst / "site" / "agent" / "sources.jsonl",
             inst / "site" / "agent" / "pages.jsonl",
             inst / "wiki" / "index.md",
             inst / "wiki" / "contradictions.md"]
    return fixed + sorted((inst / "wiki").glob("index-sources*.md"))


def snapshot(paths: list[Path]) -> dict:
    return {str(p): (p.read_bytes() if p.is_file() else None) for p in paths}


# ---------------------------------------------------------------- 阶段

def phase_render(ci: CI, cfg_path: Path, inst: Path, label: str) -> None:
    print("\n[%s/a] init_render + overlay 注入 + check-slots" % label)
    ci.run_ok("%s init_render" % label,
              [PY, FW / "tools" / "init_render.py", "--config", cfg_path,
               "--target", inst, "--date", DATE])
    n = overlay_inject(inst)
    ci.check("%s overlay 注入(%d 文件)" % (label, n), n >= 15,
             "overlay 文件数异常:%d" % n)
    ci.run_ok("%s lint --check-slots" % label,
              [PY, inst / "tools" / "lint_wiki.py", "--check-slots", "--target", inst])


def phase_build(ci: CI, inst: Path, label: str) -> dict:
    print("\n[%s/b] build_site + build_index → 幂等重跑逐字节比对" % label)
    b1 = ci.run_json("%s build_site #1" % label,
                     [PY, inst / "tools" / "build_site.py", "--root", inst, "--json"])
    ci.check("%s build_site ok=true" % label, b1.get("ok") is True,
             json.dumps(b1.get("problems"), ensure_ascii=False))
    i1 = ci.run_json("%s build_index #1" % label,
                     [PY, inst / "tools" / "build_index.py", "--root", inst, "--json"])
    ci.check("%s build_index ok=true" % label, i1.get("ok") is True)

    snap = snapshot(derived_paths(inst))
    ci.check("%s 派生产物齐备" % label, all(v is not None for v in snap.values()),
             "缺失:%s" % [k for k, v in snap.items() if v is None])

    b2 = ci.run_json("%s build_site #2(重跑)" % label,
                     [PY, inst / "tools" / "build_site.py", "--root", inst, "--json"])
    ci.check("%s build_site 重跑全部 unchanged" % label,
             all(v == "unchanged" for v in b2.get("outputs", {}).values()),
             json.dumps(b2.get("outputs"), ensure_ascii=False))
    i2 = ci.run_json("%s build_index #2(重跑)" % label,
                     [PY, inst / "tools" / "build_index.py", "--root", inst, "--json"])
    ci.check("%s build_index 重跑 written=[]" % label, i2.get("written") == [],
             json.dumps(i2.get("written"), ensure_ascii=False))

    snap2 = snapshot(derived_paths(inst))
    diff = [k for k in snap if snap.get(k) != snap2.get(k)]
    ci.check("%s 派生产物逐字节相同(确定性)" % label, not diff, "漂移:%s" % diff)
    return b1


def phase_lint(ci: CI, inst: Path, label: str) -> dict:
    print("\n[%s/c] lint_wiki 全量(夹具即 lint 干净样例)" % label)
    data = ci.run_json("%s lint_wiki --json" % label,
                       [PY, inst / "tools" / "lint_wiki.py", "--root", inst, "--json"])
    ci.check("%s lint errors == 0(exit 0)" % label, data.get("errors") == 0,
             json.dumps([c for c in data.get("checks", []) if c["count"]],
                        ensure_ascii=False)[:1500])
    totals = data.get("totals", {})
    for cid in ZERO_ERROR_CHECKS:
        ci.check("%s lint %s == 0" % (label, cid), totals.get(cid) == 0,
                 "totals=%s" % json.dumps(totals, ensure_ascii=False))
    mdata = ci.run_json("%s lint --manifest" % label,
                        [PY, inst / "tools" / "lint_wiki.py", "--root", inst, "--manifest", "--json"])
    ci.check("%s lint --manifest 零 fork 漂移" % label, mdata.get("errors") == 0,
             json.dumps([c for c in mdata.get("checks", []) if c["count"]], ensure_ascii=False)[:800])
    return data


def assert_contradictions(ci: CI, inst: Path, label: str) -> None:
    p = inst / "wiki" / "contradictions.md"
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
             if ln.startswith("- [[")]
    ci.check("%s contradictions.md 派生恰 1 条" % label, len(lines) == 1,
             "得到 %d 条:%s" % (len(lines), lines))
    ci.check("%s 矛盾条目溯源 concepts/greeting-protocol" % label,
             "concepts/greeting-protocol" in lines[0], lines[0][:200])


def phase_sync(ci: CI, inst: Path) -> None:
    print("\n[base/d1] sync status/pending:notes pending==1;guide 依 rolling_digest")
    sync = inst / "tools" / "sync.py"

    def status() -> dict:
        st = ci.run_json("sync status --json",
                         [PY, sync, "status", "--root", inst, "--json"])
        return {p["name"]: p for p in st["pipelines"]}

    by = status()
    notes, guide = by["notes"], by["guide"]
    ci.check("notes raw=4 / ingested=3 / pending=1",
             (notes["raw_count"], notes["ingested_count"], notes["pending_count"]) == (4, 3, 1),
             json.dumps(notes, ensure_ascii=False)[:400])
    p0 = notes["pending"][0]
    ci.check("notes pending 条目字段(no-source-page / pitfall→light)",
             p0["raw_file"] == PENDING_RAW and p0["expected_source"] == PENDING_SRC
             and p0["reason"] == "no-source-page" and p0["source_kind"] == "pitfall"
             and p0["tier"] == "light",
             json.dumps(p0, ensure_ascii=False))
    ci.check("guide raw=1 / ingested=1 / pending=0(rolling_digest 匹配)",
             (guide["raw_count"], guide["ingested_count"], guide["pending_count"]) == (1, 1, 0),
             json.dumps(guide, ensure_ascii=False)[:400])

    pd = ci.run_json("sync pending --json",
                     [PY, sync, "pending", "--root", inst, "--json"])
    ci.check("sync pending 扁平清单 pending_total==1", pd.get("pending_total") == 1,
             json.dumps(pd.get("pending"), ensure_ascii=False)[:400])

    # rolling 判新即 digest:CI 现场改快照 → digest-changed;还原 → 归零
    snap_file = inst / "raw" / "guide" / "style-guide.md"
    orig = snap_file.read_bytes()
    snap_file.write_bytes(orig + b"\n<!-- ci mutation -->\n")
    guide2 = status()["guide"]
    ci.check("快照变更后 guide pending==1 且 reason=digest-changed",
             guide2["pending_count"] == 1
             and guide2["pending"][0]["reason"] == "digest-changed",
             json.dumps(guide2, ensure_ascii=False)[:400])
    snap_file.write_bytes(orig)
    guide3 = status()["guide"]
    ci.check("快照还原后 guide pending==0", guide3["pending_count"] == 0,
             json.dumps(guide3, ensure_ascii=False)[:400])


def phase_local_notes(ci: CI, inst: Path) -> None:
    print("\n[base/d2] local_notes status/register(push 台账,幂等)")
    ln = FW / "adapters" / "local_notes.py"
    s1 = ci.run_json("local_notes status #1",
                     [PY, ln, "status", "--root", inst, "--json"])
    ci.check("status:4 件全合格、未登记",
             s1.get("ok") is True and s1.get("total") == 4
             and s1.get("qualified") == 4 and s1.get("registered") == 0,
             json.dumps({k: s1.get(k) for k in ("ok", "total", "qualified", "registered")}))
    r1 = ci.run_json("local_notes register #1",
                     [PY, ln, "register", "--root", inst, "--json"])
    ci.check("register:新登记 4、无跳过",
             r1.get("added") == 4 and r1.get("skipped") == [],
             json.dumps(r1, ensure_ascii=False)[:400])
    ci.check("台账落位 state/notes.manifest.json",
             (inst / "state" / "notes.manifest.json").is_file())
    r2 = ci.run_json("local_notes register #2(幂等)",
                     [PY, ln, "register", "--root", inst, "--json"])
    ci.check("register 幂等:added=0 / updated=0",
             r2.get("added") == 0 and r2.get("updated") == 0,
             json.dumps(r2, ensure_ascii=False)[:400])
    s2 = ci.run_json("local_notes status #2",
                     [PY, ln, "status", "--root", inst, "--json"])
    ci.check("status:登记数=4", s2.get("registered") == 4,
             json.dumps(s2, ensure_ascii=False)[:300])


def phase_eval(ci: CI, inst: Path) -> None:
    print("\n[base/e] eval_retrieval 对 scripted run → 确定分数")
    shutil.copyfile(str(FX / "evals" / "golden.jsonl"),
                    str(inst / "evals" / "golden.jsonl"))
    (inst / "evals" / "runs").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(FX / "evals" / "runs" / "scripted.jsonl"),
                    str(inst / "evals" / "runs" / "scripted.jsonl"))
    ev = ci.run_json("eval_retrieval --json",
                     [PY, inst / "tools" / "eval_retrieval.py",
                      "evals/runs/scripted.jsonl", "--root", inst, "--json"])
    ci.check("summary 等于预期常数 %s" % json.dumps(EXPECT_SUMMARY),
             ev.get("summary") == EXPECT_SUMMARY,
             json.dumps(ev.get("summary"), ensure_ascii=False))
    q = {x["qid"]: x for x in ev.get("per_question", [])}
    ci.check("q1 P=1.0/R=1.0",
             q["q1-single-hop-default-greeting"]["precision"] == 1.0
             and q["q1-single-hop-default-greeting"]["recall"] == 1.0)
    ci.check("q2 P=0.5/R=0.6667(漏 helpful、多读 1 页)",
             q["q2-how-do-i-add-language"]["precision"] == 0.5
             and q["q2-how-do-i-add-language"]["recall"] == 0.6667)
    ci.check("q3 P=1.0/R=1.0(raw 切片不惩罚)",
             q["q3-exact-fallback-chain"]["precision"] == 1.0
             and q["q3-exact-fallback-chain"]["recall"] == 1.0)
    ci.check("q4 为 unanswerable 诚实探针(不计分)",
             q["q4-unanswerable-deploy"]["status"] == "unanswerable")


def phase_multifacet(ci: CI, tmp: Path, base: Path) -> None:
    label = "mf"
    mf = tmp / "mf"
    print("\n[mf/f] multifacet 变体:facets + peers(条件模块矩阵)")
    cfg = json.loads((FX / "config.multifacet.json").read_text(encoding="utf-8"))
    ci.check("mf config peers 占位符待替换",
             cfg["peers"][0]["path"] == "__PEER_PATH__",
             json.dumps(cfg["peers"], ensure_ascii=False))
    cfg["peers"][0]["path"] = str(base)   # CI 现场造:peer 指向同批渲染的 base 实例
    cfg_path = tmp / "config.multifacet.rendered.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    phase_render(ci, cfg_path, mf, label)

    # CI 现场注入 peer 互引:一条可达命中(应无 finding)+ 一条故意断链(soft warning)
    syn = mf / "wiki" / "syntheses" / "greeting-design-story.md"
    syn.write_text(syn.read_text(encoding="utf-8")
                   + "\n## 跨库参照(CI 现场注入,仅 multifacet 变体)\n\n"
                     "- 对比:[[hub::concepts/greeting-protocol|peer 库的问候协议]] "
                     "—— peer 可达且 slug 命中,应无 finding。\n"
                     "- [[hub::concepts/no-such-page]] —— 故意 peer 断链,"
                     "断言 W-XRF-1 soft warning 不 fail。\n",
                   encoding="utf-8")
    ci.check("mf peer 互引注入完成", "hub::" in syn.read_text(encoding="utf-8"))

    phase_build(ci, mf, label)

    infra = mf / "wiki" / "index-sources-infra.md"
    app = mf / "wiki" / "index-sources-app.md"
    ci.check("mf 分片文件 index-sources-{infra,app}.md 生成",
             infra.is_file() and app.is_file())
    ci.check("mf 无单一 index-sources.md(分面分片取代)",
             not (mf / "wiki" / "index-sources.md").exists())
    itxt = infra.read_text(encoding="utf-8")
    atxt = app.read_text(encoding="utf-8")
    ci.check("infra 分片含 adr + 滚动指南源",
             "sources/2026-07-01-adr-greeting-default" in itxt
             and "sources/guide-style-guide" in itxt)
    ci.check("app 分片含 pitfall + howto 源",
             "sources/2026-07-05-pitfall-emoji-encoding" in atxt
             and "sources/2026-07-08-howto-add-greeting-language" in atxt)
    data = json.loads((mf / "site" / "data.json").read_text(encoding="utf-8"))
    ci.check("mf data.json by_facet.team == {app:2, infra:2}",
             data["stats"]["by_facet"].get("team") == {"app": 2, "infra": 2},
             json.dumps(data["stats"]["by_facet"], ensure_ascii=False))

    lint = phase_lint(ci, mf, label)
    checks = {c["id"]: c for c in lint.get("checks", [])}
    peer = checks.get("peer_links", {})
    ci.check("mf peer 断链为 soft warning(恰 1 条,exit 仍 0)",
             peer.get("count") == 1 and peer.get("severity") == "warning"
             and "no-such-page" in (peer.get("items") or [""])[0],
             json.dumps(peer, ensure_ascii=False)[:400])
    assert_contradictions(ci, mf, label)


# ---------------------------------------------------------------- 主流程

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="hello-wiki 夹具 CI(标准库,唯一入口)")
    ap.add_argument("--keep", action="store_true", help="结束后保留 tmp 实例(默认成功即清理)")
    ap.add_argument("--verbose", action="store_true", help="回显子进程命令与 stdout")
    args = ap.parse_args(argv)

    for need in (FX / "config.json", FX / "config.multifacet.json",
                 FX / "overlay", FX / "evals" / "golden.jsonl",
                 FX / "evals" / "runs" / "scripted.jsonl",
                 FW / "tools" / "init_render.py", FW / "tools" / "lint_wiki.py",
                 FW / "tools" / "build_site.py", FW / "tools" / "build_index.py",
                 FW / "tools" / "sync.py", FW / "tools" / "eval_retrieval.py",
                 FW / "adapters" / "local_notes.py", FW / "tools" / "lib" / "fm.py"):
        if not need.exists():
            print("错误: 缺少夹具/框架文件:%s" % need, file=sys.stderr)
            return 2

    tmp = Path(tempfile.mkdtemp(prefix="llmwiki-hello-ci-"))
    base = tmp / "base"
    ci = CI(args.verbose)
    print("== hello-wiki CI ==\ntmp: %s" % tmp)
    crashed = False
    try:
        phase_render(ci, FX / "config.json", base, "base")     # (a)
        phase_build(ci, base, "base")                          # (b)
        phase_lint(ci, base, "base")                           # (c)
        assert_contradictions(ci, base, "base")
        phase_sync(ci, base)                                   # (d)
        phase_local_notes(ci, base)
        phase_eval(ci, base)                                   # (e)
        phase_multifacet(ci, tmp, base)                        # (f)
    except CheckFail:
        pass                                                   # 已记账,fail-fast
    except Exception:                                          # noqa: BLE001 — 环境级故障也要给出现场
        crashed = True
        traceback.print_exc()

    ok = not ci.failed and not crashed
    print("\n" + "=" * 60)
    if ok:
        print("PASS — %d 项断言全部通过" % len(ci.passed))
        if args.keep:
            print("(--keep)tmp 保留:%s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("FAIL — 通过 %d 项;失败:" % len(ci.passed))
        for name, detail in ci.failed:
            print("  ✗ %s" % name)
            if detail:
                print("      %s" % detail.replace("\n", "\n      ")[:800])
        if crashed:
            print("  ✗ (环境级异常,见上方 traceback)")
        print("tmp 现场保留排查:%s" % tmp)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
