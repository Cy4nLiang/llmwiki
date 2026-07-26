#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki tools/bootstrap_scan.py — 冷启动候选扫描(S5;仅 Python 标准库)。

新实例刚渲染完是空库,而宿主项目往往已经攒了一堆值得入库的文档。本工具**只读**扫宿主
仓,产出按推荐优先级排序的候选清单,供 `wiki-bootstrap` 向导引导用户勾选 → 逐篇投
`raw/inbox/` → 批量 light 档 ingest。扫描面(rank 即推荐优先级,组内按路径定序):

  1 readme     任意深度 `README*`
  2 changelog  `CHANGELOG*` / `HISTORY*` / `RELEASES*` / `UPGRADING*`(版本决策流水)
  3 adr        `adr|adrs|decisions|rfc|rfcs` 目录下的 md(决策信号最强)
  4 docs       `docs|doc|documentation` 下的 md(`design-docs` 除外——开发过程文档,
               与 init_render.py 的 skip_dirs / gen_manifest 的 EXCLUDE 同名同口径)
  5 root-doc   仓根一层的 `*.md`(AGENTS/CLAUDE/CONTRIBUTING 类总览)
  6 contract   `CONTRACT/CONVENTION/GUIDELINE/STYLE/ARCHITECTURE/SPEC*` 命名的 md
               与 `framework/` `evals/` 下的 md(工程约定面)
  7 git-log    `git log --grep=<决策关键词>` 命中的 commit(**git 缺席 / 非 git 仓 /
               空仓 / 超时一律静默降级跳过本组**,不报错、不影响退出码)

**候选 ≠ 投递**(W-CAP-1):本工具只产清单,绝不投 `raw/`、绝不写 `wiki/`——勾选与投递
权全在人/agent 手上;也绝不"整仓无脑搬运"。

写入边界(W-ARCH-2):只写 `state/bootstrap-candidates.json`;只读 `--repo` 宿主树与
`wiki.config.json`。确定性:分组内按路径定序 + 组按 rank 拼接(git 组保 git 逆时序);
产物不含时间戳/绝对路径/机器信息,同一宿主状态两次运行逐字节相同(内容未变不重写,
不污染 mtime)。est_tokens 与 kind 建议均以实例 config 为准(不硬编码)。

用法:python3 tools/bootstrap_scan.py [--root DIR] [--repo DIR] [--json]
exit:0 成功(零候选亦为 0——"宿主没文档"是诚实结果)/ 2 用法或 config 错误
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# lib/fm.py = frontmatter / est_tokens / config 的单一实现(同目录 sys.path 导入,与 lint_wiki 同款)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib import fm
except ImportError as e:                        # pragma: no cover — 安装损坏才会走到
    print("错误: 无法导入 tools/lib/fm.py(config/est_tokens 单一实现):%s" % e,
          file=sys.stderr)
    sys.exit(2)

FORMAT = 1                                      # 产物格式版本(消费方按此判读)
MAX_BYTES = 512 * 1024                          # 单文件上限:超限跳过(防生成物/巨物读爆)
MD_SUFFIXES = {".md", ".markdown", ".mdx"}
GIT_LOG_LIMIT = 200                             # git 取样上限(确定性 + 防巨仓)
TITLE_SCAN_LINES = 40                           # H1 回退只看正文前 N 行

# 剪枝目录:VCS / 依赖与构建产物 / 实例运行态与数据面(W-ARCH-2 两侧) / 仓内非知识面
EXCLUDE_DIR_NAMES = {
    ".git", ".hg", ".svn",
    "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".next", ".tox",
    "state", "site", "wiki", "raw", "_attic",   # 实例自身产物:扫了会自指
    "knowledge", "tests", "design-docs",        # 内嵌实例 / 夹具 / 开发过程文档
    "templates", ".claude", ".claude-plugin",   # 未渲染模板(含 <SLOT:>)与 agent 配置面
}
_ADR_DIRS = {"adr", "adrs", "decisions", "decision-records", "rfc", "rfcs"}
_DOC_DIRS = {"docs", "doc", "documentation"}
_CONTRACT_DIRS = {"framework", "evals"}
_CONTRACT_STEMS = ("CONTRACT", "CONVENTION", "GUIDELINE", "STYLE", "ARCHITECTURE", "SPEC")
_HOWTO_WORDS = ("howto", "how-to", "guide", "tutorial", "setup", "install", "runbook",
                "quickstart", "getting-started", "usage")
