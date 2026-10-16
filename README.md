# 续章 · XUZHANG

以参考小说为起点的改编工作台。用户在网页建立项目、编辑并锁定创作条件，Codex 通过 MCP 读取同一份约定，持续完成原著分析、故事设定、大纲、逐章改写、全文审查和独立版本导出。

React / TypeScript + FastAPI / Python + PostgreSQL。原始 EPUB / TXT 保存在本地，项目条件、进度、正文和冻结版本保存在 PostgreSQL。网页与 MCP 调用同一个应用服务。

## 使用流程

1. 在 **原著书架** 导入 EPUB / TXT，补充原作、版本、译者和来源信息。
2. 在 **改编项目** 新建项目，明确选择参考原章，填写想法、方向、读者、语言、目标章数与篇幅。
3. 打开项目的 **改编条件**，编辑时代、年份、地点、史实与虚构边界、姓名与身份、制度迁移、剧情因果、允许重构部分和禁止元素。
4. **保存框架草案** 可保留条件继续编辑；**保存并锁定改编条件** 后，才能点击 **交给 Codex 改编**。
5. 复制交接任务，发送到已连接 `novelstudio` MCP 的 Codex 会话。任务引用已有项目，要求读取最新约定和修订号，并从 `next_action` 恢复。
6. 页面每 4 秒同步进度，可查看 **创作总览 / 人物与世界 / 大纲与正文 / 创作记录**。完成后下载 EPUB、TXT、Markdown 或 JSON 创作记录。

项目列表支持按项目名、原著和想法搜索，按阶段筛选、按时间或名称排序。每个项目都有可重新打开的独立网址。已完成项目可 **以此创建新项目**，复制需求、参考范围和框架，新方案需重新锁定，正文和审查各自独立。

所有新项目必须经过前置框架。姓名和别名属于改编框架的一部分；产品只保留完整改编工作流，独立的人物替换、替换预览和改名审查功能已移除。

## 先完整翻译，再解析改编

创建项目时可选择 **先逐章全译**。流程是 **翻译约定与译名表 → 一对一目录 → 逐章逐段完整翻译 → 对照审校 → 冻结译稿 → 全稿解析 → 改编框架与重构 → 独立重写**。用户可以在页面编辑翻译约定，再在重写项目编辑时代、姓名、身份与剧情条件，分别锁定后交给 Codex。

全译阶段保留原作背景与信息顺序，原章和译章严格按目录一一对应，不合并、拆分、重排或删章。每个正文段落对应一段译文，`source_paragraph_ids` 与译文段落等长且顺序一致。篇幅服从原章信息量，不使用固定目标字数压缩译文。章节上限为 200，《基督山伯爵》的 117 个正文章节可全部保留。

**目录与译文** 页逐段并排显示原文与译文。可确证的重复章标题、Gutenberg 插图编号和显式插图说明另存版面记录，原始文件和原段落 ID 不变。覆盖校验能发现漏段、并段、重复和错序；译意准确与细节完整仍须 Codex 逐段对照，显式提交 `translation_fidelity` 和 `translation_completeness` 审校。

MCP 使用 `get_adaptation_guide(section="translation")`，然后 `create_adaptation(mode="translation", ...)`；`brief.preset` 为 `custom`，`target_units` 等于所选原章数。此阶段不要求先提交故事结构分析。冻结全部所选译稿后，使用现有 `create_deep_rewrite` 创建独立项目；`analysis` 解析冻结中译稿，`original` 仍可读最初英文原作，重构和差异审查保留三方证据及原始文件指纹。直接改编流程继续可用。

首章真实试作位于 `examples/public-domain/monte-cristo/translation-pilot/`：英文原章 126 个正文段落 → 126 段、5,593 字符的新中译 → 《长夜归舟·未签的任命》136 段、5,962 字符的民国重写。两份独立冻结版均可在项目列表打开；试作范围仅第一章，不代表 117 章全本完成。

## 改编完成后的深度重写

