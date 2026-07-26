#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki extras/mcp_server.py — MCP server(可选组件;JSON-RPC 2.0 over stdio,仅标准库)

【extras 声明】本文件属 extras 可选组件(Spec §1.1〔D7〕):随框架交付、MANIFEST 归
frozen 档做 hash 追踪,但**不进核心依赖面**——tools/ 与各工作流对本文件零依赖,
删除它不影响任何核心承诺。何时不需要它见 extras/README.md。

【为什么存在】一级宿主 Claude Code 走 skills 就够了;MCP 是给**非 skills 宿主**
(Claude Desktop / Cursor / Windsurf 等)消费同一座 wiki 的通用接口(R7)。

【边界】只读为主,唯一写面是 `wiki_capture` → push 管线的 raw 目录(W-ARCH-2 允许
工具写 raw/;W-ARCH-1 raw 不可变 → **只新建、已存在即幂等跳过,绝不覆盖**)。
**绝不写 `wiki/`**:整合是 agent 的活(双写入者分权)。投递 ≠ 整合(W-CAP-1)。

【单源纪律】检索判定住在 `tools/search.py`(BM25 打分/tokenize),本文件经 subprocess
调它的 `--json` 出口,**不复制任何打分逻辑**(W-IDX-3);slug 解析走 `tools/lib/wikigraph`,
frontmatter/est_tokens 走 `tools/lib/fm`,config 载入经 `fm.load_config`(实例钉版优先)。

【stdio 是协议通道】stdout **只写 JSON-RPC 帧**(每帧单行 + flush),一切诊断走 stderr
——这是对 serve.py(诊断打 stdout)的显式偏离,照抄那边会当场毁掉握手。子进程 stdout
一律捕获,绝不透传。

工具(4)
------
  wiki_map      读 `wiki/_map.md` 全文 + 读取档位表节 + token 预算(路由入口,先读它)
  wiki_search   = `tools/search.py --json`(BM25 排名检索;检索单源)
  wiki_page     按 slug 取页:mode=tldr|full、max_tokens 截断,回 est_tokens 供预算
  wiki_capture  投递草稿到 push 管线 raw 目录(不整合),随后 subprocess 调
                `adapters/local_notes.py register` 登记台账

用法:python3 extras/mcp_server.py [--root DIR]
协议:MCP `2025-11-25`(常量钉死;版本协商见 _handle_initialize)。
exit 0 对端关闭 stdin 正常退出 / 1 stdio 级失败 / 2 配置用法错(--root 不是实例)。
2026-07-25 · S8。宿主注册片段与 MCP inspector 验证清单见 `docs/mcp.md`。
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

PY = sys.executable
PROTOCOL_VERSION = "2025-11-25"          # 钉死;客户端请求别的版本时按协商规则仍回本值
SERVER_NAME = "llmwiki"
SEARCH_TIMEOUT = 60                      # 本地 BM25,给足余量
REGISTER_TIMEOUT = 60
MAX_TOKENS_DEFAULT = 2000
_TLDR_RE = re.compile(r"^##[^\n]*(?:TL;DR|一句话摘要)[^\n]*\n(.+?)(?=\n#|\Z)",
                      re.S | re.M | re.I)   # 与 build_site.py 逐字同口径(含 re.I)
_TIERS_ANCHOR = '<a id="read-tiers"></a>'
_TRUNC_NOTE = "\n\n…(已按 max_tokens 截断)\n"
_FM_BAD_RE = re.compile(r"^---|\n|\r")   # frontmatter 标量字段禁含:换行 / 起首 `---`


def _posint(v, default, name):
    """正整数入参:合形则用,不合形**不静默吞**——退默认值并回 ignored_args 让调用方可察觉。

    (声明了 inputSchema 但本服务不跑 JSON Schema 引擎;LLM 把整数写成 "40" 是高频抖动,
    静默换成默认值会让 max_tokens 这类「硬承诺」变成谎。bool 是 int 子类,显式排除。)
    """
    if isinstance(v, int) and not isinstance(v, bool) and v > 0:
        return v, {}
    if v is None:
        return default, {}
    return default, {"ignored_args": {name: v}}


