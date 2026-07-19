#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki extras/serve.py — 本地阅读器 + action API(可选组件;标准库 http.server)

【extras 声明】本文件属 extras 可选组件(Spec §1.1〔D7〕):随框架交付、MANIFEST 归
frozen 档做 hash 追踪,但**不进核心依赖面**——tools/ 与四个工作流对本文件零依赖,
删除它不影响任何核心承诺。何时不需要它见 extras/README.md。

【边界】**机械动作走 HTTP,LLM 动作 Copy-as-Prompt**(承袭参考实例 newpj4 tools/serve.py):
  - 机械动作(采集/派生重建/机械 lint/积压查询)由本服务经 subprocess 调 tools/ 执行;
  - 一切写 wiki/ 的分析动作(ingest、语义 lint、查询归档)是 agent 的活(W-ARCH-2
    双写入者分权)——UI 上的分析类按钮**只生成可拷贝的 prompt**,粘回 Claude Code
    会话执行,本服务绝不代跑。

【单源纪律】pending/status 判定、管线注册表驱动、lint 检查全部住在 tools/(sync.py /
lint_wiki.py 的 --json 出口),本文件仅做 HTTP 封装,不复制任何判定逻辑;config 载入
经 tools/lib/fm.load_config(实例钉版优先)。

