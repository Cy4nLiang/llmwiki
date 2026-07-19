#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lib.fm — frontmatter / est_tokens / wikilink 的单一实现(M2,仅 Python 标准库)

本模块是框架内 **钉死 API**(Spec §1.1 `tools/lib/fm.py`):其余工具一律 import 本模块,
禁止私写副本;签名与语义变更 = 框架 MAJOR(W-UPG-1 frozen 档)。

钉死 API:
    parse_frontmatter(text) -> (meta: dict, body: str)
    est_tokens(text, profile="cjk") -> int
    WIKILINK_RE                                   # [[...]] 编译正则(group(1) = 方括号内原文)
    iter_wikilinks(text, skip_code=True) -> [(target, display, lineno)]
    read_page(path) -> {"path", "meta", "body", "est_tokens"}
    iter_pages(wiki_dir, subdirs=("sources","entities","concepts","syntheses","queries"))
    load_config(root) -> dict

收敛依据(2026-07-19,以参考实例 newpj4 现行 tools/ 三处实现为准):
  - est_tokens 取 build_site.py 版本(build_site / lint_wiki / eval_compare 三处公式一致):
    CJK(U+4E00..U+9FFF)≈ 1 字/token,其余 ≈ 4 字符/token;latin 档 ≈ len/4。
  - wikilink 正则与码块豁免取 lint_wiki.py 逻辑:```fence 内整行豁免(fence 行本身也豁免)、
    行内 `code span` 豁免、表格转义 \\| 识别、#anchor 剥离、空 target 跳过。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

__all__ = [
    "ConfigError", "WIKILINK_RE", "est_tokens", "iter_pages", "iter_wikilinks",
    "load_config", "parse_frontmatter", "read_page",
]

# ---------------------------------------------------------------- 正则(收敛版)

# frontmatter 块:文件起始 `---` … `---`(允许 \r\n 与围栏行尾空白)
_FM_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.S)
# 键:字母开头,允许数字/下划线/连字符(facet key 是 slug,可含连字符)
_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
# wikilink:与 newpj4 lint_wiki.LINK_RE 一致;group(1) = 方括号内原文(可含 |display、#anchor)
WIKILINK_RE = re.compile(r"\[\[([^\]\[]+)\]\]")
# 行内代码 span(码块豁免的行内部分)
_CODE_SPAN_RE = re.compile(r"`[^`]*`")

_CJK_LO, _CJK_HI = "一", "鿿"  # 「一」..「鿿」,与 newpj4 三处实现一致

_DEFAULT_SUBDIRS = ("sources", "entities", "concepts", "syntheses", "queries")


# ---------------------------------------------------------------- frontmatter

def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _split_list_items(inner: str) -> list:
    """引号感知的单行列表切分:`"a, b", c` → ['a, b', 'c']。"""
    items, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf))
    out = []
    for it in items:
        v = _unquote(it)
        if v:
            out.append(v)
    return out


def _parse_value(v: str):
    """简易 YAML 子集:标量(字符串原样)/引号串/单行列表 [a, b]。一律不做类型转换。"""
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return _split_list_items(v[1:-1])
    return _unquote(v)


def parse_frontmatter(text: str):
    """解析文件头 YAML frontmatter(简易子集)。

    返回 (meta, body):meta 为 dict(值 = 字符串或字符串列表,不做类型转换;
    多行值/嵌套结构等子集外语法行被跳过);body 为闭合 `---` 之后的正文。
    无 frontmatter 或块未闭合(解析失败)时返回 ({}, text) 原文照还。
    """
    if text.startswith("﻿"):
        text = text[1:]
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        km = _KEY_RE.match(line)
        if km:
            meta[km.group(1)] = _parse_value(km.group(2))
    return meta, text[m.end():]


# ---------------------------------------------------------------- est_tokens

def est_tokens(text: str, profile: str = "cjk") -> int:
    """粗估 token 数(与参考实例 newpj4 实测口径一致的启发式)。

    - profile="cjk"  :CJK(U+4E00..U+9FFF)≈ 1 字/token,其余 ≈ 4 字符/token;
    - profile="latin":≈ 4 字符/token(len//4)。
    profile 取 config `budgets.est_tokens_profile`(枚举 cjk|latin,load_config 已校验);
    传入未知档位直接抛 ValueError(宁可炸响,不做静默误估)。
    """
    if profile == "latin":
        return len(text) // 4
    if profile != "cjk":
        raise ValueError("est_tokens: 未知 profile %r(枚举 cjk|latin)" % profile)
    cjk = sum(1 for c in text if _CJK_LO <= c <= _CJK_HI)
    return cjk + (len(text) - cjk) // 4


# ---------------------------------------------------------------- wikilink

