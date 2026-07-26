# llmwiki — 框架仓开发契约

llmwiki 是「LLM 主导维护的复利型知识库」框架:模板 + 工具 + 评测,content-free;实例经 `tools/init_render.py` 确定性渲染出生。本文件是框架仓自身的开发契约(实例契约由 `CLAUDE.template.md` 渲染,勿混淆)。

## 开发验证

- 全量回归:`python3 tests/run_ci.py`(hello-wiki 夹具全闭环,全量断言;必须全绿才可提交)。
- 工具一律纯 Python 标准库;frozen 档(tools/schema/docs/evals/adapters/extras)改动后必跑 `python3 tools/gen_manifest.py` 重导 MANIFEST(例外:`docs/design-docs/` 开发过程文档不入三档、不随实例分发,豁免口径见 gen_manifest.py 头注)。

## 发布流程

见 `framework/UPGRADING.md`(semver 判级 + 条目格式约定 + 逐版本迁移清单);贡献与回流通道见 `CONTRIBUTING.md`(两档 PR 政策 / 回流格式 / 脱敏 checklist)。规则 ID 总表:`framework/RULES.md`。

<!-- llmwiki:pointer:begin(本段由 llmwiki 维护;升级时整段替换,请勿手改)-->
## 知识库(llmwiki)
- Boot:domain 知识问题先读 `knowledge/wiki/_map.md` 按决策表路由;工作流见 `knowledge/.claude/skills/`。
- 会话收尾检查点:本次会话是否产生值得留底的踩坑/约定/决策?有则投递 `knowledge/raw/inbox/<date>-<slug>.md`(frontmatter:title/date/kind ∈ adr|pitfall|decision|howto)。投递≠整合、不打断任务主线(W-CAP-1);整合由下次 wiki-sync 报 pending 后走 light 档。
<!-- llmwiki:pointer:end -->