def _flat(v) -> str:
    """任意入参 → 单行字符串:压平 CR/LF/TAB 为空格(frontmatter 标量不可跨行)。"""
    return re.sub(r"[\r\n\t]+", " ", str(v if v is not None else "")).strip()


def _log(msg: str) -> None:
    """诊断只走 stderr——stdout 是 JSON-RPC 帧通道。"""
    print("[mcp_server] %s" % msg, file=sys.stderr, flush=True)


def _import_libs(root: Path):
    """优先实例自持有的 <root>/tools/lib(实例钉版),退回本文件同仓 ../tools/lib。

    返回 (fm, wikigraph, tools_dir);找不到返回 (None, None, None)。照 serve.py:55 口径。
    """
    needed = ("fm.py", "wikigraph.py")
    for tools_dir in (root / "tools", Path(__file__).resolve().parent.parent / "tools"):
        # 进 import 之前先查**全集**:只查 fm.py 会让不完整的老实例(缺 wikigraph)导入到
        # 一半,把 `lib` 包连同 `lib.fm` 钉进 sys.modules,后续候选再 import 也解析到
        # 那份缓存 → "退回同仓" 分支永久失效。
        if not all((tools_dir / "lib" / f).is_file() for f in needed):
            continue
        sys.path.insert(0, str(tools_dir))
        try:
            from lib import fm  # noqa: PLC0415
            from lib import wikigraph  # noqa: PLC0415
            return fm, wikigraph, tools_dir
        except ImportError as e:
            _log("从 %s 导入 lib 失败:%s(尝试下一候选)" % (tools_dir, e))
            for mod in [m for m in list(sys.modules) if m == "lib" or m.startswith("lib.")]:
                del sys.modules[mod]                  # 清残留,否则下一候选命中坏缓存
            if sys.path and sys.path[0] == str(tools_dir):
                sys.path.pop(0)
            continue
    return None, None, None


# ---------------------------------------------------------------- 工具实现

