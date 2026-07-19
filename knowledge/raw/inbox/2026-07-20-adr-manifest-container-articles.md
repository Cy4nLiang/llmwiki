---
title: "ADR:适配器 manifest 容器冻结为 {\"articles\": {slug: {...}}}"
date: 2026-07-20
kind: adr
---

# 决策

0.3.0(M3)起,fetcher 适配器台账 `state/<pipeline>.manifest.json` 的容器形状 **v1 冻结**为:顶层 `articles` 键,条目以 slug 为键的对象——`{"articles": {slug: {...}}}`。

# 理由

- 多适配器(实例自写)与框架工具(build_site/sync)之间需要一个稳定的读取合同;容器键名漂移(如有的适配器写 `items`)会让 build_site 静默读不到条目;
- slug 作键天然去重、幂等可续(已抓跳过按键查),比 list 容器省一次线性扫描。

# 兼容与迁移

- build_site 兼容读取历史形态:顶层 `{"articles": dict|list}` 等旧样均可读,但 `articles` 以外的容器键名(如 `items`)不被识别——新适配器一律用冻结形状;
- 随框架发布的 `local_notes.py` 在 0.3.0 完成容器键 items→articles 迁移,**载入时自动迁移**旧台账(见 UPGRADING 0.3.0 frozen 覆盖清单);
- manifest 六必填字段:slug / url(push 可空)/ title / date / fetched / raw_file;合规自查清单里有对应打勾项。

# 出处

- `llmwiki/adapters/CONTRACT.md` §4(推荐容器键 v1 冻结、容器兼容性说明)、§11 自查清单;
- `llmwiki/framework/UPGRADING.md` 0.3.0(「CONTRACT 冻结 manifest 容器推荐形状」「local_notes 容器键 items→articles,载入自动迁移」)。
