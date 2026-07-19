#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki extras/i18n_link.py — raw 语言对切换横幅注入(可选组件;bilingual_link 泛化)

【extras 声明】本文件属 extras 可选组件(Spec §1.1〔D7〕):随框架交付、MANIFEST 归
frozen 档做 hash 追踪,但**不进核心依赖面**——tools/ 与四个工作流对本文件零依赖,
删除它不影响任何核心承诺。何时不需要它见 extras/README.md。

【W-ARCH-1 例外声明】「raw/ 不可变」是框架 frozen 不变式;本工具是框架层面**显式豁免**
的 raw 增强(Spec §1.1 extras 条目「双语增强……幂等 marker」):
  - 只注入/剥离**带唯一 marker 的一行横幅**,marker 行内内容不算源文本——事实裁决
    (raw wins)、引用与任何针对 raw 的 grep 语义都不应把横幅行当作源内容;
  - 幂等:重跑先剥后插,内容未变不重写;
  - **退出机制 `--strip`**:一键剥离全部横幅,raw 回到未增强状态(豁免必须可撤销);
  - rolling 管线的 raw_dir **禁止**配置进语言对(本工具校验后拒绝,exit 2)——
    注入会改变快照 sha256,把 rolling 判新(rolling_digest)搅成永久 pending。

配置(config 驱动;无该配置时报「未配置」exit 2):
    "x-extensions": {
      "i18n": {
        "pairs": [
          { "src_dir": "raw/blog", "dst_dir": "raw/blog_zn", "suffix": "",
            "src_label": "English", "dst_label": "中文" }
        ]
      }
    }
配对约定:`src_dir/<stem>.md` ↔ `dst_dir/<stem><suffix>.md`,仅两侧都存在的对注入
(参考实例 newpj4:同名 basename、suffix="";同目录后缀式如 foo.md ↔ foo.zh.md 用
src_dir == dst_dir + suffix=".zh")。src/dst_label 缺省取目录名。两目录均须在 raw/ 下
(W-ARCH-2:工具只写 raw/ + site/ + state/)。

附带增强(默认开启,--no-patch-site 关闭):回填 site/data.json 的 file_zh/title_zh
双语槽位(build_site 明示「extras/i18n_link 增强填充;核心默认 None/""」)。槽位名沿用
参考实例(_zh),语义 = 「配对语言版本」,目标语言不是中文时亦复用该槽位。注意
data.json 每次 build_site 都会重建(槽位归零),重建后需重跑本工具回填。

用法(CLI 约定:exit 0 完成 / 1 有文件读写失败被跳过 / 2 配置用法错;机器输出 --json):
    python3 extras/i18n_link.py [--root DIR] [--dry-run] [--strip] [--no-patch-site] [--json]

2026-07-19 · 泛化自参考实例 newpj4 tools/bilingual_link.py(含 iCloud dataless 防呆)。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MARK = "<!-- llmwiki:i18n-switch -->"     # 唯一幂等 marker(剥离只认它,不认横幅其余内容)
STRIP_RE = re.compile(r"^>[^\n]*" + re.escape(MARK) + r"[ \t]*\r?\n(?:[ \t]*\r?\n)*",
                      re.M)
FM_READ_LIMIT = 65536                     # 读 dst 头部提取 frontmatter title 的上限
SHOW_CAP = 20                             # 文本模式逐文件明细上限


# ── fm 单源定位(单源纪律:config 校验一律 fm.load_config)──────────────────

def _import_fm(root: Path):
    """优先实例自持有的 <root>/tools/lib/fm.py(实例钉版),退回本文件同仓的
    ../tools/lib/fm.py(在框架 checkout 内对外部实例运行的场景)。"""
    for tools_dir in (root / "tools", Path(__file__).resolve().parent.parent / "tools"):
        if (tools_dir / "lib" / "fm.py").is_file():
            sys.path.insert(0, str(tools_dir))
            try:
                from lib import fm  # noqa: PLC0415
                return fm
            except ImportError:
                continue
    return None


def _die(code: int, msg: str) -> "None":
    print("错误: %s" % msg, file=sys.stderr)
    sys.exit(code)


