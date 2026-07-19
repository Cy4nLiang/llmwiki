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
      peer 互引 lint 为 soft warning(W-XRF-1)不 fail;
  (g) eval_retrieval --check-golden:夹具 golden 零 error 零 warning(exit 0);
      现场造坏 golden(未知 type=warning + golden 非对象=结构错误)断言 exit 2;
      any-of 组(golden_groups):现场造 2 题小 golden(1 题带 2 权组)+ 命中/未命中
      两态 run——命中态断言 R=1.0/exit 0 与组明细(hit/hit_pages),未命中态断言
      组题 R=0.5/漏必读组计 problem_q/exit 1,无组对照题输出形状不变;
      再造坏组(组内单页 / 组页与单点重复)--check-golden 断言 exit 2;
      hello-wiki 既有 golden 与 (e) 的 EXPECT_SUMMARY 不动;
  (h) 模拟升级一轮(M3 核心;Spec §10):tmp 内复制框架仓为 fw-next,改一个 frozen
      工具(加注释行)+ 一个 render-once 模板(followups 加一行)+ bump NEXT_V
      (由当前 VERSION 按 semver patch+1 派生,不硬编码)+ UPGRADING.md 顶插条目 +
      重跑 gen_manifest;对 base 实例:
      (h1) --dry-run 全树逐文件比对零写入,计划列出上述文件;
      (h2) 实跑:frozen 干净覆盖、未被实例改过的 render-once 自动采用新版、
           VERSION==NEXT_V、framework/base/ 与 MANIFEST 快照刷新、lint 门禁 rc=0、
           wiki/log.md 新增 upgrade 条目(W-LOG-1);
      (h3) 冲突路(克隆实例):手改 render-once 再升级 → 原文件保留 +
           <file>.upgrade-new 生成 + exit 1;
      (h4) fork 路(克隆实例):手改 frozen 工具再升级 → 列 fork 候选未覆盖 + exit 1;
      (h5) stub-ir 回退护栏:tmp 造剥离 compute_conds/stamp_dates/snapshot_manifest
           的 stub init_render(拷真文件删三函数,模拟函数化前旧渲染器),importlib
           驱动 upgrade.render_tree 走镜像回退路径,断言渲染产物与新路径(init_render
           单源)逐字节等价;snapshot_manifest 镜像同法比对(upgrade.py 头注声明的
           旧版回退设计,防两侧口径漂移);
  (i) extras 冒烟:serve.py 子进程起随机高位口 → GET /api/status 合法 JSON 且含
      pipelines 段 → 关停;i18n_link.py 未配置语言对 exit 2;
  (j) manual 哨兵:base sync status 不再出「未声明适配器」警告(guide adapter=manual),
      peers 段与 framework_version 进 status --json;mf 实例 peers[0](hub→base)
      可达、pages.jsonl 非空、报版本 skew(base 已升 NEXT_V)。

退出码:0 = 全部断言通过;1 = 任一断言失败(fail-fast,失败后保留 tmp 便于排查);
        2 = 用法/环境错误(夹具或框架文件缺失)。
用法:python3 tests/run_ci.py [--keep] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

PY = sys.executable
HERE = Path(__file__).resolve().parent          # llmwiki/tests
FW = HERE.parent                                # llmwiki 框架根
FX = HERE / "hello-wiki"                        # 夹具根
# 固定渲染日期(确定性)。与 overlay log.md 的 bootstrap 条目日期对齐:升级三方合并的
# base 侧按 bootstrap 日期重渲染,「现文件 == base_rendered」判定要求逐字节一致(§h2)。
DATE = "2026-07-16"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

# 手写 run 的确定分数(推导:q1 P=1 R=1;q2 P=1/2 R=1/1.5;q3 P=1 R=1;q4 不计分)
EXPECT_SUMMARY = {"n": 3, "precision": 0.8333, "recall": 0.8889, "problem_q": 0}
PENDING_RAW = "raw/inbox/2026-07-15-pitfall-timezone-greeting.md"
PENDING_SRC = "wiki/sources/2026-07-15-pitfall-timezone-greeting.md"

# lint 中必须为 0 的 error 级检查项(soft/warning 项不在此列)
ZERO_ERROR_CHECKS = ("broken_links", "fm_required", "fm_drift", "map_budget",
                     "stale_index", "log_format")