路由
----
  GET  /               阅读器 UI(单文件内嵌 HTML/CSS/JS,零外部资源;读 site/data.json,
                       筛选面由 config facets/pipelines 驱动,无 facet 时自动隐藏)
  GET  /site|/raw|/wiki/**   静态只读(仅此三前缀;config/state 等不暴露)
  GET  /api/status      = tools/sync.py status --json(零网络:分管线库存/pending)
  GET  /api/pending     = tools/sync.py pending --json(待 ingest 清单 + 分档建议)
  POST /api/lint        = tools/lint_wiki.py --json(机械体检;exit 1=有发现,仍回报告)
  POST /api/fetch[?only=NAME]  = tools/sync.py sync --json:走管线注册表——声明 adapter
                       的 pull/rolling 管线子进程跑 discover/fetch;push(人/CI 直投)
                       与未声明 adapter 的管线在结果 fetch[].skipped 里返回说明,不报错。

用法:python3 extras/serve.py [--root DIR] [--port N] [--no-browser]
仅绑定 127.0.0.1,不可从网络访问。exit 0 正常退出(Ctrl+C)/ 1 端口占用等启动失败 /
2 配置用法错。2026-07-19 · 泛化自参考实例 newpj4 tools/serve.py(含 iCloud dataless 防呆)。
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PY = sys.executable
STATIC_PREFIXES = ("site", "raw", "wiki")   # 静态只读白名单(config/state 不暴露)


# ── fm 单源定位(config 校验一律 fm.load_config)───────────────────────────

def _import_fm(root: Path):
    """优先实例自持有的 <root>/tools/lib/fm.py(实例钉版),退回本文件同仓的
    ../tools/lib/fm.py(在框架 checkout 内对外部实例运行的场景)。
    返回 (fm 模块, tools 目录);找不到返回 (None, None)。"""
    for tools_dir in (root / "tools", Path(__file__).resolve().parent.parent / "tools"):
        if (tools_dir / "lib" / "fm.py").is_file():
            sys.path.insert(0, str(tools_dir))
            try:
                from lib import fm  # noqa: PLC0415
                return fm, tools_dir
            except ImportError:
                continue
    return None, None


# ── 工具子进程封装(单源:判定逻辑全在 tools/,这里只透传 --json)──────────

def tool_json(tools_dir: Path, root: Path, script: str, extra: list[str],
              timeout: int, ok_rcs=(0,)) -> tuple[dict, int]:
    """跑 `python3 tools/<script> <extra> --root <root> --json`,解析 stdout JSON。
    返回 (payload, http_status);工具 exit code 原样透传在 payload["exit"]。"""
    path = tools_dir / script
    if not path.is_file():
        return {"ok": False, "error": "%s 未就位(tools/ 不完整?)" % script}, 500
    cmd = [PY, str(path), *extra, "--root", str(root), "--json"]
    try:
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "%s 超时(>%ds)" % (script, timeout)}, 504
    except OSError as e:
        return {"ok": False, "error": "%s 启动失败:%s" % (script, e)}, 500
    out = (r.stdout or "").strip()
    try:
        data = json.loads(out) if out else {}
    except json.JSONDecodeError:
        return {"ok": False, "error": "%s 输出不是 JSON" % script, "exit": r.returncode,
                "stdout_tail": out[-800:], "stderr_tail": (r.stderr or "")[-400:]}, 500
    payload = {"ok": r.returncode in ok_rcs, "exit": r.returncode, "result": data}
    if (r.stderr or "").strip():
        payload["stderr_tail"] = r.stderr.strip()[-400:]
    return payload, 200


# ── 阅读器 UI(单文件内嵌,零外部资源;数据全部来自 /site/data.json 与 /api/*)──

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>llmwiki 阅读器</title>
<style>
:root{--bg:#fafaf7;--fg:#1f2328;--mut:#6a737d;--line:#e1e4e8;--card:#fff;
--acc:#0b6bcb;--chip:#eef2f6;--ok:#1a7f37;--warn:#9a6700;--err:#cf222e;--code:#f4f4f2}
@media (prefers-color-scheme: dark){:root{--bg:#14161a;--fg:#e6e8eb;--mut:#98a1ab;
--line:#2b3138;--card:#1b1f24;--acc:#58a6ff;--chip:#262c33;--ok:#3fb950;--warn:#d29922;
--err:#f85149;--code:#22272e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line)}
header h1{margin:0;font-size:17px}header p{margin:2px 0 0;color:var(--mut);font-size:12px}
nav{display:flex;gap:6px;padding:8px 20px;border-bottom:1px solid var(--line);flex-wrap:wrap}
nav button{border:1px solid var(--line);background:var(--card);color:var(--fg);
padding:5px 14px;border-radius:15px;cursor:pointer;font-size:13px}
nav button.on{background:var(--acc);border-color:var(--acc);color:#fff}
main{display:flex;min-height:calc(100vh - 110px)}
#left{flex:1;min-width:0;padding:12px 20px}
#doc{flex:1.1;min-width:0;border-left:1px solid var(--line);padding:14px 22px;display:none}
#doc.show{display:block}
#filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
#filters input,#filters select{background:var(--card);color:var(--fg);
border:1px solid var(--line);border-radius:6px;padding:5px 8px;font-size:13px}
#filters input{flex:1;min-width:140px}
.row{display:flex;gap:10px;align-items:baseline;padding:7px 8px;border-radius:6px;
cursor:pointer;border-bottom:1px solid var(--line)}
.row:hover{background:var(--chip)}
.row .d{color:var(--mut);font-size:12px;white-space:nowrap;width:82px;flex:none}
.row .t{flex:1;min-width:0}.row .t small{color:var(--mut);display:block;font-size:12px;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chip{display:inline-block;background:var(--chip);color:var(--mut);border-radius:9px;
padding:0 8px;font-size:11px;margin-left:4px;white-space:nowrap}
h2.sec{font-size:14px;margin:16px 0 6px;color:var(--mut)}
#doc .meta{color:var(--mut);font-size:12px;margin:4px 0 10px}
#doc .btns{margin:0 0 12px}#docbody{max-width:76ch}
button.mini,#doc .btns a{display:inline-block;border:1px solid var(--line);
background:var(--card);color:var(--acc);text-decoration:none;border-radius:6px;
padding:3px 10px;font-size:12px;cursor:pointer;margin-right:6px}
#docbody pre,#out{background:var(--code);border:1px solid var(--line);border-radius:6px;
padding:10px;overflow-x:auto;font-size:12.5px}
#docbody code{background:var(--code);border-radius:4px;padding:1px 4px;font-size:.92em}
#docbody pre code{background:none;padding:0}
#docbody blockquote{border-left:3px solid var(--line);margin:8px 0;padding:2px 12px;
color:var(--mut)}
#docbody h1{font-size:20px}#docbody h2{font-size:17px;border-bottom:1px solid var(--line);
padding-bottom:3px}#docbody h3{font-size:15px}
#docbody a{color:var(--acc)}.wl{color:var(--acc);border-bottom:1px dashed var(--acc)}
.cols{display:flex;gap:24px;flex-wrap:wrap}.col{flex:1;min-width:300px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:12px 14px;margin-bottom:14px}
.panel h3{margin:0 0 4px;font-size:14px}.panel p.hint{color:var(--mut);font-size:12px;
margin:0 0 8px}
#out{min-height:60px;white-space:pre-wrap;max-height:50vh;overflow:auto}
#prompt{width:100%;min-height:200px;background:var(--code);color:var(--fg);
border:1px solid var(--line);border-radius:6px;padding:10px;font-size:12.5px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.status-ok{color:var(--ok)}.status-warn{color:var(--warn)}.status-err{color:var(--err)}
#boot-err{padding:30px;color:var(--err)}
.badge{font-size:12px}
@media (max-width:900px){main{flex-direction:column}#doc{border-left:none;
border-top:1px solid var(--line)}}
</style>
</head>
<body>
<header>
  <h1 id="hd-name">llmwiki 阅读器</h1>
  <p id="hd-desc"></p>
  <p id="hd-stats"></p>
</header>
<nav>
  <button id="tab-src" class="on">来源</button>
  <button id="tab-wiki">Wiki 页</button>
  <button id="tab-act">动作</button>
</nav>
<main>
<div id="left">
  <div id="view-src">
    <div id="filters">
      <input id="f-q" placeholder="搜索标题 / TL;DR / slug …">
      <select id="f-pipeline" style="display:none"></select>
      <select id="f-kind" style="display:none"></select>
      <select id="f-year" style="display:none"></select>
      <span id="f-facets"></span>
    </div>
    <div id="list"></div>
  </div>
  <div id="view-wiki" style="display:none"></div>
  <div id="view-act" style="display:none">
    <div class="cols">
      <div class="col">
        <div class="panel">
          <h3>机械动作(HTTP,本地执行)</h3>
          <p class="hint">采集 / 派生重建 / 机械 lint / 积压查询由本服务经 tools/ 子进程执行,不碰 wiki/。</p>
          <button class="mini" id="b-status">状态 status</button>
          <button class="mini" id="b-pending">待 ingest</button>
          <button class="mini" id="b-lint">机械 lint</button>
          <button class="mini" id="b-fetch">采集 fetch(联网)</button>
          <pre id="out">(结果显示在这里)</pre>
        </div>
      </div>
      <div class="col">
        <div class="panel">
          <h3>LLM 动作(Copy-as-Prompt,不在此执行)</h3>
          <p class="hint">一切写 wiki/ 的分析动作(ingest / 语义 lint / 查询)是 agent 的活——这里只生成 prompt,拷回 Claude Code 会话执行(W-ARCH-2 双写入者分权)。</p>
          <button class="mini" id="p-ingest">ingest 积压 → prompt</button>
          <button class="mini" id="p-slint">语义 lint → prompt</button>
          <button class="mini" id="p-query">查询模板 → prompt</button>
          <button class="mini" id="p-copy">复制</button>
          <span id="copied" class="status-ok" style="display:none">已复制</span>
          <textarea id="prompt" placeholder="点上方按钮生成 prompt …"></textarea>
        </div>
      </div>
    </div>
  </div>
</div>
<div id="doc">
  <button class="mini" id="doc-close">关闭 ×</button>
  <h2 id="doc-title"></h2>
  <div class="meta" id="doc-meta"></div>
  <div class="btns" id="doc-btns"></div>
  <div id="docbody"></div>
</div>
</main>
<script>
"use strict";
let D=null, F={q:"",pipeline:"",kind:"",year:"",facets:{}}, last={pending:null,lint:null};
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

/* ── 极简 markdown 渲染(实用优先):标题/围栏码/行内码/粗体/链接/wikilink/引用/列表 ── */
function md(src){
  const lines=String(src).split("\\n"); let out=[],fence=false,fbuf=[],list=false;
  const inline=t=>{
    t=esc(t);
    t=t.replace(/`([^`]+)`/g,"<code>$1</code>");
    t=t.replace(/\\[\\[([^\\]]+)\\]\\]/g,(m,x)=>{const p=x.split("|");
      return '<span class="wl">'+(p[1]||p[0])+"</span>";});
    t=t.replace(/\\*\\*([^*]+)\\*\\*/g,"<b>$1</b>");
    t=t.replace(/\\[([^\\]]+)\\]\\((https?:[^)]+)\\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return t;};
  const flushList=()=>{if(list){out.push("</ul>");list=false;}};
  for(const ln of lines){
    if(ln.trimStart().startsWith("```")){
      if(fence){out.push("<pre><code>"+esc(fbuf.join("\\n"))+"</code></pre>");fbuf=[];}
      fence=!fence;continue;}
    if(fence){fbuf.push(ln);continue;}
    const h=ln.match(/^(#{1,4})\\s+(.*)/);
    if(h){flushList();out.push("<h"+h[1].length+">"+inline(h[2])+"</h"+h[1].length+">");continue;}
    if(/^\\s*[-*]\\s+/.test(ln)){if(!list){out.push("<ul>");list=true;}
      out.push("<li>"+inline(ln.replace(/^\\s*[-*]\\s+/,""))+"</li>");continue;}
    flushList();
    if(/^>\\s?/.test(ln)){out.push("<blockquote>"+inline(ln.replace(/^>\\s?/,""))+"</blockquote>");continue;}
    if(/^---+\\s*$/.test(ln)){out.push("<hr>");continue;}
    if(ln.trim()==="")out.push("");
    else out.push("<p>"+inline(ln)+"</p>");}
  if(fence)out.push("<pre><code>"+esc(fbuf.join("\\n"))+"</code></pre>");
  flushList();return out.join("\\n");}

