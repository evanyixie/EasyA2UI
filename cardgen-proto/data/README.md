# data/ — 原始数据

**这是全项目唯一一份金标数据。** 论文侧不复制、不另存，只按 commit + 清单指针引用。

```
data/
├── MANIFEST.sha256                      # 98 个文件的哈希清单
└── gold/
    ├── 生成卡片的DSL结果/                 # qN.jsonl：金标终产物（49 个）
    └── 生成卡片的中间环节的输入数据/       # qN_artifact.md：人验中间产物（49 个）
```

共 98 个文件 / 1.1 MB。q28 / q36 / q37 三张特殊效果卡已下线，故为 49 而不是 52。

## 为什么放在原型里

数据是**输入**，不是产物。原型必须能 clone 下来直接跑通测试、重建基准、做金标比对——数据不在仓库里，它就不是一个完整项目。论文侧需要的是「结果」，那些进 `paper/data/`。

## 怎么校验没被改动

```bash
cd cardgen-proto/data && sha256sum -c MANIFEST.sha256
```

数据一改，清单立刻对不上。论文里每个数字都随附 `cardgen-proto@<commit>` 与清单哈希，因此"这批结果对应哪一版数据"永远可判定——不需要第二份拷贝。

## 谁在读它

| 工具 | 读什么 | 干什么 |
|---|---|---|
| `tools/gold_dataset.py` | 两个子目录 | 构建 `fixtures/gold_pairs.json` + `fixtures/batch_queries.json` |
| `tools/build_content_oracle.py` | `生成卡片的DSL结果` | 抽"应有事实集" → `fixtures/content_oracle.json` |
| `tools/diff_gold.py` | `生成卡片的DSL结果` | 逐卡元素级比对 |
| `tools/check_layout.py` | `生成卡片的DSL结果` | 金标几何基线 |
| `tools/gen_card_compare.py` | `生成卡片的DSL结果` | 并排渲染页 |
| `tools/extract_skeletons_from_cards.py` | 两个子目录 | 骨架区划聚类探索 |

## 已知事项

- 三张已下线卡的旧批跑产物仍在 `runs/batch/`（52 张那几批），`diff_gold` 会自动跳过金标缺失的卡。
- 敏感信息：手机号/邮箱/身份证正则扫描均为假阳性（`14285714285` 是经典假号，`1792045xxxx` 是时间戳型 ID）；人名与公司名仍需人工过一遍（待办 H-06）。
- 子目录保留中文名：它们准确描述了内容，且被 6 个工具引用，改名只会增加回归面。
