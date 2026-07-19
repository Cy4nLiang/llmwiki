# 适配器编写指南 / fetcher-contract.md

> 面向**实例作者**:你要给自己的 wiki 接一条新采集管线,从骨架出发 30–60 分钟可完成。
> 合同条款的权威文本在 `adapters/CONTRACT.md`(本文只讲怎么做,条款冲突以 CONTRACT 为准);
> sync 如何调度见 `tools/sync.py` docstring。2026-07-19,framework v1.0。

## 0. 先想清楚:你的源是哪一型?

| 问题 | 答案 → 型 |
|---|---|
| 源是「一堆会不断新增的独立文章/文档」? | **pull**(`article_fetcher.skeleton.py`) |
| 源是「一份会整体演进的滚动文档」(CHANGELOG/规范/runbook 总纲)? | **rolling**(`rolling_source.skeleton.py`) |
| 内容由人或 CI 直接放进 raw 目录,没有「抓」这回事? | **push**(直接用现成的 `local_notes.py`,不用写代码) |

判据是**内容的增长方式**,不是来源介质。一个网站可以同时喂两条管线
(文章列表走 pull,其 changelog 页走 rolling)。

## 1. 从 skeleton 出发(pull 型为例)

```bash
cp <框架>/adapters/article_fetcher.skeleton.py  tools/adapters/my_docs.py
```

1. **改常量区**(文件顶部):`PIPELINE` / `RAW_SUBDIR` / `PREFIX` / `DEFAULT_KIND` /
   `LISTING_URL` / `UA`。前三者必须与你即将写进 `wiki.config.json` 的
   `pipelines[]` 条目**逐字一致**——sync 靠 config 调度,pending 靠
   `raw_dir` + `prefix` + 文件 stem 对齐源页名,任何一处错位都表现为
   「永远 pending」或「pending 永远为空」;
2. **注册管线**(`wiki.config.json`):

   ```jsonc
   { "name": "my-docs", "kind": "pull", "raw_dir": "raw/my-docs", "prefix": "md-",
     "adapter": "tools/adapters/my_docs.py", "source_kinds": ["reference"] }
   ```

3. **先验管道再写抓取**:此时就跑一遍

   ```bash
   python3 tools/adapters/my_docs.py discover --demo --root .
   python3 tools/adapters/my_docs.py fetch --root .
   python3 tools/adapters/my_docs.py status --root .
   python3 tools/sync.py status --root .        # demo 条目应出现在 pending
   ```

   全链路绿了,才动真抓取(骨架的 manifest/raw 写盘/幂等/退出码都已合规,你只补两个函数);
4. **实现 `discover_items()`**:抓清单页/RSS,返回
   `[{"slug","url","title","date"}, …]`——只发现不抓正文,廉价可频繁跑;
5. **实现 `fetch_article_body(item)`**:抓单篇正文转 markdown,顺手回填
   `item["title"]/["date"]/["authors"]`;非文章页返回 `None`(计 skip 不算失败);
6. **清理 demo 产物**:删 `raw/<dir>/` 下 demo 文件与 `state/<pipeline>.manifest.json`
   里的 demo 条目(或整个删掉台账重新 discover——pending 不依赖台账,删了无损);
7. 跑 `python3 tools/sync.py --only=my-docs --root .` 验收全链路。

rolling 型同理:拷 `rolling_source.skeleton.py`,实现 `fetch_snapshot()`
(+ 可选 `aux_dates()`);push 型零代码,见 `local_notes.py --help`。

## 2. 合规自查(提交前过一遍)

完整清单在 `adapters/CONTRACT.md §11`,其中**最容易违反的五条**:

1. `--root` 必收且一切路径以之解析 —— 在任意 cwd 下跑一次确认;
2. 只写自己的 `raw/<dir>/` + `state/`;临时件全进 `state/tmp/`;
3. manifest 六必填:`slug / url(push 可空)/ title / date / fetched / raw_file`;
4. 幂等:连跑两次 fetch,第二次应 0 抓取;`--force` 才重抓;
5. 退出码:成功 0 / 失败或发现问题 1 / 用法配置错 2(sync 靠它裁决管线成败)。

## 3. 常见坑

- **prefix/raw_dir 与 config 不一致**:pending 判定是
  `raw/<dir>/<stem>.md ↔ wiki/sources/<prefix><stem>.md` 的目录 diff,常量拼错的
  症状是 ingest 完了 sync 还报 pending。改常量或改 config,二选一,别两头都改;
- **把清洗做过头**:raw 层要「干净的正文」,不是「摘要」——TL;DR/取舍是 agent 在
  ingest 时做的(W-ARCH-2)。反之 faithful(rolling)一点都不许清洗;
- **rolling 忘了 dated 分离**:把日期注进 faithful 快照 = 污染事实源(raw-wins
  裁决靠它),日期/版本标注永远写 `<slug>.dated.md` 派生件;
- **digest 断链**:rolling 刷新后 agent 忘了把新 sha256 回写源页
  `rolling_digest:` → 该源永远 pending。刷新滚动源页的最后一步就是回写 digest
  (适配器 `status` 会打印当前值,拷走即可);
- **依赖静默失败**:用了 bs4/playwright 却没附 `requirements.<name>.txt`,别人的
  实例上 import 爆栈。按 CONTRACT §9:文件头声明 + import 失败给修复提示后 exit 2;
- **凭证入库**:token 写进适配器源码或 config → 违反 W-SEC-2。只读环境变量,
  README 里写清需要哪个变量;
- **demo 数据忘删**:`--demo` 产物长得和真数据一样(同构是特性),会被 sync 当真
  pending 报出来。体验完删 raw 里的 demo 文件即可;
- **忽略「连续空页即停」**:discover 翻页无上限 + 站点改版 = 死循环。参考实例
  newpj4 的做法:安全上限 + 连续两个无新页即停;
- **在 fetch 里写 wiki/**:任何「顺手建源页」的冲动都是越界(W-ARCH-2)——
  源页七段骨架需要理解与取舍,那是 agent 的 ingest,不是采集。

## 4. 分发与升级语义

- 适配器属 **instance 档**:升级框架永不触碰 `tools/adapters/`;
- 写得好的通用适配器欢迎回流:脱敏(去内部 URL/专名,W-SEC 系)后 PR 到框架仓库
  `adapters/`,进 MINOR 版;
- skeleton 本身是 frozen 档发布物:别在框架目录里改它,拷出去再改。