/* ── 启动:读 site/data.json(build_site 派生;缺失时给指路)─────────────── */
async function boot(){
  let r;
  try{r=await fetch("/site/data.json");if(!r.ok)throw new Error(r.status);D=await r.json();}
  catch(e){document.querySelector("main").innerHTML=
    '<div id="boot-err">site/data.json 不可用('+esc(e.message)+')。先在实例根跑:'+
    '<code>python3 tools/build_site.py</code>,刷新本页。</div>';return;}
  $("hd-name").textContent=(D.domain&&D.domain.name||"llmwiki")+" — 阅读器";
  $("hd-desc").textContent=D.domain&&D.domain.description||"";
  const s=D.stats||{};
  $("hd-stats").textContent="来源 "+(s.articles||0)+" · 概念 "+(s.concepts||0)+
    " · 实体 "+(s.entities||0)+" · 综合 "+(s.syntheses||0)+" · 查询 "+(s.queries||0)+
    (s.translated?" · 双语 "+s.translated:"");
  buildFilters();renderList();renderWiki();}

function opt(sel,vals,label){
  sel.innerHTML='<option value="">'+label+"(全部)</option>"+
    vals.map(v=>'<option value="'+esc(v)+'">'+esc(v)+"</option>").join("");
  sel.style.display=vals.length>1?"":"none";}