# ---- (h) 模拟升级一轮的常数 --------------------------------------------------
CUR_V = (FW / "framework" / "VERSION").read_text().strip()   # 框架当前版本(升级起点)
_CUR_M = re.match(r"^(\d+)\.(\d+)\.(\d+)$", CUR_V)
if _CUR_M is None:                              # 常量区即时校验:VERSION 须为三段 semver
    print("错误: framework/VERSION 不是三段语义版本:%r" % CUR_V, file=sys.stderr)
    sys.exit(2)
# fw-next bump 到的版本:CUR_V patch+1 派生(发版后免手改模拟版本号)
NEXT_V = "%s.%s.%d" % (_CUR_M.group(1), _CUR_M.group(2), int(_CUR_M.group(3)) + 1)
UPG_DATE = "2026-07-19"                         # 升级簿记日期(log 条目/UPGRADING 落款)
FROZEN_TOUCH = "tools/build_index.py"           # ① fw-next 改动的 frozen 工具
FROZEN_MARK = "# fw-next: upgrade smoke marker(hello-wiki CI 注入,%s)" % NEXT_V
TPL_TOUCH = "templates/wiki/followups.md"       # ② fw-next 改动的 render-once 模板
TPL_MARK = "- 升级冒烟标记:%s 模板新增行(hello-wiki CI 注入;纯文本非 wikilink)。" % NEXT_V
INST_MARK = "<!-- 实例手改:本地补充条目(hello-wiki CI 注入,h3 冲突路) -->"
FORK_MARK = "# 实例本地改动:fork 候选(hello-wiki CI 注入,h4 fork 路)"
# (h5) stub 剥离的三个单源函数(upgrade.py 头注:旧版渲染器缺它们时 hasattr 回退镜像)
STRIP_FUNCS = ("compute_conds", "stamp_dates", "snapshot_manifest")
UPGRADING_ENTRY = """## %s — %s(判级:PATCH)

### 变更摘要
- CI 升级冒烟造版:frozen 工具 %s 追加注释行;%s 追加一行。

### 迁移清单(逐条引规则 ID)
| 规则 ID | 变更类型 | 实例动作 | 涉及档位 |
|---|---|---|---|
| — | 文案 | 无动作(MANIFEST 校验干净 → frozen 自动覆盖;实例未改 → 模板自动采用) | frozen / render-once |

### frozen 覆盖清单
- %s —— 注释行追加;hash 校验干净则整体覆盖(W-UPG-1)

### 验收
- lint 全绿(W-UPG-2:实例 golden 属实例数据,升级不触碰)。

""" % (NEXT_V, UPG_DATE, FROZEN_TOUCH, TPL_TOUCH, FROZEN_TOUCH)


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


def tree_state(root: Path) -> dict:
    """全树逐文件状态(相对路径 → sha256 / symlink 目标),用于 --dry-run 零写入断言。"""
    st = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            st[rel] = ("link", os.readlink(str(p)))
        elif p.is_file():
            st[rel] = ("file", hashlib.sha256(p.read_bytes()).hexdigest())
    return st


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