def _link_target(raw: str) -> str:
    """[[原文]] → 目标 slug:剥 |display(含表格转义 \\|)与 #anchor(与 lint_wiki._target 一致)。"""
    return re.split(r"\\?\|", raw, maxsplit=1)[0].split("#")[0].strip().rstrip("\\")


def iter_wikilinks(text: str, skip_code: bool = True) -> list:
    """扫全文 wikilink,返回 [(target, display, lineno)](lineno 从 1 起)。

    skip_code=True(默认)时套用码块豁免(收敛自 newpj4 lint_wiki):
    ```fence 围栏内整行豁免(围栏行本身也豁免)、行内 `code` 豁免。
    display 为 | 之后的显示文本(无则 None);空 target(如纯锚点 [[#sec]])跳过。
    注意:跨实例引用 [[alias::path]](W-XRF-1)按原样出现在 target 中,由调用方自行分流。
    """
    out = []
    fence = False
    for lineno, line in enumerate(text.split("\n"), 1):
        if skip_code:
            if line.lstrip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            line = _CODE_SPAN_RE.sub("", line)
        for m in WIKILINK_RE.finditer(line):
            raw = m.group(1)
            target = _link_target(raw)
            if not target:
                continue
            parts = re.split(r"\\?\|", raw, maxsplit=1)
            display = parts[1].strip() if len(parts) > 1 else None
            out.append((target, display, lineno))
    return out


# ---------------------------------------------------------------- 页面读取

def read_page(path, profile: str = "cjk") -> dict:
    """读单页:{"path","meta","body","est_tokens"}。

    est_tokens 按整文件文本(含 frontmatter)计——与页面预算检查(W-PAGE-1)口径一致。
    profile 为可选扩展参数(默认 cjk,不影响钉死签名)。
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    return {"path": str(p), "meta": meta, "body": body,
            "est_tokens": est_tokens(text, profile)}


def iter_pages(wiki_dir, subdirs=_DEFAULT_SUBDIRS, profile: str = "cjk"):
    """按 subdirs 声明顺序迭代 wiki 各子目录页面(目录内按文件名排序,确定性)。

    逐页 yield read_page 结果,并附加便捷键 "rel"(wiki 相对 slug,如 "sources/foo")。
    缺失的子目录静默跳过(空库/新实例友好)。
    """
    wiki = Path(wiki_dir)
    for sub in subdirs:
        d = wiki / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            page = read_page(f, profile)
            page["rel"] = "%s/%s" % (sub, f.stem)
            yield page


# ---------------------------------------------------------------- config 载入

class ConfigError(Exception):
    """config 定位/解析/校验失败(CLI 约定:调用方捕获后 exit 2)。"""

    def __init__(self, message: str, errors=None):
        super().__init__(message)
        self.errors = list(errors or [])

    def __str__(self):
        base = super().__str__()
        if self.errors:
            return base + "\n" + "\n".join("  - %s" % e for e in self.errors)
        return base


_init_render = None


def _import_init_render():
    """经 sys.path 同目录导入 tools/init_render.py(校验器单源,W-UPG-1)。"""
    global _init_render
    if _init_render is None:
        tools_dir = str(Path(__file__).resolve().parent.parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        try:
            import init_render  # noqa: PLC0415
        except ImportError as e:
            raise ConfigError("无法导入 tools/init_render.py(config 校验器单源所在):%s" % e)
        _init_render = init_render
    return _init_render


def load_config(root, on_warning=None) -> dict:
    """定位并载入 <root>/wiki.config.json,返回补齐默认值后的 config dict。

    校验单源复用 init_render.validate_config + apply_defaults;校验错误抛 ConfigError
    (带逐条字段路径,调用方按 CLI 约定 exit 2)。warnings 经 on_warning 回调逐条上报,
    缺省打印到 stderr(不污染 stdout 的 --json 机器输出)。
    """
    root = Path(root)
    cfg_path = root / "wiki.config.json"
    if not cfg_path.is_file():
        raise ConfigError("wiki.config.json 不存在:%s(--root 应指向实例根)" % cfg_path)
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError("wiki.config.json 读取失败:%s(%s)" % (cfg_path, e))
    except json.JSONDecodeError as e:
        raise ConfigError("wiki.config.json 不是合法 JSON(%s:%d:%s)" % (cfg_path, e.lineno, e.msg))
    ir = _import_init_render()
    errors, warnings = ir.validate_config(raw)
    if errors:
        raise ConfigError("config 校验失败(%d 处)" % len(errors), errors)
    if on_warning is None:
        on_warning = lambda w: print("config 警告: %s" % w, file=sys.stderr)  # noqa: E731
    for w in warnings:
        on_warning(w)
    return ir.apply_defaults(raw)
