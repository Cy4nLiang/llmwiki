---
title: 踩坑:emoji 问候在 ASCII 终端乱码
date: 2026-07-05
kind: pitfall
---

# 踩坑:emoji 问候在 ASCII 终端乱码

给问候语加了 👋 emoji 后,CI 里的 dumb terminal 打出 `????`,一条冒烟用例挂掉。

- 根因:回退链只降语言不降字符集,emoji 不在 ascii 档的可打印集合内。
- 修法:ascii 档渲染前过一遍 `strip_non_ascii()`;emoji 只在 zh/en 档保留。
- 教训:回退链的最后一档必须是「任何终端可显示」的最小集,新增装饰字符
  要先问一句「ascii 档怎么办」。