function buildFilters(){
  const arts=D.articles||[];
  opt($("f-pipeline"),(D.pipelines||[]).map(p=>p.name),"管线");
  opt($("f-kind"),Object.keys(D.kind_label||{}),"类型");
  opt($("f-year"),Object.keys((D.stats||{}).by_year||{}).sort().reverse(),"年份");
  /* facet 筛选完全由 config facets 驱动;无 facet 时整块隐藏(不留特化残迹) */
  const fc=$("f-facets");fc.innerHTML="";
  for(const f of (D.facets||[])){
    const seen=Object.keys(((D.stats||{}).by_facet||{})[f.key]||{});
    const vals=[...new Set([...(f.values||[]),...seen])];
    const sel=document.createElement("select");sel.id="f-facet-"+f.key;
    sel.innerHTML='<option value="">'+esc(f.key)+"(全部)</option>"+
      vals.map(v=>'<option value="'+esc(v)+'">'+
        esc((f.badges&&f.badges[v]?f.badges[v]+" ":"")+v)+"</option>").join("");
    sel.onchange=()=>{F.facets[f.key]=sel.value;renderList();};
    fc.appendChild(sel);}
  $("f-q").oninput=e=>{F.q=e.target.value.toLowerCase();renderList();};
  $("f-pipeline").onchange=e=>{F.pipeline=e.target.value;renderList();};
  $("f-kind").onchange=e=>{F.kind=e.target.value;renderList();};
  $("f-year").onchange=e=>{F.year=e.target.value;renderList();};}

