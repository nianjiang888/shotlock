# ShotLock — 短剧分镜脚本的结构化规范与一致性校验引擎

[English](./README.md) | 中文

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![无第三方依赖](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](./shotlock)

一套分镜脚本规范，加一个零依赖的校验引擎。

大模型写分镜，单看每一镜都挺像回事，连起来全是洞：第五场女主还是长发，第十七场变成短发；上一镜男主在画面左边，下一镜跑到右边；三秒钟的镜头塞了六十字台词，配音根本念不完。ShotLock 把这些翻车现场变成了十五条可检验的规则。

## 赞助位

虚位以待。ShotLock 是 MIT 协议，永久免费——赞助买的是曝光，不是话语权。档位与条款见 [SPONSORING.md](./SPONSORING.md)。

<!-- 首席 / 服务 / 支持三档赞助位售出后挂在这里。 -->

---

## 为什么还要做一个

市面上已有三种做法，都解决不了这个问题：

| 做法 | 给你什么 | 问题 |
|---|---|---|
| 文字大纲 | 一份能读的分场 | 机器读不了，没有任何东西会去查漂移 |
| 表格模板 | 统一的字段格式 | 只能验"填没填"，验不了"连不连贯" |
| 让模型自己复查 | "我看了一遍，没问题" | 模型复查自己的输出，会漏掉和它写的时候一样的东西——因为它还是一次只看一个镜头 |

ShotLock 把两件事拆开：**模型负责写内容，脚本负责守一致性。** 角色和场景在表里定义一次，每个镜头用 id 引用，引擎负责验这些引用有没有漂。

## 快速开始

不需要安装，除标准库外零依赖：

```bash
git clone https://github.com/nianjiang888/shotlock.git
cd shotlock
python -m shotlock examples/good_deck.json
```

```
==============================================================
ShotLock 一致性报告  ·  夜班便利店 · 第一集片段
==============================================================
镜头 5 个 · 角色 2 个 · 场景 1 个
总时长 13.9s / 目标 14.0s

结论：通过
阻断 0 · 严重 0 · 建议 0   共 0 项
==============================================================
```

退出码：0 通过，1 存在达到拦截级别的问题，2 输入错误，3 内部错误。所以它能直接当生成流程里的卡口用。

其他用法：

```bash
python -m shotlock deck.json --html report.html   # 自包含 HTML，Ctrl+P 可存 PDF
python -m shotlock deck.json --json result.json   # 结构化结果
python -m shotlock deck.json --fail-on P1         # 有严重项也返回非零
python -m shotlock deck.json --only SL003,SL008   # 只跑指定规则
python -m shotlock deck.json --skip SL015         # 跳过指定规则
```

## 规则

十五条规则分三级。完整表格和阈值依据见 [references/RULES.md](./references/RULES.md)。

- **P0 阻断**：`SL001` 结构完整性、`SL002` 镜头时长边界、`SL003` 台词语速、`SL006` 角色注册、`SL007` 场景注册
- **P1 严重**：`SL004` 角色外貌漂移、`SL005` 场景连续性、`SL008` 越轴检测、`SL009` 总时长预算、`SL010` 转场合法性
- **P2 建议**：`SL011` 景别节奏、`SL012` 情绪单调、`SL013` 字幕长度、`SL014` 物件闪现、`SL015` 建置镜头

其中三条撑起整个项目：

**SL003 语速。** 中文对白超过 7.5 字每秒，带情绪配音必然吞字。下限定在 2.2 而不是 3.0——早期版本设 3.0，结果误伤了大量正常镜头，因为五个字配两秒是再普通不过的表演节奏，中间有停顿和表演，不算拖。

**SL008 越轴。** 同一场景相邻两镜，两个以上共同角色的画面左右位置整体对调。前一个是全景时不算，因为全景会重设轴线。这条是模型翻车最多的——生成第 n 镜时它根本不知道第 n-1 镜谁站在左边。

**SL011 景别节奏。** 连续四个以上同景别才报，因为正反打本来就是三个连续特写。只有平均单镜超过 3.5 秒时才升到 P1——快切同景别是风格，长镜头堆同景别才叫发闷。

## Gallery

两份报告都由仓库自带样例生成，可以原样复现：

| | |
|---|---|
| [examples/good_deck.json](./examples/good_deck.json) | [报告](./gallery/good_report.html) —— 干净，0 问题 |
| [examples/bad_deck.json](./examples/bad_deck.json) | [报告](./gallery/bad_report.html) —— 15 处故意埋的违规，每条规则一个 |

写坏的那份每个镜头都注明了违反了什么。它存在的意义是让你看到每条规则真的会抓到东西，而不是只在文档里读到。

## 当作 Agent Skill 用

仓库带 [SKILL.md](./SKILL.md)，所以它在 Claude Code、Cursor、Codex、Copilot 里也能当技能跑。循环是：建实体表 → 生成镜头 → 跑校验 → 按报告修 → 复验到 P0 清零。

把它装成技能才是这个校验器真正有用的地方，因为模型可以自己跑完整个循环，不用你把 JSON 来回贴。

## 文档

- [ShotSpec v0.1](./references/SHOT_SPEC.md) —— 全部字段、枚举与约束
- [规则清单](./references/RULES.md) —— 完整规则表与阈值依据
- [SKILL.md](./SKILL.md) —— Agent 工作流

## 参与

规则是这个项目最有价值的部分，而最好的规则都来自真实翻车。见 [CONTRIBUTING.md](./CONTRIBUTING.md)，简短版：先说清楚你实际踩的那个坑，再提能抓住它的规则。

## 配套产品

ShotLock 只管校验分镜，不负责生成。生产环节的另一半在[墨金格](https://www.mojinge.cloud/?utm_source=github_shotlock&utm_medium=readme&utm_campaign=shotlock_v01)（mojinge.cloud）：把故事变成短剧——一句想法进来，一部能拍的剧本出去，分集剧情、人物 / 场景 / 道具资产、每集分镜提示词一次给齐；手上有多长文，走剧本大师全流程改编（导入 → 故事中枢 → 分集大纲 → 改编剧本 → 分镜脚本）。按次付费，失败不扣费，邮箱即账号。

## 协议

MIT。见 [LICENSE](./LICENSE)。