def _say(quiet: bool, msg: str) -> None:
    """人读诊断:--json 模式走 stderr,stdout 只留纯 JSON。"""
    print(msg, file=sys.stderr if quiet else sys.stdout)


# ── 平台防呆(参考实例 newpj4 实测教训:iCloud 驱逐的 dataless 文件读取会阻塞)──

def _dataless(p: Path) -> bool:
    try:
        return bool(getattr(os.stat(str(p)), "st_flags", 0) & 0x40000000)  # SF_DATALESS
    except OSError:
        return False


# ── 配置解析与校验 ────────────────────────────────────────────────────────

def _norm_dir(v: str) -> str:
    return v.strip().strip("/").replace("\\", "/")


def load_pairs(cfg: dict) -> list[dict]:
    """读 x-extensions.i18n.pairs;校验失败 exit 2(含「未配置」)。"""
    i18n = (cfg.get("x-extensions") or {}).get("i18n")
    if not isinstance(i18n, dict) or not i18n.get("pairs"):
        _die(2, "未配置:wiki.config.json 缺 x-extensions.i18n.pairs——本工具是可选增强,"
                "不用双语横幅就无需配置(配置样例见本文件头注)")
    pairs_raw = i18n["pairs"]
    if not isinstance(pairs_raw, list):
        _die(2, "x-extensions.i18n.pairs 须为数组")
    rolling_dirs = {_norm_dir(p["raw_dir"]) for p in cfg.get("pipelines", [])
                    if p.get("kind") == "rolling"}
    pairs = []
    for i, pr in enumerate(pairs_raw):
        loc = "x-extensions.i18n.pairs[%d]" % i
        if not isinstance(pr, dict):
            _die(2, "%s 须为 object" % loc)
        src = pr.get("src_dir")
        dst = pr.get("dst_dir")
        if not isinstance(src, str) or not src.strip():
            _die(2, "%s.src_dir 必填(字符串)" % loc)
        if not isinstance(dst, str) or not dst.strip():
            _die(2, "%s.dst_dir 必填(字符串)" % loc)
        src, dst = _norm_dir(src), _norm_dir(dst)
        suffix = pr.get("suffix", "")
        if not isinstance(suffix, str):
            _die(2, "%s.suffix 须为字符串(可为空)" % loc)
        for d in (src, dst):
            if not d.startswith("raw/") or ".." in d.split("/"):
                _die(2, "%s:目录 %r 必须位于 raw/ 之下(W-ARCH-2 写入边界)" % (loc, d))
            if d in rolling_dirs:
                _die(2, "%s:%r 是 rolling 管线的 raw_dir——横幅注入会改变快照 sha256,"
                        "搅乱 rolling_digest 判新,禁止配置进语言对" % (loc, d))
        if src == dst and not suffix:
            _die(2, "%s:src_dir 与 dst_dir 相同时 suffix 不能为空(否则文件与自身配对)" % loc)
        pairs.append({
            "src_dir": src, "dst_dir": dst, "suffix": suffix,
            "src_label": str(pr.get("src_label") or src.rsplit("/", 1)[-1]),
            "dst_label": str(pr.get("dst_label") or dst.rsplit("/", 1)[-1]),
        })
    return pairs


# ── 横幅注入/剥离 ─────────────────────────────────────────────────────────

def banner(src_link: str, dst_link: str, src_label: str, dst_label: str,
           current: str) -> str:
    src = "**%s**" % src_label if current == "src" else "[[%s|%s]]" % (src_link, src_label)
    dst = "**%s**" % dst_label if current == "dst" else "[[%s|%s]]" % (dst_link, dst_label)
    return "> 🌐 %s · %s %s" % (src, dst, MARK)


def inject_text(text: str, line: str, fmmod) -> str:
    """先剥后插(幂等);插在 frontmatter 之后,无 frontmatter 时置顶。
    frontmatter 边界复用 fm.parse_frontmatter(单源,不私写解析)。"""
    text = STRIP_RE.sub("", text)
    _meta, body = fmmod.parse_frontmatter(text)
    head = text[: len(text) - len(body)] if body != text else ""
    if head:
        return head + "\n" + line + "\n\n" + body.lstrip("\n")
    return line + "\n\n" + text.lstrip("\n")