function match(a){
  if(F.pipeline&&a.pipeline!==F.pipeline)return false;
  if(F.kind&&a.source_kind!==F.kind)return false;
  if(F.year&&a.year!==F.year)return false;
  for(const k in F.facets){if(F.facets[k]&&a[k]!==F.facets[k])return false;}
  if(F.q){const hay=((a.title_en||"")+" "+(a.title_zh||"")+" "+(a.tldr||"")+" "+
    (a.slug||"")).toLowerCase();if(!hay.includes(F.q))return false;}
  return true;}

function chips(a){
  let h="";
  if(a.source_kind)h+='<span class="chip">'+esc(a.source_kind)+"</span>";
  if((D.pipelines||[]).length>1)h+='<span class="chip">'+esc(a.pipeline)+"</span>";
  for(const f of (D.facets||[])){const v=a[f.key];if(!v)continue;
    const b=f.badges&&f.badges[v];
    h+='<span class="chip badge">'+esc(b?b+" "+v:v)+"</span>";}
  if(a.file_zh)h+='<span class="chip">双语</span>';
  return h;}

function renderList(){
  const arts=(D.articles||[]).filter(match);
  $("list").innerHTML=arts.map((a,i)=>'<div class="row" data-i="'+i+'">'+
    '<span class="d">'+esc(a.date||"?")+'</span><span class="t">'+esc(a.title_en)+
    (a.title_zh?" <small>"+esc(a.title_zh)+"</small>":"")+
    (a.tldr?'<small>'+esc(a.tldr)+"</small>":"")+
    "</span><span>"+chips(a)+"</span></div>").join("")||
    '<p class="hint" style="color:var(--mut)">没有匹配的来源。</p>';
  $("list").querySelectorAll(".row").forEach(el=>el.onclick=()=>openArticle(arts[+el.dataset.i]));}

function renderWiki(){
  const KINDS=[["syntheses","综合 syntheses"],["concepts","概念 concepts"],
    ["entities","实体 entities"],["queries","查询 queries"]];
  let h="";
  for(const [k,label] of KINDS){
    const pages=(D.wiki||{})[k]||[];if(!pages.length)continue;
    h+='<h2 class="sec">'+label+"("+pages.length+")</h2>";
    h+=pages.map(p=>'<div class="row" data-f="'+esc(p.file)+'" data-t="'+esc(p.title)+'">'+
      '<span class="t">'+esc(p.title)+
      (p.summary?"<small>"+esc(p.summary)+"</small>":"")+"</span>"+
      (p.status?'<span class="chip">'+esc(p.status)+"</span>":"")+"</div>").join("");}
  $("view-wiki").innerHTML=h||'<p style="color:var(--mut)">wiki/ 还没有聚合页。</p>';
  $("view-wiki").querySelectorAll(".row").forEach(el=>
    el.onclick=()=>openDoc(el.dataset.f,el.dataset.t,""));}

