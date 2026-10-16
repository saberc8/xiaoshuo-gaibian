# 深度重写：流程、架构与开源调研

调研日期：2026-10-15。本文对应续章的 `mode=deep_rewrite` 功能。

## 产品流程

从已完成、已冻结的改编项目点击 **深度重写**，建立一个独立项目。作者先在页面编辑重写要求和框架，锁定后复制任务到 Codex。Codex 当前会话通过 MCP 完成创作，页面展示同一份持久数据。

```text
已冻结改编版
  → 新建深度重写项目
  → 用户编辑并锁定重写条件
  → 全稿结构诊断
  → 全书重构方案
  → 按新大纲写正文
  → 九项逐章审查
  → 全书三方差异审查
  → 独立版本与导出
```

用户可以约定八类变化：人物动机、人物关系、核心冲突、情节结构、叙事视角、主题、结局、语言表达。至少选择三个结构维度，其中包含核心冲突或情节结构；语言润色不计入这三个结构维度。

新方案允许合并、拆分、删减、重排章节。全稿诊断必须覆盖上版所有章节；最终输出章数可与上版不同。原章必须被新章引用或记明删减原因。新稿每章必须落实至少一个结构维度。

## 三层约定

1. **重写需求 `brief.rewrite`**：作者选定的变化维度、叙事组织、结局方向和避免事项。`brief.preserve` 记录保留底线。
2. **全书方案 `plan.rewrite_design`**：每个约定维度的原有结构、新设计、改变原因、落实章节，以及原著和上版两类引用。世界规则、人物动机和分章节拍继续使用现有 `bible` / `units`。
3. **全书审查 `rewrite_audit`**：绑定所有稿件修订号与正文分块；对每个“维度 × 约定目标章”提交原著、上版、新稿的逐字证据及判断。不能只为一个维度举一章例子就跳过其余目标章。

创建时可沿用上版的时代、地点、命名原则，作者可以编辑；上版的人物映射与因果主线不会自动成为新稿的冻结约束。这样既能延续已选择的文化背景，也允许重新组织角色和故事。

## 状态与恢复

复用原改编状态机，新增 `auditing`：

| 状态 | 深度重写中的含义 | 推进条件 |
| --- | --- | --- |
| `framing` | 编辑重写需求与框架 | 保存并锁定框架 |
| `analyzing` | 诊断上版全稿 | 每块分析含结构观察与逐字引用 |
| `planning` | 设计全书结构 | 全部分析完成，重构维度及证据完整 |
| `writing` | 按新大纲重写 | 依章节顺序提交完整正文及连续性记忆 |
| `reviewing` | 逐章审查 | 全稿有效，当前修订的九项检查通过 |
| `auditing` | 全书差异审查 | 全修订、全分块、全维度及目标章的证据完整且判断通过 |
| `ready` | 可以保存版本 | 全部审查对应当前稿件 |
| `completed` | 独立版本已冻结 | 可导出 EPUB / TXT / Markdown / JSON |

- `get_adaptation` 返回 `next_action` 和当前 `revision`，中断后可据此恢复。
- 所有写入使用 `expected_revision`，PostgreSQL 事务行锁保护更新。
- 同一份成功提交可幂等重试；不同内容使用过期 revision 会被拒绝。
- 改动前章会使后章连续性记忆和全部逐章审查失效；任何稿件修改都会使全书差异审查失效。
- 差异审查失败时回到相关正文修订、逐章重审、全书复审。若需要推翻已经写作的大纲，应打开上版另建深度重写项目，保留当前方案和稿件。
- 大纲保存前可修改需求与框架，修改后清空依赖它的诊断并解除锁定；已写正文后不能静默替换方案。

## 数据模型

使用现有 PostgreSQL `records` 表中的 adaptation 记录，不增加第二套数据库，也不把上版重新导入成一份虚假原著。

```text
original book
  └─ completed adaptation
       └─ deep_rewrite adaptation
            parent_project_id
            parent_release_sha256
            original_chapter_ids
            original_source_sha256
            brief.rewrite
            plan.rewrite_design
            units + reviews
            rewrite_audit
            immutable release
```

上版冻结稿作为虚拟参考书读取：章节 ID 使用上版 unit ID，段落 ID 稳定生成。读取时校验上版冻结快照的 SHA-256。最初原著通过根 `book_id` 和 `original_chapter_ids` 访问。再次深度重写时，父版本指向最近的完成版，最初原著引用保持可追溯。