已完成项目可点击 **深度重写**，建立独立项目。先在页面编辑要改变的维度、保留底线、叙事视角与顺序、结局方向、避免沿用的内容及目标篇幅，再核对并锁定框架，点击 **交给 Codex 深度重写**。

流程为 **全稿诊断 → 全书重构 → 正文重写 → 九项逐章审查 → 全书差异审查 → 独立版本**。可以合并、拆分、删减和重排章节，不要求与上版一一对应。页面新增 **重构与差异**，展示每项变化的前后设计、原因、目标章节，以及原著／上版／新稿的逐字依据。

至少选择三个结构维度，包含核心冲突或情节结构；语言润色不计入三个结构维度。全稿和全书审查必须完整覆盖。修改正文会使旧审查失效，当前全部审查通过后才能保存新版本。

新项目通过冻结版本和内容指纹引用上版，保留最初原著的来源链；旧版本继续可读、可导出。该流程提供可复核的创作差异，不给出原创率或平台判定保证。

架构、MCP 字段与 GitHub 选型依据见 [深度重写设计与开源调研](docs/deep-rewrite.md)。

## 条件与版本规则

- 大纲保存前，用户可以修改需求、参考范围和框架。需求或范围变更会清空依赖旧条件的原著分析，并解除框架锁定；更改项目名称本身不会清空分析。
- 框架保存为草案时不能交接；已锁定框架在页面处于调整状态时，也必须先保存锁定或取消调整再交接。
- 所有写入携带 `expected_revision`。PostgreSQL 行锁与修订号共同保护并发更新。页面编辑过程中出现其他更新，会提示重新载入，避免覆盖新约定。
- 大纲保存后，前置条件冻结。第一份正文保存后，设定大纲冻结。改变方向可复制为新项目。
- 修改前文章节会使后章连续性记忆及全部审查失效，须顺序更新后章并重新审查。
- 发布后的正文、来源、条件、分析和审查随版本冻结。原作与其他项目保留。
- 迁移前已完成的旧项目按原样保留，包括早期没有前置框架的作品；新建项目不能绕过框架。

MCP 提供数据和工作流，创作由 Codex 当前会话执行。网页上的交接按钮生成可复制的任务，不会在后台自行启动模型，也不需要在后端配置额外的 LLM API Key。

## 本地运行

需要 Python 3.12+、Node.js 20.19+ / 22+、npm、PostgreSQL 16+。推荐使用 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
npm ci --prefix frontend

# 在已启动的 PostgreSQL 中创建数据库（仅首次）
createdb xuzhang

# 没有 .env 时创建；保留已有的本机配置
cp -n .env.example .env

# 同时启动前后端，Ctrl+C 停止两者
uv run python scripts/dev.py
```

`.env`：

```dotenv
NOVEL_DATABASE_URL=postgresql://localhost/xuzhang
NOVEL_DATABASE_SCHEMA=public
NOVEL_API_URL=http://127.0.0.1:8010
# 可选：原始文件存储目录
# NOVEL_DATA_DIR=/absolute/path/to/xuzhang-data
```

数据库连接使用本机 PostgreSQL 角色。需要账号口令时在连接字符串中设置，仅保存在本机环境配置中。服务启动时创建 `records` 表和索引，数据库本身需预先创建。

- [项目列表](http://127.0.0.1:5173/#/projects)
- [原著书架](http://127.0.0.1:5173/#/library)
- [连接与设置](http://127.0.0.1:5173/#/settings)
- [API 文档](http://127.0.0.1:8010/docs)

也可以分别启动：

```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload
npm run dev --prefix frontend
```

端口更改时同步设置 `NOVEL_API_URL`，或使用 `scripts/dev.py --api-port 端口`。前端代理与 MCP 应指向同一个后端。生产构建可直接由 Python 提供：

```bash
npm run build --prefix frontend
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
```

此时访问 [http://127.0.0.1:8010](http://127.0.0.1:8010)。这是本机工作台，目前没有多人账号和鉴权。

## 从 SQLite 迁移

先停止旧后端，避免迁移期间产生新写入；准备 PostgreSQL 数据库并配置 `.env`，再执行：

```bash
uv run python scripts/migrate_sqlite.py
```

默认读取 `data/studio.sqlite3`，先用 SQLite 在线备份接口生成 `data/migration-backups/` 快照，然后在一个 PostgreSQL 事务中插入并逐条校验全部记录。原始小说文件继续保留在数据目录。

- 完全相同的目标记录会跳过，可安全重放未发生变化的迁移。
- 目标已有同 ID 的不同内容时整批回滚，避免覆盖 PostgreSQL 中更新的项目。
- 原 SQLite 文件、备份和原著文件均保留。开始使用 PostgreSQL 后，SQLite 仅作为迁移前快照。

可通过 `--source` 和 `--backup-dir` 指定源文件和备份目录。运行中的项目数据应使用 `pg_dump` 备份，并同时备份 `NOVEL_DATA_DIR` 中的原始文件。

## 连接 Codex MCP

```bash
uv run python scripts/configure_mcp.py --write
```

该脚本将本机 Python、项目目录和后端地址写入项目的 `.codex/config.toml`，保留其他配置。项目移动或后端端口变更后重新运行；重新加载 MCP 连接以发现工具更新。连接 ID 保持为 `novelstudio`。

```toml
[mcp_servers.novelstudio]
command = "/absolute/path/to/project/.venv/bin/python"
args = ["-m", "backend.app.mcp_server"]
cwd = "/absolute/path/to/project"
startup_timeout_sec = 20
tool_timeout_sec = 120