async function openDoc(path,title,meta){
  $("doc").classList.add("show");
  $("doc-title").textContent=title||path;
  $("doc-meta").textContent=meta||path;
  $("doc-btns").innerHTML='<a href="/'+esc(path)+'" target="_blank">原文件</a>';
  $("docbody").innerHTML="加载中 …";
  try{const r=await fetch("/"+path);if(!r.ok)throw new Error(r.status);
    $("docbody").innerHTML=md(await r.text());}
  catch(e){$("docbody").innerHTML='<p class="status-err">读取失败:'+esc(e.message)+"</p>";}}

function openArticle(a){
  const metas=[a.date,a.source_kind,a.pipeline,(a.authors||[]).join(", ")]
    .filter(Boolean).join(" · ");
  openDoc(a.file_en,a.title_en,metas);
  let btns='<a href="/'+esc(a.file_en)+'" target="_blank">raw 原文</a>';
  if(a.file_zh)btns+='<button class="mini" id="doc-zh">配对语言版</button>';
  if(a.wiki_source)btns+='<button class="mini" id="doc-wiki">wiki 源页</button>';
  if(a.url)btns+='<a href="'+esc(a.url)+'" target="_blank" rel="noopener">外部链接</a>';
  $("doc-btns").innerHTML=btns;
  if(a.file_zh)$("doc-zh").onclick=()=>openDoc(a.file_zh,a.title_zh||a.title_en,metas);
  if(a.wiki_source)$("doc-wiki").onclick=()=>
    openDoc("wiki/"+a.wiki_source+".md",a.title_en+" — wiki 源页",metas);}

$("doc-close").onclick=()=>$("doc").classList.remove("show");

/* ── tab 切换 ── */
const TABS={ "tab-src":"view-src","tab-wiki":"view-wiki","tab-act":"view-act"};
for(const t in TABS)$(t).onclick=()=>{
  for(const x in TABS){$(x).classList.toggle("on",x===t);
    $(TABS[x]).style.display=x===t?"":"none";}};

/* ── 机械动作(HTTP)── */
async function api(method,path){
  $("out").textContent="运行中 … "+path;
  try{const r=await fetch(path,{method});const j=await r.json();
    $("out").textContent=JSON.stringify(j,null,1);return j;}
  catch(e){$("out").textContent="请求失败:"+e.message;return null;}}
$("b-status").onclick=()=>api("GET","/api/status");
$("b-pending").onclick=async()=>{const j=await api("GET","/api/pending");
  if(j&&j.result)last.pending=j.result;};
$("b-lint").onclick=async()=>{const j=await api("POST","/api/lint");
  if(j&&j.result)last.lint=j.result;};
$("b-fetch").onclick=async()=>{
  if(!confirm("采集 fetch:对声明 adapter 的管线跑 discover/fetch(联网)+ 派生重建。继续?"))return;
  const j=await api("POST","/api/fetch");
  if(j&&j.result&&j.result.pipelines)last.pending={pending:
    j.result.pipelines.flatMap(p=>p.pending||[]),pending_total:j.result.pending_total};};

/* ── LLM 动作:Copy-as-Prompt(只生成,不执行)── */
function setPrompt(t){$("prompt").value=t;$("copied").style.display="none";}
$("p-copy").onclick=async()=>{
  const t=$("prompt").value;if(!t)return;
  try{await navigator.clipboard.writeText(t);}
  catch(e){$("prompt").select();document.execCommand("copy");}
  $("copied").style.display="";};

