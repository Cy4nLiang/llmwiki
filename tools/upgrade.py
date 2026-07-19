#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki upgrade — 实例跟版升级器(Spec §10 端到端时序的机械部分;仅 Python 标准库)

用法:
    python3 tools/upgrade.py --root <实例根> --framework <框架仓根> \
        [--dry-run] [--date YYYY-MM-DD] [--force-frozen] [--json]

时序(编号对应 Spec §10 / wiki-upgrade skill):
  ① 版本对比:实例 framework/VERSION vs 框架 VERSION;相同 → 「无事可做」exit 0;
     打印新版 framework/UPGRADING.md 中介于 (旧, 新] 的条目(规则 ID 差距清单);
  ② 预备份:本次会改动的实例文件按相对路径备份到 state/tmp/pre-upgrade-<旧版>/
     (实例未必是 git 仓,不假设 git;git 实例的 pre-upgrade tag 由 skill 层负责);
  ③ frozen 档(W-UPG-1):按框架新 MANIFEST 的 frozen 条目(限实例实际持有路径):
     实例文件 hash == 旧快照(实例 framework/MANIFEST.json)→ 整体覆盖为新版;
     hash 不符 → fork 候选,列出并跳过(--force-frozen 才覆盖);
     新版新增文件落在实例已持有的顶层目录下 → 直接安装(与 ⑤ 快照「按持有过滤」口径自洽);
  ④ render-once 三方合并:用实例 config 分别渲染 base 模板(实例 framework/base/,旧渲染器)
     与新模板(框架仓,新渲染器)得 base_rendered / new_rendered;逐文件判定:
       实例现文件 == base_rendered → 采用 new_rendered;
       new_rendered == base_rendered → 保留实例;
       三者互异 → 写 <file>.upgrade-new 交 agent 合并(不覆盖原文件)。
     契约〈实例扩展附录〉段(lint 豁免区标记以下)永不参与合并:合并前摘出、合并后原样接回;
     wiki/log.md 为 append-only 实例数据,不参与三方合并(模板变更不回灌);
  ⑤ 收尾:更新实例 framework/VERSION、base/(新模板快照)、MANIFEST 快照(按实例持有过滤,
     口径同 init_render);wiki 页有写入时重建派生索引(W-IDX-1);跑 lint_wiki 全量 + --manifest
     作门禁;打印 golden 回归提醒(W-UPG-2);向 wiki/log.md append 一条 upgrade 条目(W-LOG-1);
  ⑥ --dry-run:只打印计划(备份/覆盖/合并/冲突各清单),零写入。

exit:0 完成且零冲突零 fork 候选 / 1 有冲突或 fork 候选待处理(或门禁未过)/ 2 用法配置错。

写入者例外声明(W-ARCH-2):工具本只写 raw/ + site/ + state/;**upgrade.py 是唯一获准写
wiki/log.md 的工具**——升级是框架层簿记而非知识写入,仅 append 一条 W-LOG-1 格式的 upgrade
条目,绝不改历史。除此之外本工具不触碰 instance 档(wiki 正文、raw/、config、adapters、golden)。