class Wiki:
    """实例数据面;每个工具一个方法,返回 (payload_dict, is_error)。"""

    def __init__(self, root: Path, fm, wikigraph, tools_dir: Path, cfg: dict):
        self.root, self.fm, self.wg = root, fm, wikigraph
        self.tools_dir, self.cfg = tools_dir, cfg
        self.wiki = root / "wiki"
        self.profile = cfg["budgets"]["est_tokens_profile"]

    # ---- 子进程封装(单源:判定住在 tools/,这里只透传 --json)----
    def _tool_json(self, script: Path, args: list, timeout: int, ok_rcs=(0,)):
        if not script.is_file():
            return {"ok": False, "error": "%s 未就位(安装不完整?)" % script.name}, True
        try:
            r = subprocess.run([PY, str(script), *args], cwd=str(self.root),
                               capture_output=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "%s 超时(>%ds)" % (script.name, timeout)}, True
        except OSError as e:
            return {"ok": False, "error": "%s 启动失败:%s" % (script.name, e)}, True
        out = (r.stdout or "").strip()
        try:
            data = json.loads(out) if out else {}
        except json.JSONDecodeError:
            return {"ok": False, "error": "%s 输出不是 JSON" % script.name,
                    "exit": r.returncode, "stderr_tail": (r.stderr or "")[-400:]}, True
        payload = {"ok": r.returncode in ok_rcs, "exit": r.returncode, "result": data}
        if (r.stderr or "").strip():
            payload["stderr_tail"] = r.stderr.strip()[-400:]
        return payload, r.returncode not in ok_rcs

    def _page_set(self) -> set:
        return {p.relative_to(self.wiki).as_posix()[:-3]
                for p in sorted(self.wiki.rglob("*.md"))}

    def _push_raw_dir(self):
        """第一条 push 型管线的 raw_dir(禁硬编码 raw/inbox——实例可改)。"""
        for p in self.cfg.get("pipelines", []):
            if p.get("kind") == "push":
                return p.get("raw_dir"), p
        return None, None

    # ---- wiki_map ----
    def wiki_map(self, _args):
        p = self.wiki / "_map.md"
        if not p.is_file():
            return {"ok": False, "error": "wiki/_map.md 未就位(实例是否已渲染?)"}, True
        text = p.read_text(encoding="utf-8")
        tiers = None
        if _TIERS_ANCHOR in text:                     # 抽「读取档位」节到下一个 `## `
            tail = text.split(_TIERS_ANCHOR, 1)[1]
            m = re.search(r"\n## ", tail)
            tiers = (tail[:m.start()] if m else tail).strip()
        b = self.cfg["budgets"]
        return {"ok": True, "content": text, "read_tiers": tiers,
                "est_tokens": self.fm.est_tokens(text, self.profile),
                "budgets": {"map_lines": b.get("map_lines"),
                            "page_tokens": b.get("page_tokens"),
                            "boot_tokens": b.get("boot_tokens")}}, False

    # ---- wiki_search ----
    def wiki_search(self, args):
        q = str(args.get("query", "")).strip()
        if not q:
            return {"ok": False, "error": "query 不能为空"}, True
        if not (self.root / "site" / "agent" / "search-index.json").is_file():
            return {"ok": False, "error": "检索索引未就位 → 先跑 "
                    "`python3 tools/build_site.py && python3 tools/build_index.py`"}, True
        extra = ["--root", str(self.root), "--json"]
        k, ignored = _posint(args.get("k"), None, "k")
        if k is not None:
            extra += ["--k", str(k)]
        # `--` 终止选项解析:查询词以 `-` 开头时不会被 argparse 误当旗标
        payload, is_err = self._tool_json(self.tools_dir / "search.py",
                                          extra + ["--", q], SEARCH_TIMEOUT)
        payload.update(ignored)
        return payload, is_err

    # ---- wiki_page ----
    def _truncate(self, text: str, max_tokens: int):
        """按 est_tokens 权威判定截断(字符前缀二分 + 回退到换行);不切坏 UTF-8。

        截断提示语自身也占 token,必须**先从预算里扣掉**——否则 returned_est_tokens
        会超过调用方给的 max_tokens,预算承诺就成了谎。预算连提示都放不下时不加提示
        (仍由 truncated=True 表达)。
        """
        if self.fm.est_tokens(text, self.profile) <= max_tokens:
            return text, False
        note = _TRUNC_NOTE
        budget = max_tokens - self.fm.est_tokens(note, self.profile)
        if budget <= 0:
            note, budget = "", max_tokens

        def composed(n: int) -> str:
            cut = text[:n]
            nl = cut.rfind("\n")
            if nl > len(cut) * 0.6:                   # 回退到行边界(除非会砍掉过多)
                cut = cut[:nl]
            return cut.rstrip() + note

        lo, hi = 0, len(text)
        while lo < hi:                                # 先按裸前缀二分(est 对前缀长度单调)
            mid = (lo + hi + 1) // 2
            if self.fm.est_tokens(text[:mid], self.profile) <= budget:
                lo = mid
            else:
                hi = mid - 1
        # est_tokens 含整除余数、**非线性可加**(est(a)+est(b) ≠ est(a+b)):拼上提示语后
        # 可能多出 1–2 token,故对最终结果再收敛几步,把 max_tokens 变成硬承诺。
        while lo > 0 and self.fm.est_tokens(composed(lo), self.profile) > max_tokens:
            lo -= 1
        return composed(lo), True

    def wiki_page(self, args):
        slug = str(args.get("slug", "")).strip()
        if not slug:
            return {"ok": False, "error": "slug 不能为空"}, True
        if "::" in slug:
            return {"ok": False, "error": "跨实例引用(alias::slug)不由本服务解析"}, True
        # 只认 page_set 内的 slug:天然挡住 ../ 路径穿越与绝对路径
        target = self.wg.resolve_slug(slug, self._page_set())
        if target is None:
            return {"ok": False, "error": "未收录:%s(先用 wiki_search 找 slug)" % slug}, True
        page = self.fm.read_page(self.wiki / (target + ".md"), self.profile)
        mode = args.get("mode") or "tldr"
        if mode not in ("tldr", "full"):
            return {"ok": False, "error": "mode 只支持 tldr|full"}, True
        body, tldr_source = page["body"], None
        if mode == "tldr":                            # 降级链:TL;DR 节 → 首个 ## 节 → 整 body
            m = _TLDR_RE.search(body)
            if m:
                body, tldr_source = m.group(0).strip(), "tldr-section"
            else:
                secs = re.split(r"(?m)^(?=## )", body)
                cand = next((s for s in secs if s.startswith("## ")), "")
                body, tldr_source = ((cand.strip(), "first-section") if cand
                                     else (body, "whole-body"))
        mt, ignored = _posint(args.get("max_tokens"), MAX_TOKENS_DEFAULT, "max_tokens")
        content, truncated = self._truncate(body, mt)
        return {"ok": True, "slug": target, "path": "wiki/%s.md" % target,
                "meta": page["meta"], "mode": mode, "tldr_source": tldr_source,
                "content": content, "truncated": truncated, **ignored,
                "max_tokens_applied": mt,
                "est_tokens": page["est_tokens"],     # 整页(与 pages.jsonl / 档位表同口径)
                "returned_est_tokens": self.fm.est_tokens(content, self.profile)}, False

    # ---- wiki_capture ----
    def wiki_capture(self, args):
        # frontmatter 是逐行 `key: value` 解析的:标量字段里的换行 / `---` 会**注入伪键或提前
        # 闭合 frontmatter**(实测可注入任意键)。落盘前一律压平换行、拒 `---`。
        # 顺序要紧:先对**原始值**判注入并**拒绝**(静默清洗等于悄悄改写调用方数据),
        # 通过后再 _flat 压平残余控制字符(TAB 等)作二道防御。
        raw_title, raw_kind = str(args.get("title") or ""), str(args.get("kind") or "draft")
        if _FM_BAD_RE.search(raw_title) or _FM_BAD_RE.search(raw_kind):
            return {"ok": False, "error": "title/kind 不得含换行或起首 `---`"
                    "(frontmatter 逐行解析,换行会注入伪键或提前闭合)"}, True
        title, kind = _flat(raw_title)[:200], _flat(raw_kind) or "draft"
        slug = "".join(c for c in str(args.get("slug", "")).strip()
                       if c.isalnum() or c in "-_")[:60]
        if not title or not slug:
            return {"ok": False, "error": "title 与 slug 必填(slug 限 [A-Za-z0-9-_])"}, True
        raw_dir, pl = self._push_raw_dir()
        if raw_dir is None:
            return {"ok": False, "error": "本实例无 push 型管线(投递口);"
                    "在 wiki.config.json 加一条 kind=push 管线后重试"}, True
        date = str(args.get("date") or datetime.date.today().isoformat()).strip()
        try:                                          # fullmatch + 真日历校验(挡 9999-99-99)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise ValueError("格式")
            datetime.date.fromisoformat(date)
        except ValueError:
            return {"ok": False, "error": "date 须为合法日历日 YYYY-MM-DD"}, True
        target = self.root / raw_dir / ("%s-%s.md" % (date, slug))
        rel = target.relative_to(self.root).as_posix()
        if target.exists():                           # W-ARCH-1 raw 不可变:只新建,不覆盖
            return {"ok": True, "drafted": None, "skipped_existing": rel,
                    "hint": "同名投递件已存在,幂等跳过(raw 不可变,W-ARCH-1)"}, False
        body = str(args.get("body") or
                   "- (踩坑 / 约定 / 决策 —— 一条一行;无则删除本文件)\n")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("---\ntitle: %s\ndate: %s\nkind: %s\n---\n\n# %s\n\n%s"
                              % (title, date, kind, title, body), encoding="utf-8")
        except OSError as e:
            return {"ok": False, "error": "写投递件失败:%s" % e}, True
        # 台账登记(exit 1 = 有不合格文件,仍是正常结果;只有 2 才是配置/用法错)。
        # 旗标是 `--pipeline`(local_notes) 而**不是** `--only`(那是 sync.py 的)——写错会 rc=2。
        reg, reg_err = self._tool_json(
            self.root / "adapters" / "local_notes.py",
            ["register", "--root", str(self.root), "--json",
             "--pipeline", pl.get("name", "")], REGISTER_TIMEOUT, ok_rcs=(0, 1))
        out = {"ok": True, "drafted": rel, "pipeline": pl.get("name"),
               "register": reg.get("result"),
               "hint": "投递 ≠ 整合(W-CAP-1):下次 sync 会报 pending,再走 light 档 ingest;"
                       "本服务绝不写 wiki/"}
        if reg_err:      # 投递件已落盘,故仍 ok:true;但登记失败必须让调用方看见,不能吞
            out["register_error"] = reg.get("error") or reg.get("stderr_tail") or "登记失败"
            out["hint"] += ";⚠️ 台账登记失败(见 register_error),pending 判定不受影响" \
                           "(sync 从 raw 现场重算)"
        return out, False


