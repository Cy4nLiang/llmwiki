---
title: how-to:新增一门问候语言
date: 2026-07-08
kind: howto
---

# how-to:新增一门问候语言

以新增法语(fr)为例,三步:

1. 在 `locales/` 下新建 `fr.msg`,首行写问候正文(如 `Bonjour, le monde`),
   文件名即语言码。
2. 在 `locales/registry.txt` 追加一行 `fr`,并声明它的回退目标(缺省回退 en,
   即失败时进入 zh → en → ascii 链的 en 档)。
3. 跑 `make greet-test`:冒烟用例会对每门登记语言各请求一次,并强制走一遍
   回退链(包括 ascii 档,防 emoji 类踩坑复发)。

注意:不改 `registry.txt` 只放 `.msg` 文件是无效的——registry 是唯一登记处,
greeter 启动时只加载登记过的语言。