单源纪律:渲染逻辑一律 import init_render 复用(build_plan / compute_slots / render_text,
含条件模块块处理);base 侧优先加载实例 tools/init_render.py(旧渲染器语义),新侧加载框架仓
tools/init_render.py。init_render.main 内联的「日期打戳」与「MANIFEST 快照过滤」两段未成函数,
本文件按同规则最小镜像并注明出处(见 _stamp_dates / _snapshot_manifest)——框架侧改动该两段
时须同步本文件(gen_manifest 会因 hash 变化强制走升级流程,不会静默漂移)。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# 单源纪律:同目录 sys.path(与 lint_wiki 同款),fm.load_config / init_render 复用
_TOOLS = Path(__file__).resolve().parent
for _p in (str(_TOOLS), str(_TOOLS / "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER3_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")
UPG_HDR_RE = re.compile(r"(?m)^## (\d+\.\d+\.\d+)[^\n]*$")
BOOT_DATE_RE = re.compile(r"(?m)^## \[(\d{4}-\d{2}-\d{2})\] bootstrap \|")
# 契约〈实例扩展附录〉起点标记(CLAUDE.template.md 尾段「lint 豁免区」注释;标记行以下 = 实例私有)
APPENDIX_MARK = "<!-- lint 豁免区"
CONFLICT_SUFFIX = ".upgrade-new"
LOG_SKIP_NOTE = "wiki/log.md 为 append-only 实例数据,不参与三方合并(模板变更不回灌)"


class UpgradeError(Exception):
    """升级预检/渲染失败(调用方按 CLI 约定 exit 2)。"""


# ---------------------------------------------------------------- 小工具

def _semver(s):
    m = SEMVER3_RE.match(s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_module(py_path: Path, name: str):
    """importlib 按独立名加载 init_render(实例旧版与框架新版共存,互不覆盖)。"""
    spec = importlib.util.spec_from_file_location(name, str(py_path))
    if spec is None or spec.loader is None:
        raise UpgradeError("无法加载模块:%s" % py_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_manifest(path: Path):
    """返回 (doc, entries):entries 为 [{'path','tier','sha256'}, ...];兼容裸列表形态。"""
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("files", doc) if isinstance(doc, dict) else doc
    if not isinstance(entries, list):
        raise UpgradeError("MANIFEST 结构异常(%s):files 不是数组" % path)
    return doc, entries


# ---------------------------------------------------------------- 渲染(import init_render 复用)

def _stamp_dates(rel: str, text: str, date: str) -> str:
    """日期打戳:口径镜像 init_render.main 的两段渲染后处理(该逻辑内联于 main 未成函数,
    无法 import;此处逐规则同构最小实现,框架侧改动须同步)。
      a) wiki/log.md:删 bootstrap 指引注释、bootstrap 首条日期占位 → date;
      b) 其余 wiki/*.md:frontmatter 区 created/updated 的 YYYY-MM-DD 占位 → date。"""
    if rel == "wiki/log.md":
        lines = []
        for ln in text.splitlines():
            if re.match(r"^\s*<!--.*bootstrap.*-->\s*$", ln):
                continue
            if ln.startswith("## [YYYY-MM-DD] bootstrap"):
                ln = ln.replace("[YYYY-MM-DD]", "[%s]" % date, 1)
            lines.append(ln)
        return "\n".join(lines) + "\n"
    if rel.startswith("wiki/"):
        lines, in_fm, fm_seen = text.splitlines(), False, 0
        for i, ln in enumerate(lines):
            if ln.strip() == "---":
                fm_seen += 1
                in_fm = fm_seen == 1
                if fm_seen >= 2:
                    break
            elif in_fm and re.match(r"^(created|updated):\s*YYYY-MM-DD\s*$", ln):
                lines[i] = ln.split(":")[0] + ": " + date
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text


def render_tree(ir, tpl_root: Path, cfg: dict, fw_version: str, date: str):
    """用 ir 模块渲染 tpl_root 全部 render-once 模板 → ({rel: str|bytes}, plan)。
    渲染函数全部 import 复用:build_plan / compute_slots / render_text(含条件模块块)。"""
    plan, missing = ir.build_plan(tpl_root)
    if missing:
        raise UpgradeError("模板缺失,无法渲染(%s):\n%s"
                           % (tpl_root, "\n".join("  - %s" % m for m in missing)))
    slots = ir.compute_slots(cfg, fw_version)
    conds = {  # 条件模块开关:与 init_render.main 同口径(config 派生,三行)
        "multi_facet": bool(cfg["facets"]),
        "rolling_source": any(p["kind"] == "rolling" for p in cfg["pipelines"]),
        "peers": bool(cfg["peers"]),
    }
    out, errors = {}, []
    for src, rel in plan:
        if src.suffix == ".md":
            text, errs = ir.render_text(src.read_text(encoding="utf-8"), slots, conds,
                                        str(src.relative_to(tpl_root)))
            errors += errs
            out[rel] = _stamp_dates(rel, text, date)
        else:
            out[rel] = src.read_bytes()  # skills 附属非 md 文件:字节级比较/拷贝
    if errors:
        raise UpgradeError("渲染失败(%d 处槽位/模块错误):\n%s"
                           % (len(errors), "\n".join("  - %s" % e for e in errors)))
    return out, plan


def split_appendix(text: str):
    """契约〈实例扩展附录〉切分:返回 (head, tail)。head 含标记行本身;
    tail = 标记行以下的实例私有内容(无标记时 tail=None,整文件参与合并)。"""
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if APPENDIX_MARK in ln:
            return "".join(lines[: i + 1]), "".join(lines[i + 1:])
    return text, None


# ---------------------------------------------------------------- 收尾镜像件

def _snapshot_manifest(new_doc, root: Path) -> str:
    """实例 MANIFEST 快照:按实例实际持有过滤。口径镜像 init_render.main 的快照过滤段
    (内联未成函数;保持同构:保留 dict 外形、indent=1)。"""
    data = json.loads(json.dumps(new_doc))
    entries = data.get("files", data) if isinstance(data, dict) else data
    if isinstance(entries, list):
        kept = [e for e in entries if (root / e.get("path", "")).exists()]
        if isinstance(data, dict) and "files" in data:
            data = dict(data, files=kept)
        else:
            data = kept
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _write_any(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _pick_backup_dir(root: Path, old_v: str) -> Path:
    base = root / "state" / "tmp" / ("pre-upgrade-%s" % old_v)
    if not base.exists():
        return base
    n = 2
    while (root / "state" / "tmp" / ("pre-upgrade-%s-%d" % (old_v, n))).exists():
        n += 1
    return root / "state" / "tmp" / ("pre-upgrade-%s-%d" % (old_v, n))


def _run_tool(root: Path, script: str, extra):
    """subprocess 跑实例自己的 tools/<script>;返回 (rc, stdout+stderr) 或 (None, 缺失原因)。"""
    p = root / "tools" / script
    if not p.is_file():
        return None, "tools/%s 缺失,跳过" % script
    proc = subprocess.run([sys.executable, str(p)] + list(extra),
                          capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ---------------------------------------------------------------- 主流程

def _die(code, *msgs):
    for m in msgs:
        print(m, file=sys.stderr)
    raise SystemExit(code)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="llmwiki 实例跟版升级器(Spec §10 机械部分)")
    ap.add_argument("--root", required=True, help="实例根(含 wiki.config.json 与 framework/VERSION)")
    ap.add_argument("--framework", required=True, help="框架仓根(含 CLAUDE.template.md 与 framework/VERSION)")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划,零写入")
    ap.add_argument("--date", default=None, help="簿记日期 YYYY-MM-DD(缺省今天)")
    ap.add_argument("--force-frozen", action="store_true",
                    help="fork 候选也覆盖为新版(本地改动先入预备份;W-UPG-1)")
    ap.add_argument("--json", action="store_true", help="机器输出(结构化)")
    args = ap.parse_args(argv)

    say = (lambda *a, **k: None) if args.json else print
    rpt = {"mode": "dry-run" if args.dry_run else "apply"}

    date = args.date or _dt.date.today().isoformat()
    if not DATE_RE.match(date):
        _die(2, "错误: --date 须为 YYYY-MM-DD,得到 %r" % date)

    root = Path(args.root).resolve()
    fw = Path(args.framework).resolve()
    if root == fw:
        _die(2, "错误: --root 与 --framework 不能是同一目录")
    if not (fw / "CLAUDE.template.md").is_file() or not (fw / "framework" / "VERSION").is_file():
        _die(2, "错误: --framework 不是框架仓根(缺 CLAUDE.template.md 或 framework/VERSION):%s" % fw)
    inst_ver_file = root / "framework" / "VERSION"
    if not inst_ver_file.is_file():
        _die(2, "错误: 实例缺 framework/VERSION(未经 init_render 渲染?):%s" % inst_ver_file)

    old_v = inst_ver_file.read_text(encoding="utf-8").strip()
    new_v = (fw / "framework" / "VERSION").read_text(encoding="utf-8").strip()
    ovt, nvt = _semver(old_v), _semver(new_v)
    if ovt is None or nvt is None:
        _die(2, "错误: VERSION 不是语义版本(实例 %r / 框架 %r)" % (old_v, new_v))
    rpt.update(old=old_v, new=new_v)

    # ---- ① 版本对比 -----------------------------------------------------
    if ovt == nvt:
        say("== upgrade == 实例已在 framework %s,无事可做。" % old_v)
        if args.json:
            print(json.dumps({**rpt, "noop": True, "rc": 0}, ensure_ascii=False))
        return 0
    if ovt > nvt:
        _die(2, "错误: 实例版本 %s 新于框架 %s——降级不支持(回滚请用升级前 tag / state/tmp 备份)"
             % (old_v, new_v))

    say("== upgrade %s -> %s%s ==" % (old_v, new_v, "(--dry-run)" if args.dry_run else ""))

    upg_file = fw / "framework" / "UPGRADING.md"
    entries_between = []
    if upg_file.is_file():
        text = upg_file.read_text(encoding="utf-8")
        matches = list(UPG_HDR_RE.finditer(text))
        for i, m in enumerate(matches):
            v = _semver(m.group(1))
            if v is None or not (ovt < v <= nvt):
                continue
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            entries_between.append((m.group(1), text[m.start():end].rstrip()))
    rpt["upgrading_entries"] = [v for v, _ in entries_between]
    say("\n① 规则 ID 差距清单(framework/UPGRADING.md,(%s, %s] 共 %d 条):"
        % (old_v, new_v, len(entries_between)))
    if entries_between:
        for _, block in entries_between:
            say("-" * 56)
            say(block)
        say("-" * 56)
    else:
        say("  (UPGRADING.md 无该区间条目——请确认框架仓已随版本补写迁移说明)")

    # ---- config(fm.load_config 单源)+ MANIFEST 双端 --------------------
    try:
        import fm as fmmod
    except ImportError as e:
        _die(2, "错误: 无法导入 tools/lib/fm.py(钉死 API 所在):%s" % e)
    try:
        cfg = fmmod.load_config(root)
    except fmmod.ConfigError as e:
        _die(2, "配置错误: %s" % e)

    new_mf_path = fw / "framework" / "MANIFEST.json"
    if not new_mf_path.is_file():
        _die(2, "错误: 框架仓缺 framework/MANIFEST.json(先在框架仓跑 gen_manifest.py)")
    try:
        new_doc, new_entries = _read_manifest(new_mf_path)
    except (json.JSONDecodeError, UpgradeError) as e:
        _die(2, "错误: 框架 MANIFEST 解析失败:%s" % e)

    old_hash, old_tier = {}, {}
    old_mf_path = root / "framework" / "MANIFEST.json"
    warns = []
    if old_mf_path.is_file():
        try:
            _, old_entries = _read_manifest(old_mf_path)
            for e in old_entries:
                old_hash[e.get("path", "")] = e.get("sha256")
                old_tier[e.get("path", "")] = e.get("tier")
        except (json.JSONDecodeError, UpgradeError) as e:
            warns.append("实例旧 MANIFEST 快照解析失败(%s)——frozen 无基线,不匹配者一律按 fork 候选" % e)
    else:
        warns.append("实例缺 framework/MANIFEST.json 旧快照——frozen 无基线,不匹配者一律按 fork 候选")

    # ---- ③ frozen 档决策(W-UPG-1)---------------------------------------
    fr_overwrite, fr_forced, fr_install = [], [], []   # (rel, src)
    fr_uptodate, fr_not_held, fr_fork = [], [], []     # rel / rel / (rel, 原因)
    mf_stale = []
    new_paths = set()
    for e in new_entries:
        rel = e.get("path", "")
        new_paths.add(rel)
        if e.get("tier") != "frozen":
            continue
        src = fw / rel
        if not src.is_file():
            warns.append("%s: 框架仓缺该 frozen 文件(MANIFEST 声明),跳过" % rel)
            continue
        inst = root / rel
        if inst.is_file():
            cur = _sha256(inst)
            if cur == e.get("sha256"):
                fr_uptodate.append(rel)
            elif old_hash.get(rel) and cur == old_hash[rel]:
                fr_overwrite.append((rel, src))
            else:
                reason = "hash 与旧快照不符" if old_hash.get(rel) else "旧快照无基线记录"
                if args.force_frozen:
                    fr_forced.append((rel, src))
                else:
                    fr_fork.append((rel, reason))
        else:
            if rel in old_hash:
                # 曾持有、现缺失 = 本地改动(删除)→ fork 候选;--force-frozen 重装
                if args.force_frozen:
                    fr_forced.append((rel, src))
                else:
                    fr_fork.append((rel, "文件缺失(旧快照曾持有,视为本地删除)"))
            elif (root / rel.split("/", 1)[0]).is_dir():
                fr_install.append((rel, src))     # 新版新增文件,顶层目录已持有 → 安装
            else:
                fr_not_held.append(rel)           # 实例未持有该目录(如未采纳 extras/)
        # 框架仓自身与其 MANIFEST 的一致性(过期 = 配置错,fail-fast)
        if src.is_file() and any(rel == r for r, _ in fr_overwrite + fr_forced + fr_install):
            if _sha256(src) != e.get("sha256"):
                mf_stale.append(rel)
    if mf_stale:
        _die(2, "错误: 框架仓与其 MANIFEST 不一致(%s)——先在框架仓重跑 gen_manifest.py"
             % ", ".join(mf_stale))
    fr_removed = sorted(p for p, t in old_tier.items()
                        if t == "frozen" and p not in new_paths and (root / p).exists())

    say("\n③ frozen 档(新 MANIFEST %d 条 frozen;W-UPG-1):"
        % sum(1 for e in new_entries if e.get("tier") == "frozen"))
    for label, rows in (("覆盖为新版", [r for r, _ in fr_overwrite]),
                        ("强制覆盖(--force-frozen,本地改动入备份)", [r for r, _ in fr_forced]),
                        ("新增安装", [r for r, _ in fr_install])):
        if rows:
            say("  %s %d:" % (label, len(rows)))
            for r in rows:
                say("    - %s" % r)
    say("  已是新版 %d;未持有跳过 %d%s" % (len(fr_uptodate), len(fr_not_held),
        ((":" + "、".join(fr_not_held)) if fr_not_held else "")))
    if fr_fork:
        say("  ⚠️ fork 候选 %d(跳过不覆盖;确认放弃本地改动用 --force-frozen;"
            "确认保留 = 显式 fork 记入 log,W-UPG-1):" % len(fr_fork))
        for r, why in fr_fork:
            say("    - %s(%s)" % (r, why))
    if fr_removed:
        say("  框架已移除 %d(不自动删除,建议移 _attic/ 或手工清理):%s"
            % (len(fr_removed), "、".join(fr_removed)))

    # ---- ④ render-once 三方合并 -----------------------------------------
    base_root = root / "framework" / "base"
    if not (base_root / "CLAUDE.template.md").is_file():
        _die(2, "错误: 实例缺 framework/base/ 模板快照(三方合并基线;未经 init_render 渲染?)")

    boot_date = date
    log_path = root / "wiki" / "log.md"
    if log_path.is_file():
        m = BOOT_DATE_RE.search(log_path.read_text(encoding="utf-8"))
        if m:
            boot_date = m.group(1)
        else:
            warns.append("wiki/log.md 无 bootstrap 条目,渲染日期回退 %s(只影响「现文件==base」判定精度)" % date)
    else:
        warns.append("wiki/log.md 缺失,渲染日期回退 %s;收尾将新建该文件落账" % date)

    try:
        ir_new = _load_module(fw / "tools" / "init_render.py", "_upg_ir_new")
    except Exception as e:  # noqa: BLE001 — 加载失败一律配置错
        _die(2, "错误: 无法加载框架仓渲染器 tools/init_render.py:%s" % e)
    try:
        ir_base = _load_module(root / "tools" / "init_render.py", "_upg_ir_base")
    except Exception as e:  # noqa: BLE001
        warns.append("实例旧渲染器加载失败(%s),base 渲染回退用新渲染器" % e)
        ir_base = ir_new

    try:
        base_r, _ = render_tree(ir_base, base_root, cfg, old_v, boot_date)
        new_r, new_plan = render_tree(ir_new, fw, cfg, new_v, boot_date)
    except UpgradeError as e:
        _die(2, "错误: %s" % e)

    # wiki/log.md 不参与三方合并(append-only 实例数据)
    base_r.pop("wiki/log.md", None)
    had_log_tpl = new_r.pop("wiki/log.md", None) is not None

    ro_adopt, ro_install, ro_conflict = [], [], []   # (rel, content)
    ro_keep, ro_uptodate, ro_removed, ro_notes = [], [], [], []
    for rel in sorted(set(base_r) | set(new_r)):
        base_c, new_c = base_r.get(rel), new_r.get(rel)
        inst_p = root / rel
        if new_c is None:                              # 模板已移除
            if inst_p.exists():
                ro_removed.append(rel)
            continue
        inst_c = None
        if inst_p.is_file():
            try:
                inst_c = inst_p.read_bytes() if isinstance(new_c, bytes) \
                    else inst_p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                ro_conflict.append((rel, new_c))
                warns.append("%s: 读取失败(%s),按冲突处理" % (rel, e))
                continue
        # 契约附录段摘出(仅 CLAUDE.md;lint 豁免区标记以下永不参与合并)
        appendix = None
        cmp_inst, cmp_base, cmp_new = inst_c, base_c, new_c
        if rel == "CLAUDE.md" and isinstance(inst_c, str):
            cmp_inst, appendix = split_appendix(inst_c)
            if isinstance(base_c, str):
                cmp_base, _ = split_appendix(base_c)
            if isinstance(new_c, str):
                cmp_new, _tail_new = split_appendix(new_c)
                if _tail_new and _tail_new.strip():
                    warns.append("CLAUDE.md: 新模板附录标记以下含内容,已忽略(附录属实例私有)")
        if inst_c is None:
            if base_c is None:
                ro_install.append((rel, new_c))        # 新模板新增 → 安装
            elif cmp_new == cmp_base:
                ro_notes.append("%s: 实例已删除且模板无变化,尊重删除不重建" % rel)
            else:
                ro_conflict.append((rel, new_c))       # 实例删除 × 框架有更新 → 冲突
            continue
        if cmp_inst == cmp_new:
            ro_uptodate.append(rel)                    # 已与新版一致(含三者全等)
        elif cmp_new == cmp_base:
            ro_keep.append(rel)                        # 框架未动 → 保留实例
        elif cmp_base is not None and cmp_inst == cmp_base:
            final = new_c
            if rel == "CLAUDE.md" and appendix is not None and isinstance(new_c, str):
                head, _ = split_appendix(new_c)
                final = head + appendix                # 附录原样接回
            ro_adopt.append((rel, final))              # 实例未动 → 采用新版
        else:
            ro_conflict.append((rel, new_c))           # 三者互异 → .upgrade-new

    say("\n④ render-once 三方合并(base=framework/base@%s × 实例现文件 × 新模板@%s;渲染日期 %s):"
        % (old_v, new_v, boot_date))
    for label, rows in (("采用新版", [r for r, _ in ro_adopt]),
                        ("新增安装", [r for r, _ in ro_install]),
                        ("保留实例(框架未动)", ro_keep),
                        ("已与新版一致", ro_uptodate)):
        if rows:
            say("  %s %d:%s" % (label, len(rows), "、".join(rows)))
    if ro_conflict:
        say("  ⚠️ 冲突 %d(三者互异 → 写 <file>%s,原文件不动,交 agent 逐 diff 合并):"
            % (len(ro_conflict), CONFLICT_SUFFIX))
        for r, _ in ro_conflict:
            say("    - %s → %s%s" % (r, r, CONFLICT_SUFFIX))
    if ro_removed:
        say("  模板已移除 %d(实例文件保留,建议手工处理):%s" % (len(ro_removed), "、".join(ro_removed)))
    for n in ro_notes:
        say("  · %s" % n)
    say("  · %s" % LOG_SKIP_NOTE + ("" if had_log_tpl else "(新模板亦无 log 模板)"))

    # ---- ② 预备份清单(实际拷贝在写入前执行)-----------------------------
    write_rels = [r for r, _ in fr_overwrite + fr_forced] + [r for r, _ in ro_adopt]
    backup_rels = set(r for r in write_rels if (root / r).is_file())
    for extra in ("framework/VERSION", "framework/MANIFEST.json", "wiki/log.md"):
        if (root / extra).is_file():
            backup_rels.add(extra)
    if base_root.is_dir():
        for f in sorted(base_root.rglob("*")):
            if f.is_file():
                backup_rels.add(f.relative_to(root).as_posix())
    agents_p = root / "AGENTS.md"
    refresh_agents = ("CLAUDE.md" in write_rels and agents_p.is_file()
                      and not agents_p.is_symlink())
    if refresh_agents:
        backup_rels.add("AGENTS.md")
    for r, _ in ro_conflict:
        if (root / (r + CONFLICT_SUFFIX)).is_file():
            backup_rels.add(r + CONFLICT_SUFFIX)
    backup_dir = _pick_backup_dir(root, old_v)
    say("\n② 预备份 → %s(%d 文件,含 framework/{VERSION,MANIFEST,base/} 与 wiki/log.md)"
        % (backup_dir.relative_to(root), len(backup_rels)))

    conflicts = [r for r, _ in ro_conflict]
    forks = [r for r, _ in fr_fork]
    rpt.update(
        frozen={"overwrite": [r for r, _ in fr_overwrite], "forced": [r for r, _ in fr_forced],
                "install": [r for r, _ in fr_install], "uptodate": len(fr_uptodate),
                "fork": [{"path": r, "reason": w} for r, w in fr_fork],
                "not_held": fr_not_held, "removed": fr_removed},
        render_once={"adopt": [r for r, _ in ro_adopt], "install": [r for r, _ in ro_install],
                     "keep": ro_keep, "uptodate": ro_uptodate,
                     "conflict": conflicts, "removed": ro_removed},
        backup_dir=str(backup_dir.relative_to(root)), backup_files=sorted(backup_rels),
        warnings=warns,
    )

    for w in warns:
        say("警告: %s" % w)

    rc = 1 if (conflicts or forks) else 0

    # ---- ⑥ dry-run:只打印计划,零写入 -----------------------------------
    if args.dry_run:
        say("\n== 计划完毕(--dry-run,零写入)== 冲突 %d / fork 候选 %d → exit %d"
            % (len(conflicts), len(forks), rc))
        if args.json:
            print(json.dumps({**rpt, "rc": rc}, ensure_ascii=False))
        return rc

    # ---- 执行:备份 → frozen → render-once → 收尾 -------------------------
    for rel in sorted(backup_rels):
        srcp = root / rel
        dstp = backup_dir / rel
        dstp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(srcp), str(dstp))

    for rel, src in fr_overwrite + fr_forced + fr_install:
        _write_any(root / rel, src.read_bytes())
    for rel, content in ro_adopt + ro_install:
        _write_any(root / rel, content)
    for rel, content in ro_conflict:
        _write_any(root / (rel + CONFLICT_SUFFIX), content)
    if refresh_agents:  # symlink 降级实例:AGENTS.md 硬拷贝须随 CLAUDE.md 重拷(lint 校验两者一致)
        shutil.copyfile(str(root / "CLAUDE.md"), str(agents_p))
        say("提示: AGENTS.md 为硬拷贝降级,已随 CLAUDE.md 重拷")

    # ---- ⑤ 收尾:VERSION / base/ / MANIFEST 快照 --------------------------
    (root / "framework").mkdir(parents=True, exist_ok=True)
    (root / "framework" / "VERSION").write_text(new_v + "\n", encoding="utf-8")
    if base_root.is_dir():
        shutil.rmtree(str(base_root))
    for src in sorted({s for s, _ in new_plan}):
        rel = src.relative_to(fw).as_posix()
        dst = base_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(dst))
    (root / "framework" / "MANIFEST.json").write_text(
        _snapshot_manifest(new_doc, root), encoding="utf-8")
    say("\n⑤ 收尾:framework/VERSION → %s;base/ 刷新为新模板快照;MANIFEST 快照按持有过滤落位"
        % new_v)

    # 派生索引重建(wiki 页有写入时,W-IDX-1)→ lint 门禁
    wiki_written = any(r.startswith("wiki/") for r in
                      [x for x, _ in ro_adopt + ro_install])
    rebuilt = False
    if wiki_written:
        for script in ("build_site.py", "build_index.py"):
            trc, out = _run_tool(root, script, ["--root", str(root)])
            if trc is None:
                warns.append(out)
            elif trc != 0:
                warns.append("tools/%s rc=%d(门禁报告里核对)" % (script, trc))
        rebuilt = True
        say("  wiki 页有写入 → 已重建派生索引(build_site + build_index,W-IDX-1)")
    rpt["rebuilt_index"] = rebuilt

    gate_rc, gate_out = _run_tool(root, "lint_wiki.py",
                                  ["--root", str(root), "--manifest"] +
                                  (["--json"] if args.json else []))
    if gate_rc is None:
        warns.append(gate_out)
        say("警告: %s(门禁未跑,按未过处理)" % gate_out)
        gate_rc = 1
    else:
        say("\n门禁:python3 tools/lint_wiki.py --root . --manifest → rc=%d" % gate_rc)
        if not args.json:
            print(gate_out.rstrip())
    if args.json:
        try:
            rpt["gate"] = json.loads(gate_out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            rpt["gate"] = {"raw": gate_out[-2000:]}
    rpt["gate_rc"] = gate_rc

    # golden 回归提醒(W-UPG-2)
    golden = root / "evals" / "golden.jsonl"
    rpt["golden_present"] = golden.is_file()
    if golden.is_file():
        say("\n⚠️ W-UPG-2 golden 回归门禁【必跑】:evals/golden.jsonl 存在——按 wiki-golden skill 的"
            "playbook 驱动会话产出 run.jsonl,`python3 tools/eval_retrieval.py <run.jsonl> --root .`,"
            "与升级前基线对照(eval_compare):P/R 与 tok/题不回退才算完成跟版;回退即回滚。")
    else:
        say("\nW-UPG-2:实例无 evals/golden.jsonl,以全量 lint 代门禁;建议尽快建基线(wiki-golden skill)。")

    # ---- log 落账(W-LOG-1;upgrade.py 是唯一获准写 wiki/log.md 的工具,理由见头注)----
    one_line = ("## [%s] upgrade | framework %s -> %s(frozen 覆盖 %d/新增 %d, "
                "render-once 采用 %d, 冲突 %d, fork 候选 %d)"
                % (date, old_v, new_v, len(fr_overwrite) + len(fr_forced),
                   len(fr_install), len(ro_adopt) + len(ro_install),
                   len(conflicts), len(forks)))
    body = ["- 差距条目: %s(framework/UPGRADING.md);备份: %s"
            % (", ".join(v for v, _ in entries_between) or "无", backup_dir.relative_to(root))]
    if fr_forced:
        body.append("- --force-frozen 覆盖(本地改动已入备份): %s" % "、".join(r for r, _ in fr_forced))
    if forks:
        body.append("- fork 候选(未覆盖,W-UPG-1;确认保留请在此后补一条显式 fork 声明): %s"
                    % "、".join(forks))
    if conflicts:
        body.append("- 冲突待合并: %s(逐 diff 合并后删 %s 文件)"
                    % ("、".join("%s%s" % (r, CONFLICT_SUFFIX) for r in conflicts), CONFLICT_SUFFIX))
    body.append("- 门禁: lint --manifest rc=%d;golden: %s(W-UPG-2)"
                % (gate_rc, "提醒已打印,必跑" if golden.is_file() else "无基线,以全量 lint 代"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existed = log_path.is_file()
    prev = log_path.read_text(encoding="utf-8") if existed else ""
    with open(str(log_path), "a", encoding="utf-8") as fh:
        if not existed:
            fh.write("# log(append-only,格式见 W-LOG-1)\n")
        elif prev and not prev.endswith("\n"):
            fh.write("\n")
        fh.write("\n%s\n%s\n" % (one_line, "\n".join(body)))

    if cfg.get("framework_version") != new_v:
        say("提示: wiki.config.json framework_version=%s,请手动 bump 至 %s(实例档,工具不代写)"
            % (cfg.get("framework_version"), new_v))

    rc = 1 if (conflicts or forks or gate_rc != 0) else 0
    say("\n== 升级%s == 冲突 %d / fork 候选 %d / 门禁 rc=%d → exit %d%s"
        % ("完成" if rc == 0 else "完成(有待处理项)", len(conflicts), len(forks), gate_rc, rc,
           "" if rc == 0 else ";处理 %s 与 fork 后复跑 lint --manifest 确认" % CONFLICT_SUFFIX))
    if args.json:
        print(json.dumps({**rpt, "warnings": warns, "rc": rc}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