def phase_golden_check(ci: CI, base: Path, tmp: Path) -> None:
    print("\n[base/g] eval_retrieval --check-golden:夹具干净 / 坏 golden exit 2")
    ev = base / "tools" / "eval_retrieval.py"
    chk = ci.run_json("check-golden 夹具 --json",
                      [PY, ev, "--check-golden", "evals/golden.jsonl",
                       "--root", base, "--json"])
    ci.check("check-golden 夹具:ok 且零 error 零 warning",
             chk.get("ok") is True and chk.get("errors") == []
             and chk.get("warnings") == [] and chk.get("n_questions") == 4,
             json.dumps(chk, ensure_ascii=False)[:500])

    bad = tmp / "bad-golden.jsonl"
    bad.write_text(
        '{"qid": "bad1", "type": "mystery-type", "question": "未知题型?", '
        '"golden": {"concepts/greeting-protocol": 2}, "answer_keys": ["x"]}\n'
        '{"qid": "bad2", "type": "single-hop", "question": "golden 非对象?", '
        '"golden": ["not", "an", "object"], "answer_keys": ["y"]}\n',
        encoding="utf-8")
    rc, out, err = ci.run([PY, ev, "--check-golden", bad, "--root", base, "--json"])
    ci.check("坏 golden(未知 type + golden 非对象)→ exit 2", rc == 2,
             "rc=%s\nstdout(tail): %s\nstderr(tail): %s" % (rc, out[-400:], err[-400:]))
    try:
        rep = json.loads(out)
    except json.JSONDecodeError:
        rep = {}
    ci.check("坏 golden 报告:恰 1 结构错误(golden 非对象)+ 未知 type 警告",
             rep.get("ok") is False and len(rep.get("errors", [])) == 1
             and "非对象" in rep["errors"][0]
             and any("未知 type" in w for w in rep.get("warnings", [])),
             json.dumps(rep, ensure_ascii=False)[:500])

    # ---- any-of 组(golden_groups):命中/未命中两态打分 + 坏组结构错误 --------
    # tmp 现场造 2 题小 golden(1 题带 2 权组 + 1 题无组对照);不动 hello-wiki
    # 既有 golden 与 (e) 的 EXPECT_SUMMARY。页名借夹具 slug,打分为 ID-based 不查盘。
    print("\n[base/g2] any-of 组:组命中/未命中两态 + 坏组 exit 2")
    ag = tmp / "anyof-golden.jsonl"
    ag.write_text(
        '{"qid": "g1-group-anyof", "type": "single-hop", "question": "默认问候语?'
        '(any-of 冒烟)", "golden": {"concepts/greeting-protocol": 2}, '
        '"golden_groups": [{"weight": 2, "pages": ["syntheses/greeting-design-story", '
        '"sources/2026-07-01-adr-greeting-default"]}], "answer_keys": ["你好,世界"]}\n'
        '{"qid": "g2-plain-single", "type": "single-hop", "question": "ascii 档字符集'
        '纪律?(无组对照)", "golden": {"concepts/localization-fallback": 2}, '
        '"answer_keys": ["可打印 ASCII"]}\n',
        encoding="utf-8")
    agc = ci.run_json("check-golden any-of golden --json",
                      [PY, ev, "--check-golden", ag, "--root", base, "--json"])
    ci.check("any-of golden:合法组零 error 零 warning",
             agc.get("ok") is True and agc.get("errors") == []
             and agc.get("warnings") == [] and agc.get("n_questions") == 2,
             json.dumps(agc, ensure_ascii=False)[:500])

    run_hit = tmp / "anyof-run-hit.jsonl"       # 组命中态:单点 + 组内一页(ADR 路径)
    run_hit.write_text(
        '{"qid": "g1-group-anyof", "files_read": ["concepts/greeting-protocol", '
        '"sources/2026-07-01-adr-greeting-default"], "answer": "你好,世界"}\n'
        '{"qid": "g2-plain-single", "files_read": ["concepts/localization-fallback"], '
        '"answer": "只允许可打印 ASCII"}\n', encoding="utf-8")
    ev_hit = ci.run_json("any-of 组命中态打分 --json",
                         [PY, ev, run_hit, "--root", base, "--golden", ag, "--json"])
    ci.check("组命中态 summary == {n:2, P:1.0, R:1.0, problem_q:0}(组满权,exit 0)",
             ev_hit.get("summary") == {"n": 2, "precision": 1.0, "recall": 1.0,
                                       "problem_q": 0},
             json.dumps(ev_hit.get("summary"), ensure_ascii=False))
    qh = {x["qid"]: x for x in ev_hit.get("per_question", [])}
    g1 = qh["g1-group-anyof"]
    ci.check("组命中明细:groups[0] hit=true / hit_pages=[ADR 页] / miss_groups=[]",
             g1.get("groups") and g1["groups"][0]["hit"] is True
             and g1["groups"][0]["hit_pages"] == ["sources/2026-07-01-adr-greeting-default"]
             and g1.get("miss_groups") == [],
             json.dumps(g1, ensure_ascii=False)[:400])
    ci.check("无组对照题输出形状不变(无 groups/miss_groups 键)",
             "groups" not in qh["g2-plain-single"]
             and "miss_groups" not in qh["g2-plain-single"],
             json.dumps(qh["g2-plain-single"], ensure_ascii=False)[:300])

    run_miss = tmp / "anyof-run-miss.jsonl"     # 组未命中态:只读单点,组两页全 miss
    run_miss.write_text(
        '{"qid": "g1-group-anyof", "files_read": ["concepts/greeting-protocol"], '
        '"answer": "你好,世界"}\n'
        '{"qid": "g2-plain-single", "files_read": ["concepts/localization-fallback"], '
        '"answer": "只允许可打印 ASCII"}\n', encoding="utf-8")
    rc, out, err = ci.run([PY, ev, run_miss, "--root", base, "--golden", ag, "--json"])
    ci.check("组未命中态(2 权组全 miss 视同漏必读)→ exit 1", rc == 1,
             "rc=%s\nstdout(tail): %s\nstderr(tail): %s" % (rc, out[-400:], err[-400:]))
    ev_miss = json.loads(out)
    ci.check("组未命中态 summary == {n:2, P:1.0, R:0.75, problem_q:1}"
             "(组权进分母:g1 R=0.5)",
             ev_miss.get("summary") == {"n": 2, "precision": 1.0, "recall": 0.75,
                                        "problem_q": 1},
             json.dumps(ev_miss.get("summary"), ensure_ascii=False))
    qm = {x["qid"]: x for x in ev_miss.get("per_question", [])}
    m1 = qm["g1-group-anyof"]
    ci.check("组未命中明细:g1 R=0.5、groups[0] hit=false、miss_groups 恰 1 组",
             m1["recall"] == 0.5 and m1["groups"][0]["hit"] is False
             and m1["groups"][0]["hit_pages"] == []
             and len(m1.get("miss_groups", [])) == 1
             and set(m1["miss_groups"][0]) == {"syntheses/greeting-design-story",
                                               "sources/2026-07-01-adr-greeting-default"},
             json.dumps(m1, ensure_ascii=False)[:500])

    badg = tmp / "anyof-bad-golden.jsonl"       # 坏组:组内单页 / 组页与单点重复(归一后)
    badg.write_text(
        '{"qid": "b1-single-page-group", "type": "single-hop", "question": "坏组一?", '
        '"golden": {"concepts/greeting-protocol": 2}, '
        '"golden_groups": [{"weight": 2, "pages": ["syntheses/greeting-design-story"]}], '
        '"answer_keys": ["x"]}\n'
        '{"qid": "b2-dup-with-single", "type": "single-hop", "question": "坏组二?", '
        '"golden": {"concepts/greeting-protocol": 2}, '
        '"golden_groups": [{"weight": 1, "pages": ["wiki/concepts/greeting-protocol.md", '
        '"syntheses/greeting-design-story"]}], "answer_keys": ["y"]}\n',
        encoding="utf-8")
    rc, out, err = ci.run([PY, ev, "--check-golden", badg, "--root", base, "--json"])
    ci.check("坏组(组内单页 + 组页与单点重复)→ exit 2", rc == 2,
             "rc=%s\nstdout(tail): %s\nstderr(tail): %s" % (rc, out[-400:], err[-400:]))
    try:
        brep = json.loads(out)
    except json.JSONDecodeError:
        brep = {}
    ci.check("坏组报告:恰 2 结构错误(不足 2 页 / 与单点重复,归一后判定)",
             brep.get("ok") is False and len(brep.get("errors", [])) == 2
             and any("不足 2 页" in e for e in brep.get("errors", []))
             and any("与 golden 单点重复" in e for e in brep.get("errors", [])),
             json.dumps(brep, ensure_ascii=False)[:600])


