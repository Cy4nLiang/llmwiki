---
title: run_ci.py(框架全量回归 / hello-wiki 夹具)
description: "查『框架 CI 都断言什么』『h0 造版夹具怎么验证发版流程』『extras 冒烟为何要空 ProxyHandler』时读本页;0.3.0 时点 119 断言(参考实例 newpj4 实测)。"
type: entity
created: 2026-07-20
updated: 2026-07-20
tags: [cluster/ci, tool, hello-wiki]
status: draft
sources: ["[[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]]", "[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]]", "[[sources/2026-07-20-howto-release-framework-version]]", "[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]]"]
aliases: ["run_ci", "框架 CI", "hello-wiki fixture CI"]
verified: 2026-07-20
---

# run_ci.py(框架全量回归 / hello-wiki 夹具)

## 概述

`tests/run_ci.py`:框架仓全量回归——hello-wiki 夹具全闭环(渲染新实例 → lint → sync → 升级四路径),0.3.0 时点 **119 断言**(参考实例 newpj4 实测);发版六步的第 5 步,必须全绿才可提交。hello-wiki CI 夹具机制来自 plugin 派嫁接(6 项嫁接之⑤)。(例证:[[sources/2026-07-20-adr-form-factor-hybrid-template-repo]])

## 关键事实

- **phase_lint 零漂移断言**:对每个新渲染实例跑 `lint_wiki.py --manifest --json` 并断言 `errors == 0`(「零 fork 漂移」,行 258–260,仓内核实)——框架仓 MANIFEST 一旦陈旧,CI 立即红,把「忘跑 gen_manifest」从静默隐患变成当场红灯。(强化:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])
- **h0 造版夹具 build_fw_next**:按「改动 → VERSION bump → UPGRADING 顶插 → gen_manifest 重导」固定顺序模拟造版(行 464、487,仓内核实),再走升级四路径——**发版流程本身被测试覆盖**,流程改了测试先红。(例证:[[sources/2026-07-20-howto-release-framework-version]]、[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])
- **extras 冒烟 loopback 直连**:对 `127.0.0.1` 显式构建空代理 opener(`ProxyHandler({})`)绕过环境 `HTTP(S)_PROXY`(行 602–604,仓内核实)——urllib 默认代理链不豁免 loopback,不绕则配置了系统代理的机器上冒烟必然超时;冒烟 `timeout=3`、整体 deadline 30s。(例证:[[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]])
- **CI 环境自洽原则**(hermetic-ci,纯文本待晋升):绕代理用进程内显式禁用(空 ProxyHandler)而非环境变量豁免(NO_PROXY)——前者 CI 内自洽、不依赖宿主机状态。(例证:[[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]])

## 关系网络

- [[concepts/framework-upgrade-protocol]] —— 发版第 5 步;升级四路径的验证场。
- [[entities/gen-manifest]] —— MANIFEST 新鲜度的 CI 兜底。
- [[entities/lint-wiki]] —— phase_lint 逐实例调用对象。
- [[syntheses/framework-design-evolution]] —— 嫁接项⑤的落地物。

## 时间线

- M1–M3 全绿推进;0.3.0 时点 119 断言(参考实例 newpj4 实测,断言数随版本演进)。
- M2:stale-manifest fork 误报踩坑后,phase_lint 零漂移断言 + h0 固定顺序成为兜底。(演进:[[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]])

## 来源

- [[sources/2026-07-20-pitfall-local-proxy-intercepts-loopback]](例证)· [[sources/2026-07-20-pitfall-stale-manifest-fork-false-positive]](强化)· [[sources/2026-07-20-howto-release-framework-version]](例证)· [[sources/2026-07-20-adr-form-factor-hybrid-template-repo]](例证)

## 待补充

- 行号锚点(258–260 / 464 / 487 / 602–604)会随版本漂移,引用时以当次仓内核实为准。
- extras/serve.py 本地阅读器仅单源提及,待晋升。