JSON 导出冻结来源链、需求、框架、分析、重构设计、正文和审查报告。EPUB / TXT / Markdown 导出新稿。原著与父版本保留。

## MCP 与 HTTP

新增两个 MCP 工具，总数为 22：

- `create_deep_rewrite(project_id, name, brief)`：从完成版建立独立重写项目，要求 `brief.rewrite`。
- `submit_deep_rewrite_audit(project_id, audit, expected_revision)`：提交全书三方差异审查。

现有工具继续承担框架、诊断、大纲、正文、逐章审查与冻结。`get_adaptation_guide` 新增 `rewrite`、`rewrite_requirements`、`rewrite_design`、`rewrite_audit`。

`get_adaptation_context` 的深改专用 stage：

- `original`：分页读取最初原著。
- `baseline`：分页读取上版冻结稿。
- `audit`：分页读取全书新稿，并返回全部稿件修订号与必审分块。

`analysis` 使用上版全文，新增必填的结构观察 `structural_observations`。`plan` 必须包含 `rewrite_design`。逐章 review 在既有七项检查外，增加 `structural_change` 和 `independent_expression`。

HTTP 对应入口：

```text
POST /api/adaptations/{id}/deep-rewrites
GET  /api/adaptations/{id}/source-chapters/{chapter_id}
PUT  /api/adaptations/{id}/rewrite-audit
```

更新工具代码后需重新加载 Codex 中的 `novelstudio` MCP 连接，才能发现新增工具；连接 ID 和后端端口保持原配置。

## GitHub 开源调研

读取仓库 README、公开文件及许可信息后，采用适配当前工作台的流程方法，没有安装这些仓库，也没有复制其实现代码。

| 仓库 | 调研版本与许可 | 可借鉴的方法 | 本项目的取舍 |
| --- | --- | --- | --- |
| [DOC](https://github.com/yangkevin2/doc-story-generation) | `9d727cdbae40c72169ab03b729bff4419a113dac`，MIT | 详细分层大纲控制长故事，让写作服从预先设计的情节 | 采用先规划再写作；不引入其研究模型和控制器训练依赖。README 指向后续 [doc-storygen-v2](https://github.com/facebookresearch/doc-storygen-v2) |
| [Long-Novel-GPT](https://github.com/MaoXiaoYuZ/Long-Novel-GPT) | `107c31e54686947a6d00404e332475a60b66e630`，本次未确认明确许可证 | 导入小说、剧情人物拆解、检索相关段落、正文与纲要同步 | 借鉴分析—纲要—正文联动；通过现有分页上下文和连续性记忆实现，不复制代码 |
| [AI_NovelGenerator](https://github.com/YILING0013/AI_NovelGenerator) | `da3cbbe1c579e855c52562c7cd3f494aa1587c0b`，AGPL-3.0 | 当前主线的卷／篇章／场景／章节规划、人物关系及章后状态 | 借鉴层级规划与状态记录；保留当前 PostgreSQL 和 MCP 架构，不再引入其 MongoDB 应用。该项目已重写，旧实现保存在 old 分支 |
| [novel-rewriting-toolkit](https://github.com/sssst1118/novel-rewriting-toolkit) | `11e851f632966c2efc52b182644bd352a9c8f5fc`，MIT | 提炼原稿、重构故事弧、再写正文的分阶段流程 | 借鉴全书重构阶段；仓库主要是提示词与手册，不是即插即用的后端服务；不沿用具体长篇工程的硬编码参数 |
| [ai-novel-rewriter](https://github.com/hollis-openlab/ai-novel-rewriter) | `22889d17a0c347c8cf44fcfac23c04ee0f60acc7`，AGPL-3.0 | 场景拆解、章节大纲、串行滚动改写、review 与组装 | 借鉴分步重写和修订循环；片段改写本身不足以替代全书结构重构 |

选择自行集成流程，是因为现有工作台已经有来源、条件、版本、正文和 MCP 状态管理。再嵌入另一套完整小说服务会造成数据和生成职责重复。此次增加一个明确的重构层与全书审查门，继续让 Codex 负责创作。

## 判断范围

后端能确定性验证证据是否真实、是否覆盖全文和全部约定、是否对应当前修订，以及原样提交上版单章正文的情况。人物动机和情节变化是否足够充分，仍是有证据支持的创作判断，需要作者复核。

此功能不输出“原创率”或“平台必过”的结论。开源仓库中的宣传语也不作为能力依据。交付物是能够逐项检查的结构重构与创作差异记录。