_PITFALL_WORDS = ("pitfall", "postmortem", "post-mortem", "incident", "troubleshoot",
                  "gotcha", "faq", "踩坑", "复盘")

# git log 决策关键词(OR 语义)。中英并给:纯英文集合在中文仓常 0 命中,反之亦然。
# 挑「决策/取舍」语义词而非 conventional-commit 前缀(feat/fix 噪声大且非决策)。
GIT_KEYWORDS = (
    "decision", "decide", "ADR", "RFC", "rationale", "tradeoff", "trade-off",
    "revert", "root cause", "postmortem", "breaking change", "deprecate",
    "决策", "定稿", "取舍", "方案", "改为", "因为", "踩坑", "回滚", "复盘",
    "根因", "契约", "约定", "规范", "弃用", "迁移",
)

# git 子进程:用 -c 显式压掉用户 gitconfig 的一切不确定性(pager/颜色/签名/日期/编码),
# 否则 format.pretty、log.date、log.showSignature、grep.patternType 会改变输出。
_GIT_CFG = ("-c", "core.pager=cat", "-c", "color.ui=false",
            "-c", "log.showSignature=false", "-c", "log.decorate=false",
            "-c", "i18n.logOutputEncoding=UTF-8")
_GIT_ENV = {"GIT_PAGER": "cat", "TZ": "UTC", "LC_ALL": "C"}
_GIT_PRETTY = "%H%x09%ad%x09%s"                 # 制表分隔;行内无本地化文本


# ---------------------------------------------------------------- 扫描面

def _excluded(parts) -> bool:
    """路径任一父目录命中剪枝名单。"""
    return any(p in EXCLUDE_DIR_NAMES for p in parts)


def group_of(rel: str):
    """把宿主相对路径(posix)归到扫描组;返回 (rank, source) 或 None(不入候选)。

    顺序即优先级:先按文件名信号(README/CHANGELOG),再按目录信号(adr/docs),
    最后是仓根总览与工程约定面。同一文件只归一组(rank 唯一,不重复计数)。
    """
    parts = rel.split("/")
    name = parts[-1]
    upper = name.upper()
    if upper.startswith("README"):
        return 1, "readme"
    if upper.startswith(("CHANGELOG", "HISTORY", "RELEASES", "UPGRADING")):
        return 2, "changelog"
    if any(d in _ADR_DIRS for d in parts[:-1]):
        return 3, "adr"
    if parts[0] in _DOC_DIRS:
        return 4, "docs"
    if len(parts) == 1:
        return 5, "root-doc"
    if upper.startswith(_CONTRACT_STEMS) or parts[0] in _CONTRACT_DIRS:
        return 6, "contract"
    return None


def declared_kinds(cfg: dict) -> list:
    """实例 config 声明的 source_kind 并集(保序去重,与 init_render 的 kind_enum 同口径)。

    框架层不存在 kind 白名单——合法集合由实例 `pipelines[].source_kinds` 封闭声明,
    所以建议 kind 必须与它求交,不能凭空造词。
    """
    seen = []
    for p in cfg["pipelines"]:
        for k in p["source_kinds"]:
            if k not in seen:
                seen.append(k)
    return seen