[mcp_servers.novelstudio.env]
NOVEL_API_URL = "http://127.0.0.1:8010"
```

现有 22 个工具：

| 工具 | 用途 |
| --- | --- |
| `list_books` / `get_book` / `read_chapter` | 原著列表、目录、章节段落 |
| `import_novel` | 导入指定本机 EPUB / TXT 绝对路径 |
| `get_source_catalog` / `set_book_source` | 十部经典来源入口与版本信息 |
| `get_adaptation_guide` | 工作流与各阶段 JSON Schema |
| `create_adaptation` / `list_adaptations` / `get_adaptation` | 建立、跨原著查找、恢复项目；可按 `book_id` 筛选 |
| `save_adaptation_framework` | 按用户要求保存或锁定框架 |
| `get_adaptation_handoff` | 读取页面锁定条件后的 Codex 交接任务 |
| `get_adaptation_context` | 分页读取当前阶段的来源、设定、记忆和待办 |
| `submit_source_analysis` | 提交原著分析与逐字证据 |
| `save_adaptation_plan` | 保存人物、世界规则、能力系统与章节大纲 |
| `submit_adaptation_draft` / `read_adaptation_unit` | 按顺序写稿、修订与读取完整正文 |
| `submit_adaptation_review` | 当前稿件的七项检查及问题记录；深度重写为九项 |
| `create_deep_rewrite` | 从冻结改编版建立独立深度重写项目 |
| `submit_deep_rewrite_audit` | 绑定全稿修订与分块，提交全书三方差异审查 |
| `finalize_adaptation` / `get_adaptation_export_url` | 冻结独立版本，获取作品或创作记录 |

```text
页面编辑需求和框架 → 锁定 → 交接已有项目
  → analyzing：分页读原著，逐块提交原文证据
  → planning：保存人物、世界规则和目标章节大纲
  → writing：按章节顺序写正文并更新连续性记忆
  → reviewing：全文逐章审查，修稿后更新后章并重审
  → ready：所有当前稿件审查通过
  → completed：冻结版本并导出
