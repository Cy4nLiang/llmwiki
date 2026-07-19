---
title: "踩坑:本机 HTTP 代理拦截 127.0.0.1 请求,serve 冒烟必然超时"
date: 2026-07-20
kind: pitfall
---

# 现象

CI 冒烟 `extras/serve.py`(起本地阅读器后 GET `http://127.0.0.1:<port>/api/status`)在配置了系统级 HTTP(S)_PROXY 的开发机上必然超时:服务明明起来了,urllib 却连不上。

# 根因

Python `urllib.request` 默认读取环境变量 `HTTP_PROXY` / `HTTPS_PROXY` 构建代理 opener,**loopback 地址不豁免**——对 127.0.0.1 的请求也被送进代理,而本机代理通常不会回连 loopback 高位端口,请求就死在代理里。

# 修法(已落位)

冒烟请求显式构建**空代理** opener 直连:

```python
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
opener.open("http://127.0.0.1:%d/api/status" % port, timeout=3)
```

`ProxyHandler({})` 传空字典 = 禁用一切代理(含环境变量注入),与设置 NO_PROXY 相比不依赖外部环境状态,CI 内自洽。

# 教训

一切对 loopback 的程序化 HTTP 请求都应显式绕过代理;「本机能 curl 通但脚本超时」优先怀疑代理环境变量。

# 出处

- `llmwiki/tests/run_ci.py` phase_extras(注释原文:「loopback 直连:显式空 ProxyHandler,绕过环境 HTTP(S)_PROXY(否则 127.0.0.1 请求会被 urllib 送进代理,冒烟必然超时)」,行 602–604 附近)。