def suggest_kind(source: str, rel: str, declared: list):
    """按组/路径特征给 kind 首选序列,取第一个被实例声明的;返回 (kind, note)。

    全不命中则退 declared[0] 并回一条 note(诚实标注"config 未声明该 kind"),
    让人在勾选时改判——不静默塞一个实例不认的 kind 进 inbox。
    """
    low = rel.lower()
    prefer = []
    if any(w in low for w in _PITFALL_WORDS):
        prefer.append("pitfall")
    if source == "adr":
        prefer += ["adr", "decision"]
    elif source in ("changelog", "git-log"):
        prefer += ["decision", "adr"]
    elif source == "contract":
        prefer += ["convention", "reference"]
    elif source == "docs":
        prefer += (["howto", "reference"] if any(w in low for w in _HOWTO_WORDS)
                   else ["reference", "howto"])
    else:                                       # readme / root-doc:宿主总览
        prefer += ["reference", "howto"]
    for k in prefer:
        if k in declared:
            return k, None
    if not declared:                            # config 校验保证 pipelines 非空,兜底不崩
        return prefer[0], "实例 config 未声明任何 source_kind"
    return declared[0], ("建议 kind %s 未被 config 声明(已退 %s,勾选时可改判)"
                         % ("|".join(prefer), declared[0]))


def guess_title(text: str, stem: str) -> str:
    """标题三级回退:frontmatter title → 正文首个 ATX H1 → 文件名。

    H1 抽取内联在本工具里:fm.py 是钉死的 MAJOR 面(零改动),不为一次性启发式下沉 helper。
    """
    meta, body = fm.parse_frontmatter(text)
    t = meta.get("title")
    if isinstance(t, list):
        t = t[0] if t else None
    if isinstance(t, str) and t.strip():
        return t.strip()
    fence = False
    for line in body.splitlines()[:TITLE_SCAN_LINES]:
        s = line.strip()
        if s.startswith(("```", "~~~")):
            fence = not fence
            continue
        if fence:
            continue
        if s.startswith("# "):
            return s[2:].strip().rstrip("#").strip() or stem
    return stem


def scan_files(repo: Path, root: Path, cfg: dict) -> tuple:
    """只读枚举宿主 repo 的候选文件;返回 (candidates, stats)。

    动态排除比静态名单更要紧:① `--root` 自身子树(embedded 下 --repo 默认 `..`,实例
    必在宿主内);② 任何含 wiki.config.json 的嵌套目录(别人的实例)——否则实例会把自己
    已整合的 wiki 页当成新候选,候选虚高且 dogfood 陷入自指。
    """
    profile = cfg["budgets"]["est_tokens_profile"]
    declared = declared_kinds(cfg)
    cands, scanned, oversize, unreadable = [], 0, 0, 0
    bad_dirs = []                               # 不可读目录:记账让"漏扫"可见(os.walk 默认静默吞)

    def _on_walk_error(err):
        bad_dirs.append(getattr(err, "filename", None) or "?")

    for dirpath, dirnames, filenames in os.walk(str(repo), onerror=_on_walk_error):
        here = Path(dirpath)
        # 剪枝(就地改 dirnames 阻止下潜)+ 排序保证遍历确定
        keep = []
        for d in sorted(dirnames):
            if d in EXCLUDE_DIR_NAMES or d.startswith("."):
                continue
            sub = here / d
            try:
                if sub.is_symlink():            # 不跟符号链接:防环与越界读
                    continue
                if sub.resolve() == root:       # 实例自身子树
                    continue
                if (sub / "wiki.config.json").is_file():
                    continue                    # 嵌套的另一个 llmwiki 实例
            except OSError:                     # 无 x 位/悬挂/NFS 抖动:剪掉该目录,绝不让扫描失败
                bad_dirs.append(sub.name)       # (扫的是别人的树:无权目录是常态,不是错误)
                continue
            keep.append(d)
        dirnames[:] = keep
        for fname in sorted(filenames):
            p = here / fname
            if p.suffix.lower() not in MD_SUFFIXES:
                continue
            if fname.endswith(".template.md"):  # 未渲染模板(含 <SLOT:>)不是知识
                continue
            rel = p.relative_to(repo).as_posix()
            if _excluded(rel.split("/")[:-1]):
                continue
            g = group_of(rel)
            if g is None:
                continue
            scanned += 1
            try:
                if p.is_symlink():
                    continue
                if p.stat().st_size > MAX_BYTES:
                    oversize += 1
                    continue
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                unreadable += 1                 # 二进制/权限/坏编码:跳过,不让扫描失败
                continue
            rank, source = g
            kind, note = suggest_kind(source, rel, declared)
            c = {"rank": rank, "source": source, "path": rel,
                 "title": guess_title(text, p.stem),
                 "est_tokens": fm.est_tokens(text, profile), "kind": kind}
            if note:
                c["kind_note"] = note
            cands.append(c)
    cands.sort(key=lambda c: (c["rank"], c["path"]))
    return cands, {"files_scanned": scanned, "skipped_oversize": oversize,
                   "skipped_unreadable": unreadable,
                   "skipped_unreadable_dirs": len(bad_dirs)}


