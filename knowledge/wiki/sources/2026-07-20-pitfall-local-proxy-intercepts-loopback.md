---
title: "踩坑:本机 HTTP 代理拦截 127.0.0.1 请求,serve 冒烟必然超时"
description: "CI/脚本里对 loopback 的 HTTP 请求超时、『本机 curl 通但 urllib 连不上』、怀疑 HTTP(S)_PROXY 干扰时读本页:根因(urllib 代理不豁免 loopback)与空 ProxyHandler 直连修法。"
type: source
created: 2026-07-20
ingest_tier: light
raw_file: raw/inbox/2026-07-20-pitfall-local-proxy-intercepts-loopback.md
source_kind: pitfall
date_published: 2026-07-20
date_ingested: 2026-07-20
authors: [llmwiki-dev]
tags: [pitfall, ci, network, cluster/ci-hermeticity]
status: draft
---

# 踩坑:本机 HTTP 代理拦截 127.0.0.1 请求,serve 冒烟必然超时

## 一句话摘要 / TL;DR

Python `urllib` 默认把环境变量 `HTTP(S)_PROXY` 注入代理 opener 且 **loopback 不豁免**,导致 CI 冒烟对 `127.0.0.1` 的请求死在代理里;修法是显式 `ProxyHandler({})` 空代理直连,不依赖 NO_PROXY 等外部环境状态。

## 关键论点 / Key Claims

- `urllib.request` 的默认 opener 读取 `HTTP_PROXY` / `HTTPS_PROXY` 构建代理链,对 127.0.0.1 的请求同样送进代理;本机代理通常不回连 loopback 高位端口,表现为「服务起来了但脚本必然超时」。
- 一切对 loopback 的程序化 HTTP 请求都应显式绕过代理;「本机能 curl 通但脚本超时」优先怀疑代理环境变量。
- `ProxyHandler({})` 传空字典 = 禁用一切代理(含环境变量注入);相比设置 NO_PROXY,不依赖外部环境状态,CI 内自洽。

## 关键事实 / Key Facts(数字、日期、版本、专名 —— 如实记录)

- 触发场景:`tests/run_ci.py` phase_extras 冒烟 `extras/serve.py`(起本地阅读器后 GET `http://127.0.0.1:<port>/api/status`),在配置了系统级 HTTP(S)_PROXY 的开发机上必然超时。
- 修法已落位:`tests/run_ci.py` 行 602–604,`opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))`(仓内核实与原注释一致)。
- 冒烟请求超时参数 `timeout=3`,整体 deadline 30s(run_ci 现行代码)。

## 我学到了什么 / Takeaways

- loopback 请求绕代理要用「进程内显式禁用」(空 ProxyHandler)而非「环境变量豁免」(NO_PROXY)——前者自洽、后者依赖宿主机状态,这正是 CI 环境自洽纪律的一个实例。
- 排障启发式:服务在、curl 通、脚本超时 → 先查代理环境变量,再查服务本身。

## 与其它来源的关系 / Connections

- 例证:[[entities/run-ci]] —— run_ci 的 extras 冒烟以空 ProxyHandler 实现环境无关直连,是其「CI 内自洽」设计的具体案例。
- 例证(纯文本待晋升):CI 环境自洽约定(hermetic-ci)——「不依赖外部环境状态」在网络层的投影;reduce 裁定 rule-of-three 未达(仅本篇),暂由 [[entities/run-ci]] 承载。
- 单提及(纯文本,未建链):extras/serve.py 本地阅读器——仅本篇触及,待晋升。

## 引用片段 / Quotes

> loopback 直连:显式空 ProxyHandler,绕过环境 HTTP(S)_PROXY(否则 127.0.0.1 请求会被 urllib 送进代理,冒烟必然超时)——`tests/run_ci.py` 行 602–603 注释原文。

## 处理记录 / Processing Notes

- 档位:light(source_kind=pitfall,touch 下限 1)。
- 触及/更新页面(reduce 落实,2026-07-20):[[entities/run-ci]](例证)——共 1,满足 light 档下限(W-ING-1)。
- light 档「待晋升」条目(extras/serve.py、hermetic-ci)已由 reduce 登记 followups。
- W-SEC-1:内生 inbox 源,未见指令性注入内容。