TOOLS = [
    {"name": "wiki_map",
     "description": "读路由页 wiki/_map.md 全文 + 读取档位表 + token 预算。"
                    "**任何检索前先调它**:它给出每个文件的体量与该用哪种读法。",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "wiki_search",
     "description": "BM25 排名检索(经 tools/search.py,检索单源)。关键词说不准、"
                    "想跨库排名候选时用;精确事实仍应 grep 原文 exact-match(W-QRY-1)。",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "查询词(空格分隔;支持中英文)"},
         "k": {"type": "integer", "description": "返回条数(默认由 search.py 决定)"}},
         "required": ["query"], "additionalProperties": False}},
    {"name": "wiki_page",
     "description": "按 slug 取页。mode=tldr 只回一句话摘要节(便宜),full 回全文;"
                    "max_tokens 截断。响应带整页 est_tokens 与本次返回量,便于预算。",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string", "description": "页 slug,如 concepts/foo(裸 foo 也会补全)"},
         "mode": {"type": "string", "enum": ["tldr", "full"], "description": "默认 tldr"},
         "max_tokens": {"type": "integer", "description": "返回上限,默认 2000"}},
         "required": ["slug"], "additionalProperties": False}},
    {"name": "wiki_capture",
     "description": "投递一条草稿到 push 管线的 raw 目录(踩坑/约定/决策)。"
                    "**投递 ≠ 整合**(W-CAP-1):本工具不写 wiki/,整合等下次 sync 报 pending。",
     "inputSchema": {"type": "object", "properties": {
         "title": {"type": "string", "description": "标题(必填)"},
         "slug": {"type": "string", "description": "文件 slug,限 [A-Za-z0-9-_](必填)"},
         "kind": {"type": "string", "description": "source_kind;默认 draft"},
         "date": {"type": "string", "description": "YYYY-MM-DD,默认今天"},
         "body": {"type": "string", "description": "正文 markdown(默认检查点模板)"}},
         "required": ["title", "slug"], "additionalProperties": False}},
]