$("p-ingest").onclick=async()=>{
  if(!last.pending){const j=await api("GET","/api/pending");
    if(j&&j.result)last.pending=j.result;}
  const p=(last.pending&&last.pending.pending)||[];
  if(!p.length){setPrompt("(没有待 ingest 积压——wiki 已覆盖所有已采集内容。)");return;}
  const lines=p.map((x,i)=>(i+1)+". "+x.raw_file+" → "+x.expected_source+
    "  ["+(x.source_kind||"?")+" → "+x.tier+"]"+
    (x.reason&&x.reason!=="no-source-page"?"("+x.reason+")":""));
  setPrompt(
"请按 wiki-ingest 工作流处理以下待 ingest 积压(共 "+p.length+" 篇):\\n\\n"+
lines.join("\\n")+"\\n\\n要求:\\n"+
"- touch 下限随档位(W-ING-1:full ≥5 / light ≥1);light 档必记 followups「待晋升」;\\n"+
"- ≥10 篇走 bulk map-reduce(W-ING-2:源页可并行,共享聚合页单写者收敛);\\n"+
"- rolling 刷新走滚动源特例,变化记「演进」;真矛盾 ⚠️ 标记,禁止静默覆盖(W-ING-3);\\n"+
"- 完成后跑 python3 tools/build_site.py && python3 tools/build_index.py,"+
"append log 一条(W-LOG-1),回执 created / updated / contradictions。");};

$("p-slint").onclick=()=>{
  let mech="(建议先点「机械 lint」把机械层结果带上)";
  if(last.lint)mech="机械层已跑(error "+last.lint.errors+" / warning "+last.lint.warnings+
    ";totals: "+JSON.stringify(last.lint.totals)+")";
  setPrompt(
"请按 wiki-lint 工作流做语义体检。"+mech+"\\n\\n语义层逐项审(机械工具测不出的):\\n"+
"- 跨页矛盾与静默覆盖痕迹(W-ING-3:演进/对比/⚠️ 三分裁决);\\n"+
"- 过时声明与 stale 操作页(W-LNT-3:核实后 bump verified:,推翻的按演进处理);\\n"+
"- 晋升候选裁决(W-PAGE-3:rule-of-three 达标的纯文本提及升 wikilink+建页);\\n"+
"- mature 页空段与 description 分诊质量(W-PAGE-2)。\\n\\n"+
"先报告发现清单,经我批准后再改;完成后 append log 一条 lint(W-LOG-1)。");};

$("p-query").onclick=()=>{setPrompt(
"请按 wiki-query 工作流回答:「<在此填你的问题>」\\n\\n"+
"- 先读 wiki/_map.md 按问题类型选入口,按读取档位表阅读(大文件 grep-only,W-LNT-1);\\n"+
"- 精确事实(版本/日期/数字)只认 exact-match,不信参数记忆(W-QRY-1);\\n"+
"- 未命中走显式降级链:声明「wiki 未收录」→ grep raw/ → 标注来源作答 + 记 followups(W-QRY-3);\\n"+
"- 答案有保留价值默认归档 wiki/queries/(告知可否决,W-QRY-2),归档后跑索引派生 + log。");};