# ---------------------------------------------------------------- git 决策面

def _git(repo: Path, args: list, timeout: int = 20):
    """跑一条 git;返回 stdout,或 None(git 缺席/非仓/空仓/超时/任何异常)。恒不抛。

    显式 encoding='utf-8' 而非 text=True:后者按 locale 解码,非 UTF-8 locale 下中文
    commit message 会解码失败或乱码。
    """
    exe = shutil.which("git")
    if exe is None:
        return None
    try:
        r = subprocess.run([exe, "--no-pager", *_GIT_CFG, *args],
                           cwd=str(repo), capture_output=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           env={**os.environ, **_GIT_ENV})
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None
    return r.stdout if r.returncode == 0 else None


def scan_git(repo: Path, cfg: dict) -> tuple:
    """git log 决策面候选;返回 (candidates, info)。git 不可用时返回 ([], info) 静默降级。

    降级三形态全覆盖:git 未安装 / 目标非 git 仓(rc=128) / 空仓(无 commit,rc=128)。
    info.reason 只写环境无关的短语(不含路径/版本),保持产物跨机可比。
    """
    profile = cfg["budgets"]["est_tokens_profile"]
    declared = declared_kinds(cfg)
    if shutil.which("git") is None:
        return [], {"available": False, "reason": "git 不可用(未安装)", "matched": 0}
    inside = _git(repo, ["rev-parse", "--is-inside-work-tree"])
    if inside is None or inside.strip() != "true":
        return [], {"available": False, "reason": "宿主不是 git 工作树", "matched": 0}
    args = ["log", "--no-color", "--no-decorate", "--date=short",
            "--pretty=format:" + _GIT_PRETTY, "-n", str(GIT_LOG_LIMIT), "-i", "-F"]
    for kw in GIT_KEYWORDS:
        args += ["--grep", kw]                  # 多 --grep = OR;-F 压掉 grep.patternType 语义漂移
    out = _git(repo, args)
    if out is None:
        return [], {"available": False, "reason": "git log 不可用(空仓或读取失败)",
                    "matched": 0}
    cands = []
    for line in out.splitlines():               # 保持 git 逆时序(已确定,不再按日期重排)
        parts = line.split("\t", 2)
        if len(parts) != 3 or not parts[0]:
            continue
        sha, date, subject = parts
        kind, note = suggest_kind("git-log", subject.lower(), declared)
        c = {"rank": 7, "source": "git-log", "path": None, "ref": sha[:12], "date": date,
             "title": subject.strip(), "est_tokens": fm.est_tokens(subject, profile),
             "kind": kind}
        if note:
            c["kind_note"] = note
        cands.append(c)
    return cands, {"available": True, "reason": None, "matched": len(cands)}


# ---------------------------------------------------------------- 落盘

def _write_if_changed(path: Path, content: str) -> bool:
    """内容未变不重写(不污染 mtime;CI 据此断言重跑 written==[])。"""
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _repo_label(root: Path, repo: Path) -> str:
    """宿主标签:只在 repo 是实例的祖先/内嵌时用相对路径,否则退 basename。

    绝不把绝对路径成分写进产物——relpath 跨树时会生成 `../../../Users/<用户名>/...`,
    既泄漏机器信息又让产物跨机不可比(embedded 常态是干净的 `..`)。
    """
    try:
        rel = Path(os.path.relpath(str(repo), str(root))).as_posix()
    except ValueError:                          # 跨盘(Windows)无相对路径
        return repo.name
    parts = rel.split("/")
    if ".." not in parts or all(p == ".." for p in parts):
        return rel                              # `..`(embedded)/ `../..` / 实例内嵌
    return repo.name                            # 无关两棵树:只留目录名