# ---------------------------------------------------------------- JSON-RPC / MCP

def _result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def _text_result(payload: dict, is_error: bool):
    """MCP tools/call 结果:工具执行失败用 isError=true(不是 JSON-RPC error)——
    协议分层:JSON-RPC error 只用于协议级问题(未知方法/坏参数)。"""
    return {"content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False, indent=1)}],
            "isError": is_error}


def handle(msg: dict, wiki: Wiki):
    """处理一条消息;返回响应 dict,或 None(notification 不回响应)。"""
    mid, method = msg.get("id"), msg.get("method")
    if not isinstance(method, str):
        return _error(mid, -32600, "method 缺失或不是字符串")
    params = msg.get("params") or {}
    # JSON-RPC 2.0 允许 params 为数组,MCP 全部方法都用对象——非对象一律协议级拒绝,
    # 绝不让它流到下面的 .get() 上炸成 AttributeError(那会打死整个 server 进程)
    if not isinstance(params, dict):
        return _error(mid, -32602, "params 须为对象(本服务不接受数组/标量 params)")
    if method == "initialize":
        want = str(params.get("protocolVersion", ""))
        if want and want != PROTOCOL_VERSION:        # 协商:回本服务支持的版本
            _log("客户端请求协议 %s,本服务支持 %s" % (want, PROTOCOL_VERSION))
        return _result(mid, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": _fw_version()},
            "instructions": "llmwiki 知识库。先调 wiki_map 看路由页与读取档位,再按需 "
                            "wiki_search / wiki_page;精确事实(版本/日期/数字)只认原文 "
                            "exact-match,未收录就明说未收录,不要用参数记忆补(W-QRY-1/3)。"
                            "有值得留底的踩坑/决策用 wiki_capture 投递(投递≠整合)。"})
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None                                  # notification 无 id,不回响应
    if method == "ping":
        return _result(mid, {})
    if method == "tools/list":
        return _result(mid, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str):                # 非字符串不可作字典键查表(会炸 unhashable)
            return _error(mid, -32602, "name 须为字符串")
        fn = {"wiki_map": wiki.wiki_map, "wiki_search": wiki.wiki_search,
              "wiki_page": wiki.wiki_page, "wiki_capture": wiki.wiki_capture}.get(name)
        if fn is None:
            return _error(mid, -32602, "未知工具:%s" % name)
        if not isinstance(args, dict):
            return _error(mid, -32602, "arguments 须为对象")
        try:
            payload, is_err = fn(args)
        except Exception as e:  # noqa: BLE001 — 工具级异常归 isError,不打断会话
            _log("工具 %s 异常:%r" % (name, e))
            payload, is_err = {"ok": False, "error": "%s 执行异常:%s" % (name, e)}, True
        return _result(mid, _text_result(payload, is_err))
    if mid is None:
        return None                                  # 未知 notification:静默忽略
    return _error(mid, -32601, "未知方法:%s" % method)


