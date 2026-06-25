# AES 文献工作台 · 前后台细设 v2.0

> **文档用途**：产品/开发**顶层总设**（唯一主文档，living document）。  
> **状态**：设计阶段，**设计定型前不写模块拆分文档**。  
> **版本**：v2.0 — 阅读交互（中间页/卡片）；稍后阅读=Miniflux starred；中文 MVP 无导读；AI 阅读文案。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1 | 2026-06-23 | §1.6 Folo+Amadeus；C35 已读；**C36 阅读笔记管线**；§17.1 L1/L2/L3；§20.6 笔记生产与 token |
| v2.0 | 2026-06-20 | §4 阅读交互/中间页；Miniflux starred；中文 MVP；AI 阅读；C26–C33 |
| v1.9 | 2026-06-20 | 标识符分路由；判重分级；DOI 重试队列；C25 |
| v1.8 | 2026-06-20 | §6.5 全渠道入流去重；打标前去重；C24 |
| v1.6 | 2026-06-20 | 去掉按平台浏览；搜索延 P2+；未订阅空态+推荐标签；§2.5 三阶段；C18–C21 |
| v1.5 | 2026-06-20 | §2.5 打标训练生命周期；§2.6 多标签并集 **DB 读路径**；C16–C17；D10 已定 |
| v1.4 | 2026-06-20 | §23 中英文文献格式；C11–C15；§17.6 采样法；级联补全；Reader 中英文分轨展示 |
| v1.3 | 2026-06-20 | §16 随手入流；§17–§20 元信息/PDF/Zotero/状态机/AI 导读；撤回模块文档（C10） |
| v1.2 | 2026-06-20 | 用户只读；标签订阅；稍后阅读；匿名+6 位码；编辑 L1/L2 分级 |
| v1.1 | 2026-06-20 | 双角色；移动工作台 |
| v1.0 | 2026-06-20 | 初版（对话内） |

**已确认决策（C1–C33）**

| 编号 | 结论 |
|------|------|
| C1 | 用户为**只读**：能读看、稍后阅读、订阅/管理标签；**无**纠错、无后台、无 PDF 投递 |
| C2 | 用户侧**不做 AI 筛选**；改为订阅**系统标签**（标签由编辑在后台维护） |
| C3 | **稍后阅读** = 星标语义；**存储走 Miniflux starred API**；UI 仍称「稍后阅读」（§4.1） |
| C4 | 用户体系**极简**：默认无需注册；Cookie + 本地存储；可选 6 位数编码跨端同步；可选绑定微信 |
| C5 | 移动后台与 Reader **合并**；仅编辑多「工作台」Tab；重操作在桌面 Console |
| C10 | **模块化开发暂缓**；设计基本定型后再拆模块与实现文档 |
| C11 | **详细文档优先**：跨对话接续以本文完整正文为准，不用 compact 摘要代替 |
| C12 | **英文占绝大多数**；元信息含 DOI/PMID/PII；**各有官方 API、分路由补全**（非串联 fallback） |
| C13 | **英文流内标题显示中文翻译**；详情保留英文原标题；作者不译 |
| C14 | **英文**：中间页含 AI 导读 + **AI 阅读**（全文 PDF 分享链）；官网/数据库链纳入元信息 |
| C26 | 卡片 badge = **`issue_or_pub` 实际期数/发表时间**，不显示 `[当期目录]`/`Ahead of Print` 原文前缀 |
| C27 | **元数据 UI**：每个字段独立一行（期刊、期数、作者、DOI…），禁止 HTML 块堆砌 |
| C28 | **中文 MVP**：大流点进 → **中间页**（摘要+库链）；**不做**流内下拉摘要；**不做**导读 |
| C29 | **英文**：**必须中间页**（导读+AI 阅读+英文摘要）；列表 **中文标题下跟英文原标题** |
| C30 | UI 文案 **「AI 阅读」**（原「豆包阅读」）；字段名仍 `doubao_read_url` |
| C31 | **转发按钮**分享中间页 URL `/article/:key`；无中间页则转发无法落地 → 中英文均用中间页 |
| C32 | **英文装饰大图**：PDF 抽插图 → 编辑 Console 选用 → 大流卡片/中间页头图（按视觉规范） |
| C33 | **长对话**：成果以本文为准；上下文 >50% 建议新对话 **轻量 Read 主文档** 续（§21.2–§21.4） |
| C34 | **产品定位（用户视角）**：**文献助手**——①获悉（标签订阅上新）②深读（摘要→导读→英文 AI 阅读）③收纳（转发企业微信→稍后阅读）；**非**文献管理/Zotero 替代/用户侧 AI 筛稿；全文合规为唯一硬边界（§1.0） |
| C35 | **已读**（§4.1.1，Inoreader 式简化）：① 中间页**停留 ≥1s** → 已读；② 列表头 **「全部标已读」清零**（MVP）。**无**列表扫过自动标、**无**单条手动标已读/未读；要留用 🔖稍后阅读。存 `user_read_state`，随同步码同步 |
| C36 | **阅读笔记**（§20.6）：中间页 `reading_note_brief` **≤1000字**；**DeepSeek V4 Flash API** 生产（`pypdf` 抽文本）；豆包 Web 仅深读外链 |
| C37 | **L2→L3 三轨定型**（2026-06-25）：深读=`doubao_read_url` 豆包 Web chip；导读=`reading_note_zh` DeepSeek API；头图=本地抽图+编辑 Console 择一（C32，非 LLM） |
| C15 | **中文**（CNKI/CMA）：**MVP 无 AI 导读**，仅摘要+库链；P5+ 可开导读；**不提供 AI 阅读**（版权） |
| C16 | **打标冷启动**：初期编辑**全手动打标**作 AI 学习素材；样本足够后编辑与 AI **共拟基础标签体系**；之后 AI **自动打标**，编辑**随时可改** |
| C17 | **用户订阅流**：多标签并集 = **单次 DB 查询 + 倒排索引去重**；**禁止**按标签 K 次查询再客户端合并（§2.6） |
| C18 | 用户阅读域 **不做按平台浏览**（CNKI/LWW/…）；平台信息仅在卡片/详情展示 |
| C19 | **搜索 MVP 不做**；P2+ 若做，限 **标题+作者** FTS，不含摘要/导读全文 |
| C20 | **未订阅任何标签** = 空态 + 推荐标签一键订阅；**默认不展示**全库大流（§2.2） |
| C21 | 打标训练 **三阶段**（积累→上线→稳态）；样本 **宁多勿少、覆盖主要标签类**，不设过低硬性篇数门槛（§2.5） |
| C22 | **随手入流核心键** = **DOI / PMID / PII**（可直接输入）；URL 仅作载体，**必须先解析出三键之一**再走 §17 级联补全 |
| C23 | 随手入流 **主入口**：桌面 **浏览器插件**；移动 **转发微信**（个人号/企业号）；Console 为全功能兜底（§16） |
| C24 | **全渠道去重在打标/筛选之前**：normalize 标识符 → lookup → 命中则跳过打标（§6.5） |
| C25 | **解析与判重分离**：有 DOI 只走 CrossRef；有 PMID 只走 PubMed；有 PII 只走 PII API；**冗余**=多标识符关联同一篇 + DOI 滞后重试队列（§17.7） |

---

## 0. 如何使用本文档

- **唯一主文档**：`docs/aes_workbench_design.md` — 所有对话成果汇总于此（修订记录、§15 反馈表、各章正文）。
- **已定** / **待决**：改 §15 表格，或直接在正文修改；新对话说「请读 aes_workbench_design.md 最新版」即可接续。
- **模块化**：暂不维护模块注册表；设计定型后再拆（见 C10）。
- **详细优于 compact**（C11）：新对话应读**本文完整版**，不要依赖对话里的简短 recap、AI 自动摘要或「上一对话要点」——那些会丢条件、丢待决、丢否定项。
- **相关但独立**：[`AES_PIPELINE_HANDOFF.md`](../AES_PIPELINE_HANDOFF.md)（豆包 RPA）、[`AGENTS.md`](../AGENTS.md)（CNKI 源）。

---

## 1. 系统使用者模型

### 1.0 产品定位（用户视角）✅ C34

**对外一句话**：AES 是**文献助手**——帮你**及时获悉**订阅领域的上新，按需要你**加深阅读**，并把路上遇到的文献**收进稍后阅读**。

**不是什么**（避免错误预期）：

| 不是 | 原因 |
|------|------|
| 文献管理软件 / Zotero 替代 | 用户只读（C1）；无上传、纠错、个人书库 |
| 泛 RSS / 全库阅读器 | 默认标签订阅流，未订阅不铺全库（C20） |
| 用户侧「AI 帮我筛稿」 | 筛选在编辑侧；用户订阅**系统标签**（C2） |

**助手三能力**（用户心智，对应已有设计）：

| 能力 | 用户体感 | 锚点 |
|------|----------|------|
| **获悉助手** | 订阅标签后，领域内新文献进入个人流 | C2、C17、C20 |
| **深读助手** | 列表略读 → 中间页精读 →（英文）AI 阅读辅助全文 | C28–C29、C14、C15 |
| **收纳助手** | 看到好文 → 转发企业微信 → 解析入库 → **稍后阅读**（英文附 AI 阅读链） | C3、C22–C23；用户开放前见 D11、D21 |

**阅读深度梯**（同一产品内递进，非四个 App）：

```
浏览（卡片+期数/作者）
  → 略读（中间页：结构化元信息 + 摘要）
    → 精读（英文：AI 导读）
      → 全文辅助（英文：AI 阅读外链，AES 不托管 PDF）
        → 沉淀（稍后阅读 / 阅读历史）
```

**合规边界（唯一硬风险）**：

- **中文**（CNKI/CMA）：MVP 仅摘要 + 库链；**无** AI 导读、**无** AI 阅读（C15，版权）。
- **英文 AI 阅读**：经第三方分享链（`doubao_read_url`），AES **不存储、不分发** PDF 全文；UI 称「AI 阅读」（C30）。
- **随手入流**：Phase 1 仅编辑（D11）；对用户开放收纳助手前，须定微信形态与权责（D21）。

**界面文案倾向**：主界面叫「阅读」；队列叫「稍后阅读」（非「我的文献库」）；按钮叫「AI 阅读」（非「免费全文」）。

### 1.1 角色定义

| 角色 | 代号 | 核心诉求 |
|------|------|----------|
| **用户** | `user` | **文献助手**（C34）：获悉（标签订阅流）→ 深读（中间页/导读/AI 阅读）→ 收纳（稍后阅读） |
| **编辑** | `editor` | **内容生产与运维**：打标、AI 筛选训练、源管理、管线巡检、Worker、读文献（与用户同款 Reader） |
| **广告主** | `advertiser` | 本阶段不讨论 |

### 1.2 用户核心能力（只读）✅

用户**只能**做以下四类事：

```
① 读看     浏览文献列表与详情（元信息、摘要、AI 总结、原文链接）
② 稍后阅读  点选加入个人队列（原「星标」语义，见 §4.1）
③ 订阅标签  从系统标签库中订阅/取消；管理自己的订阅组合
④ 个人数据  阅读历史、稍后阅读列表、订阅偏好（本地为主，可同步）
```

用户**不能**：纠错、附言、上传 PDF、触发 Worker、看 AI 置信度/筛选色、访问 `/editor` 与 `/admin`。

### 1.3 编辑核心能力

编辑 = 用户全部阅读能力 + 内容后台 + 移动碎片化处置 + 桌面重处理（见 **§7 操作分级总表**）。

编辑在阅读流内**可与用户看同一套 UI**；打标、纠错、加工等**不进用户界面**，在「工作台」Tab 或桌面 Console 完成。

### 1.4 权限矩阵

| 能力 | 用户 | 编辑 |
|------|:----:|:----:|
| 浏览文献（按订阅标签 / 单标签） | ✅ | ✅ |
| 看元信息 + 摘要 + AI 总结 | ✅ | ✅ |
| 稍后阅读 | ✅ | ✅ |
| 订阅/取消系统标签 | ✅ | ✅ |
| 阅读历史（个人） | ✅ | ✅ |
| 6 位码同步 / 绑定微信 | ✅ | ✅ |
| 看 AI 筛选色 / 置信度 | ❌ | ✅ |
| 纠错 / 附言 / 训练学习集 | ❌ | ✅ |
| 上传 PDF / 触发 Worker | ❌ | ✅ |
| 管理**系统标签**（增删改） | ❌ | ✅ |
| 移动「工作台」快捷处置 | ❌ | ✅ |
| 桌面 Console 重处理 | ❌ | ✅ |

### 1.5 架构关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    AES 文献工作台（单一 PWA）                   │
├────────────────────────────┬────────────────────────────────┤
│  用户 · 阅读域              │  编辑 · 额外能力                 │
│  · 标签订阅流               │  · 阅读域（与用户相同）           │
│  · 稍后阅读                 │  · 移动「工作台」Tab（碎片化）    │
│  · 阅读历史                 │  · 桌面 Console（重处理）        │
│  · 匿名身份 + 可选同步       │                                │
└────────────────────────────┴────────────────────────────────┘
         ▲                                    ▲
         │ 消费                               │ 生产
         │                                    │
┌────────┴────────┐              ┌────────────┴────────────┐
│ 系统标签 + 文献   │◄─────────────│ 编辑后台：打标、AI 筛选、  │
│ （XML + 标签）   │   编辑维护    │ Worker、源、管线          │
└─────────────────┘              └─────────────────────────┘
```

### 1.6 结构学习执行清单（参考开源 · 只学结构）✅

> **用途**：设计定型前，从 GitHub / Agent Skills **拆结构**对照 AES，不 fork 全产品。  
> **筛选**：结构可拆 × 填补 AES 缺口 × 不冲突合规（不托管用户侧 PDF 全文）。

#### 1.6.1 执行序（7 GitHub + 3 Skills）

| 序 | 参考 | 只学哪块结构 | 对照 AES |
|----|------|-------------|----------|
| 1 | [RSSNext/Folo](https://github.com/RSSNext/Folo) | Feed / Library / Later 三域 | 标签订阅流、稍后阅读、中间页深度梯 |
| 2 | [CurryTang/Amadeus](https://github.com/CurryTang/Amadeus) | Tracker：源→爬取→去重→Feed；（**不学** PDF 存储层） | §6.5 去重、§17 补全、cron/XML 入流 |
| **3** | **[ChangLabSNU/PaperSorter](https://github.com/ChangLabSNU/PaperSorter)** | **标注 UI → embedding → train → predict → 阈值推送** 闭环 | **§2.5 打标冷启动 C16/C21**（见 1.6.2） |
| 4 | [sseanliu/PaperClip](https://github.com/sseanliu/PaperClip) | 浏览捕获环：canonical ID 去重 → enrich → read/unread | §16 插件、稍后阅读 D11 |
| 5 | [mathpn/karakeep-miniflux-webhook](https://github.com/mathpn/karakeep-miniflux-webhook) | Miniflux starred → webhook 下游 | C3 starred、D24 |
| 6 | [XimilalaXiang/YourRSS](https://github.com/XimilalaXiang/YourRSS) | 全量轻筛 + TopN 精摘要；偏好反馈 | 编辑 digest、推荐标签 |
| 7 | [DelinQu/zotero-arxiv-feishu-llm](https://github.com/DelinQu/zotero-arxiv-feishu-llm) | 排序 → 结构化卡片 → 企微/飞书 | D21 微信形态 |
| S1 | [ai-skill-scholar](https://github.com/dsebastien/ai-skill-scholar) `literature-review` | 两轮综述 + session 状态 | 编辑选题验证 |
| S2 | [paper-search-pro](https://github.com/O0000-code/paper-search-pro) | Quick/Deep 档位；脚本层 vs LLM 层分离 | 自研 AES skill 模板 |
| S3 | [Literature_push](https://github.com/family3253/Literature_push) | 检索→报告→定时多渠道推送 recipe | 企微日/周报 |

**按需插队（不进首轮通读）**：PaperFeeder（多级 LLM filter）、paper-digest（canonical 去重 state）、Jamie-Cui/paper-pulse（双语摘要卡片）。

**明确不学**：Paper Agent / Omelette（研究台）、Elicit/Consensus（问答检索）、Paperlib/Zotero 系（管理主模型）、Readwise（闭源仅概念）。

#### 1.6.2 PaperSorter → §2.5 结构对照（序 3 精读）

PaperSorter 命令与阶段：

```
papersorter update      → 拉 RSS + 生成 embedding
Web UI 标注             → Interested / Not Interested
papersorter train       → XGBoost（ROC-AUC 监控）
papersorter broadcast   → 按 channel 阈值推送 Slack
```

| PaperSorter 结构 | AES 映射（§2.5） | 差异（不照搬） |
|------------------|------------------|----------------|
| `update` 入流+向量化 | 入流 → `tag_worker` 前：**元信息 L1 就绪** | AES 标识符分路由 CrossRef/PubMed（C25），非仅 RSS |
| Web **标注 UI**（浏览流内点选） | 阶段① **编辑手打** + Console 学习集 D4 | AES 是**多标签 taxonomy**，非二分类 Interested |
| `learning-set` 正/反例 | `learning-set.json` + `learning_notes.jsonl` | 已规划（§2.5.3） |
| `train` + ROC-AUC | 阶段② 试跑满意后开批量；D20 置信度 **0.85** | AES 主路径是 **LLM 打标 + 置信度**，非必须用 XGBoost |
| `broadcast` + 每 channel 阈值 | 编辑 **digest/Slack**；用户侧走**标签订阅 SQL** | 推送对象是编辑运维，不是用户大流 |
| 稳态持续标注 | 阶段③ 纠错回流学习集 | §2.5.2 编辑可随时改 |

**从 PaperSorter 只摘 4 条结构原则写入 AES Console**：

1. **管线分拆**：`ingest` / `label-ui` / `train` / `notify` 四命令，禁止 UI 里同步跑训练。  
2. **标注与浏览同屏**：编辑在「待标队列」里边看摘要边打标，不单独开表格页。  
3. **样本质量门**：ROC-AUC 或等价指标 + **覆盖主要标签类**（C21），不设 30+30 硬篇数。  
4. **channel = 标签或项目组**：多路模型/阈值 → AES 多 **系统标签** 各自置信度策略（可共用 `tag_worker`，分 tag 调 D20）。

#### 1.6.3 学习方法

每项产出 **一张结构图**（数据流 / 状态 / UI 域）+ **AES 映射表**一行「保留 / 改造 / 拒绝」；不 clone 全仓实现。

#### 1.6.4 Folo → §4 结构对照（序 1 精读）✅

> 源码：[RSSNext/Folo](https://github.com/RSSNext/Folo)（`dev` 分支 shallow 精读；monorepo：`apps/desktop` renderer + `packages/internal/store`）。  
> **命名澄清**：执行清单「Feed / Library / Later」是**结构学习抽象**（对照 Readwise 双域心智），**非** Folo 界面字面文案。Folo 实际为 **Feed 时间线 + Starred（collections）+ Inbox 入站**；**无** Readwise 式 Library/Later 双队列。

**Folo 三域（实际实现）**

| 抽象域 | Folo 实现 | 路由/键 | 数据 |
|--------|-----------|---------|------|
| **Feed** | 订阅时间线：feeds / lists / inbox 聚合 | `/timeline/:view/:feedId/:entryId`；`feedId=all` 为全订阅 | `entry` + `subscription` store；按 `FeedViewType` 分 Articles/Videos/… |
| **Library** | **Starred**（侧栏置顶 ⭐） | `feedId=collections`（`FEED_COLLECTION_LIST`） | `collection` store；`starEntry` → API `collections.post` + 本地 SQLite |
| **Later** | **合并入 Starred**；另 **Inbox** = 外部推送邮箱入站（newsletter） | Inbox：`inbox/{id}` 订阅类型 | 非「稍后读队列」；AES **不学** Inbox 邮箱模型 |

**数据流**

```
Folo Cloud API (@follow-app/client-sdk)
        │ morph（api → 内部 model）
        ▼