def build(root: Path, repo: Path, cfg: dict) -> dict:
    """扫描 + 落盘;返回统计 dict(即 --json 输出体)。只写 state/bootstrap-candidates.json。"""
    files, stats = scan_files(repo, root, cfg)
    gits, ginfo = scan_git(repo, cfg)
    cands = files + gits                        # 文件组已按 (rank, path) 定序;git 组 rank=7 收尾
    by_source = {}
    for c in cands:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    repo_label = _repo_label(root, repo)
    doc = {
        "_comment": "派生物:python3 tools/bootstrap_scan.py 生成,勿手编。"
                    "候选 ≠ 投递(W-CAP-1):勾选与投递由 wiki-bootstrap 向导引导人来做。",
        "format": FORMAT,
        "repo": repo_label,
        "counts": {"total": len(cands), "by_source": dict(sorted(by_source.items())),
                   **stats},
        "git": ginfo,
        "candidates": cands,
    }
    out = root / "state" / "bootstrap-candidates.json"
    out.parent.mkdir(parents=True, exist_ok=True)   # 裸 --root(未 scaffold)也能落
    changed = _write_if_changed(out, json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    rel_out = out.relative_to(root).as_posix()
    return {"ok": True, "repo": repo_label, "candidates": len(cands),
            "counts": doc["counts"], "git": ginfo,
            "written": [rel_out] if changed else [], "unchanged": [] if changed else [rel_out]}


def report(res: dict, cands: list) -> None:
    """人读候选清单(供 agent 呈给用户勾选)。--json 时不走本函数(stdout 须纯 JSON)。"""
    print("== bootstrap 候选 %d 条(宿主:%s)==" % (res["candidates"], res["repo"]))
    cur = None
    for c in cands:
        tag = "%d %s" % (c["rank"], c["source"])
        if tag != cur:
            cur = tag
            print("[%s]" % tag)
        where = c["path"] or ("%s@%s" % (c["ref"], c["date"]))
        print("- %s  [%s]  ~%d tok  %s" % (where, c["kind"], c["est_tokens"], c["title"]))
    if not res["git"]["available"]:
        print("(git 决策面已跳过:%s)" % res["git"]["reason"])
    if (res["counts"]["skipped_oversize"] or res["counts"]["skipped_unreadable"]
            or res["counts"]["skipped_unreadable_dirs"]):
        print("(跳过:超 %dKB %d 个 / 不可读文件 %d 个 / 不可读目录 %d 个)"
              % (MAX_BYTES // 1024, res["counts"]["skipped_oversize"],
                 res["counts"]["skipped_unreadable"],
                 res["counts"]["skipped_unreadable_dirs"]))
    print("清单已落 state/bootstrap-candidates.json%s"
          % ("(内容未变)" if res["unchanged"] else ""))
    print("下一步:勾选后逐篇投 raw/inbox/<date>-<slug>.md(投递≠整合,W-CAP-1),"
          "再走批量 light 档 ingest;详见 .claude/skills/wiki-bootstrap/SKILL.md。")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="只读扫宿主 repo 产出冷启动 ingest 候选(S5;只写 state/,候选≠投递)")
    ap.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    ap.add_argument("--repo", default=None,
                    help="宿主仓根(缺省:embedded 安装的 <root>/..;只读扫描)")
    ap.add_argument("--json", action="store_true", help="机器输出(结构化统计)")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    try:
        cfg = fm.load_config(root)
    except fm.ConfigError as e:
        print("配置错误: %s" % e, file=sys.stderr)
        return 2
    repo = (Path(args.repo).expanduser().resolve() if args.repo else root.parent)
    if not repo.is_dir():
        print("配置错误: --repo 不是目录:%s" % repo, file=sys.stderr)
        return 2

    res = build(root, repo, cfg)
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        doc = json.loads((root / "state" / "bootstrap-candidates.json")
                         .read_text(encoding="utf-8"))
        report(res, doc["candidates"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