def _fw_version() -> str:
    for p in (Path(__file__).resolve().parent.parent / "framework" / "VERSION",):
        try:
            return p.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return "0.0.0"


def serve(stdin, stdout, wiki: Wiki) -> int:
    """NDJSON 帧循环:逐行读 JSON-RPC,逐帧写单行 JSON + flush。

    stdout 只写协议帧(MCP stdio 规范:禁写非 MCP 内容、消息内禁裸换行——
    json.dumps 默认把换行转义成 \\n,故正文多行也安全)。
    """
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = _error(None, -32700, "Parse error")
        else:
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
                resp = _error(msg.get("id") if isinstance(msg, dict) else None,
                              -32600, "Invalid Request(须为 jsonrpc 2.0 对象)")
            else:
                try:
                    resp = handle(msg, wiki)
                except Exception as e:  # noqa: BLE001 — 一帧处理崩不得带走整个 server:
                    _log("处理帧异常:%r" % e)  # 回 -32603 后继续读下一帧,否则排队的帧全丢
                    resp = _error(msg.get("id"), -32603, "Internal error: %s" % e)
        if resp is None:
            continue
        stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        stdout.flush()                               # 不 flush 宿主永远读不到
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki MCP server(stdio;4 工具;可选组件)。注册片段见 docs/mcp.md")
    ap.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    fm, wikigraph, tools_dir = _import_libs(root)
    if fm is None:
        print("配置错误: 找不到 tools/lib/fm.py(--root 应指向实例根)", file=sys.stderr)
        return 2
    try:
        cfg = fm.load_config(root)
    except fm.ConfigError as e:
        print("配置错误: %s" % e, file=sys.stderr)
        return 2
    _log("serving %s(协议 %s)" % (root, PROTOCOL_VERSION))
    try:
        return serve(sys.stdin, sys.stdout, Wiki(root, fm, wikigraph, tools_dir, cfg))
    except (BrokenPipeError, KeyboardInterrupt):
        return 0                                     # 对端关闭/中断:正常收摊
    except OSError as e:
        print("stdio 失败: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