boot();
</script>
</body>
</html>
"""


# ── HTTP handler ─────────────────────────────────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    ROOT: Path = Path(".")
    TOOLS: Path = Path("tools")
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".md": "text/markdown; charset=utf-8",
                      ".jsonl": "application/json; charset=utf-8"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(self.ROOT), **kw)

    def log_message(self, *a):  # 安静;错误仍由 _json 回给调用方
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        # 参考实例 newpj4 实测教训:iCloud 驱逐的 dataless 文件读取会阻塞等云端,
        # 元数据检查后 503 快速失败(0x40000000 = SF_DATALESS;非 macOS 平台恒 0)。
        path = self.translate_path(self.path)
        try:
            if os.path.isfile(path) and (getattr(os.stat(path), "st_flags", 0) & 0x40000000):
                self.send_error(503, "File evicted by iCloud (dataless); download it first")
                return None
        except OSError:
            pass
        return super().send_head()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text: str):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _api(self, script: str, extra: list[str], timeout: int, ok_rcs=(0,)):
        payload, code = tool_json(self.TOOLS, self.ROOT, script, extra, timeout, ok_rcs)
        self._json(payload, code)

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            self._html(HTML)
        elif p == "/api/status":
            self._api("sync.py", ["status"], 120)
        elif p == "/api/pending":
            self._api("sync.py", ["pending"], 120)
        elif p.startswith("/api/"):
            self._json({"ok": False, "error": "not found"}, 404)
        elif p.split("/", 2)[1:2] and p.split("/", 2)[1] in STATIC_PREFIXES:
            super().do_GET()   # 静态只读白名单:site/ raw/ wiki/
        else:
            self._json({"ok": False, "error": "not found(静态仅暴露 /site /raw /wiki)"}, 404)

    def _local_origin_ok(self):
        # 仅接受本机来源:浏览器跨源 POST 会带非 localhost 的 Origin,拒之(动作端点驱动子进程/出网)
        origin = self.headers.get("Origin")
        if origin is not None:
            host = urlparse(origin).hostname or ""
            if host not in ("127.0.0.1", "localhost", "::1"):
                return False
        host_hdr = (self.headers.get("Host") or "").split(":")[0]
        return host_hdr in ("127.0.0.1", "localhost", "::1", "")

    def do_POST(self):
        if not self._local_origin_ok():
            self._json({"ok": False, "error": "forbidden: non-local origin"}, 403)
            return
        u = urlparse(self.path)
        if u.path == "/api/lint":
            # lint exit 1 = 有发现,报告照常回传(ok=true;发现内容在 result 里)
            self._api("lint_wiki.py", [], 900, ok_rcs=(0, 1))
        elif u.path == "/api/fetch":
            # 管线注册表驱动(单源在 sync.py):声明 adapter 的 pull/rolling 管线
            # 子进程跑 discover/fetch;push 与缺 adapter 的管线在 fetch[].skipped 返回说明。
            extra = ["sync"]
            only = (parse_qs(u.query).get("only") or [None])[0]
            if only:
                extra += ["--only", only]
            self._api("sync.py", extra, 3900)
        else:
            self._json({"ok": False, "error": "not found"}, 404)


# ── main ─────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="llmwiki extras — 本地阅读器 + action API(可选组件;机械动作 HTTP,"
                    "LLM 动作 Copy-as-Prompt;仅绑定 127.0.0.1)")
    ap.add_argument("--root", default=".", help="实例根(含 wiki.config.json;默认 cwd)")
    ap.add_argument("--port", type=int, default=8787, help="端口(默认 8787)")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    fmmod, tools_dir = _import_fm(root)
    if fmmod is None:
        print("错误: 找不到 tools/lib/fm.py(--root 应指向实例根,或在框架 checkout 内运行)",
              file=sys.stderr)
        return 2
    try:
        cfg = fmmod.load_config(root)
    except fmmod.ConfigError as e:
        print("配置错误: %s" % e, file=sys.stderr)
        return 2

    # 启动前 best-effort 刷一次派生(阅读器数据源;失败不阻断,UI 会给指路)
    build = tools_dir / "build_site.py"
    if build.is_file():
        r = subprocess.run([PY, str(build), "--root", str(root)], cwd=str(root),
                           capture_output=True, text=True)
        print("  build_site: %s" % ("OK" if r.returncode == 0
                                    else "rc=%s(阅读器仍可启动)" % r.returncode))

    Handler.ROOT, Handler.TOOLS = root, tools_dir
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    url = "http://localhost:%d/" % args.port
    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        print("错误: 端口 %d 绑定失败:%s(换 --port)" % (args.port, e), file=sys.stderr)
        return 1
    with httpd:
        print("\n  llmwiki 阅读器(%s) →  %s" % (cfg["domain"]["name"], url))
        print("  root=%s(localhost only;机械动作 HTTP,LLM 动作 Copy-as-Prompt)"
              % root)
        print("  Ctrl+C 停止\n")
        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