Local SQLite（Drizzle）──hydrate──► Zustand（subscription/entry/collection/unread/summary）
        │                                    │
        │                                    ▼
        │                          TanStack Query（分页 entry 列表）
        ▼
UI 三栏：SubscriptionColumn │ EntryColumn（列表）│ EntryContent（详情 ± AI Chat 侧栏）
```

**UI 域结构（桌面 Timeline 主路径）**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ MainDesktopLayout                                                        │
├─────────────────┬──────────────────────────┬─────────────────────────────┤
│ SubscriptionColumn│ EntryColumn              │ EntryContentView          │
│ ⭐ Starred        │ 标题行 + TL;DR / AI 时间线 │ ArticleLayout             │
│ Lists             │ 虚拟列表 entry cards       │  ├ AISummary（文首卡片）   │
│ Inbox             │ 滚动标已读                 │  ├ 正文 ShadowDOM         │
│ Feeds（分类树）    │                          │  └ 选区「问 AI」          │
│ View Tabs         │                          │ （可选）AI Chat 固定/浮层   │
└─────────────────┴──────────────────────────┴─────────────────────────────┘
移动：列表与详情分屏/跳转，无 AES 式独立中间页 URL。
```

**AI 摘要触发（Folo）**

| 层级 | 触发 | 实现锚点 |
|------|------|----------|
| **条目** | 打开文章 → 文首自动摘要卡 | `ArticleLayout` → `AISummary` → `usePrefetchSummary`（`summarySyncService.generateSummary`）；受全局 + 单条 `settings.summary` 控制 |
| **时间线** | 列表头「Timeline summary」按钮 | `EntryListHeader` → `useSendAIShortcut`（`DEFAULT_SUMMARIZE_TIMELINE_SHORTCUT_ID`） |
| **时间线** | AI Timeline 模式开关 | `aiTimelineEnabledAtom`；重排/过滤未读流（宽屏） |
| **定时** | 每日 digest / 效率分析 | `ai-task` 模块；`once/daily/weekly/monthly` |
| **对话** | AI Chat 附 entry block；选区 Ask AI | `ai-chat` parts + `TextSelectionToolbar`；BYOK / MCP 扩展 |
| **缓存** | 摘要本地持久化 | `summary` store + SQLite；`staleTime` 24h |

**AES 映射表（保留 / 改造 / 拒绝）**

| Folo 结构 | AES 对照（§4 / C 表） | 决策 |
|-----------|----------------------|------|
| Feed 订阅时间线 + 分页列表 | 标签订阅流 `/`、`/tag/:id`（C17/C20） | **保留** 列表扫标题 → 点进详情 |
| 桌面三栏（订阅｜列表｜详情） | §4.3 左订阅 + 中列表 + 右中间页 | **保留** |
| Starred = `collections` 用户收藏 | 稍后阅读 = Miniflux **starred**（C3）；UI「稍后阅读」 | **改造** 独立路由 `/read-later`，**存储走 Miniflux API**，非 Folo collections 表 |
| Inbox 邮箱/Webhook 入站 | 随手入流微信转发（C23） | **改造** 仅学「外部入站」概念，**不学** Inbox 邮箱实现 |
| EntryContent 流内全文 + 文首 AISummary | 中间页 `/article/:key`（C28–C31）；导读**仅**中间页 | **改造** AES **强制**中间页 URL 供转发（C31）；**拒绝**流内下拉摘要 |
| Timeline / AI Timeline 批量摘要 | 用户侧不做 AI 筛选（C2） | **拒绝** 时间线 TL;DR 不进用户 Reader |
| 条目级 AI Chat（BYOK/MCP） | 英文：预生成 `ai_summary_zh` + `doubao_read_url`（C14/C30） | **改造** 非对话式；中文 MVP 无导读（C15/C28） |
| `FeedViewType` 多媒体分 view | 文献助手单一 Article 流（C18） | **拒绝** 不做视频/社交/图片分 Tab |
| 用户自建 Lists / 社区 Collections | 编辑维护**系统标签** + 用户订阅（C2/C16） | **拒绝** |
| local-first SQLite + 云同步 | AES SQLite `entries` + 打标索引；Miniflux 只读代理 starred | **改造** 主数据在 AES DB，非 Folo 式全文离线镜像 |
| 未订阅默认「全订阅 all」 | 未订阅 = 空态 + 推荐标签（C20） | **拒绝** Folo 默认 all feeds；AES 默认**无**全库大流 |

**从 Folo 摘 3 条写入 AES §4 的产品结论**（详见 §4.2.1）：

1. **阅读域 = 同一 App 内域切换**（订阅流 / 稍后阅读 / 单标签），非独立「文献库」App——与 C34 文献助手一致。  
2. **深度梯在详情页展开**（Folo 文首摘要 → 正文 → Chat）；AES 对齐为 **卡片 → 中间页 → 导读 → AI 阅读外链**（§1.0 深度梯），且中间页必须有稳定 URL。  
3. **用户侧 AI 只做「读这一篇」**，不做「帮我筛时间线」——Folo Timeline summary 能力**不**映射到用户标签订阅流。

#### 1.6.5 Amadeus → §6.5 / §17 结构对照（序 2 精读）✅