def strip_text(text: str) -> str:
    return STRIP_RE.sub("", text)


def _read(p: Path) -> str | None:
    if _dataless(p):
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _write_if_changed(p: Path, old: str, new: str, dry: bool) -> bool:
    """返回是否(将)写入;dry-run 不落盘。"""
    if new == old:
        return False
    if not dry:
        p.write_text(new, encoding="utf-8")
    return True


def _src_files(d: Path, pr: dict) -> list[Path]:
    """src 侧候选:顶层 *.md,排除 `_` 开头与 `*.dated.md` 派生件(与 sync 的
    content 文件约定一致);同目录后缀式时排除已是 dst 形态的文件。"""
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("_") or p.stem.endswith(".dated"):
            continue
        if pr["src_dir"] == pr["dst_dir"] and pr["suffix"] and p.stem.endswith(pr["suffix"]):
            continue
        out.append(p)
    return out


def run_pair(root: Path, pr: dict, dry: bool, fmmod, details: list) -> dict:
    st = {"src_dir": pr["src_dir"], "dst_dir": pr["dst_dir"], "suffix": pr["suffix"],
          "matched": 0, "written": 0, "unchanged": 0, "unmatched": 0, "skipped": 0}
    for sf in _src_files(root / pr["src_dir"], pr):
        stem = sf.stem
        df = root / pr["dst_dir"] / ("%s%s.md" % (stem, pr["suffix"]))
        if not df.is_file():
            st["unmatched"] += 1
            continue
        st["matched"] += 1
        src_link = "%s/%s" % (pr["src_dir"], stem)
        dst_link = "%s/%s%s" % (pr["dst_dir"], stem, pr["suffix"])
        for f, side in ((sf, "src"), (df, "dst")):
            old = _read(f)
            if old is None:
                st["skipped"] += 1
                details.append("skip(读取失败/dataless): %s" % f.relative_to(root))
                continue
            line = banner(src_link, dst_link, pr["src_label"], pr["dst_label"], side)
            try:
                if _write_if_changed(f, old, inject_text(old, line, fmmod), dry):
                    st["written"] += 1
                    details.append("%s: %s" % ("would-write" if dry else "write",
                                               f.relative_to(root)))
                else:
                    st["unchanged"] += 1
            except OSError as e:
                st["skipped"] += 1
                details.append("skip(写入失败): %s(%s)" % (f.relative_to(root), e))
    return st


def run_strip(root: Path, pairs: list[dict], dry: bool, details: list) -> dict:
    st = {"stripped": 0, "unchanged": 0, "skipped": 0}
    dirs = sorted({pr["src_dir"] for pr in pairs} | {pr["dst_dir"] for pr in pairs})
    for d in dirs:
        dd = root / d
        if not dd.is_dir():
            continue
        for f in sorted(dd.glob("*.md")):
            old = _read(f)
            if old is None:
                st["skipped"] += 1
                details.append("skip(读取失败/dataless): %s" % f.relative_to(root))
                continue
            try:
                if _write_if_changed(f, old, strip_text(old), dry):
                    st["stripped"] += 1
                    details.append("%s: %s" % ("would-strip" if dry else "strip",
                                               f.relative_to(root)))
                else:
                    st["unchanged"] += 1
            except OSError as e:
                st["skipped"] += 1
                details.append("skip(写入失败): %s(%s)" % (f.relative_to(root), e))
    return {"dirs": dirs, **st}


# ── site/data.json 双语槽位回填(build_site 明示的 extras 增强点)──────────

def _scalar(v) -> str:
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v).strip() if v is not None else ""


def _dst_title(path: Path, fmmod) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            head = f.read(FM_READ_LIMIT)
    except OSError:
        return ""
    meta, _ = fmmod.parse_frontmatter(head)
    return _scalar(meta.get("title"))