def build_fw_next(ci: CI, tmp: Path) -> Path:
    """(h0) tmp 内复制框架仓为 fw-next 并造 NEXT_V 版:frozen 工具加注释行、
    followups 模板加一行、VERSION bump、UPGRADING.md 顶插条目、重跑 gen_manifest。"""
    print("\n[h0] fw-next 造版:frozen+模板各一处改动 → %s + UPGRADING + gen_manifest" % NEXT_V)
    fwn = tmp / "fw-next"
    shutil.copytree(str(FW), str(fwn), symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

    ft = fwn / FROZEN_TOUCH                    # ① frozen 工具:文末追加注释行
    ft.write_text(ft.read_text(encoding="utf-8") + FROZEN_MARK + "\n", encoding="utf-8")

    tt = fwn / TPL_TOUCH                       # ② render-once 模板:文末追加一行
    ttxt = tt.read_text(encoding="utf-8")
    tt.write_text(ttxt + ("" if ttxt.endswith("\n") else "\n") + TPL_MARK + "\n",
                  encoding="utf-8")

    (fwn / "framework" / "VERSION").write_text(NEXT_V + "\n", encoding="utf-8")
    upg = fwn / "framework" / "UPGRADING.md"   # ③ 条目区顶部插入 NEXT_V 条目(新→旧)
    utxt = upg.read_text(encoding="utf-8")
    m = re.search(r"(?m)^## \d+\.\d+\.\d+", utxt)
    ci.check("fw-next UPGRADING.md 找到条目区插入点(首个版本条目)", m is not None,
             utxt[:200])
    upg.write_text(utxt[:m.start()] + UPGRADING_ENTRY + utxt[m.start():],
                   encoding="utf-8")

    ci.run_ok("fw-next gen_manifest 重导",
              [PY, fwn / "tools" / "gen_manifest.py", "--root", fwn])
    return fwn


def phase_upgrade(ci: CI, tmp: Path, base: Path) -> Path:
    fwn = build_fw_next(ci, tmp)
    upgrade = base / "tools" / "upgrade.py"    # 实例自持有的升级器(frozen 拷贝)

    # ---- (h1) --dry-run:零写入 + 计划列出改动 ----------------------------
    print("\n[base/h1] upgrade --dry-run:全树零写入 + 计划列出改动文件")
    before = tree_state(base)
    rep = ci.run_json("upgrade --dry-run --json",
                      [PY, upgrade, "--root", base, "--framework", fwn,
                       "--dry-run", "--date", UPG_DATE, "--json"])
    ci.check("dry-run 计划:%s → %s,差距条目 == [%s]" % (CUR_V, NEXT_V, NEXT_V),
             rep.get("old") == CUR_V and rep.get("new") == NEXT_V
             and rep.get("upgrading_entries") == [NEXT_V],
             json.dumps({k: rep.get(k) for k in ("old", "new", "upgrading_entries")},
                        ensure_ascii=False))
    ci.check("dry-run 计划:frozen 覆盖列出 %s" % FROZEN_TOUCH,
             FROZEN_TOUCH in rep.get("frozen", {}).get("overwrite", []),
             json.dumps(rep.get("frozen"), ensure_ascii=False)[:500])
    adopt = rep.get("render_once", {}).get("adopt", [])
    ci.check("dry-run 计划:render-once 采用列出 wiki/followups.md 与 CLAUDE.md",
             "wiki/followups.md" in adopt and "CLAUDE.md" in adopt,
             json.dumps(rep.get("render_once"), ensure_ascii=False)[:500])
    ci.check("dry-run 计划:零冲突零 fork",
             rep.get("render_once", {}).get("conflict") == []
             and rep.get("frozen", {}).get("fork") == [],
             json.dumps(rep, ensure_ascii=False)[:500])
    after = tree_state(base)
    diff = sorted(set(before) ^ set(after)) + \
        sorted(k for k in before if k in after and before[k] != after[k])
    ci.check("dry-run 零写入(实例全树逐文件比对)", before == after,
             "差异:%s" % diff[:20])

    # 克隆两份升级前现场留给 h3/h4(必须在 h2 实跑改动 base 之前)
    h3root, h4root = tmp / "base-h3", tmp / "base-h4"
    for c in (h3root, h4root):
        shutil.copytree(str(base), str(c), symlinks=True)

    # ---- (h2) 实跑:frozen 覆盖 / 模板自动采用 / 收尾与门禁 ---------------
    print("\n[base/h2] upgrade 实跑:frozen 覆盖 / render-once 自动采用 / 收尾 + 门禁")
    rep = ci.run_json("upgrade apply --json",
                      [PY, upgrade, "--root", base, "--framework", fwn,
                       "--date", UPG_DATE, "--json"])
    ci.check("升级完成:零冲突零 fork、lint 门禁 rc=0",
             rep.get("rc") == 0 and rep.get("gate_rc") == 0
             and rep.get("render_once", {}).get("conflict") == []
             and rep.get("frozen", {}).get("fork") == [],
             json.dumps({k: rep.get(k) for k in ("rc", "gate_rc")}, ensure_ascii=False))
    ci.check("frozen 干净覆盖:实例 %s 出现 fw-next 注释行" % FROZEN_TOUCH,
             FROZEN_MARK in (base / FROZEN_TOUCH).read_text(encoding="utf-8"))
    ftxt = (base / "wiki" / "followups.md").read_text(encoding="utf-8")
    ci.check("render-once 未被实例改过 → 自动采用新版(followups 出现新行)",
             TPL_MARK in ftxt, ftxt[-300:])
    ci.check("实例 framework/VERSION == %s" % NEXT_V,
             (base / "framework" / "VERSION").read_text(encoding="utf-8").strip() == NEXT_V)
    ci.check("framework/base/ 已刷新为新模板快照",
             TPL_MARK in (base / "framework" / "base" / TPL_TOUCH).read_text(encoding="utf-8"))
    snap = json.loads((base / "framework" / "MANIFEST.json").read_text(encoding="utf-8"))
    ci.check("MANIFEST 快照随升级刷新(framework_version == %s)" % NEXT_V,
             snap.get("framework_version") == NEXT_V,
             json.dumps({k: snap.get(k) for k in ("framework_version",)}))
    logtxt = (base / "wiki" / "log.md").read_text(encoding="utf-8")
    ci.check("wiki/log.md 新增 upgrade 条目(W-LOG-1)",
             ("## [%s] upgrade | framework %s -> %s" % (UPG_DATE, CUR_V, NEXT_V)) in logtxt,
             logtxt[-400:])

    # ---- (h3) 冲突路:实例手改 render-once 再升级 -------------------------
    print("\n[h3] 冲突路:实例手改 render-once 后升级 → .upgrade-new + exit 1")
    f3 = h3root / "wiki" / "followups.md"
    f3.write_text(f3.read_text(encoding="utf-8") + INST_MARK + "\n", encoding="utf-8")
    rep = ci.run_json("upgrade(冲突路)--json",
                      [PY, h3root / "tools" / "upgrade.py", "--root", h3root,
                       "--framework", fwn, "--date", UPG_DATE, "--json"], want_rc=1)
    ci.check("冲突清单 == [wiki/followups.md]",
             rep.get("render_once", {}).get("conflict") == ["wiki/followups.md"],
             json.dumps(rep.get("render_once"), ensure_ascii=False)[:500])
    t3 = f3.read_text(encoding="utf-8")
    ci.check("原文件保留实例手改、未被新模板覆盖",
             INST_MARK in t3 and TPL_MARK not in t3, t3[-300:])
    up_new = h3root / "wiki" / ("followups.md" + ".upgrade-new")
    ci.check("followups.md.upgrade-new 生成且为纯新模板渲染(含新行,无实例手改)",
             up_new.is_file() and TPL_MARK in up_new.read_text(encoding="utf-8")
             and INST_MARK not in up_new.read_text(encoding="utf-8"),
             str(up_new))

    # ---- (h4) fork 路:实例手改 frozen 工具再升级 -------------------------
    print("\n[h4] fork 路:实例手改 frozen 工具后升级 → fork 候选未覆盖 + exit 1")
    f4 = h4root / FROZEN_TOUCH
    f4.write_text(f4.read_text(encoding="utf-8") + FORK_MARK + "\n", encoding="utf-8")
    rep = ci.run_json("upgrade(fork 路)--json",
                      [PY, h4root / "tools" / "upgrade.py", "--root", h4root,
                       "--framework", fwn, "--date", UPG_DATE, "--json"], want_rc=1)
    forks = [x.get("path") for x in rep.get("frozen", {}).get("fork", [])]
    ci.check("fork 候选 == [%s](hash 与旧快照不符)" % FROZEN_TOUCH,
             forks == [FROZEN_TOUCH],
             json.dumps(rep.get("frozen"), ensure_ascii=False)[:500])
    t4 = f4.read_text(encoding="utf-8")
    ci.check("fork 候选未被覆盖(本地改动在、fw-next 注释行不在)",
             FORK_MARK in t4 and FROZEN_MARK not in t4, t4[-300:])

    phase_stub_fallback(ci, tmp, base)             # (h5)
    return fwn


def _import_module(py_path: Path, name: str):
    """importlib 按独立名加载模块(与 upgrade.py._load_module 同法,CI 侧自持)。"""
    spec = importlib.util.spec_from_file_location(name, str(py_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载模块:%s" % py_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_stub_ir(tmp: Path) -> Path:
    """(h5) 造 stub 渲染器:整拷 tools/ 树后把 init_render.py 剥离 STRIP_FUNCS 三个
    模块级函数,模拟「函数化前的旧版渲染器」——upgrade.render_tree 对其 hasattr 探测
    失败,必然走本文件镜像(_compute_conds/_stamp_dates/_snapshot_manifest)回退路径。
    整拷 tools/ 是必要的:compute_slots 按 __file__ 同目录探测姊妹工具存在性
    (缺席会给 tools.cmds 追加「待交付」后缀),裸拷单文件会引入与剥函数无关的渲染差异。"""
    stub_tools = tmp / "stub-ir" / "tools"
    if not stub_tools.exists():
        shutil.copytree(str(FW / "tools"), str(stub_tools),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    src = (FW / "tools" / "init_render.py").read_text(encoding="utf-8")
    out, skip = [], False
    for ln in src.splitlines(keepends=True):
        if skip:
            if ln.strip() and not ln[0].isspace():
                skip = False                       # 回到顶层非空行 = 函数体结束,本行继续判定
            else:
                continue
        m = re.match(r"def (\w+)\(", ln)
        if m and m.group(1) in STRIP_FUNCS:
            skip = True
            continue
        out.append(ln)
    stub = stub_tools / "init_render.py"
    stub.write_text("".join(out), encoding="utf-8")
    return stub


def phase_stub_fallback(ci: CI, tmp: Path, base: Path) -> None:
    """(h5) stub-ir 回退护栏(M3 验证员建议的长期护栏):upgrade.py 头注声明——旧版
    渲染器缺 compute_conds/stamp_dates/snapshot_manifest 时回退本文件镜像,口径钉死。
    此处以剥离三函数的 stub 驱动回退路径,与新路径(init_render 单源)逐字节比对,
    任何一侧口径漂移都会在此现形。"""
    print("\n[h5] stub-ir 回退护栏:剥离 %s → 镜像回退与单源新路径逐字节等价"
          % "/".join(STRIP_FUNCS))
    upg = _import_module(FW / "tools" / "upgrade.py", "_ci_upgrade")
    ir_real = _import_module(FW / "tools" / "init_render.py", "_ci_ir_real")
    ir_stub = _import_module(make_stub_ir(tmp), "_ci_ir_stub")
    ci.check("stub 三函数确已剥离且真渲染器齐备(回退路径必然触发)",
             all(not hasattr(ir_stub, f) for f in STRIP_FUNCS)
             and all(hasattr(ir_real, f) for f in STRIP_FUNCS),
             "stub 残留:%s;real 缺失:%s"
             % ([f for f in STRIP_FUNCS if hasattr(ir_stub, f)],
                [f for f in STRIP_FUNCS if not hasattr(ir_real, f)]))
    fmmod = _import_module(FW / "tools" / "lib" / "fm.py", "_ci_fm")
    cfg = fmmod.load_config(base, on_warning=lambda w: None)
    out_new, _ = upg.render_tree(ir_real, FW, cfg, CUR_V, DATE)   # 新路径(单源函数)
    out_old, _ = upg.render_tree(ir_stub, FW, cfg, CUR_V, DATE)   # 回退路径(镜像)
    ci.check("stub 渲染非空且覆盖 CLAUDE.md 与 wiki/log.md(%d 文件)" % len(out_old),
             len(out_old) >= 10 and "CLAUDE.md" in out_old and "wiki/log.md" in out_old,
             "keys(head): %s" % sorted(out_old)[:10])
    diff = sorted(set(out_new) ^ set(out_old)) + \
        sorted(k for k in out_new if k in out_old and out_new[k] != out_old[k])
    ci.check("render_tree 回退路径与新路径产物逐字节等价", not diff,
             "差异文件:%s" % diff[:10])
    mfp = FW / "framework" / "MANIFEST.json"
    new_doc = json.loads(mfp.read_text(encoding="utf-8"))
    snap_new = ir_real.snapshot_manifest(mfp, base)               # 新路径(单源函数)
    snap_old = upg._snapshot_manifest(new_doc, base)              # 回退路径(镜像)
    ci.check("snapshot_manifest 镜像回退与单源逐字节等价",
             snap_new is not None and snap_new == snap_old,
             "new(head): %r\nold(head): %r" % (str(snap_new)[:200], str(snap_old)[:200]))


def phase_extras(ci: CI, base: Path) -> None:
    print("\n[base/i] extras 冒烟:serve /api/status;i18n_link 未配置 exit 2")
    with socket.socket() as s:                  # 随机高位口:OS 分配后立即释放复用
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [str(PY), str(FW / "extras" / "serve.py"), "--root", str(base),
         "--port", str(port), "--no-browser"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
    # loopback 直连:显式空 ProxyHandler,绕过环境 HTTP(S)_PROXY(否则 127.0.0.1
    # 请求会被 urllib 送进代理,冒烟必然超时)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    body, last_err = None, None
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if proc.poll() is not None:
                break                           # 服务提前退出(端口/配置问题)
            try:
                with opener.open(
                        "http://127.0.0.1:%d/api/status" % port, timeout=3) as r:
                    body = r.read().decode("utf-8")
                break
            except (urllib.error.URLError, OSError) as e:
                last_err = e
                time.sleep(0.25)
        ci.check("serve.py 启动并响应 GET /api/status(port %d)" % port,
                 body is not None,
                 "proc rc=%s;last_err=%s" % (proc.poll(), last_err))
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            data = None
            ci.check("/api/status 返回合法 JSON", False, "%s;body head: %r" % (e, body[:300]))
        pipelines = (data.get("result") or {}).get("pipelines")
        ci.check("/api/status 合法 JSON 且含 pipelines 段(notes+guide)",
                 data.get("ok") is True and isinstance(pipelines, list)
                 and {p.get("name") for p in pipelines} == {"notes", "guide"},
                 body[:400])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    rc, out, err = ci.run([PY, FW / "extras" / "i18n_link.py", "--root", base])
    ci.check("i18n_link 未配置语言对 → exit 2(报「未配置」)",
             rc == 2 and "未配置" in (out + err),
             "rc=%s\nstderr(tail): %s" % (rc, err[-300:]))


def phase_manual_peers(ci: CI, base: Path, mf: Path) -> None:
    print("\n[base+mf/j] manual 哨兵零警告;peers 段进 status --json")
    rc, out, err = ci.run([PY, base / "tools" / "sync.py", "status", "--root", base, "--json"])
    ci.check("base sync status --json → rc=0", rc == 0,
             "rc=%s\nstderr(tail): %s" % (rc, err[-400:]))
    ci.check("不再出「未声明适配器」警告(guide adapter=manual 哨兵)",
             "未声明适配器" not in err and "未声明适配器" not in out, err[-400:])
    st = json.loads(out)
    ci.check("status --json 顶层含 peers 段与 framework_version(升级后 %s)" % NEXT_V,
             isinstance(st.get("peers"), list) and st.get("framework_version") == NEXT_V,
             json.dumps({k: st.get(k) for k in ("peers", "framework_version")},
                        ensure_ascii=False)[:300])
    guide = {p["name"]: p for p in st["pipelines"]}["guide"]
    ci.check("guide 管线报 adapter == manual 且零 pending",
             guide.get("adapter") == "manual" and guide.get("pending_count") == 0,
             json.dumps(guide, ensure_ascii=False)[:300])

    rc2, out2, err2 = ci.run([PY, mf / "tools" / "sync.py", "status", "--root", mf, "--json"])
    ci.check("mf sync status --json → rc=0", rc2 == 0,
             "rc=%s\nstderr(tail): %s" % (rc2, err2[-400:]))
    pe = json.loads(out2).get("peers") or []
    ci.check("mf peers[0](hub→base)可达、pages.jsonl 非空、报版本 skew(base 已 %s)" % NEXT_V,
             len(pe) == 1 and pe[0].get("alias") == "hub"
             and pe[0].get("reachable") is True and pe[0].get("pages_jsonl") is True
             and (pe[0].get("pages_lines") or 0) > 0
             and pe[0].get("framework_version") == NEXT_V
             and pe[0].get("version_skew") is True,
             json.dumps(pe, ensure_ascii=False)[:400])


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
                 FW / "adapters" / "local_notes.py", FW / "tools" / "lib" / "fm.py",
                 FW / "tools" / "upgrade.py", FW / "tools" / "gen_manifest.py",
                 FW / "extras" / "serve.py", FW / "extras" / "i18n_link.py",
                 FW / "framework" / "VERSION", FW / "framework" / "MANIFEST.json",
                 FW / "framework" / "UPGRADING.md"):
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
        phase_golden_check(ci, base, tmp)                      # (g)
        phase_upgrade(ci, tmp, base)                           # (h)
        phase_extras(ci, base)                                 # (i)
        phase_manual_peers(ci, base, tmp / "mf")               # (j)
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