> 源码：[CurryTang/Amadeus](https://github.com/CurryTang/Amadeus)（`backend/src/services/paper-tracker.service.js` + 各 `*-tracker.service.js`）。  
> **范围**：只学 **Tracker 入流管线**（源→爬取→去重→Feed/入库）；**不学** PDF/S3 存储、ARIS、Chrome 扩展、多 pass AI 阅读。

**Amadeus 在整体产品中的位置**

Amadeus ≠ 纯 Tracker：它是「个人论文库 + Tracker 发现流 + AI 深读」三合一。AES 只拆其中 **Tracker + 入库前处理** 一段，对应编辑侧 **cron/XML / 随手入流**，**不**对应用户 Reader。

**模块结构**

| 模块 | 文件/表 | 作用 |
|------|---------|------|
| **源注册** | `tracker_sources`（type/name/config/enabled/last_checked_at） | Admin UI 配置 RSS、HF、Twitter、arxiv_authors、finance… |
| **编排器** | `paper-tracker.service.js` → `runAll()` / `runSource()` | 按优先级遍历 enabled 源；per-source timeout；`run-tracker.js` 独立 cron |
| **源适配器** | `rss-tracker` / `hf-tracker` / `twitter-*` / `alphaxiv-tracker` / `arxiv.service` … | 各源拉取 → 归一化 item 列表 |
| **爬取去重 A** | `tracker_seen_papers(arxiv_id)` + `tracker_archived_posts(post_url)` | 避免同一 arXiv / 同一推文重复处理 |
| **业务库去重 B** | `documents.original_url LIKE %arxiv%` | 与 A 叠加，防已入库重复 |
| **入库** | `importArxivPaper()` → metadata + **PDF→S3** → `documents` | **AES 不学** |
| **发现流 Feed** | `tracker.js` + `tracker_feed_cache`（24h 快照） | 多源聚合排序、分页 API；**非**个人论文库 |
| **发现-only** | `isDiscoveryOnlySource()`：rss/hf/twitter/arxiv_authors/… | 只进 Feed，**不** auto-import 到 Library |

**数据流（Tracker 主路径）**

```
tracker_sources（enabled）
        │
        ▼
paper-tracker.runSource(type) ──► *-tracker.service（拉取）
        │
        ├─ discovery-only（rss/hf/twitter/…）
        │       └─► tracker_feed_cache / GET /api/tracker/feed（展示用）
        │
        └─ import 路径（如 scholar 等，arxiv 候选）
                │
                ├─ isAlreadySeen(arxiv_id) ──► skip
                │
                └─ importArxivPaper → PDF/S3 + documents  ← AES 截断于此之前
```

**Feed vs Library（Amadeus 双出口）**

```
爬取条目 ──┬──► Tracker Feed（发现流，可个性化排序）
           └──► Library/documents（需 import + PDF）  ← 个人论文管理主库
```

AES **无**用户侧「发现流 + 论文库」双产品：用户只看 **打标后的标签订阅流**；编辑侧 **cron→XML→Miniflux→entries** 已是固定管道。

**AES 映射表（保留 / 改造 / 拒绝）**

| Amadeus 结构 | AES 对照 | 决策 |
|--------------|----------|------|
| `tracker_sources` 源注册 + Admin | `cnki_targets.json` + Console `/admin/feeds`（D10） | **保留** 源配置与 enabled/interval 分源管理 |
| `runAll()` 编排 + per-source timeout | cron 脚本 + `cnki_downloader --journal`；单源失败不拖死全局 | **保留** |
| `last_checked_at` + crawlIntervalHours | 各期刊/通道独立 cron 或 last_run 日志（§7 pipeline） | **保留** |
| discovery-only vs import 分叉 | **A 爬取去重**写 XML（`cnki_dedup_log`）≠ **B 业务去重**写 `entries`（§6.5.1） | **改造** AES 用 Miniflux+XML 作聚合池，**不**做 Amadeus 式 Feed API |
| `tracker_seen_papers`（arxiv_id） | §6.5.1 **层 A** `cnki_dedup_log` / XML 写前 hash | **改造** 键为 **DOI/PMID/PII/platform_id**，非仅 arXiv |
| `documents` URL 模糊查重 | §6.5.3 `entry_identifiers` Tier 1 精确 lookup | **改造** AES 业务去重**强于** Amadeus |
| `importArxivPaper` + PDF→S3 | §17 enrich **分路由**（C25）；PDF 走 Zotero 状态机（§18–§20） | **改造** 补全在 dedup **之后**（§6.5.2 ⑤），**不**在 ingest 时拉 PDF 入用户库 |
| `tracker_feed_cache` + 个性化排序 | 用户 **标签订阅 SQL**（§2.6）；编辑 digest 另议（序 6 YourRSS） | **拒绝** 用户侧不做 Tracker Feed |
| `tracker_item_events` 行为加权 | C2 用户侧不做 AI 筛选/排序 | **拒绝** |
| RSS 适配器（通用 feed URL） | Miniflux poll `aes-feeds/*.xml`；CNKI 用 web 深度爬 | **保留**「一源一适配器」模式 |
| Twitter/Playwright 社交源 | 非 AES MVP 信源 | **拒绝** |
| `run-tracker.js` 独立进程 | cron + `cnki_downloader` 可与 API 进程分离 | **保留** 重爬取不占 API worker |

**从 Amadeus 摘 4 条写入 AES 管线（§6.5.6）**

1. **源注册与编排分拆**：配置在表/JSON，执行在 cron worker，**禁止**在 Reader/Console 请求里同步跑全量爬取。  
2. **两层去重不要混**：Amadeus 的 `seen_papers`≈AES 层 A；`entry_identifiers`≈层 B——**层 B 必须在 tag_worker 前**（C24，已成立）。  
3. **发现与入库分流**：Amadeus Feed≠Library；AES 等价物是 **XML/Miniflux 探测** vs **`entries` 正式入流**，用户只见后者且须已打标。  
4. **标识符先于一切**：Amadeus 绑 arXiv ID；AES 必须用 **C22/C25** 多键，否则跨渠道必撞。

#### 1.6.5.1 Amadeus 深读 · 对 AES 导读的结论（序 2 续）✅

> **结论**：Amadeus **3 Pass 管线对 AES 几乎无可学**——Pass1/3 与 AES 无关；Pass2 仅 **输出格式纪律** 可借鉴，**内容框架须按医美/临床文献重写**，不能通用。  
> 源码：[`auto-reader.service.js`](https://github.com/CurryTang/Amadeus/blob/main/backend/src/services/auto-reader.service.js) `PAPER_PASS_2_PROMPT`。

**为何「三步」在 AES 里是假命题**

| 说法 | 实际 |
|------|------|
| Step A 本地 outline ≈ Pass1 | 若 LLM **直接读 PDF**，outline 对导读**增益很小**；仅 **API 只吃文本** 时 extract 是工程必需，不是「第一轮阅读」 |
| Step B ≈ Pass2 | **唯一用户可见的一步** = 1× LLM |
| Step C 豆包外链 | **不是导读**，与 Pass 无关 |

**Amadeus Pass2 写了什么（CS/ML 向）**

固定 Markdown 节：`核心问题` · `方法概述` · `关键图表复现`（ASCII 流程图 + 表格）· `实验设置`（数据集/基线/指标）· `主要结果` · `存疑点` · `待追读文献`。  
依赖 Pass1 的 `{previous_notes}` 指定「关键页」——AES 单步模式下**不依赖**。

**可借鉴 vs 必须重写**

| 可借鉴 | 必须丢弃/改写 |
|--------|----------------|
| 固定小节、禁止开场白 | ASCII 复现图表（临床论文价值低） |
| 关键数字用表格 | 「数据集 / 基线 / 指标」→ 改为 **PICO / 样本量 / 主要终点** |
| 输出 Markdown 直渲染 | 「存疑点 / 待追读」→ 改为 **局限 / 证据等级 / 临床启示** |
| — | 同一 prompt **不能**覆盖 RCT、综述、病例、基础实验、指南 |

**AES 导读策略（修订）**：`paper_type` 路由 → `prompts/reading_note_{type}.md`（见 §20.6）；MVP 先 **RCT + 观察性** 两版，综述 P2+。

---

## 2. 标签体系（取代用户侧 AI 筛选）

### 2.1 概念区分

| 概念 | 说明 | 谁维护 |
|------|------|--------|
| **系统标签** | 平台提供的分类标签，如 `隆鼻`、`肉毒素`、`激光`、`行业资讯` | 编辑在 Console |
| **用户订阅** | 用户勾选的系统标签子集 | 用户自己在设置/订阅页 |
| **文章标签** | 每篇文献被贴上的系统标签（可多篇） | 冷启动：编辑手动；稳态：AI 自动 + 编辑随时改（见 §2.5） |

用户**不看到**「相关/无关/不确定」；用户**只看到**「我订阅的标签下的文献」。

### 2.2 用户阅读流逻辑

```
全部可阅文献（Miniflux 聚合）
        │
        ▼
编辑/AI 已打系统标签
        │
        ▼
用户订阅标签过滤  ──→  用户收件箱（默认）
        │
        └─ 可按单标签浏览（/tag/:id，同 §2.6 单次查询）
```

**MVP 不做**：按平台浏览（C18）、全文搜索（C19，延 P2+）。

**默认首页**：用户订阅标签的**并集**下的未读文献（按时间倒序）。DB 实现见 **§2.6**。

**未订阅任何标签时** ✅（C20）：

```
首次打开 / 订阅为空
        │
        ▼
┌─ 空态首页 ─────────────────────────────┐
│  「选择你关心的主题，开始阅读」          │
│  推荐标签（编辑精选 6–12 个，带篇数）    │
│  [一键订阅推荐包]  [去标签订阅页自选]    │
└────────────────────────────────────────┘
        │
        ├─ 可选：点击某推荐标签 → 预览该标签最近 N 篇（只读，未订阅前）
        └─ 订阅 ≥1 个标签后 → 正常订阅流
```

**为何不用「全库大流打底」**：标签订阅是产品核心（C2）；未筛选的全量流噪音大、未打标篇也会露出，且与「订阅个性化」心智冲突。全量浏览若需要，留给 **设置里可选开关**（§15 D5），不对新用户默认开放。

#### 2.2.1 搜索为何 MVP 不做（C19）

| 搜什么 | 代价 | MVP |
|--------|------|-----|
| 标题 + 作者 | SQLite **FTS5** 索引，万篇级毫秒级 | P2+ 可加 |
| 摘要 | 字段长、命中多，需独立 FTS 或 LIKE 扫表 | 暂不做 |
| AI 导读全文 | 更长、更新频，索引维护成本高 | 暂不做 |

标签订阅已覆盖「我想看什么主题」；搜索是 **补充能力**，不挡 P1 阅读闭环。初期用户靠 **订阅 + 单标签浏览** 即可。

### 2.3 系统标签数据（编辑维护）

```sql
tags (
  id TEXT PK,              -- tag_rhinoplasty
  name TEXT,               -- 隆鼻
  slug TEXT,
  group TEXT,              -- 术式 | 材料 | 部位 | 行业 | …
  description TEXT,        -- 编辑可见说明
  sort_order INT,
  enabled BOOL,
  article_count INT,       -- 冗余统计
  created_at TEXT
)

entry_tags (
  article_key TEXT,
  tag_id TEXT,
  source TEXT,             -- editor | ai_auto | ai_suggested
  confidence REAL,           -- AI 置信度 0–1；editor 手打可为 NULL
  status TEXT,             -- confirmed | pending_review  （ai_suggested 待 M8 复核）
  created_at TEXT,
  updated_by TEXT,         -- editor device_id 或 system
  PK (article_key, tag_id)
)
```

`inoreader-aes-filter` 的 AI 筛选能力**整体迁入编辑后台**（§2.5），用于**入流时打标**与质控，**不对用户暴露**，**不在用户开流时运行**。

### 2.4 标签订阅（用户）

```sql
user_tag_subscriptions (
  user_id TEXT,
  tag_id TEXT,
  subscribed_at TEXT,
  PK (user_id, tag_id)
)
```

`user_id` 即 `device_id` 或 `sync_profile` id，见 §3。

### 2.5 打标与 AI 训练生命周期 ✅（C16）

**核心原则**：标签是文献的**写入时属性**（write-time），不是用户读流时的**运行时筛选**（read-time）。AI 算力花在编辑后台的入流/补标队列，用户订阅只改 SQL 过滤条件。

#### 2.5.1 三阶段（简化版）✅（C21）

| 阶段 | 名称 | 编辑 | AI | 用户侧 |
|------|------|------|-----|--------|
| **① 积累** | 手打喂样本 | 持续手动打标；录入学习集（正/反例 + 标签归属）；**样本尽量多**，覆盖主要标签类别 | 可选后台试跑，**不写入**生产 `entry_tags` | 仅见已 `enabled` 的标签；首页空态+推荐 |
| **② 上线** | 标签定型 + 辅助打标 | 与 AI 共拟标签树（D1）；M8 复核低置信；随时改单篇 | 新文献自动建议；高置信直写，低置信待复核 | **订阅流正式可用** |
| **③ 稳态** | 日常 |  sporadic 纠错 → 学习集 | 新文献自动打标为主 | 正常 |

**不设僵硬的「满 30 篇才能开下一阶段」**——门槛看 **覆盖度**，不看单纯篇数：

- **相关/无关判决**：持续积累，越多越好；需覆盖中英文、各主要来源类型的典型篇
- **每个主要标签类**（术式/材料/部位/行业…）：均有 **若干** 编辑确认正例后，该标签才 `enabled=true`；篇数不设下限公式，**有代表样本即可**，但总体 **宁多勿少**
- **开 AI 批量打标**：主要标签类均有样本 + 编辑对 Prompt 试跑满意 → 进阶段②；非固定 headcount
- AI 自动直写阈值：单标签置信度 ≥ **0.85**（D20 待决）；以下进 M8

> 原五阶段（P0–P4）合并为以上三阶段；「shadow run」「样本 30+30」等硬门槛废弃，以免样本不足却强行开 AI。

#### 2.5.2 编辑可随时修改

| 修改类型 | 效果 | 是否回流学习集 |
|----------|------|----------------|
| 单篇增删标签 | 立即更新 `entry_tags`；用户流下一请求可见 | ✅ 记入 `learning_notes` |
| 驳回 AI 建议 | `status=rejected`，不展示给用户 | ✅ 负例 |
| 改标签名/分组 | `tags` 表更新；**不**重跑全库 LLM | — |
| 合并两标签 | `entry_tags` 批量迁移 + 旧 tag `enabled=false` | — |
| 改 System Prompt | 新文献用新版；可选「待补标队列」低峰重跑 | — |

**无「锁定」**：不存在 AI 打标后用户侧不可改的情况；编辑改标签**不触发**用户侧任何 LLM。

#### 2.5.3 与现有资产衔接

沿用 `inoreader-aes-filter` 数据形态，迁入 `aes_workflow.db` + Console：

> **结构参考**：开源 [PaperSorter](https://github.com/ChangLabSNU/PaperSorter) 的 `update → 标注 UI → train → broadcast` 闭环，见 **§1.6.2**（学结构，AES 用 LLM 多标签 + 置信度，非二分类 XGBoost）。

| 旧路径 | 新归属 |
|--------|--------|
| `system-prompt.txt` | D3 Prompt 版本管理 |
| `learning-set.json` | D4 学习集（正/负例） |
| `learning_notes.jsonl` | D4 纠错流水（自动追加） |
| `taxonomy_notes.jsonl` | D1 标签定义说明 / P2 草案来源 |
| `ai_curator.py` | 入流 Worker：`tag_worker`（批量打标，非用户请求路径） |

`tag_worker` 触发时机：**新条目入 Miniflux 后**、**随手入流后**、编辑手动「重新打标」——与 cron/XML 同级，**非**用户打开 `/` 时。

### 2.6 多标签订阅流：数据库读路径 ✅（C17）

> **本节只讨论 DB / I/O**，不讨论 AI token。打标在入流时**一次性**完成（§2.5 `tag_worker`），用户每次刷新订阅流**不调 LLM**——这点与「多标签并集」的性能问题是两件事。

#### 2.6.1 你关心的损耗：读路径上的 DB，不是推理

订阅 K 个标签合成一条流时，真正的开销通常在：

| 损耗类型 | 是否本节范围 |
|----------|--------------|
| 打标时 LLM 调一次/篇 | ❌ 一次性，与「开流」无关 |
| 用户刷新时重复调 LLM | ❌ AES 不做；本来就不是读路径设计 |
| **按标签查 K 次库再合并** | ✅ **这是本节要解决的** |
| **JOIN 行膨胀后在应用层去重** | ✅ |
| **列表接口返回过重字段** | ✅ |

「订阅 3 个标签感觉更慢」——在错误实现下，常见原因是 **I/O 随 K 线性放大**，而不是同一篇被 AI 推理 3 次。

#### 2.6.2 三种 DB 反模式（易造成 K 倍读取）

| 反模式 | 做法 | 为何慢 |
|--------|------|--------|
| **K 次查询 + 应用合并** | `SELECT … WHERE tag=A LIMIT 50`，再查 B、C，Node/Python 里 `dict` 去重、重排 | 每标签一次 round-trip；重叠篇被重复读出；合并排序在内存，分页 cursor 难维护 |
| **每标签一条「子流」表/缓存** | `feed_tag_A`、`feed_tag_B` 各存一份 article_key 列表，读时 UNION 多表 | 新篇入库要写 K 份；读时扫 K 个结构；与标签数绑死 |
| **无去重的 JOIN** | `entries JOIN entry_tags` 不 `GROUP BY`，一篇 3 标签返回 3 行，前端/中间层再去重 | 传输行数 × 命中标签数；`LIMIT 50` 实际只覆盖十几篇 |

另：**客户端拉 K 条 RSS/XML 再 merge** 是 RSS 层的同类问题（K 次 HTTP + parse），不是 DB 本身，但症状一样——**K 路读、一路合**。

#### 2.6.3 推荐架构：倒排索引 + 单次并集查询

```
【写入路径 · 一次性】
入流 → tag_worker 打标 → entry_tags(article_key, tag_id)

【读取路径 · 每次刷新】
user_tag_subscriptions → [A, B, C]
        │
        ▼
一条 SQL：tag_id IN (A,B,C) → GROUP BY article_key → ORDER BY published_at
        │
        ▼
订阅流 JSON（仅列表字段，无 LLM）
```

| 性质 | 说明 |
|------|------|
| 打标 | 每篇一次，入库/补标时完成 |
| 用户改订阅 | 只改 `user_tag_subscriptions`，**不重查打标、不重跑 AI** |
| 并集去重 | 在 SQL 层 `GROUP BY article_key`，不把膨胀行丢给应用 |
| 命中标签展示 | 同一次查询 `GROUP_CONCAT(et.tag_id)`，避免 N+1 |
| K 与 I/O | 有索引时，Planner 对 `IN` 中每个 tag 走索引再合并，**不是** K 次独立全表扫 |

**注意**：订阅标签越多，**命中篇数**可能越多（内容变宽），这是业务上的并集变大，不是实现失误。要避免的是 **同样 50 篇结果却读了 K 遍库**。

#### 2.6.4 推荐查询与索引（SQLite）

```sql
-- 必建：按标签查文章（倒排）
CREATE INDEX idx_entry_tags_tag ON entry_tags(tag_id, article_key);

-- 列表排序
CREATE INDEX idx_entries_published ON entries(published_at DESC, article_key);

-- 并集 + 去重 + 分页（列表只取轻字段，摘要/导读在详情接口再取）
SELECT e.article_key,
       e.title_display,
       e.published_at,
       e.platform,
       GROUP_CONCAT(et.tag_id) AS matched_tags
FROM entry_tags et
JOIN entries e ON e.article_key = et.article_key
WHERE et.tag_id IN (:subscribed_ids)
  AND et.status = 'confirmed'
GROUP BY e.article_key
ORDER BY e.published_at DESC, e.article_key DESC
LIMIT :limit;
-- 游标分页用 (published_at, article_key) < (:cursor_t, :cursor_k)，避免大 OFFSET
```

**未读过滤**（C35）：优先 `LEFT JOIN user_read_state` + `WHERE read_at IS NULL`；避免把大量已读 key 塞进 `NOT IN (...)`。

#### 2.6.5 读路径清单（实现时对照）

| ✅ 应做 | ❌ 不应做 |
|---------|-----------|
| 一次 API `/entries?tags=subscribed` 内部一条 SQL | 前端循环调 `/entries?tag=A` × K |
| 列表接口只返回卡片字段 | 列表带出全文摘要、导读 HTML |
| Keyset 游标分页 | 深翻页 `OFFSET 10000` |
| `entry_tags(tag_id)` 索引 | 先 `SELECT * FROM entries` 再在内存筛标签 |
| 详情 `/entries/:key` 再 JOIN 重字段 | 为省一次查询在列表里塞满元数据 |

AES 初期（<1 万篇、单 SQLite）：上述足够，**不必**做 per-user 物化视图。只有 profiling 证明单查询 >100ms 时再考虑缓存层。

#### 2.6.6 产品层（与 DB 相关部分）

| 场景 | 做法 |
|------|------|
| 默认首页 | 已订阅标签并集，**一条**列表 API |
| 单标签浏览 | `/tag/:id` — `IN` 仅 1 个 id，查询更窄，仍走同一套表 |
| 订阅很多标签 | 限制订阅上限（如 30）；UI 分组；**不**为每标签维护独立 feed 表 |
| 未打标文献 | 无 `entry_tags` 行 → 不进用户流；编辑走待打标队列 |

#### 2.6.7 与 Miniflux 的分工

- **Miniflux**：poll XML，维护**未按业务标签切分**的全局条目池
- **AES `entry_tags`**：业务标签的倒排索引；用户订阅过滤**在 AES 库完成**，不依赖 Miniflux per-category 多次拉取
- **不要**：每个系统标签在 Miniflux 建一个 Category，读时调 K 次 Miniflux API 再合并——那是 RSS 层的「K 次查询」反模式

---

## 3. 用户体系（极简匿名 + 可选同步）

### 3.1 设计原则

- **零门槛**：首次打开即用，不弹注册。
- **本地优先**：稍后阅读、历史、订阅存浏览器（IndexedDB + Cookie）。
- **可选跨端**：用户自愿生成/输入 **6 位数字编码** 同步数据。
- **可选升级**：随时绑定微信，与 6 位码账号合并。

### 3.2 身份状态机

```
[访客] 首次访问
   │ 自动分配 device_id（Cookie，365d）
   │ 画像存 local IndexedDB
   ▼
[匿名用户] 仅有本机数据
   │ 设置页：「生成同步码」→ 6 位数字 + 服务端创建 sync_profile
   ▼
[可同步用户] 其他设备输入同一 6 位码 → 拉取/合并画像
   │ 可选：「绑定微信」
   ▼
[微信用户] openid 与 sync_profile 绑定；6 位码仍可作为备用同步方式
```

### 3.3 6 位同步码规则（建议）

| 项 | 规则 |
|----|------|
| 格式 | 6 位数字 `000000–999999`，用户自选或系统随机 |
| 冲突 | 创建时查重；冲突则提示换一个 |
| 合并策略 | 以 `updated_at` 较新为准；稍后阅读取并集 |
| 安全 | 6 位码 = 低安全便利方案；可「重置同步码」 |
| 存储 | 服务端 `sync_profiles` 存 JSON 快照 |

```sql
sync_profiles (
  sync_code TEXT PK,
  user_data JSON,
  wechat_openid TEXT NULL,
  created_at TEXT,
  updated_at TEXT
)

devices (
  device_id TEXT PK,
  sync_code TEXT NULL,
  last_seen TEXT
)
```

### 3.4 用户本地数据结构（IndexedDB）

```json
{
  "device_id": "uuid",
  "sync_code": null,
  "tag_subscriptions": ["tag_rhinoplasty", "tag_botox"],
  "settings": { "theme": "dark", "density": "comfortable" }
}
```

`read_later` **不再**作为 IndexedDB 主存（C3 修订）；稍后阅读列表以 **Miniflux starred** 为准。6 位码同步时 starred 状态随 Miniflux 用户（或映射表）同步。

### 3.5 与 Miniflux 的关系

- Miniflux：**聚合引擎** + **starred（稍后阅读）** API（C3）。
- 用户**未读/已读**：AES `user_read_state`（C35）；**随 6 位同步码同步**；与 starred 独立；**不**以 Miniflux unread 为用户真相源。
- **稍后阅读**：**Miniflux starred**；AES 代理并映射 `article_key` ↔ `miniflux_entry_id`。

### 3.6 微信绑定（可选，Phase 2+）

- 入口：设置 → 「绑定微信」
- 用途：跨端识别、未来通知；**不强制**

---

## 4. 阅读域细设（用户 + 编辑共用 UI）

> 用户与编辑看到的**文献列表和详情一致**。差异：编辑多顶栏「Console」、多底部「工作台」Tab；用户无筛选色、无纠错区。

### 4.1 稍后阅读 = 星标 ✅（C3 · 修订）

| 层 | 决策 |
|----|------|
| **语义** | 与用户个人收藏队列，同 Inoreader **星标** |
| **存储** | **Miniflux starred API**（AES API 代理 + 映射 `article_key` ↔ miniflux_entry_id） |
| **UI** | 文案/图标用 **「稍后阅读」🔖**，不用「星标」 |
| **同步** | 绑定 Miniflux 账号或 AES 统一 Miniflux 只读用户 + 6 位码映射（⬜ D24 多用户 starred 方案） |

### 4.1.1 已读 / 未读 ✅（C35 · Inoreader 式简化）

> **产品取向**（2026-06-23）：对齐真实 Inoreader 习惯——**清零按钮**最常用；**点开中间页停留约 1s** 判已读。**不要**列表扫过计时（不如手动清零干净）；**不要**单条「标已读/标未读」（要留用 🔖稍后阅读）。**拒绝** Folo 滚动标已读。

**语义**

| 状态 | 含义 | 要「留着」怎么办 |
|------|------|------------------|
| **未读** | 当前流里还没被 ① 或 ② 标掉 | — |
| **已读** | 中间页停留够久，或参与过一次清零 | 用 **🔖稍后阅读**（C3），不靠「标未读」 |

默认首页：已订阅并集，**未读优先**排序（§2.2）。已读条目**仍留在列表**（仅样式变淡/去蓝点），不自动消失——扫完靠清零收束。

**仅两条触发**

```
  未读 ──► ① 中间页停留 ≥1s ──► 已读
    │
    └──► ② 列表头「全部标已读」──► 已读（当前列表上下文内全部未读）
```

| # | 触发 | 规则 |
|---|------|------|
| **① 点开** | 桌面：右栏中间页展示该篇；移动：`/article/:key` | 同一篇连续展示 **≥1s** 写 `read_at`；快速划过多篇只标**最后停留够久**的 |
| **② 清零** | 中栏列表头 **「全部标已读」**（Inoreader 同款心智） | 将**当前列表上下文**内所有未读一次标已读（见下） |

**② 清零范围**（MVP）

| 当前页面 | 清零作用域 |
|----------|------------|
| `/` 订阅流 | 已订阅标签并集下的**全部未读**（非仅屏幕可见条） |
| `/tag/:tagId` | 该标签下**全部未读** |
| `/read-later` | **不提供**清零（队列语义，逐篇点开即可） |

确认：一次 `POST /read-state/mark-all-read`，服务端按 scope 批量 upsert；与 starred **无关**（稍后阅读里未读项也可被「订阅流清零」标已读——已读≠从稍后移除）。

**刻意不做**

| 不做 | 原因 |
|------|------|
| 列表滚过自动标已读 | 计时难调、易误标；用户习惯用清零 |
| 单条标已读 / 标未读 | 操作栏臃肿；收藏意图走稍后阅读 |
| 按侧栏「每个标签」各一个清零 | MVP 只做列表头一个按钮；单标签页进 `/tag/:id` 再清 |

**实现要点**

- ① 客户端：`article_key` 在中间页 mount 后 `setTimeout(1000)` → debounce `POST /read-state`。
- ② 批量：`mark-all-read` 一条 SQL `INSERT … ON CONFLICT` 或 `UPDATE … WHERE tag IN subscribed`。
- 读路径不变：`LEFT JOIN user_read_state`（§2.6.4）。

**UI**

- 列表头（中栏顶）：刷新｜**全部标已读**｜（P2+ 未读-only 筛选）
- 中间页操作栏：**🔖稍后 · 转发**（无「标已读」）

**设置**（§4.9）：默认排序（未读优先 / 时间序）；**无**扫过/grace 开关。

### 4.2 大流 vs 中间页 ✅（C28–C31）

| | 大流（列表卡片） | 中间页 `/article/:key` |
|--|------------------|-------------------------|
| **作用** | 扫标题、期数、标签 | 读摘要、外链、导读、转发落地 |
| **中文 MVP** | 标题、期数、作者、标签、库链图标 | **摘要全文** + 字段化元数据 + **转发** |
| **英文** | 中+英双标题、期数、标签、可选头图 | **必须**：导读 + AI 阅读 + 英文摘要 + 转发 |
| **流内下拉摘要** | ❌ 不做 | — |

**为何不用流内下拉**：转发需稳定 URL；英文导读/AI 阅读需版面；中英文交互统一。

#### 4.2.1 结构参考：Folo 对照结论（序 1 · §1.6.4）✅

| 结论 | 说明 |
|------|------|
| **三栏布局成立** | Folo 桌面「订阅侧栏｜列表｜详情」与 §4.3 同构；AES 右栏 = 中间页（非流内展开）。 |
| **稍后阅读独立域** | Folo Starred（`collections`）≈ 个人队列心智；AES 用 Miniflux starred + 文案「稍后阅读」（C3），路由 `/read-later`。 |
| **中间页优于流内详情** | Folo 在 `EntryContent` 内嵌 AISummary + 全文；AES **拒绝**流内下拉/展开（C28），导读与 AI 阅读**仅**中间页，以支撑转发 URL（C31）。 |
| **用户侧无时间线 AI** | Folo `timeline summary` / AI Timeline **不**迁入用户 Reader（C2）；编辑 digest 另议（序 6 YourRSS）。 |
| **中文无文首 AI 卡** | Folo 条目摘要卡对中英文一视同仁；AES 中文 MVP 中间页**仅**摘要+库链（C28/C15），英文中间页含导读区（C29）。 |

**桌面**：中间页 = 右栏详情（三栏布局 §4.3）；**移动**：跳转 `/article/:key` 全屏中间页。

**转发按钮**（中间页操作栏）：复制/分享 `https://reader…/article/{article_key}`；微信等可打开同一中间页。

### 4.3 桌面布局（≥1024px）

```
┌──────────────────────────────────────────────────────────────────────┐
│ Logo | 刷新 | [Console]※ | 同步码状态 | 设置                          │
├──────────┬─────────────────────────────┬─────────────────────────────┤
│ 左栏      │ 中栏 · 文献列表              │ 右栏 · **中间页**              │
│ 我的订阅  │                             │                             │
│ 稍后阅读  │                             │                             │
│ 标签订阅 →│                             │                             │
└──────────┴─────────────────────────────┴─────────────────────────────┘
※ 仅编辑可见
```

### 4.4 移动底部导航

**用户（4 Tab）**

```
[ 📥 订阅流 ]  [ 🔖 稍后 ]  [ 🏷 标签 ]  [ ⚙ 设置 ]
```

**MVP 无搜索入口**（C19）；P2+ 若加，放顶栏图标，不占 Tab。

**编辑（5 Tab）**

```
[ 📥 订阅流 ]  [ 🔖 稍后 ]  [ 🏷 标签 ]  [ 🛠 工作台 ]  [ ⚙ 设置 ]
```

### 4.5 文献卡片 `ArticleCard`（大流 · C26–C29）

**共用规则**

- Badge：`[CNKI]`/`[LWW]` = **平台**；第二 badge = **`issue_or_pub`**（如 `2026年06期` / `Jun 2026 · Vol 148(3)`），**不是** XML 前缀 `[当期目录]` / `Ahead of Print`。
- 元数据在卡片上 **一行摘要**（期刊 · 期数 · 作者）；完整字段在中间页 **逐行**（C27）。
- 点击卡片 → **中间页**（非流内展开）。

**中文 MVP（C28）**

```
┌────────────────────────────────────────────────────────────┐
│ [CNKI] [2026年06期]                            2h前        │
│ 皮肤镜结合皮肤生理指标检测在3%十二烷基硫酸钠斑贴试验…          │
│ 中国美容医学 · 叶聪秀等                                     │
│ [隆鼻] [激光]     [🔗知网] [🔖稍后]                          │
└────────────────────────────────────────────────────────────┘
```

- **无**导读徽章；**无** AI 阅读
- `🔗知网` / `🔗中华医学会` = 数据库原文链（可点，亦在中间页重复）

**英文（C29–C30）**

```
┌────────────────────────────────────────────────────────────┐
│ [LWW] [Jun 2026 · Ahead of Print]              3h前        │
│  （badge 仍用解析后的 issue_or_pub，上例可为 Jun 2026）      │
│ ┌──────────────────────────────────────────────────────┐   │
│ │  [可选：编辑选用的 PDF 插图装饰头图 · C32]              │   │
│ └──────────────────────────────────────────────────────┘   │
│ 糖尿病患者的皮肤健康                    ← title_zh_display   │
│ Skin Health in Patients With Diabetes Mellitus  ← title EN │
│ Plastic and Reconstructive Surgery · Sibbald, R. G.; …     │
│ [激光]  [🔗原文] [🔖稍后] [导读✓]                           │
└────────────────────────────────────────────────────────────┘
```

- 列表 **中文标题下方必须带英文原标题**（一行，可 truncate）
- `导读✓` / `笔记✓` = `reading_note_status=note_complete`；笔记正文仅在中间页

**用户不可见**：筛选色条、置信度、✓/✕ 纠错、附言、PDF 上传。

### 4.6 中间页 `/article/:articleKey`（C27–C31）

**布局原则**：元数据 **字段一行一个**（标签名 + 值 + 复制/外链按钮）。

#### 中文 MVP

| 字段块 | 内容 |
|--------|------|
| 标题 | 中文标题 |
| 期刊 | `journal` |
| 期数/出版时间 | `issue` / `pub_date` |
| 作者 | `authors` |
| 摘要 | `abstract`（原文，MVP **唯一**正文区） |
| 数据库链接 | `publisher_url` → 知网/CMA |
| 标签 | 系统标签 chips + 追订 |
| 操作栏 | 🔖稍后 · **转发** |

**无** AI 导读区、**无** AI 阅读（P5+ 再加导读，仍无 AI 阅读）。

#### 英文

| 字段块 | 内容 |
|--------|------|
| 头图 | `hero_image_url`（C32，可选） |
| 标题 | **中文译题**（主）+ **英文原标题**（副，完整） |
| 期刊 / 期数 / 发表时间 / 作者 | 各一行 |
| DOI / PMID / PII | 各一行，可复制 |
| 原文链接 | `publisher_url` |
| 摘要 | 英文 `abstract`（不翻译） |
| **阅读笔记** | `reading_note_zh`（§20.6；UI 文案「阅读笔记」或保留「AI 导读」） |
| **AI 阅读** | `doubao_read_url` → **外链**（C30）；非 AES 内嵌阅读 |
| 标签 + 操作栏 | 同左；**转发** 分享本页 URL |

**无**：纠错区、PDF 上传、Worker 触发（用户）。

### 4.7 英文装饰大图（C32 · 编辑侧）

```
PDF 就绪 → 自动抽取 figures/thumbnails
  → Console `/admin/fulltext` 或条目详情「选头图」
  → 编辑择一 → hero_image_url 写入 entries
  → 大流卡片（可选）+ 中间页顶图
```

规格 ⬜ D25：宽高比、裁切、无图时的默认占位——跟视觉设计规范单独立项。

### 4.8 标签订阅页 `/tags`

```
┌─ 我的订阅 (3) ──────────────────────────────┐
│  [隆鼻 ✓] [肉毒素 ✓] [激光 ✓]                 │
├─────────────────────────────────────────────┤
│  按分组浏览全部系统标签                         │
│  术式:  [隆鼻] [双眼皮] [吸脂] …               │
│  材料:  [玻尿酸] [肉毒素] …                    │
│  点击切换订阅 → 保存后刷新订阅流                  │
└─────────────────────────────────────────────┘
```

### 4.9 设置页 `/settings`（用户）

| 分组 | 项 |
|------|-----|
| 同步 | device_id、生成/输入 6 位同步码、上次同步、绑定微信 |
| 阅读 | 卡片密度、默认排序（未读优先 / 时间序）（§4.1.1） |
| 隐私 | 清除本机历史、退出同步码 |
| 关于 | 版本 |

### 4.10 阅读域路由

```
# 用户 + 编辑
/                          订阅流（默认首页；未订阅见 §2.2 空态）
/tag/:tagId                单标签浏览
/read-later                稍后阅读
/tags                      标签订阅管理
/article/:articleKey       中间页（移动全屏；桌面右栏）
/settings                  设置

# P2+ 可选
/all                       全部已打标文献（设置开关，见 D5）
/search                    标题+作者搜索（FTS，见 C19）

# 仅编辑
/editor                    移动工作台
/editor/worker             Worker 简版
/editor/pipeline           管线摘要
/editor/review             AI 待复核
/editor/tagging            待打标队列
/admin/*                   桌面 Console（§7.3）
```

---

## 5. 编辑在阅读域的补充

编辑使用与用户**相同的**订阅流 / 稍后阅读 / 标签页。内容生产集中在 **§7**，不在用户卡片上放 ✓/✕。

| 能力 | 入口 |
|------|------|
| 单篇打标 | 工作台 M9 或 Console D2 |
| AI 辅助筛选 | Console D3–D6 |
| 纠错/附言 | 工作台 M10 |
| PDF/Worker | 工作台 M4/M5 或 Console D11 |

---

## 6. 核心架构（技术层）

### 6.1 三层真源

| 层 | 存储 | 职责 |
|----|------|------|
| 内容 | `aes-feeds/*.xml` | 文献 + AI 总结注入 |
| 聚合 | Miniflux | 上游 poll、条目池 |
| 业务 | `aes_workflow.db` | 标签、entry_tags、筛选、Worker、feeds、sync_profiles |

### 6.2 文章唯一键

```
canonical_guid = doi:10.xxxx | pmid:12345 | pii:Sxxxx | cnki:v=… | cmaid:… | lww:{guid}
article_key    = sha256("aes" + "|" + canonical_guid)
```

- **跨渠道同一篇**必须算出 **同一个** `canonical_guid`（故随手入流强制先抽 DOI/PMID/PII，§16.1）
- `feed_id` / `ingest_source` 只记**来源**，**不参与**去重键
- 旧式 `sha256(feed_source_id + "|" + guid)` **废弃**——否则 KTN cron 与插件送入同一 DOI 会变成两条

### 6.5 全渠道入流去重 ✅（C24）

> **结论**：去重发生在 **L1 元信息补全之后、tag_worker 打标/筛选之前**。重复篇 **不重复打标、不重复进用户流**。

#### 6.5.1 两层去重（不要混）

| 层 | 范围 | 时机 | 存储 | 与 AES 关系 |
|----|------|------|------|-------------|
| **A 爬取去重** | 单期刊 cron 抓下来的条目 | 写 XML **前** | `cnki_dedup_log.json` 等 | 上游 pipeline；防重复爬 |
| **B 业务去重** | **全库**同一文献 | 写入 `entries` **前** | `entries` + `entry_identifiers` | **本章**；cron / 随手 / 微信 / 插件共用 |

用户问的「任何渠道」指 **B 层**。

#### 6.5.2 统一管道顺序（所有渠道）

```
cron XML ──┐
Miniflux ──┤
插件/微信 ──┼→ ① 解析原始条目
Console ───┘
        │
        ▼
     ② normalize_id（DOI / PMID / PII / platform_id）
        │
        ▼
     ③ dedup_lookup（查 entry_identifiers + entries 唯一索引）
        │
        ├─ 命中已有 article_key ──→ ④a 合并更新（可选）→ 记录 ingest 日志 → STOP
        │                              （不调 tag_worker，除非 force_retag）
        │
        └─ 未命中 ──→ ④b INSERT entries + entry_identifiers
        │
        ▼
     ⑤ enrich_metadata（§17.7 **分路由**；仅新篇或需补字段）
        │
        ▼
     ⑥ tag_worker（AI 打标 / 编辑向筛选）  ← 仅新篇或强制重标
        │
        ▼
     ⑦ entry_tags confirmed → 用户订阅流可见
```

**在筛选（打标）之前吗？** —— **是。** ③ 命中重复则 **不进 ⑥**；避免同一篇被 LLM 打标两次、订阅流出现两条。

#### 6.5.3 判重标准（lookup 逻辑）

> **不是**「先查 DOI，没有再查 PMID」的**解析串联**；是：输入里**有哪些码就查哪些码**，任一命中即视为同一篇。

**Tier 1 · 唯一码（自动判重，可靠）**

| 类型 | 键 | 说明 |
|------|-----|------|
| 英文 | **DOI** | 规范化后精确匹配 |
| 英文 | **PMID** | 精确匹配 |
| 英文 | **PII** | ScienceDirect 等，精确匹配 |
| 中文 | **cnki_v** / **cmaid** | 平台唯一 ID，精确匹配 |

```sql
-- 输入提取到 {doi?, pmid?, pii?, cnki_v?, cmaid?}
SELECT article_key FROM entry_identifiers
 WHERE (id_type, id_value) IN ( (:present_ids...) )
 LIMIT 1;
-- 任一命中 → duplicate
```

**Tier 2 · 弱判重（待样本验证后决定是否自动化）**

| 组合 | 状态 |
|------|------|
| **normalize(title) + normalize(journal)** | ⬜ **D22**：从 CNKI/CMA 无 platform_id 样本验证碰撞率；验证前 **仅进编辑手动合并队列**，不自动 dedup |

**跨标识符关联（冗余设计）**

同一篇文献可能先以 PMID 入流、后以 DOI 入流。补全 API 返回的**次要标识符**写入 `entry_identifiers`，均指向同一 `article_key`：

```
先 PMID 入流 → article_key_A
CrossRef 后来返回同篇 DOI → 写入 (doi, article_key_A)
再 DOI 入流 → lookup 命中 → duplicate ✅
```

**新建篇**时 `canonical_guid` 取值（仅用于生成 `article_key`，与 enrich 路由无关）：  
`doi` > `pmid` > `pii` > `platform_id`（取输入中**优先级最高且已有**的一个）。

```sql
entry_identifiers (
  id_type TEXT,
  id_value TEXT,
  article_key TEXT,
  PRIMARY KEY (id_type, id_value)
);
```

#### 6.5.4 命中重复时的行为

| 场景 | 行为 |
|------|------|
| 插件送入，cron 已有同 DOI | `200 { duplicate: true, article_key }`；微信回复「🔁 已收录」 |
| 新渠道带来更完整 abstract | **合并**更新 `entries` 空字段；`meta_status` 升级；**仍不**自动重跑 tag_worker |
| 编辑强制重标 | Console「重新打标」→ `force_retag=1` → 进 ⑥ |
| 仅 Miniflux 重复 poll 同一 XML item | ③ 命中 → 无写入；零成本 |

#### 6.5.5 为何依赖 DOI/PMID/PII（与 §16 一致）

若随手入流只存 URL、不抽标识符，则：

- KTN XML 用 `doi:10.xxxx` 作 guid
- 插件用 `sha256(ktn_feed|url)` 作 key  

→ **同一篇两条记录**，去重失效，打标与订阅流都会重复。

因此 **C22（标识符核心）是 C24（去重）的前提**。

#### 6.5.6 结构参考：Amadeus Tracker（序 2 · §1.6.5）✅

| 结论 | 对 AES 管线 |
|------|-------------|
| **源→编排→适配器** | 维持 `cnki_targets` + per-journal cron；学 Amadeus `runSource` 的**分源超时、单源失败隔离** |
| **爬取去重 ≠ 业务去重** | 与 §6.5.1 两层一致；`cnki_dedup_log` 不得替代 `entry_identifiers` lookup |
| **无用户侧 Tracker Feed** | Miniflux/XML 是编辑管道；用户流必须经 **打标 + 标签订阅**（C2） |
| **入库前截断 PDF** | ingest 止于 L1 元信息 + dedup；PDF/豆包在 §18–§20 状态机，非 Tracker 一环 |
| **判重键升级** | 不照搬 `arxiv_id`/`original_url LIKE`；坚持 §6.5.3 Tier 1 + C25 分路由 enrich |

### 6.3 服务拓扑

```
Mac 24/7
├── nginx :8080       → /feeds/ + /inbox/（随手入流，§16）
├── Miniflux :8081    → 聚合（cron XML + 随手源）
├── AES API :8301     → 业务 + 用户画像 + 编辑 RBAC + 状态机
├── AES App :8302     → 统一 PWA
├── Zotero Desktop    → PDF 资产库 + 元信息（§18，本机协作）
├── data/             → 扩展状态机目录（§19）
└── cron + batch_worker + doubao_rpa
```

### 6.4 内容生命周期总览（两层进阶）

```
入流（任意渠道）
  → ③ 去重 lookup（§6.5，打标前）
  → L1 元信息层（全自动，尽量完整）     ← §17
  → L2 全文层（半自动，编辑桌面批量）    ← §18
       ├─ PDF 获取（浏览器含权 + Zotero）
       └─ 豆包 AI 导读 + 分享链接        ← §20
  → Reader 展示（用户看导读；豆包链跳转全文）
```

**原则**：元信息正确 → 全自动；全文 PDF → **半自动**（机构权限页 + 人工/Zotero 补漏），由状态机在桌面 Console 批量推进。

### 6.4 移动端：后台与 Reader 合并 ✅（C5）

单一 PWA；编辑多「工作台」Tab；完整 Console 在桌面 `/admin`。

---

## 7. 编辑后台操作分级

### 7.1 分级原则

| 级别 | 场景 | 设备 | 特征 |
|------|------|------|------|
| **L0 阅读** | 读文献、稍后阅读、订标签 | 移动+桌面 | 与用户相同 |
| **L1 移动快捷** | 巡检、处置、确认、单条打标 | **手机优先** | 碎片化、单手、只读+少量确认 |
| **L2 桌面重处理** | 批量、大表单、日志、导入 | **桌面浏览器** | 大屏、键盘、向导、危险操作 |

### 7.2 L1 移动快捷 · 「工作台」操作清单

路径：`/editor`

| ID | 操作 | 说明 | 可操作 |
|----|------|------|--------|
| M1 | 管线红绿灯 | KTN/CNKI/CMA/LWW | 只看 |
| M2 | 今日巡检摘要 | patrol 日记最近 10 条 | 只看 |
| M3 | Worker 队列计数 | pending/processing/failed | 只看 |
| M4 | 处理下一篇 Worker | 触发 batch_worker 单篇 | **确认** |
| M5 | 重试失败 Worker | failed 列表 | **确认** |
| M6 | 手动刷新单源 | 选 A 批源触发 RSS | **确认** |
| M7 | 运行 patrol | pipeline_patrol | **确认** |
| M8 | AI 待复核 | AI 建议标签/筛选不确定 | **逐条确认/驳回** |
| M9 | 单篇快速打标 | 勾选系统标签 | **勾选保存** |
| M10 | 单条纠错 | 相关/无关 + 短附言 | **短输入** |
| M11 | 跳转桌面 Console | 深链 `/admin/*` | 链接 |
| M12 | 随手入流状态 | 查看微信/插件刚送入的 ingest 队列 | **只看 + 失败重试** |

**移动端禁止（必须 L2）**

| 操作 | 引导 |
|------|------|
| 编辑 System Prompt | 桌面 Console → 筛选引擎 |
| 学习集批量删改 | 同上 |
| 新增 CNKI 期刊（7 步） | 桌面 Console → 源管理 |
| OPML 导入 | 同上 |
| API Key / Miniflux 配置 | 同上 |
| 排除文件夹大列表 | 同上 |
| 完整日志 tail（>50 行） | 桌面 Console → 管线监控 |
| 系统标签 CRUD | 桌面 Console → 标签管理 |

### 7.3 L2 桌面 Console 操作清单

路径：`/admin`（需编辑 PIN）

#### A. 内容生产

| ID | 页面 | 操作 |
|----|------|------|
| D1 | `/admin/tags` | 系统标签 CRUD、分组、排序 |
| D2 | `/admin/tags/batch` | 批量打标、AI 建议复核 |
| D3 | `/admin/filter/prompt` | System Prompt、测试、版本 |
| D3b | `/admin/style-guide` | **中文表述规范**（D28）→ `data/style_guide.json`；**8300 维护**：侧边栏「文档维护」→ 中文表述规范 |
| D4 | `/admin/filter/learning` | 学习集分页、删改、导入导出 |
| D5 | `/admin/filter/excluded` | 排除文件夹 |
| D6 | `/admin/filter/cache` | 筛选缓存清理 |

#### B. 源与聚合

| ID | 页面 | 操作 |
|----|------|------|
| D7 | `/admin/feeds` | A/B 批源 CRUD |
| D8 | `/admin/feeds/scraped/:id` | A 批详情、RSS/Web、reset-journal |
| D9 | `/admin/feeds/opml` | OPML、Inoreader 迁移 |
| D10 | `/admin/feeds/sync` | 同步 Miniflux |

#### C. 加工、全文与管线

| ID | 页面 | 操作 |
|----|------|------|
| D11 | `/admin/fulltext` | 全文 Kanban：待 PDF / 待豆包 / 已完成 |
| D12 | `/admin/inbox/add` | 随手入流：DOI/PMID/PII / URL / BibTeX / Zotero |
| D13 | `/admin/worker` | 豆包 Kanban、批量重试 |
| D14 | `/admin/pipeline` | 通道、日记、日志 tail |

#### D. 系统

| ID | 页面 | 操作 |
|----|------|------|
| D15 | `/admin` | 仪表盘 |
| D16 | `/admin/settings` | Miniflux、API Key、危险区 |
| D17 | `/admin/users` | 同步码、微信审计（Phase 2） |

### 7.4 移动 ↔ 桌面对照总表

| 业务 | 移动 L1 | 桌面 L2 |
|------|---------|---------|
| 看管线状态 | M1/M2 ✅ | D14 ✅ |
| 处置 Worker / 豆包 | M4/M5 ✅ | D13 ✅ |
| 全文 PDF 批量 | ❌ → D11 | D11 ✅ |
| 随手入流 | 插件 / 微信 / Console D12 | D12 ✅ |
| 确认 AI 打标 | M8 ✅ | D2 ✅ |
| 单篇打标 | M9 ✅ | D2 ✅ |
| 单条纠错 | M10 ✅ | D4 ✅ |
| 维护系统标签 | ❌ → D1 | D1 ✅ |
| 调 Prompt | ❌ → D3 | D3 ✅ |
| 管学习集 | ❌ → D4 | D4 ✅ |
| 新增期刊源 | ❌ → D8 | D8 ✅ |
| OPML | ❌ → D9 | D9 ✅ |
| 系统配置 | ❌ → D16 | D16 ✅ |

### 7.5 移动工作台线框

```
┌─ 工作台 ────────────────────────────────────┐
│  管线  [KTN🟢] [CNKI🟢] [CMA🟡] [LWW🔴]      │
│        查看巡检 ›                           │
├───────────────────────────────────────────┤
│  Worker  待3 进行1 败0   [处理下一篇]        │
├───────────────────────────────────────────┤
│  待复核  12 篇 AI 建议       [去确认 ›]      │
│  待打标   5 篇               [去打标 ›]      │
├───────────────────────────────────────────┤
│  待全文   8 篇（无 PDF）     [桌面处理 ↗]      │
├───────────────────────────────────────────┤
│  [刷新源] [运行巡检] [查看入流队列] [Console ↗]  │
└───────────────────────────────────────────┘
```

---

## 8. 认证

### 8.1 用户

- 无需登录；`device_id` Cookie 自动签发。
- 可选 6 位同步码；可选微信（Phase 2）。

### 8.2 编辑

- **编辑 PIN** 解锁工作台 Tab + `/admin`。
- PIN 会话 24h（sessionStorage）。

---

## 9. API 概要

### 9.1 用户 API

```
GET  /api/entries?tags=subscribed&unread=1
GET  /api/entries/:articleKey
GET  /api/tags
GET  /api/user/profile
PUT  /api/user/profile
POST /api/user/read-later
POST /api/user/history
POST /api/user/sync/create
POST /api/user/sync/pull
POST /api/user/sync/push
# GET /api/entries/search?q=   ← P2+，FTS 标题+作者
```

### 9.2 编辑 API（需 editor 凭证）

```
GET  /api/editor/dashboard
POST /api/editor/worker/run-next
POST /api/editor/worker/retry/:id
POST /api/editor/patrol/run
GET  /api/editor/review-queue
POST /api/editor/review/:articleKey
POST /api/editor/tag-entry
POST /api/editor/verdict
POST /api/inbox/ingest              # 插件 / 微信 / Console；doi|pmid|pii|url
CRUD /api/admin/tags
CRUD /api/admin/feeds
PUT  /api/admin/filter/prompt
…
```

---

## 10. 与现有资产迁移

| 现有 | v1.2 去向 |
|------|-----------|
| `inoreader-aes-filter` | AI 筛选 → 编辑后台；扩展可演进为 **AES 送入插件**（§16.2.1） |
| 用户侧「筛选色」 | **废弃** → 系统标签 chips |
| Miniflux starred | **稍后阅读** 真源（C3）；AES 代理 + article_key 映射 |
| `feed_reader.html` | Reader 壳参考；**不**保留按平台浏览 |
| `ai_curator.py` | 编辑后台打标/质控 |
| `pipeline_patrol.py` | M1/M2 + D12 |

---

## 11. 实施分期

| 阶段 | 交付 | 用户 | 编辑 |
|------|------|------|------|
| P1 | 订阅流 + **中间页** + 标签库 + 中文摘要 MVP + Miniflux starred | 能读、能稍后 | — |
| P2 | 6 位同步 + **英文导读+AI 阅读** + 装饰头图 | 英文阅读闭环 | — |
| P3 | 编辑 PIN + 工作台 L1 + 标签 CRUD + **插件/Console 随手入流** | 同 | 移动看入流队列 |
| P4 | Console L2 + 元信息层完善 + PDF 状态机 UI + **微信转发入流** | 同 | 桌面重处理 |
| P5 | Zotero 协作 + 豆包 Worker 闭环 | **看导读+豆包链** | PDF→导读完整 |
| P6 | 微信绑定 + 广告主扩展 | 同 | 同 |

---

## 16. 入流渠道（cron XML 之外 · 随手添加）

> **与 §17 关系**：cron/XML 是批量入流；本章是 **编辑单篇补入**。英文走 **标识符分路由 API**；中文 CNKI/CMA 走 **平台 ID** 路径（§16.5）。

### 16.1 核心入参：DOI / PMID / PII ✅（C22）

随手入流的 **真输入** 是标识符，不是 URL 本身。  
**每种标识符有独立官方 API，互不串联**（有 DOI 只调 CrossRef，不会「DOI 失败再试 PMID」）。

| 标识符 | 示例 | **唯一**补全 API |
|--------|------|------------------|
| **DOI** | `10.1097/PRS.…` | CrossRef `/works/{doi}`（或 datacite，按 DOI 前缀） |
| **PMID** | `38123456` | PubMed E-utilities `efetch` |
| **PII** | `S0140673624003107` | Elsevier / ScienceDirect PII 接口 |

**DOI 太新 / 未登录**：CrossRef 404 或空 → **不转 PMID**；入 **`doi_retry_queue`** 间隔重试（§17.7），同时保留 XML/URL 已解析字段。

**可直接输入**：Console / 插件 / 微信均可提交纯 DOI、PMID、PII。

**URL 的角色**：从 URL **抽取**标识符（可抽出多个，如 PMC 页同时有 PMID）→ 对每个码做 lookup + 分路由 enrich：

```
URL / 纯文本
    ├─ 提取到 DOI      → dedup by DOI → enrich via CrossRef
    ├─ 提取到 PMID     → dedup by PMID → enrich via PubMed
    ├─ 提取到 PII      → dedup by PII → enrich via PII API
    └─ 仅 CNKI/CMA 链  → §16.5 platform_id
         │
         ▼
补全返回的次要 ID（如 CrossRef 带回 PMID）→ 写入 entry_identifiers（冗余关联）
         │
         ▼
tag_worker 打标
```

**禁止**：仅凭 URL 域名做「整页 scrape 当元信息真源」而不先落 DOI/PMID/PII——与 L1 设计不一致，且难与 cron/XML 条目 **dedup 对齐**。

### 16.2 入口位置 ✅（C23）

| 端 | 主入口 | 说明 | 阶段 |
|----|--------|------|------|
| **桌面** | **浏览器插件**（`browser_capture`） | 含权页一键「送入 AES」；自动取当前页 URL → 抽 DOI/PMID/PII；最顺手 | P3 |
| **移动** | **转发微信** | 编辑把文献链接/卡片 **转发给 AES 微信号**（个人号或企业号）；服务端 webhook 收消息 → ingest | P3–P4 |
| **桌面** | Console `/admin/inbox/add`（D12） | DOI/PMID/PII **直输**、URL、BibTeX、Zotero、XML；**全功能兜底** | P3 |
| **移动** | 工作台 M12 | **只看** ingest 队列状态、失败重试；**不**作为主要输入方式 | P3 |

```
编辑日常：
  桌面浏览文献页 → 插件一键送入
  手机看到链接   → 转发给 AES 微信 → 自动入队
  批量/调试      → Console D12
```

> **D11** ✅ Phase 1 **仅编辑**可入流；用户侧未来「荐稿」走同一 ingest 管道 + 待审队列。

#### 16.2.1 浏览器插件（桌面主入口）

| 项 | 规范 |
|----|------|
| 形态 | Chrome/Edge 扩展（可与现有 `inoreader-aes-filter` 演进或独立「AES 送入」） |
| 触发 | 工具栏按钮 / 右键「送入 AES」 |
| 行为 | 读 `location.href` + 页内 `<meta citation_doi>` 等 → 调 `POST /api/inbox/ingest` |
| 鉴权 | 编辑 PIN 或长效 editor token（仅存扩展本地） |
| 反馈 | 页内 toast：已入队 / 已存在 / 缺 DOI 请 Console 手输 |

#### 16.2.2 微信转发（移动主入口）

| 项 | 规范 |
|----|------|
| 形态 | AES **专用微信号**（企业微信或经认证的服务号/个人号企业能力，⬜ D21 选型） |
| 用户动作 | 在微信内打开文献 → **转发**给 AES 号（链接消息 / 公众号文章卡片） |
| 服务端 | 微信消息回调 → 解析 URL/文本 → 同 ingest 管道 |
| 回复 | 短消息：✅ 已收录《译题…》/ ⚠️ 缺 DOI 请桌面补 / 🔁 重复 |
| 与 C4 | 微信 **绑定**（用户同步）与 **入流号** 可同主体或分号；入流号仅编辑使用 |

### 16.3 渠道类型（汇总）

| 类型 | 代号 | 典型输入 | 谁操作 | 入流后 |
|------|------|----------|--------|--------|
| **A 批 cron** | `scraped` | — | 自动 | Miniflux poll XML |
| **B 批官方 RSS** | `official_rss` | — | 自动 | Miniflux poll |
| **浏览器插件** | `browser_capture` | 当前页 URL → DOI/PMID/PII | 编辑 | ingest → entries |
| **微信转发** | `wechat_forward` | 链接/卡片 → URL → 标识符 | 编辑 | 同上 |
| **Console 直输** | `manual_id` | DOI / PMID / PII 字符串 | 编辑 | 同上 |
| **Console URL** | `manual_url` | URL（解析为三键之一） | 编辑 | 同上 |
| **Zotero 导入** | `zotero_import` | 条目 DOI/title | 编辑 | 对齐或新建 |
| **单篇 XML 注入** | `xml_inject` | inbox/*.xml | 编辑 | 同 cron 解析器 |
| **批量文件** | `batch_bib` | RIS/BibTeX/CSV | 编辑 Console | 批量建条目 |

### 16.4 Console UI（兜底 · D12）

**`/admin/inbox/add`**

```
添加方式:  [DOI/PMID/PII] [粘贴 URL] [上传 BibTeX] [Zotero] [手写 XML]

标识符（推荐）:
  DOI:  _______________________
  PMID: _______________________
  PII:  _______________________
  （填其一即可；三键优先于 URL）

或 URL: _______________________  → [解析标识符] 预览

目标标签: [隆鼻] [肉毒素]  （可选，默认进待打标）
[抓取元信息] → 预览 → [入队]
```

### 16.5 中文例外路径（CNKI / CMA）

多数中文刊 **无 DOI/PMID/PII**。URL 无法抽出三键时：

```
cnki.net / yiigle.com / cma 域名
    → 提取 platform_id（v= / cmaid / guid）
    → 平台页或已有 XML 解析器补 L1
    → meta_status 可 complete（不强制 DOI）
    → 不走 CrossRef/PubMed 主路径（§17.7）
```

与英文 **同 ingest API**，响应里 `id_type=platform` 区分即可。

### 16.6 技术路径与 API

```
任意入口（插件 / 微信 / Console）
    → POST /api/inbox/ingest
         body: { doi?, pmid?, pii?, url?, source: browser|wechat|console }
    → normalize_id()           // 直输 or 从 URL 抽取
    → dedup_lookup()           // §6.5 ③ 打标前；命中则 duplicate
    → enrich_metadata()        // §17.7 分路由（仅新篇或需补全）
    → INSERT/UPDATE entries + entry_identifiers
    → tag_worker（仅新篇或 force_retag）
    → 200 { article_key, title, meta_status, duplicate? }
```

**article_key**：见 §6.2 `canonical_guid` 规则；**dedup 靠 identifier lookup，不靠 feed_id**。

### 16.7 与 Miniflux

- cron/B 批仍走 Miniflux poll
- 随手入流 **可直接写 entries**，Miniflux 订阅 `inbox/*.xml` **可选**（便于与现有 RSS 工具链兼容，非必须）

---

## 17. 元信息层（L1）· XML 采样与字段规范

### 17.1 三层模型（L1 / L2 / L3 分离）✅

| 层 | 内容 | 谁消费 | 数据来源 | 与「阅读笔记 Pass」关系 |
|----|------|--------|----------|-------------------------|
| **L1 元信息** | 标题、作者、期刊、期数、DOI、**源摘要**、标签… | **卡片 + 中间页元信息行** | cron/XML、CrossRef、PubMed（§17.7） | **无关**；入流即有，不等 PDF |
| **L2 全文资产** | PDF 文件、Zotfile 附件 | 编辑管线 | `data/pdf/`、Zotero（§18） | 笔记与豆包链的**输入**，不展示给用户 |
| **L3 阅读笔记** | 结构化中文 **阅读笔记**（原 `ai_summary_zh`） | 中间页 **笔记区**（英文 P2+；中文 P5+） | §20.6 `note_worker` | **本章重点**；依赖 L2 PDF 时质量最高 |

```
入流 ──► L1（entries 卡片字段）──────► 用户列表/中间页元数据行
              │
PDF 就绪 ──► L2 ──┬──► L3 阅读笔记（1×文本 LLM，结构化 prompt）
                  └──► doubao_read_url（1×RPA 外链，用户自己点开深读）
```

**深读梯再划清**（C34）：

- **略读**：L1 摘要 + 元信息（无笔记）
- **精读**：L3 **阅读笔记**（AES 算力/API）
- **全文辅助**：**豆包外链**（AES **不**托管、**不**为阅读付推理算力，仅 RPA 生成链接）

### 17.2 现有 XML 实测采样（2026-06-20）

#### CNKI（中文期刊 · web 深度爬取）

| 字段 | XML 来源 | 示例 | 备注 |
|------|----------|------|------|
| 标题 | `<title>` | `[当期目录] [2026年06期] 皮肤镜结合…` | 含栏目前缀，需解析 |
| 链接 | `<link>` | `kns.cnki.net/kcms2/article/abstract?v=…` | 摘要页，非 PDF |
| 作者 | `description` | `叶聪秀;易金玲;…` | 结构化 HTML |
| 期数 | `description` | `2026年06期` / `网络首发` | |
| 页码 | `description` | `1-6` | |
| 摘要 | `description` | **通常无**（仅三行元信息） | RSS 模式有摘要，web 模式常缺 |
| GUID | `<guid>` | `08be4ef3…`（32 位 hash） | **稳定主键** |
| pubDate | `<pubDate>` | ✅ | |
| DOI | — | **XML 中无** | 需二阶：抓摘要页或 CNKI API |
| PMID | — | **无** | 中文刊一般无 |
| CNKI 专用码 | `link` 参数 `v=` | 长加密串 | 可存为 `platform_id` |

#### CMA / 中华系列（中文 · yiigle）

| 字段 | XML 来源 | 示例 | 备注 |
|------|----------|------|------|
| 标题 | `<title>` | `抗p200类天疱疮…` | CDATA |
| 链接/GUID | `<link>` / `<guid>` | `rs.yiigle.com/cmaid/1683577` | **cmaid 即平台 ID** |
| 作者 | `<author>` + description | ✅ | |
| 期数 | description | `2026年59卷05期` | |
| 摘要 | description `<b>摘要：</b>` | ✅ **较完整** | 优于 CNKI web |
| DOI/PMID | — | **无** | |

#### LWW（英文 · Wolters Kluwer）

| 字段 | XML 来源 | 示例 | 备注 |
|------|----------|------|------|
| 标题 | `<title>` | ✅ | |
| 作者 | `<author>` | `Adler, Neta; …` | |
| 栏目 | `<category>` | `Breast: Original Articles` | 可作标签候选 |
| 摘要 | `<description>` | 常有 `No abstract available` | 不稳定 |
| **DOI** | `<citation>` | `doi: 10.1097/PRS.0000000000012568` | **需 regex 提取** |
| LWW 专用码 | `<guid>` | `00006534-202606000-00003` | 出版社内部 ID |
| pubDate | `<pubDate>` | ✅ | |
| PMID | — | **XML 中无** | |

#### KTN / Google Scholar 告警（英文 · 混杂源）

| 字段 | XML 来源 | 示例 | 备注 |
|------|----------|------|------|
| 标题 | `<title>` | ✅ | |
| 链接 | `<link>` | 常含 `/doi/10.xxxx` | **DOI 可从 URL 抽** |
| GUID | `<guid>` | 常 = link URL | |
| 摘要 | description | Google 告警**上下文块**，噪声大 | 需清洗，非标准摘要 |
| PMID/PMCID | link 域名 | `pmc.ncbi.nlm.nih.gov/articles/PMC13268452` | **从 URL 抽 PMCID** |
| PDF 直链 | link | 部分条目 link 即 `.pdf` | 可自动进 L2 |

### 17.3 统一元信息 schema（`entries` 表扩展）

```sql
entries (
  article_key TEXT PK,
  feed_id TEXT,
  lang TEXT,              -- zh | en
  title TEXT,                -- canonical：中文=原文；英文=英文原标题
  title_zh_display TEXT,     -- 英文：列表用中文译题；中文=title
  title_prefix TEXT,         -- [当期目录] 等
  journal TEXT,              -- 期刊名
  authors TEXT,              -- 不翻译
  abstract TEXT,             -- 原文语言
  abstract_zh TEXT,          -- 可选；默认英文不译摘要（D16）
  doi TEXT,
  pmid TEXT,
  pmcid TEXT,
  pii TEXT,                  -- ScienceDirect 等
  platform TEXT,        -- cnki|cma|lww|ktn|official|manual
  platform_id TEXT,       -- cnki_v | cmaid | lww_guid | ...
  source_url TEXT,           -- 官网/数据库落地页（展示用）
  publisher_url TEXT,        -- 英文：期刊社原文页；中文：CNKI/CMA 链接
  issue TEXT,
  pages TEXT,
  pub_date TEXT,
  meta_tier TEXT,            -- A|B|C|D|E 见 §23.3
  meta_enrich_source TEXT,   -- xml|crossref|pubmed|pii|manual
  -- L3 阅读笔记（与 L1 卡片字段分离 · C36）
  reading_note_status TEXT,  -- none|outline_ready|note_pending|note_complete|note_failed
  reading_note_zh TEXT,      -- 用户可见结构化笔记（Markdown 或 JSON 渲染）
  reading_note_schema TEXT,  -- 如 v1_clinical_pass2
  reading_note_at TEXT,      -- 生成时间
  pdf_outline_json TEXT,     -- 本地抽取：章节标题、页码、结论段（供 note_worker，非用户展示）
  ai_summary_zh TEXT,        -- 兼容旧字段名 = reading_note_zh（迁移期别名）
  doubao_read_url TEXT,      -- 仅英文 L2；外链全文，非 AES 阅读算力
  ...
)
```

**卡片/列表 API 只返回 L1 轻字段** + `reading_note_status`（供 `笔记✓` 徽章）；**不**返回 `reading_note_zh` 全文（详情接口再取，§2.6.5）。

### 17.4 标识符获取策略

| 标识符 | CNKI | CMA | LWW | KTN/GS | 二阶补全 |
|--------|------|-----|-----|--------|----------|
| DOI | ❌ XML | ❌ | ✅ citation | ✅ URL regex | CrossRef；**滞后时延迟重试** |
| PMID | ❌ | ❌ | ❌ | ✅ PMC URL | PubMed API（**一般无滞后**） |
| PMCID | ❌ | ❌ | ❌ | ✅ URL | — |
| PII | ❌ | ❌ | ❌ | ✅ SD URL | Elsevier PII API（**独立路由**，非 DOI 失败兜底） |
| 平台专用码 | `v=` 参数 | `cmaid` | `guid` | link | — |

**L1 完成条件**：

| 语言 | 条件 |
|------|------|
| **英文** | `title` + `authors` + `journal` + (`doi` OR `pmid` OR `pii` OR `platform_id`) + (`abstract` OR 标记 partial） |
| **中文** | `title` + `authors` + `journal` + 期数或出版时间 + `publisher_url`（CNKI/CMA） |

### 17.5 中英文展示分轨（概要）

> **完整规范见 §23**（字段清单、补全流水线、翻译、AI 导读/豆包分轨）。

| | 中文期刊 | 英文期刊 |
|--|----------|----------|
| 流内标题 | 原文中文标题 | **中文翻译标题**（`title_zh_display`） |
| 详情原标题 | 同左 | **英文原标题**完整展示 |
| 卡片元信息行 | 期刊 · 期数 · 作者 | 期刊 · 发表时间 · 作者 |
| 标识符 | CNKI/CMA 数据库链接 | DOI · PMID · PII（若有） |
| PII | — | ScienceDirect URL `/pii/Sxxxx` |
| 摘要 | 原文（XML/补全） | 英文原文（⬜ D16 是否展示） |
| AI 导读 | ✅ 中文 | ✅ 中文（基于 PDF 提示词） |
| 豆包 AI 辅助阅读 | ❌ 不提供 | ✅ 分享链接 |
| 官网原文链接 | 数据库链接 | ✅ 出版社页面 |

### 17.6 XML 采样方法论（制定分类策略用）

对 `aes-feeds/*.xml` 做**可重复**的字段覆盖率审计，再定补全策略：

```
Step 1 · 源分类
  按 feed 文件归入：cnki | cma | lww | ktn_gs | official_b
  记录：文件名、channel title、典型 item 数

Step 2 · 逐条字段矩阵（每类抽 ≥5 item）
  对每条 item 打勾：title / author / journal / issue / pub_date /
  abstract / doi / pmid / pmcid / pii / platform_id / source_url

Step 3 · 归入补全 Tier（见 §23.3）
  Tier-A：XML 或 URL 已有 DOI
  Tier-B：仅有 PII（ScienceDirect 等）
  Tier-C：仅有 PMID/PMCID（URL 特征）
  Tier-D：仅平台专用码（cnki_v、cmaid、lww_guid）
  Tier-E：KTN 告警块（摘要噪声，需清洗）

Step 4 · 跑级联补全试跑
  每 Tier 抽 3 条 → DOI→CrossRef / PMID→PubMed / PII→Elsevier API
  记录成功率、滞后需重试比例

Step 5 · 写入补全规则表（§23.4）→ 实现 meta-enricher
```

**维护**：新增期刊源或 XML 格式变更后，重跑 Step 2–4，更新 §17.2 采样表。

### 17.7 元信息补全：分路由 + 冗余 ✅（C25）

> **纠正**：不是「DOI → PMID → PII 串联 fallback」。  
> **有哪个码，走哪条 API**；码之间通过 `entry_identifiers` **关联同一篇**。

#### 17.7.1  enrich 路由（互斥，按**输入已有**标识符）

| 入参已有 | 调用 | 不调用 |
|----------|------|--------|
| **DOI** | CrossRef（或 DataCite） | PubMed、PII |
| **PMID**（且无 DOI） | PubMed E-utilities | CrossRef、PII |
| **PII**（且无 DOI/PMID） | Elsevier / SD PII API | CrossRef、PubMed |
| **cnki_v / cmaid** | 平台页 / 已有 XML 字段 | 英文 API 链 |

若 URL/XML **同时**抽出 DOI 与 PMID：** enrich 以 DOI → CrossRef 为准**（一次调用）；PubMed 仅当**没有 DOI** 时才作为 enrich 入口。

#### 17.7.2 冗余：补全后回写关联 ID

CrossRef / PubMed 响应常含多种 ID → **全部写入** `entry_identifiers`：

```
CrossRef(doi:10.xxx) → { pmid: 123, pii: S… } → 关联到同一 article_key
```

便于后续任意渠道以任一码入流时命中判重。

#### 17.7.3 DOI 滞后：重试队列（非换 API）

```
CrossRef 404 / 空 metadata / 明显不完整
    → meta_status = partial
    → INSERT doi_retry_queue (article_key, doi, next_retry_at, attempt)
    → 保留 XML/URL 已有 title/author/journal
    → 用户流可展示 partial（或等 complete，⬜ 产品定）
    → cron 按间隔重试：建议 24h → 72h → 7d（D18）
    → 成功 → complete，写入关联 PMID 等
    → 仍失败 → 留 partial，编辑 Console 手动补
```

**不用 PMID 替代 DOI enrich**——二者是不同入口；仅当**入参本身只有 PMID** 时才走 PubMed。

#### 17.7.4 中文

CNKI/CMA：以 XML + `platform_id` 为主；无 DOI/PMID 主路径。缺 platform_id 时 **不自动** title+journal 判重（见 §6.5.3 Tier 2 / D22）。

---

## 18. PDF 全文（L2）· Zotero 协作

### 18.1 现状（as-is）

```
Mac 浏览器：机构权限保活
  → 打开文献页（含权）
  → 点 Zotero Connector：自动抓元信息 + PDF（不稳定，常漏 PDF）
  → 漏抓时：手动下载 PDF → 上传
```

**结论**：全文获取 = **半自动为主**；全自动仅适用于 link 即 PDF 的条目（部分 KTN/LWW）。

### 18.2 推荐方案：Zotero 作 PDF 主库 ✅（建议）

| 能力 | Zotero | AES 系统 |
|------|--------|----------|
| 元信息读取 | ✅ 拖 PDF 即解析 | L1 以 XML/cron 为准，Zotero 补全 |
| PDF 存储 | ✅ 主仓库 | `data/pdf/{article_key}.pdf` 作 Worker 副本 |
| 浏览器抓取 | ✅ Connector（半自动） | 状态机记录成败 |
| 与 Reader | 通过 DOI/title 对齐 `article_key` | 展示导读不直接嵌 PDF |

**分工**：

- **Zotero** = 编辑的文献资产库、PDF 真相（长期归档）
- **AES `data/pdf/`** = Worker 加工用**副本**（豆包只吃这里的文件）
- **XML description** = 用户可见的 **AI 导读 + 豆包分享链接**

### 18.3 获取模式对比

| 模式 | 适用 | 自动化 | 备注 |
|------|------|--------|------|
| **全自动** | link 直链 PDF；开放获取 | 高 | 脚本下载 → `pdf_inbox/` |
| **Zotero Connector** | 含权期刊页 | 中 | 元信息稳、PDF 漏抓需补 |
| **手动下载上传** | CNKI/付费墙 | 低 | Console 批量上传区 |
| **browseract 智能体** | 知网验证码（未来） | 待定 | 悬案，不阻塞 P5 |

> ✅ **已定方向**：**半自动**为默认路径；全自动仅作补充通道。

### 18.4 对接流程

```
编辑在含权页保存到 Zotero
  → Zotero 监听器（本机）/ 手动「从 Zotero 同步」
  → AES 按 DOI/title/platform_id 匹配 article_key
  → 有 PDF：复制到 data/pdf_inbox/{article_key}.pdf
  → 状态机 fulltext_status: has_pdf
  → 进入豆包队列（§19）
```

**漏 PDF 处理**（Console `/admin/fulltext`）

```
待全文列表（meta 完成但无 PDF）
  [在浏览器打开] [已从 Zotero 同步] [上传 PDF] [跳过]
```

### 18.5 PDF 管理入口

| 入口 | 端 | 操作 |
|------|-----|------|
| Zotero Desktop | 桌面 | 主库增删、Connector 抓取 |
| Console `/admin/fulltext` | 桌面 L2 | 批量待全文、上传、同步 Zotero |
| 工作台 `/editor/fulltext` | 移动 L1 | 只看计数 + 打开待全文列表（只读为主） |
| Reader 详情 | 用户 | **不展示 PDF**；只展示 AI 导读 + 豆包外链 |

---

## 19. 扩展状态机（含 PDF 全流程）

### 19.1 回答：原状态机是否包含 PDF？

**v1.0 仅覆盖豆包加工四车间**（`pending/processing/completed/failed`），**未覆盖** PDF 获取与 Zotero 同步。

**v1.3 扩展为完整文献加工状态机**：

### 19.2 状态定义

```
── 入流 ──
INGESTED          新条目通过 §6.5 去重后入队（重复篇不重复 INGESTED）
DEDUP_SKIP        命中已有 article_key，仅记 ingest 日志（可选状态）

── L1 元信息 ──
META_PENDING      等待解析
META_PARTIAL      缺 DOI/摘要等，可二阶补全
META_COMPLETE     元信息达标，对用户可见

── L2 全文 PDF ──
PDF_NONE          无全文
PDF_QUEUED        编辑标记需要全文 / 自动判断高价值
PDF_AUTH_READY    已打开含权页（浏览器任务，桌面批量）
PDF_DOWNLOADING   下载中
PDF_HAS_FILE      data/pdf/ 或 Zotero 已有附件
PDF_ZOTERO        已入 Zotero 主库
PDF_FAILED        下载/抓取失败

── L3 阅读笔记 + 豆包外链（解耦 · C36）──
NOTE_PENDING      PDF 已就绪，outline 待抽或笔记待生成
NOTE_PROCESSING   note_worker（API LLM）运行中
NOTE_COMPLETE     reading_note_zh 已写入
NOTE_FAILED       笔记失败待重试
DOUBAO_PENDING    英文：排队生成外链（可与 NOTE 并行）
DOUBAO_PROCESSING doubao_rpa 运行中
DOUBAO_COMPLETE   doubao_read_url 已写入（**不含**笔记正文）
DOUBAO_FAILED     外链失败待重试

── 发布 ──
PUBLISHED         用户 Reader 可见：L1 +（可选）阅读笔记 +（英文）豆包外链
```

### 19.3 目录与 v1.0 四车间映射

```
data/
├── inbox/              随手入流待解析
├── meta_queue/         L1 二阶补全队列
├── pdf_inbox/          新 PDF 待匹配 article_key（原 pending 语义扩展）
├── pdf_processing/     正在匹配/校验
├── pdf_ready/          已关联 article_key，待豆包（→ 原 pending 入口）
├── doubao_processing/  原 processing/
├── doubao_completed/   原 completed/
├── doubao_failed/      原 failed/
└── zotero_watch/       待从 Zotero 拉取的 attachment 清单（JSON）
```

### 19.4 桌面批量 vs 移动碎片化

| 状态迁移 | 移动 L1 | 桌面 L2 |
|----------|---------|---------|
| INGESTED → META_COMPLETE | — | 自动 + 手动补全 |
| META_COMPLETE → PDF_AUTH_READY | — | **批量打开含权页**（浏览器任务列表） |
| PDF 上传 / Zotero 同步 | 单篇上传 | **批量上传、Zotero 全量同步** |
| PDF_HAS_FILE → NOTE_PENDING / DOUBAO_PENDING | 「处理下一篇」M4 | Kanban D11 |
| NOTE_COMPLETE / DOUBAO_COMPLETE → PUBLISHED | 自动 | 自动写 entries（XML 注入可选） |

**桌面 Console 新增页** `/admin/fulltext`：按状态列 Kanban（元信息 / 待 PDF / 待豆包 / 已完成）。

---

## 20. 阅读笔记与豆包外链（Reader 对接）

> **L3 阅读笔记**（`reading_note_zh`）展示在 **中间页笔记区**；**豆包外链**（`doubao_read_url`）仅英文「AI 阅读」按钮，**不是导读**（C36）。  
> **导读生产**：`note_worker` + **LLM API** + 结构化 prompt（§20.6）。**不用** Web 豆包 RPA 作为导读终态。  
> **豆包 Web RPA**（`doubao_rpa.py`）：仅 (1) 生成 `doubao_read_url`；(2) **开发期**用同一账号试跑 prompt，与线上导读管线分离。

### 20.1 英文文献 · 详情 AI 区

```
┌─ 阅读笔记（中文）────────────────────────────────┐
│  基于 L1+PDF 结构抽取 + 1×LLM 的结构化笔记        │
├─────────────────────────────────────────────────┤
│  [📖 AI 阅读 ↗]  ← 豆包外链；用户自行深读全文      │
│  笔记生成于 2026-06-20 14:30                     │
└─────────────────────────────────────────────────┘
```

### 20.2 中文文献 · 详情 AI 区

```
┌─ 阅读笔记（中文，P5+）──────────────────────────┐
│  基于 PDF outline + LLM（若有 PDF）              │
│  或基于 L1 元信息/摘要的轻量笔记（若无 PDF）       │
├─────────────────────────────────────────────────┤
│  （不提供豆包全文阅读 — 中文版权敏感 C15）         │
└─────────────────────────────────────────────────┘
```

### 20.3 状态与用户可见

| 状态 | 中文 | 英文 |
|------|------|------|
| 仅有 L1 元信息 | 摘要 +「笔记筹备中」 | 同左 |
| 笔记处理中 | 「正在生成阅读笔记…」 | 同左 |
| 笔记已完成 | 阅读笔记 | 阅读笔记 |
| 豆包处理中（英文） | — | 笔记区下「正在生成 AI 阅读链接…」 |
| 外链已完成（英文） | — | 阅读笔记 + **AI 阅读** 按钮 |
| 无 PDF | 轻量笔记或筹备中 | 同左；无豆包链 |

### 20.4 技术链

```
L1 入流 → 卡片字段（与导读无关）

PDF 就绪
  ├─ note_worker（导读 · 中间页）
  │     LLM API（DeepSeek / OpenAI / Claude 等，⬜ D27 定稿）
  │     + PDF 文本抽取（或 API 原生读 PDF）
  │     + prompts/reading_note_{type}.md
  │     → reading_note_zh
  │
  └─ doubao_rpa（英文 · 仅外链，非导读）
        → doubao_read_url
```

| 能力 | 终态方案 | 现状 |
|------|----------|------|
| **AI 导读** | **API** `note_worker` | prompt 在 `prompts/`；可用豆包 RPA **临时试 prompt**，非生产 |
| **AI 阅读外链** | 豆包 Web RPA | `doubao_rpa.py` 已有 |

### 20.5 权限

| | 用户 | 编辑 |
|--|------|------|
| 看 AI 导读 | ✅ | ✅ |
| 点豆包链接（英文） | ✅ | ✅ |
| 触发加工 | ❌ | ✅ |

### 20.6 阅读笔记生产管线 ✅（C36 · 重点）

> **中间页导读**：`reading_note_brief` · **≤1000 字** · **无人工审校** · API `note_worker` 生产。  
> **深读**：豆包外链（chip 起句即可，用户自有账号续聊）。**不含**术语表 G、AB 全文纲要、MSDC/FUL 翻译链。

#### 20.6.1 导读定稿（v0.2 · 用户工作流）

| 决策 | 结论 |
|------|------|
| 展示 | 仅中间页 `reading_note_zh` |
| 长度 | **≤1000 汉字**；AB 过长，不作为导读 |
| 术语表 | **跳过** G；brief 内术语「中文（English）」首现即可 |
| 创新性 | 纳入 **「为什么值得读」**；从编辑「是否值得报道」改为读者「读完多知道什么」；**不**伪检索 PRS/ASJ/JCD |
| 质量 | 接受无人工审校误差；纪律靠 prompt 反编造 |
| 豆包 | 导读 **不用** Web RPA 终态；RPA 仅外链或开发试跑 |

**五节 schema**（`prompts/reading_note_brief.md`）：

1. **为什么值得读** — 创新/贡献/阅读价值（读者视角）  
2. **研究概要** — 设计、人群、干预对照（极简）  
3. **主要结果** — 数字为主  
4. **安全性与局限**  
5. **深读提示** — 建议全文哪几块值得看（导向豆包链）

**表述规范**（D28）：生成导读/译题时注入 [`data/style_guide.json`](../data/style_guide.json)（用词、术语、句法）；**8300 总控台**侧边栏「文档维护」→ [`aes-writing-style.html`](http://localhost:8300/projects/aes-writing-style.html)（离线回退 [`admin/style_guide.html`](../admin/style_guide.html)）。详见 [`docs/aes_writing_style.md`](../docs/aes_writing_style.md)。

#### 20.6.2 技术链

```
PDF → note_worker（LLM API + _shell_brief + reading_note_brief）→ reading_note_zh → 中间页
英文并行：doubao_rpa → doubao_read_url（深读外链，chip 起句）
```

Prompt 资产见 **`prompts/README.md`**。v0.1 长模板（`reading_note_rct` 等）已归档，非默认。

#### 20.6.3 与卡片字段的边界

| 展示位置 | 字段来源 | 示例 |
|----------|----------|------|
| 卡片 badge | L1 | `[LWW]`、`issue_or_pub`、标签 |
| 卡片一行 | L1 | 期刊 · 期数 · 作者 |
| 中间页元信息行 | L1 | DOI、PMID、各一行（C27） |
| 中间页摘要区 | L1 `abstract` | 原文，非 AI 改写 |
| 中间页笔记区 | L3 `reading_note_zh` | **唯一** AI 生成正文 |
| AI 阅读按钮 | L2 RPA | 外链 URL |

**禁止**：用阅读笔记 Pass 回写或覆盖 `title`/`authors`/`doi`/`abstract`（L1 真源不变）。

#### 20.6.4 Prompt 资产（D26）

| 文件 | 状态 |
|------|------|
| `prompts/_shell_brief.md` + `reading_note_brief.md` | 🟢 **v0.2 生产默认** |
| `data/style_guide.json` + `style_guide_loader.py` | 🟢 **D28 表述规范** |
| `prompts/reading_note_rct.md` 等 | 归档参考 |
| `prompts/editor/` | AB/翻译链，不进中间页 |

#### 20.6.5 豆包 RPA

| 用途 | prompt | 说明 |
|------|--------|------|
| **深读外链** | chip「详细总结」等 | 用户自有账号续聊 |
| **试跑导读** | `--prompt-type brief` | 开发期；终态改 API `note_worker` |

#### 20.6.8 状态机（§19）

| 状态 | 含义 |
|------|------|
| `PDF_HAS_FILE` | 可跑导读 Worker |
| `NOTE_PENDING` / `NOTE_PROCESSING` | 结构化 prompt 队列 |
| `NOTE_COMPLETE` | `reading_note_zh` 就绪 → 中间页展示；卡片 `笔记✓` |
| `DOUBAO_COMPLETE` | 英文 `doubao_read_url` 就绪（与 NOTE 独立） |
| `PUBLISHED` | L1 达标且（英文）笔记或外链至少一项可用 |

---

## 23. 中英文文献格式与元信息策略（详细）

> 英文文献占**绝大多数**；中文主要来自 **CNKI + 中华医学会（CMA）**。  
> 已确认：**C12–C15**。

### 23.1 文献语言判定

| `lang` | 来源 | 判定规则 |
|--------|------|----------|
| `zh` | CNKI、CMA、部分中文 CMA 频道 | `platform in (cnki, cma)` 或标题 CJK 占比 |
| `en` | LWW、KTN/GS、B 批官方 RSS | 其余默认 `en` |

### 23.2 元信息字段清单

#### 英文文献（目标：尽量完整）

| 字段 | 必填 | 来源优先级 |
|------|:----:|------------|
| 标题（英文原标题） | ✅ | XML `<title>` |
| 标题（中文译题，列表用） | ✅ | LLM/翻译 API（§23.5） |
| 作者 | ✅ | XML `<author>`；不翻译 |
| 期刊 | ✅ | channel title / citation / CrossRef |
| 期数 / 发表时间 | ✅ | citation / pubDate / CrossRef |
| DOI | 尽量 | citation → URL → CrossRef |
| PMID | 尽量 | PubMed（由 DOI 或 title 查） |
| PII | SD 专用 | URL `/pii/S…` |
| 摘要（英文） | 尽量 | XML description → CrossRef/PubMed |
| 官网原文链接 | ✅ | XML `<link>` = `publisher_url` |

#### 中文文献

| 字段 | 必填 | 来源 |
|------|:----:|------|
| 标题 | ✅ | XML `<title>`（去 `[当期目录]` 等前缀） |
| 作者 | ✅ | description / `<author>` |
| 期刊 | ✅ | feed 名 / channel |
| 期数 / 出版时间 | ✅ | description 结构化行 |
| 摘要 | 尽量 | CMA description 常有；CNKI web 常缺 |
| 数据库链接 | ✅ | CNKI `kns.cnki.net…` 或 CMA `rs.yiigle.com/cmaid/…` |
| DOI/PMID | — | 通常无，不强制 |

### 23.3 XML 源分类与补全 Tier

对现有 `aes-feeds` 实测归类（2026-06-20，方法论 §17.6）：

| Tier | 源类型 | XML 典型可得 | 缺口 | 补全手段 |
|------|--------|--------------|------|----------|
| **A** | LWW（PRS、ASWC、Derm Surg…） | title, author, link, pubDate, **DOI in citation**, guid | abstract 常缺 | CrossRef/PubMed 补 abstract、journal 规范化 |
| **A′** | KTN 中 OUP/Sage/RSNA（URL 含 `/doi/`） | title, link, DOI in URL | 摘要为 GS 噪声 | DOI→CrossRef；清洗 description |
| **B** | KTN 中 **ScienceDirect** | title, link, **PII in URL** | 常无 DOI | PII→Elsevier；失败则 manual |
| **C** | KTN 中 **PMC** | title, link, **PMCID in URL** | 无 DOI | PMCID→PubMed 转 PMID+abstract |
| **D** | CNKI web | title, author, 期数, guid, CNKI 链接 | **无 DOI、常无摘要** | 平台 ID；摘要二阶抓摘要页（可选） |
| **E** | CMA yiigle | title, author, **完整摘要**, cmaid | 无 DOI | 以 XML 为主，meta 易 complete |
| **F** | KTN 纯 GS 告警块 | title 可用 | description 多文献粘连 | 仅信 title+link；摘要靠补全 API |

**KTN 子域识别**（由 `<link>` 域名）：

```
academic.oup.com, journals.sagepub.com, link.springer.com  → Tier A′（DOI）
sciencedirect.com                                         → Tier B（PII）
pmc.ncbi.nlm.nih.gov, pubmed                              → Tier C（PMID/PMCID）
其他                                                       → 按 URL 尝试 DOI regex
```

### 23.4 元信息补全流水线（meta-enricher）

```
┌─ 输入：XML item / ingest 标识符 ───────────────────────────┐
│ Step 0: 本地解析（M02）→ partial MetaRecord                  │
│ Step 1: 判定 Tier（§23.3）— 决定**从 XML/URL 能抽出哪些码**   │
│ Step 2: 分路由 API（§17.7，有哪个走哪个）                     │
│   · 有 DOI     → CrossRef only                               │
│   · 仅有 PMID  → PubMed only                                 │
│   · 仅有 PII   → PII API only                                │
│   · DOI 404/空 → doi_retry_queue（24h/72h/7d），**不换 API**  │
│   · 响应带回其他 ID → 写入 entry_identifiers（冗余关联）       │
│ Step 3: 英文标题翻译 → title_zh_display（§23.5）              │
│ Step 4: 写 entries；meta_status = complete | partial         │
└────────────────────────────────────────────────────────────┘
```

**DOI 登录滞后**：见 §17.7.3 重试队列；与 PMID **无关**——除非入参本身就是 PMID 路由。

**中文**：Step 2 跳过 DOI/PMID；CMA 多可直接 Step 4 complete；CNKI 缺摘要标 partial。

### 23.5 英文标题翻译与流内展示 ✅（C13）

| 项 | 决策 |
|----|------|
| **流内列表标题** | 显示 **`title_zh_display`（中文译题）** |
| **详情页** | 主标题：中文译题；副标题/折叠：**英文原标题**完整保留 |
| **作者** | **不翻译**（原文著录） |
| **摘要** | **默认不翻译**（⬜ D16）；质量低于 AI 导读，避免重复劳动 |
| **翻译时机** | 元信息入库后异步；缓存于 `title_zh_display` |
| **翻译引擎** | ⬜ D17（DeepSeek / 专用翻译 API） |

**理由**：便于中文读者扫流；专业读者在详情仍可见英文原标题与摘要。

### 23.6 英文文献 · Reader 展示规范

**元信息区（区块 B）必显**：

```
期刊：Plastic and Reconstructive Surgery
发表：June 2026 · Ahead of Print
作者：Adler, Neta; Meshulam Derazon, Sagit
DOI：10.1097/PRS.0000000000012568  [复制]
PMID：12345678（若有）
PII：S0002939426003107（仅 SD 且有）
原文：https://journals.lww.com/plasreconsurg/...  [在官网打开 ↗]
```

**官网链接**：✅ **纳入元信息展示**（`publisher_url` = XML `<link>` 或 DOI 落地页）。

**AI 区**：

- **AI 导读**：中文（§20.1）
- **豆包 AI 辅助阅读**：分享链接（§20.1）；卡片上可显示 `豆包阅读↗` 徽章

### 23.7 中文文献 · Reader 展示规范

**元信息区**：

```
期刊：中国美容医学
期数：2026年06期
出版时间：2026-06-14
作者：叶聪秀; 易金玲; …
来源：知网 CNKI  [打开数据库页 ↗]
```

**AI 区**：

- **仅 AI 导读**（中文）
- **无**豆包 AI 辅助阅读入口（C15：中文世界版权较敏感）

### 23.8 中英文 AI 能力对比 ✅

| 能力 | 中文 | 英文 |
|------|:----:|:----:|
| AI 导读（中文，PDF+提示词） | ✅ | ✅ |
| 豆包 AI 辅助阅读（全文 PDF 分享链） | ❌ | ✅ |
| 官网/数据库原文链接 | CNKI/CMA | 出版社官网 |
| 流内标题 | 中文原标题 | **中文译题** |
| 摘要展示 | 中文摘要 | 英文摘要（不译） |

### 23.9 扩展 XML 采样表（KTN 子类型 · 2026-06-20）

| 子类型 | 样例 link | DOI | PII | PMID | 摘要质量 |
|--------|-----------|-----|-----|------|----------|
| OUP | `…/doi/10.1093/asj/sjag117/…` | URL 内 ✅ | — | — | GS 噪声 |
| Sage | `journals.sagepub.com/doi/…` | URL 内 ✅ | — | — | GS 噪声 |
| Springer | `link.springer.com/article/10.1007/…` | URL 内 ✅ | — | — | GS 噪声 |
| ScienceDirect | `…/pii/S1748681526003499` | 常滞后/无 | ✅ URL | — | GS 噪声 |
| PMC | `pmc.ncbi.nlm.nih.gov/articles/PMC13268452` | — | — | PMCID✅ | GS 噪声 |
| LWW | `journals.lww.com/…/fulltext/…` | citation✅ | — | — | 常无 abstract |

> 结论：**KTN/GS 的 XML description 不可当摘要**；摘要靠 CrossRef/PubMed/PII 补全。

### 23.10 LWW citation 解析补充

`<citation>` 示例：

```
Plastic and Reconstructive Surgery. 157(6):829e-830e, June 2026. doi: 10.1097/PRS.0000000000012568
```

可 regex 提取：`journal`、`volume(issue)`、`pages`、`month year`、`doi`。

---

## 12. 附录 A：用户旅程

```
首次打开 → 空态 + 推荐标签 → 订阅 ≥1 → 订阅流看未读 → 详情
  → 有 AI 导读则精读 → 点豆包链深读全文 → 🔖 稍后阅读
可选：6 位码跨端同步 · 绑定微信 · 设置里开 /all
```

## 13. 附录 B：编辑旅程

```
移动：订阅流 → 工作台巡检 → 待全文计数 → 处理下一篇豆包
桌面：含权浏览器批量开页 → Zotero 抓取 → Console 补 PDF
     → 豆包 Kanban → 用户侧可见导读+豆包链
```

## 14. 附录 C：组件清单

| 组件 | 用户 | 编辑 |
|------|:----:|:----:|
| ArticleCard（无筛选色） | ✅ | ✅ |
| TagChips | ✅ | ✅ |
| ReadLaterButton | ✅ | ✅ |
| AiSummaryBlock（含豆包链） | ✅ | ✅ |
| FulltextStatusBadge | ❌ | ✅ 编阅模式 |
| InboxAddPanel | ❌ | ✅ 桌面 |
| FulltextKanban | ❌ | ✅ 桌面 |
| ZoteroSyncPanel | ❌ | ✅ 桌面 |
| TagSubscriptionPanel | ✅ | ✅ |
| SyncCodePanel | ✅ | ✅ |
| EditorQuickPanel | ❌ | ✅ 移动 |
| ReviewQueueCard | ❌ | ✅ |
| PromptEditor | ❌ | ✅ 桌面 |
| TagAdminTable | ❌ | ✅ 桌面 |

---

## 15. 反馈与待决（请直接改本表）

| ID | 状态 | 议题 | 建议 / 你的意见 |
|----|------|------|----------------|
| D1 | ✅ | 用户「已读」仅本地 or 随同步码同步？ | **已定**：随同步码同步；存 AES `user_read_state`（C35） |
| D2 | ✅ | 未订阅的标签对用户是否可见？ | **已定**：列表仅已订阅并集；推荐页/详情可预览或追订（C20） |
| D3 | ⬜ | 编辑阅读域是否显示筛选色？ | 建议：默认隐藏，编阅模式开启 |
| D4 | ✅ | 自动标已读规则 | **已定**：中间页停留 **≥1s**；列表头 **全部标已读**（MVP）；无扫过计时、无单条手动（C35） |
| D5 | ⬜ | 用户能否看「全部已打标文献」？ | 建议：设置里可选 `/all`，**非**未订阅默认态 |
| D6 | ⬜ | 编辑 PIN 在移动端输入？ | 建议：允许 |
| D7 | ⬜ | 6 位码安全性是否可接受？ | 需确认 |
| D8 | ⬜ | Tab 命名「工作台」vs「运维」 | |
| D9 | ⬜ | 技术栈 React+Vite vs 纯 HTML | |
| D10 | ✅ | 系统标签初始清单来源 | **已定**：P0 编辑手打积累 → P2 编辑与 AI 共拟 → D1 发布（§2.5） |
| D11 | ✅ | 随手入流是否开放给用户？ | **已定**：Phase 1 仅编辑；未来荐稿走同管道+待审 |
| D21 | ⬜ | 微信入流号形态 | 企业微信 vs 服务号 vs 个人号企业能力；回调与鉴权 |
| D12 | ⬜ | Zotero 同步方式 | 建议：本机 API + 手动同步按钮 |
| D13 | ⬜ | PDF 副本是否必须与 Zotero 双向同步？ | 建议：Zotero 为主库，AES 只读副本 |
| D14 | ⬜ | CNKI 无 DOI 时 L1 完成条件 | 建议：title+author+platform_id 即可 |
| D15 | ⬜ | 豆包链接是否对用户始终可见？ | 建议：仅英文且有导读时 |
| D16 | ⬜ | 英文摘要是否在详情展示？ | 建议：展示英文原文，不翻译 |
| D17 | ⬜ | 英文标题翻译引擎 | DeepSeek / 其他 |
| D18 | ⬜ | DOI 滞后重试间隔 | 建议：**24h → 72h → 7d** 三档；入 `doi_retry_queue` |
| D22 | ⬜ | title+journal 弱判重 | 从 CNKI/CMA 样本验证碰撞率；通过前仅手动合并 |
| D24 | ⬜ | 多用户 Miniflux starred | 每 sync_profile 映射 Miniflux 用户 or 统一服务账号 |
| D25 | ⬜ | 英文头图 `hero_image` 规格 | 宽高比、裁切、占位图 |
| D26 | 🟢 | 中间页短导读 prompt | **8300** 文档维护 → `reading-note-prompts.html`（`_shell_brief` + `reading_note_brief`） |
| D27 | 🟡 | 导读 `reading_note_zh` 产链 | **双轨**（2026-06-24 修订）：**豆包**仅 chip 产 `doubao_read_url`（公开 thread **不得**含定制 prompt）；**导读**走 **Gemini Web RPA**（`gemini_rpa.py` · brief + 3.5 Flash → share 抠字）。豆包 thread 不再作导读源 |
| D28 | 🟢 | **中文表述规范** | **8300** 侧边栏「文档维护」→ `aes-writing-style.html` → `data/style_guide.json` |
| D19 | ✅ | 训练样本门槛 | **已定**：覆盖主要标签类、宁多勿少；无 30+30 硬门槛（C21） |
| D20 | ⬜ | AI 自动直写置信度阈值 | 建议：0.85；以下进 M8 |

**反馈记录**

| 日期 | 内容 |
|------|------|
| 2026-06-23 | **§21.2.1 模板 F**：结构学习解构新对话接续（勿 @ 旧对话） |
| 2026-06-23 | **§1.6**：结构学习执行清单；PaperSorter 纳入序 3，对照 §2.5 打标训练 |
| 2026-06-24 | **D27 双轨**：豆包链仅 chip（公开）；导读 Gemini Web + 自定义 brief；豆包 thread 泄露 prompt 问题 |
| 2026-06-24 | **D27 单轨**：导读+豆包链均走豆包 RPA；thread 抠 `reading_note_zh`；Gemini RPA 双轨暂缓；trade-off 实测后再议 |
| 2026-06-24 | **8300 文档维护**：`doc_registry.json` + 侧边栏分组；表述规范等维护页统一入口 |
| 2026-06-23 | **D28**：中文表述规范 JSON + Console `admin/style_guide.html` |
| 2026-06-23 | **C35 修订**：Inoreader 式——点开 1s + 列表清零 MVP |
| 2026-06-23 | **C35 / §4.1.1** 首版（已废止扫过方案） |
| 2026-06-23 | **§1.0 / C34**：用户视角定位=文献助手（获悉·深读·收纳）；阅读深度梯；全文合规为硬边界 |
| 2026-06-20 | 用户只读；标签订阅；稍后阅读；匿名+6 位码+微信；编辑 L1/L2 分级 |
| 2026-06-20 | 随手入流；XML 采样；PDF/Zotero；状态机；AI导读+豆包链 |
| 2026-06-20 | 删除模块拆分文档；C10 |
| 2026-06-20 | C11 详细文档优于 compact |
| 2026-06-20 | **§23 中英文分轨**：译题列表展示；DOI/PMID/PII 级联；中文无豆包链 |
| 2026-06-20 | **§2.5–§2.6**：打标训练；多标签 DB 读路径；C16–C17 |
| 2026-06-20 | **v1.6**：去平台浏览；搜索延 P2+；未订阅空态；训练三阶段；C18–C21 |
| 2026-06-20 | **§16 重写**：DOI/PMID/PII 核心键；插件+微信入口；C22–C23 |
| 2026-06-20 | **§6.5**：全渠道去重；打标前 lookup；C24 |
| 2026-06-20 | **v1.9**：分路由 API；判重分级；DOI 重试队列；C25 |
| 2026-06-20 | **v2.0**：中间页/卡片；Miniflux starred；中文 MVP 无导读；AI 阅读；C26–C33 |

---

## 21. 跨对话接续（单文档 · 详细正文优先）

### 21.1 原则：详细文档 >> compact 摘要 ✅（C11）

| 方式 | 可靠性 | 典型问题 |
|------|--------|----------|
| **本文完整正文**（1000+ 行亦可） | 高 | 需指定读哪几章；文件过长时分章阅读 |
| 对话内 compact /「上次说了」 | 低 | 丢细节、合并错误、待决当已定、否定项消失 |
| AI 生成的交接摘要 | 中偏低 | 摘要者擅自简化；与正文不同步时以摘要为准会翻车 |

**结论**：讨论成果应**写入正文**（表格、流程、采样数据、权限矩阵），不只写进聊天。新对话开场让 AI **Read 文件**，而不是粘贴三段「精华 recap」。

### 21.2 新对话怎么读

**两种开场，都有效**——取决于话题是否已收敛：

| 模式 | 何时用 | 开场 |
|------|--------|------|
| **轻量（推荐默认）** | 主文档已持续更新；话题可能发散 | 见下方「轻量模板」 |
| **窄任务** | 本轮只改一块（如只谈 PDF） | 轻量模板 + **可选**点名 § 与 D 项 |

**轻量模板** ✅（话题发散时用，**不必**写项目名、不必列章节）：

```text
Read docs/aes_workbench_design.md（以修订记录所示最新版为准），在此继续讨论。
```

或更短：

```text
@docs/aes_workbench_design.md 继续
```

AI 应自行：**修订记录 → C 表 → §15 待决 → 再按你的第一条消息选读章节**。不必事先指定 §4/§16，除非本轮任务确实只涉及那些章。

**窄任务示例**（可选加章节，非必须）：

```text
Read docs/aes_workbench_design.md，在此继续讨论。
本轮只动 §18–§19 与 D12–D14。
```

**不要**：粘贴对话 recap 代替 Read；不要假设 AI 记得旧对话里的「已定」而未写入正文的内容。

#### 要不要每次下「编辑升级」指令？

| 做法 | 能否找到文档 | 能否自动写回文档 |
|------|--------------|------------------|
| 仅 `@docs/aes_workbench_design.md 继续` | ✅ | ⚠️ 不保证 |
| `@` + **一句维护约定**（下方模板 A） | ✅ | ✅ 较稳 |
| 项目 **Cursor Rule** `.cursor/rules/aes-workbench-design.mdc` | ✅ `@` 或打开该文件时生效 | ✅ 设一次即可 |

**跨对话无法自动关联 chat ID**——Cursor 不把上一对话参数传给下一对话。对接靠：**主文档（真源）+ 新对话 `@` 文件**；Rule 减轻重复口述，**不能**代替 `@` 或 Read。

---

### 21.2.1 新开对话提示词（复制即用）

**模板 A · 推荐（轻量 + 维护）**

```text
@docs/aes_workbench_design.md 继续。
有产品/架构结论则写入该文档（修订记录、C 表、§15、正文）；纯问答可不改。
```

**模板 B · 更短（已配 Cursor Rule 时）**

```text
@docs/aes_workbench_design.md 继续
```

**模板 C · 窄任务（可选第二行）**

```text
@docs/aes_workbench_design.md 继续。
本轮只讨论：________（例：Miniflux starred 对接）
```

**模板 D · 无 @ 时**

```text
Read docs/aes_workbench_design.md（以修订记录最新版为准），在此继续讨论。
有结论写入主文档。
```

不必写项目全称；不必列 § 除非模板 C。

**模板 E · 省上下文（`@` 后已 >40% 时优先）**

```text
继续 AES 工作台设计。不要 Read 全文。
仅 Read docs/aes_workbench_design.md 第 1–65 行（修订记录 + C 表）与 §15 待决表；正文 § 等我点名再读。
```

或不 `@` 文件、只让 AI 按行号分段 Read——**通常比 `@` 整文件更省上下文**。

**模板 F · 结构学习解构接续** ✅（§1.6 执行序；**勿 `@` 旧对话**）

```text
继续 AES 工作台 · 结构学习解构（主文档 §1.6）。

不要 @ 上一对话记录，不要 Read 主文档全文。
Read：第 1–65 行 + §1.6（Grep `## 1.6` 定位）；本轮精读开源项目：序 __（见下表）；按需 Read AES 对照章（序 1→§4；序 3→§2.5）。

任务：拆该参考项目的结构（数据流/状态/UI 域）→ 结构图 + AES 映射（保留/改造/拒绝）→ 结论写入 §1.6 子节或对照正文章。

进度（更新序号即可）：
- 已完成：1 Folo · 2 Amadeus
- 本轮：序 3 · PaperSorter
- 待执行：3 PaperSorter → 4 PaperClip → 5 karakeep-webhook → 6 YourRSS → 7 feishu-llm → S1–S3
```

**不必 `@` 本对话**：真源是 `docs/aes_workbench_design.md`（C11）；旧 chat 仅作叙事参考，全文预载占上下文且无结构化进度。

### 21.3 上下文预算 ✅（`@` 与全文 Read）

| 现象 | 原因 |
|------|------|
| 新对话刚 `@` 主文档就 **~40–50%** | Cursor 常把 **整文件** 预注入上下文（~1900 行），与是否 Read 无关 |
| 再 Read 全文 | 重复占用；**禁止** bootstrap 阶段读 1900 行 |

**bootstrap 只读这两块（约 120 行，够接续 90% 讨论）**

| 块 | 行号（v2.0，随修订漂移时用 grep 定位） | 内容 |
|----|----------------------------------------|------|
| 头 | **1–65** | 版本、修订记录、**C1–C33** |
| 待决 | **§15 表格**（约 1804–1832 行） | D1–D25 |

**正文 § 按需读**：用户话题涉及哪章再 `Read` 该段（如只谈中间页 → §4；只谈入流 → §16）。用 `Grep` 定位章节行号，避免通读。

| 做法 | 上下文 | 可靠性 |
|------|--------|--------|
| `@` 整文件 | 高（常 40%+） | 高 |
| 不 `@`，Read 1–65 + §15 | 低 | 高（已决/待决不丢） |
| 不 `@`，Read 1–65 + §15 + **单章** | 中 | 最高（窄任务） |
| 对话 recap 代替 Read | 低 | 低（C11 不推荐） |

**与 C11 的关系**：详细正文仍写在**一个**主文档里；省上下文靠的是 **分步 Read**，不是另建 compact 摘要文件替代真源。

### 21.4 长对话与上下文（C33）

| 情况 | 建议 |
|------|------|
| 上下文 **<50%**，且任务与上文强连续 | 可继续本对话 |
| 上下文 **>50%**，或新开一大 topic | **开新对话**；优先 **§21.3 分步 Read**，慎用 `@` 整文件 |
| `@` 后已 **>40%** | 本轮用模板 E；正文 § 按需再读 |
| 交接方式 | 主文档为真源；**不 `@` + Read 头+§15** 与 `@` 整文件二选一（见 §21.3） |
| 质量风险 | 上下文满后更易漏改文档、混淆已决/待决 |

**主文档持续更新时**，新对话 Read + C 表 比 long chat recap 可靠（C11）。

---

*文档结束 · v2.1*