def patch_site(root: Path, pairs: list[dict], dry: bool, fmmod) -> dict:
    dj = root / "site" / "data.json"
    if not dj.is_file():
        return {"available": False, "note": "site/data.json 不存在(先跑 build_site.py)"}
    try:
        data = json.loads(dj.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return {"available": False, "note": "site/data.json 读取/解析失败:%s" % e}
    patched = 0
    for art in data.get("articles", []):
        fe = str(art.get("file_en") or "").replace("\\", "/")
        if not fe.endswith(".md"):
            continue
        stem, fdir = Path(fe).stem, fe.rsplit("/", 1)[0]
        for pr in pairs:
            if fdir != pr["src_dir"]:
                continue
            if pr["suffix"] and stem.endswith(pr["suffix"]):
                continue
            dst_rel = "%s/%s%s.md" % (pr["dst_dir"], stem, pr["suffix"])
            if not (root / dst_rel).is_file():
                continue
            title = _dst_title(root / dst_rel, fmmod)
            if art.get("file_zh") != dst_rel or (title and art.get("title_zh") != title):
                art["file_zh"] = dst_rel
                if title:
                    art["title_zh"] = title
                patched += 1
            break
    stats = data.get("stats")
    if isinstance(stats, dict):
        stats["translated"] = sum(1 for a in data.get("articles", []) if a.get("file_zh"))
    if patched and not dry:
        # 落盘格式与 build_site 完全一致(indent=1 + 尾换行),避免格式抖动
        dj.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    return {"available": True, "articles_patched": patched,
            "written": bool(patched and not dry)}


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki extras — raw 语言对切换横幅注入(可选组件;配置驱动,幂等,"
                    "W-ARCH-1 显式豁免的 raw 增强,--strip 可整体撤销)")
    ap.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    ap.add_argument("--dry-run", action="store_true", help="只报告将发生的写入,不落盘")
    ap.add_argument("--strip", action="store_true",
                    help="退出机制:剥离语言对目录内全部横幅,raw 回到未增强状态")
    ap.add_argument("--no-patch-site", action="store_true",
                    help="跳过 site/data.json 的 file_zh/title_zh 槽位回填")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    fmmod = _import_fm(root)
    if fmmod is None:
        _die(2, "找不到 tools/lib/fm.py(--root 应指向实例根,或在框架 checkout 内运行)")
    try:
        cfg = fmmod.load_config(root)
    except fmmod.ConfigError as e:
        _die(2, str(e))

    pairs = load_pairs(cfg)
    details: list[str] = []
    result: dict = {"ok": True, "root": str(root), "dry_run": args.dry_run,
                    "mode": "strip" if args.strip else "inject", "marker": MARK}

    if args.strip:
        result["strip"] = run_strip(root, pairs, args.dry_run, details)
        skipped = result["strip"]["skipped"]
    else:
        result["pairs"] = [run_pair(root, pr, args.dry_run, fmmod, details)
                           for pr in pairs]
        skipped = sum(p["skipped"] for p in result["pairs"])
        if not args.no_patch_site:
            result["site_patch"] = patch_site(root, pairs, args.dry_run, fmmod)
    result["ok"] = skipped == 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        tag = "(dry-run,未落盘)" if args.dry_run else ""
        if args.strip:
            s = result["strip"]
            print("strip%s:剥离 %d · 未变 %d · 跳过 %d(目录:%s)"
                  % (tag, s["stripped"], s["unchanged"], s["skipped"],
                     ", ".join(s["dirs"])))
        else:
            for p in result["pairs"]:
                print("语言对 %s ↔ %s%s:配对 %d · 写入 %d · 未变 %d · 无配对 %d · 跳过 %d"
                      % (p["src_dir"], p["dst_dir"], tag, p["matched"], p["written"],
                         p["unchanged"], p["unmatched"], p["skipped"]))
            sp = result.get("site_patch")
            if sp:
                print("site/data.json 槽位回填:%s"
                      % (("patched %d 条%s" % (sp["articles_patched"], tag))
                         if sp.get("available") else sp["note"]))
        for d in details[:SHOW_CAP]:
            print("  · %s" % d)
        if len(details) > SHOW_CAP:
            print("  … 还有 %d 条(--json 看全量计数)" % (len(details) - SHOW_CAP))
        if skipped:
            print("⚠️ %d 个文件读写失败被跳过(exit 1);取回/修复后重跑即可(幂等)" % skipped)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