```

新项目的七项检查：姓名与称谓、世界规则、情节因果、前后连续性、创作需求、来源对应、框架与时代。后端确定性校验范围、证据、覆盖、禁用词和修订一致性；文学质量与历史语境由 Agent 判断并由用户复核。每章字符数须在目标的 50%–180% 内，避免将梗概当成完整正文。

## 数据与代码结构

PostgreSQL 使用 `records(kind, id, payload JSONB, sequence, updated_at)` 保存原著与项目聚合，主键为 `(kind, id)`；索引支持按类型及 `book_id` 查询。连接池复用连接，`SELECT … FOR UPDATE` 将项目更新串行化，事务失败时回滚。回调中的嵌套读取复用同一连接，避免锁等待时耗尽连接池。

```text
backend/app/
  store.py              PostgreSQL / JSONB、连接池与事务行锁
  migration.py          旧 SQLite 数据备份与一次性迁移
  service.py            原著导入、目录、来源信息与章节读取
  epub.py / bookio.py    EPUB 解析、TXT 编码识别、独立改编 EPUB
  adaptation.py         改编状态机、条件交接、证据与版本校验
  rewriting.py          深度重写来源链、全书重构与三方差异审查
  translation.py        忠实全译范围、章节与段落对齐、版面信息分离
  adaptation_models.py  需求、框架、设定、正文、审查等结构模型
  catalog.py            十部经典素材入口与改编方向
  main.py               网页与 MCP 共用的 HTTP API
  mcp_server.py         STDIO MCP → HTTP 网关
frontend/src/
  App.tsx / Pages.tsx    项目路由、项目列表、原著书架、连接设置
  Adaptation.tsx         项目详情、需求编辑、正文与创作记录
  Framework.tsx          可编辑前置框架与锁定操作
  DeepRewrite.tsx        深度重写条件、重构方案与三方证据报告
  Translation.tsx        全译流程说明、原文与译文逐段对照
scripts/                启动、MCP 配置、数据库迁移与协议验证
backend/tests/          独立 PostgreSQL schema 中的回归测试
examples/public-domain/ 真实素材、来源说明和已完成改编样稿
data/                   原始小说文件及旧库迁移备份
```

EPUB 上传上限 30 MB，解压资源上限 200 MB；支持 EPUB 2/3 导航及同一 XHTML 中的目录锚点。不支持受 DRM 保护的正文。TXT 支持 UTF-8、GB18030、带 BOM 的 UTF-16，自动识别中文章回及英文 Chapter / Part / Book 标题；选择章节时可核对识别结果。导出的改编 EPUB 是新作品，不继承原著固定版式。

素材库提供原作入口，来源记录可单独填写译者、版本和适用地区；这些字段随新建项目保存。

## 现有样稿

- [《三愿簿》](examples/public-domain/README.md)：参考《猴爪》，三章 2,135 字符的修仙／系统流样稿。
- [《青屿归来》](examples/public-domain/monte-cristo/README.md)：参考《基督山伯爵》第 1、4、7 章，1920 年民国港城与中国姓名，三章 4,127 字符。1934 年归侨复仇保留为长线约定。

样稿的 EPUB / TXT / Markdown 和完整创作 JSON 均已保存；原有冻结版本可在项目列表打开。

## 验证

```bash
uv run pytest -q
npm run build --prefix frontend
uv run python scripts/check_mcp.py
```

测试使用 `NOVEL_DATABASE_URL` 指向的 PostgreSQL，但每次创建独立、随机命名的 schema，并在结束时清理。不会读写生产 `public.records`。数据库角色须有创建 schema 的权限。

`check_mcp.py` 以临时端口、文件目录和数据库 schema 启动真正的后端与 STDIO 客户端，覆盖普通改编及 **完成版 → 页面接口编辑重写条件 → 全稿诊断 → 重构方案 → 正文 → 九项检查 → 全书三方审查 → 不可变 EPUB / JSON**，并确认旧改名工具已移除。固定创作数据检验协议与约束，不代表对文学质量的评测。

## 开源许可

项目源代码与技术文档采用 [MIT License](LICENSE)，允许商业使用、修改和分发，使用时须保留版权声明与许可证。

`examples/` 中的原著、译稿、改编正文及导出文件作为演示素材提供，不纳入上述代码许可证的授权范围；其来源、版本与许可信息以各目录说明及文件内附带许可为准。Project Gutenberg 原文保留其原有许可，相关记录见 [公版素材来源说明](examples/public-domain/README.md) 与 [《基督山伯爵》来源说明](examples/public-domain/monte-cristo/README.md)。
