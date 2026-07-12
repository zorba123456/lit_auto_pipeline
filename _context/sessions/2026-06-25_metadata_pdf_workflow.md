# 文献元数据 + PDF 管理 · 设计讨论记录

> **日期**: 2026-06-25  
> **接续**: `docs/aes_workbench_design.md` §6.5 / §17–§19 / §7；上轮代码缺口见同日前序 chat  
> **状态**: 讨论中，术语与主干流转已对齐；实现未开工

---

## 1. 术语约定（本轮新增）

| 词 | 含义 | 存储/真源 |
|----|------|-----------|
| **元数据**（总称） | 一篇文献在 AES 内的**全部结构化资产** | `entries` + 附件路径 + L3 字段 |
| **基础元数据** | 元数据中**不含全文 PDF** 的部分：标题、作者、期刊、期数、标识符、摘要、链接、标签、处理状态等 | `entries` 表 L1 列 + `entry_identifiers` |
| **全文资产** | PDF 文件本体（及可选 outline） | `data/pdf/{article_key}.pdf`；Zotero 为编辑侧主归档 |
| **衍生内容** | 由全文或 API 生成的**展示用 AI 产出**（非基础元数据字段） | `reading_note_zh`、`doubao_read_url`、`hero_image_url` |
| **视频链接** | 出版商托管的**补充手术视频**（非自托管文件） | `has_video`、`video_links[]`（见 §12） |

**原则**：XML 只是**上游探测快照**，不是前端真源；基础元数据以 **`entries` 中间体** 为准，允许编辑覆盖、多源合并。

**视频 ≠ 全文 PDF**：视频不入 `data/pdf/`、不走 Zotero 附件链；只存**外链/深链**，播放仍在出版商侧（合规）。

---

## 2. 前端需要呈现什么（规整）

### 2.1 用户 Reader（只读 · C1）

**大流卡片（L1 轻量）**

| 块 | 字段 | 中文 | 英文 |
|----|------|------|------|
| Badge | `platform` + `issue_or_pub` | ✓ | ✓ |
| 标题 | `title` / `title_zh_display` + EN 副标题 | 原文中文 | 中文译题 + 英文原标题 |
| 一行元信息 | `journal` · `issue`/`pub_date` · `authors` | ✓ | ✓ |
| 标签 | `entry_tags` | ✓ | ✓ |
| 外链 | `publisher_url` | 知网/CMA | 原文 |
| 状态徽章 | `reading_note_status` | 中文 MVP 无 | `笔记✓` |
| 装饰 | `hero_image_url` | — | 可选 C32 |

**中间页（L1 逐行 + L3 区）**

| 块 | 字段 | 中文 MVP | 英文 P2+ |
|----|------|----------|----------|
| 基础元数据行 | 期刊、期数、作者、DOI/PMID/PII、原文链 | ✓ | ✓ |
| 摘要 | `abstract` | ✓（唯一正文区） | ✓（英文原文） |
| 阅读笔记 | `reading_note_zh` | P5+ 可选 | ✓ |
| AI 阅读 | `doubao_read_url` | **不提供** C15 | ✓ 外链 |
| **补充视频** | `has_video` + `video_links[]` | 后置 | ✓ 外链 ↗（D41） |
| 头图 | `hero_image_url` | — | 可选 |
| 操作 | 稍后阅读、转发中间页 URL | ✓ | ✓ |

**用户永远不看**：PDF 文件、筛选理由、置信度、Worker 状态、Zotero 路径。

### 2.2 编辑（同一 Reader + 工作台/Console · C5）

在**同一套 UI** 上，编辑对**所有会出现在前台的字段**均可改（含 `title_zh_display`、`abstract`、标签、L3 文案、头图）。  
额外可见：**处理状态**（`meta_status`、`fulltext_status`、`reading_note_status`、`doubao_status`）、ingest 来源、内部备注。

---

## 3. 是否需要 XML 与前端之间的中间体？

**需要。** 最有效率的方式 = 设计已定、代码未做的 **`aes_workflow.db` + `entries` 单篇真源**：

```
aes-feeds/*.xml ──► Miniflux（聚合池 / 编辑浏览）
        │
        ▼
   ingest worker（解析 XML item 或插件 DOI）
        │
        ▼
   entries + entry_identifiers  ◄─── 前端 / 客服 / batch_worker 唯一读写在库层
        │
        ├── 基础元数据列（可编辑）
        ├── 全文路径 pdf_path / fulltext_status
        └── L3 列 reading_note_zh, doubao_read_url, hero_image_url
```

**为何不用「继续只靠 XML 注入」**

- XML 缺字段（CNKI 常无摘要/DOI）；注入 AI 字段会让 RSS 更臃肿
- 去重、打标、客服查询、状态机都需要 **article_key** 级记录
- 多前端（用户 Reader、编辑工作台、Console、未来客服）应 **共查一张表**，而非各读 XML

**效率要点**

1. **写一次、读多端**：cron/ingest 写 `entries`；Reader API 只读 DB（Miniflux 仅作源池与「筛选前阅读器」）
2. **分列表/详情接口**：列表 L1 轻字段；详情再取 L3 长文（§2.6.5 已定）
3. **文件与行分离**：PDF 在磁盘；DB 只存 `pdf_path` + 状态，避免 BLOB
4. **XML 可选回写**：若仍要 RSS 工具链兼容，L3 完成后 **可选** 同步到 XML description（非必须）

---

## 4. 上游主干流程（任务队列视角）

```
① 爬取/cron → aes-feeds XML          [层 A 去重：cnki_dedup_log 等]
② 聚合      → Miniflux poll
③ AI 筛选   → 相关/无关（编辑后台 tag_worker / 历史训练数据曾用 `inoreader-aes-filter`）
④ ingest    → normalize_id → dedup → INSERT entries
⑤ 基础元数据 → meta-enricher（DOI/PMID/PII 分路由 API）→ meta_status
⑥ AI 打标   → tag_worker → entry_tags
⑦ 全文获取  → 半自动队列（见 §5）
⑧ L3 加工   → batch_worker（导读 API + 豆包链 + 抽图）
⑨ 发布      → PUBLISHED（用户订阅流可见）
```

**与「元数据 / 基础元数据」的对应**

| 阶段 | 产出属于 |
|------|----------|
| ④⑤ | 基础元数据入库 |
| ⑥ | 基础元数据上的标签关系 |
| ⑦ | 全文资产 + `fulltext_status` |
| ⑧ | 衍生内容字段 |

---

## 5. 哪些环节要人工？（编辑介入点）

| 环节 | 自动化目标 | 人工介入 | 在哪操作 |
|------|------------|----------|----------|
| **AI 筛选** | 高（LLM pass/reject） | **误杀/漏过**：被拒条目默认**不进** `entries` | **自建 RSS 阅读器**（`feed_reader.html` + Miniflux）看上游全量；误杀 → **pdf-router** / Console 强制入流 |
| **基础元数据补全** | 中高（API 有码则自动） | DOI 滞后、无码、摘要缺、API 404 | Console 条目编辑；`doi_retry_queue` 失败后手动补字段 |
| **AI 打标** | 稳态后高（C16 三阶段） | 冷启动全手打；低置信进 **M8 待复核** | 工作台 M8/M9；Console D2 |
| **全文 PDF** | **低～中**（直链 OA 可脚本） | **默认半自动**：含权页 + Zotero/手动下载 | Console D11 Kanban；插件打开含权页 |
| **L3 导读/豆包** | 高（batch_worker） | 失败重试、文案校对 | M4/M5；Console D13；**字段可编辑** |
| **头图** | 中（抽图自动） | 择一 | Console 选图 |

**关键结论（筛选编辑）**

- 被拒条目不在后台 → **筛选阶段的「编辑」必须在 RSS/Miniflux 侧完成**，或维护 **排除目录 + 恢复入队**（Console D5 excluded）
- 通过后进入 `entries` 的篇，**所有前台字段在编辑侧可改**

---

## 6. 一个应用还是三个？

**一个 Reader PWA + 权限分流**（C5 已定，本轮 reaffirm）：

| 壳 | 用户 | 编辑额外 |
|----|------|----------|
| **自建 RSS 阅读器** | — | `feed_reader.html` + Miniflux：看 **cron/XML 上游池**（筛选前） |
| 同一 AES Reader PWA `/` | 订阅流、中间页 | +「工作台」Tab |
| `/admin/*` | 不可见 | Console L2 |
| **`pdf-router` 浏览器插件** | 不用 | 含权页 **PDF 下载 / 权限路由**（≠ RSS 阅读器） |

```
编辑日常：
  看新文献 → 自建 RSS 阅读器（Miniflux / feed_reader）
  抓全文   → 含权页 + pdf-router 插件 → pdf_inbox / API 上传
  管已入选 → AES 工作台 / Console（entries）
  用户看   → Reader 订阅流
```

---

## 7. 打标 + 基础元数据齐了之后：全文环节

**自动化可行性**

| 来源 | 全自动 | 说明 |
|------|--------|------|
| KTN link=直链 PDF | 可 | 下载 → `pdf_inbox/{article_key}.pdf` |
| OA / 已登录 session | 部分 | 需维护含权 cookie，脆弱 |
| LWW/出版社含权页 | **半自动** | Connector 或手动 |
| CNKI 付费 | **手动为主** | 验证码/付费墙 |

**不行时**：`fulltext_status=PDF_QUEUED`，进 **D11 待全文队列**，编辑空闲处理。

**全文必须与元数据对齐**

- 统一键：`article_key`（来自 DOI/PMID/PII/platform_id，§6.2）
- 文件命名：`data/pdf/{article_key}.pdf`
- 状态：`PDF_HAS_FILE` 后才进 L3

---

## 8. Zotero：用不用、怎么用

### 8.1 定位（建议维持 §18.2）

| | Zotero | AES |
|--|--------|-----|
| 角色 | 编辑**个人文献库**、长期归档、Connector 抓页 | **产线真源** `entries` + Worker 用 PDF 副本 |
| 元数据 | 抓页时生成（常较简） | **以 ingest + API 补全为准** |
| 一致性 | **不要求与 AES 逐字段相同** | 用 DOI/title/**article_key** 对齐即可 |

Zotero 元数据可能与 AES **不一致**（Connector 常缺 abstract、期数格式不同）→ **合并策略**：AES `entries` 为主，Zotero 仅用于 **发现「这篇已有 PDF」** 并复制文件，不反向覆盖 L1 除非编辑点「采用 Zotero 元数据」。

### 8.2 与流程对接（推荐单轨）

```
entries 已有基础元数据（article_key, doi, title…）
        │
        ▼
编辑在含权页 → Zotero Connector 保存
        │
        ▼
「从 Zotero 同步」（本机 API · D12 待定）
        ├─ 按 DOI / title fuzzy 匹配 article_key
        ├─ 有 attachment → 复制到 data/pdf/{article_key}.pdf
        └─ fulltext_status → PDF_HAS_FILE → 触发 L3 队列
```

**Connector 漏 PDF 时**（已知问题）

1. Console D11：[打开含权页] [上传 PDF] [已从 Zotero 同步]
2. 或拖 PDF 进 Zotero → 同步脚本只取 **attachment 路径**，元数据仍以 AES 为准
3. 极端：拖入 PDF 让 Zotero 识别 DOI → 匹配已有 `article_key` → 同上

**不用 Zotero 的替代**：Console 直接上传 PDF + 选/搜 `article_key`；Zotero 降为可选加速器，非阻塞 P0。

### 8.3 待决（写入主文档 §15）

- D12 Zotero 同步：本机 API + 手动按钮 vs 文件夹 watch
- D13 是否双向同步：建议 **AES 只读 Zotero 附件，不反向写库**
- 新：**D38** Connector 漏 PDF 的默认 SOP（上传 vs 重试 Connector）

---

## 9. 主干：前后台流转（一页图）

```
                    ┌─────────────────┐
                    │ Miniflux / XML  │  ← 编辑看「筛选前」全量
                    └────────┬────────┘
                             │ AI 筛选
              ┌──────────────┼──────────────┐
              ▼ reject                      ▼ pass
        （留在源池/排除夹）              ingest
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ entries（中间体）  │ ← 基础元数据真源
                                    │ + entry_tags      │
                                    └────────┬────────┘
                         enrich ◄──────────┤
                         打标 ◄─────────────┤
                         编辑改字段 ◄───────┤
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                   PDF 半自动队列      batch_worker L3      用户 Reader
                   Zotero/上传         导读+豆包+头图        只读展示
                         │                    │
                         └──────────┬─────────┘
                                    ▼
                              PUBLISHED（订阅流）
```

---

## 10. 落地顺序（与代码缺口对齐）

1. `entries` + ingest（KTN/LWW 先行）— **中间体**
2. meta-enricher MVP — **基础元数据齐**
3. tag_worker 接入 — **打标**
4. `data/pdf/{article_key}.pdf` + D11 队列 — **全文**
5. `batch_worker --article-key` 回写 — **L3**
6. Zotero 同步脚本 — **P5 加速器**
7. 筛选「排除可恢复」+ Miniflux 工作流文档 — **筛选可编辑**

---

## 12. 文献视频链接（并入元数据 · 2026-06-25 补充）

> **详案**：[文献视频分享](fb0660d4-7950-497b-936d-201b9266c136) 对话（AES-Intel 项目）· 纪要 `AES-Intel/09-讨论纪要-文献视频机制.md`

### 12.1 两类视频来源（不要混）

| 类型 | 来源 | 入库 | L3（导读/豆包） |
|------|------|------|-----------------|
| **A. 论文补充视频（SDC 等）** | PDF 内短链 | 挂在**该篇论文** `article_key` 的 `video_links` | **照常**（英文论文流） |
| **B. `prs_video` 入流** | LWW Video RSS | **每条视频独立一篇** `entries` | **不做** ✅ |

**澄清（2026-06-25）**

- `prs_video` 是独立 cron 通道；description 里虽常提到母文献篇名/卷期，但 **不做程序化对齐原文**（用户：太麻烦）。
- 每条 XML item → 自有 `article_key`（建议 `lww_video:{v=}` 或 `video.aspx` URL 稳定 id）→ `has_video=true`，`video_links[0]=link`。
- **不**与 `prs_current_issue` 等论文流 merge / dedup；同一母文献若两边都有，用户侧是**两条卡片**（可接受）。

**与 A 的关系**：仅当编辑日后给**普通英文论文**跑 PDF 抽取 SDC 时，视频链仍写在**该论文**条目上——与 `prs_video` 通道无关。

### 12.2 产品共识（AES-Intel 已定）

- **不自托管、不用户上传**；只发现出版商视频并指路
- **优先跳转官网**（或 LWW 短链）；合规文案：「在期刊官网观看补充视频 ↗」
- 视频与正文 **权限常分离**：跳转后**看视频**多数无需订阅；**读 PDF** 仍可能要（勿混为一谈）
- **敏感/侵权**：专业受众；外链新标签；可选播放前提示；不做公开 SEO 索引手术镜头

### 12.3 字段（写入 `entries` · 属基础元数据扩展）

```yaml
has_video: bool
video_count: int                    # 可选
video_source: lww_sdc | elsevier_mmc | springer_supp | oup_supp | lww_gallery | unknown
video_links:
  - label: "Supplemental Digital Content 1"
    url: "https://links.lww.com/PRS/D138"
    link_type: direct_publisher | article_anchor
    playback: deep_link | cdn_direct | iframe_embed   # 按出版商策略
video_detection:
  method: regex | keyword | llm | manual
  confidence: 0.0–1.0
```

**前端中间页（英文 P2+）**：在元信息行下增加 **「补充视频」** 块（C27 一行一字段）；多段则列表。中文 MVP 可后置。

**编辑**：`has_video` / `video_links` **可手改**（与「所有前台字段可编辑」一致）。

### 12.4 检测时机（挂到主干队列）

```text
PDF_HAS_FILE
  → video_extractor（规则优先，非单靠搜 "video" 一词）
       ① 正则：links.lww.com、ars.els-cdn.com、…
       ② 关键词：SDC / Supplementary Video / See Video
       ③ 无直链：DOI/PII → 出版商文章页 #supplementary-data / #mmc1
       ④ 可选 LLM 压误报（video-assisted 等）
  → 写 entries.video_links
  → meta_status 不变（视频不阻塞 L1）
```

**与 L3 关系**：视频检测 **不依赖** `reading_note_zh` / 豆包链；可与 `batch_worker` **并行**（均需 PDF 或至少 `publisher_url`）。

**与 `prs_video` ingest**：

```text
prs_video.xml item（一条 = 一条 entries）
  → article_key = sha256("aes|lww_video:" + v参数)   # 或 guid=link
  → title / description / pubDate 来自 XML
  → has_video=true；video_links[0]=video.aspx URL
  → ingest_source=prs_video
  → 不解析母文献、不 lookup 论文流
  → L3：SKIP
```

**中间页**：XML 自带标题 + description（常含所配文献文字说明）+ **观看视频 ↗**；无导读、无豆包。

### 12.5 出版商播放策略（实现备忘）

| 出版商 | 存什么 | 能否站内 `<video>` |
|--------|--------|---------------------|
| LWW SDC | `links.lww.com` 短链（CDN 稳定） | 可选 cdn_direct；产品仍推荐 deep_link |
| Elsevier MMC | PII + `#mmc1` 或 `ars.els-cdn.com` | 直链较稳 |
| Springer APS | `video-id` 或文章页深链 | iframe，**不存** m3u8/403 MP4 |
| Oxford ASJ | 文章页 `#supplementary-data` | 仅 deep_link（签名 URL 会过期） |

### 12.6 待办（P2+，不阻塞 entries MVP）

- [ ] `video_extractor.py`（PDF 文本规则包，PRS + Elsevier 优先）
- [ ] `entries` 表列或 `video_links_json` TEXT
- [ ] 中间页 UI + 编辑 Console 字段
- [ ] `prs_video` ingest：一条 XML item → 一条 entries（**不对齐**论文流）

---

---

## 14. Zotero 可省 · 插件直抓 PDF（2026-06-25）

### 14.1 问题

若 Zotero 在管线里**只做**「含权页抓 PDF → 对齐 `article_key`」，是否用 **浏览器插件 + 落盘文件夹 + Python 对齐** 更顺？

### 14.2 结论：**对 AES 产线更顺，建议替代 Zotero 为默认路径**

| | Zotero 路径 | **插件 + `pdf_inbox/` 路径（推荐）** |
|--|-------------|--------------------------------------|
| 步骤 | 含权页 → Connector → Zotero → 手动同步 → 复制 → 匹配 | 含权页 → **插件一键** → 下载到 `pdf_inbox/` → watcher 匹配 `entries` |
| 元数据真源 | 易与 `entries` 冲突（D40） | **始终以 `entries` 为准**；PDF 只补 DOI/校验 |
| 含权下载 | Connector 常漏 PDF | 插件在**当前浏览器会话**里触发下载，成功率更高 |
| 实现 | 本机 Zotero API + 同步 UI | **`pdf-router` 插件** + `pdf_inbox/` + watcher；与 C23 ingest **可同扩展、不同职责** |
| 个人书库 | Zotero 仍适合编辑私有归档 | **可选**：编辑自用 Zotero，**不进**产线 |

**更高效的原因**：少一跳、少一套元数据、与 §16 插件入流同一入口；`batch_worker` 已会读 PDF。

### 14.3 推荐链路

```text
编辑在含权全文页
  → pdf-router 插件：
       ① 权限路由 / 触发 PDF 下载（插件本职）
       ② 落盘 pdf_inbox/ 或 POST /api/fulltext/upload
       ③ （可选）带 DOI / article_key 命名
  → pdf_watcher.py（跑在 Mac mini 或轻量 worker）：
       ① pypdf 抽 DOI / 标题（校验，非覆盖 L1）
       ② lookup entry_identifiers → article_key
       ③ 移到 data/pdf/{article_key}.pdf
       ④ fulltext_status=PDF_HAS_FILE → 进 L3 队列（若适用）
```

**插件 vs Python 分工**

| 谁 | 做什么 |
|----|--------|
| **插件** | 含权会话内下载与路由（**pdf-router**）；非 RSS 阅读器 |
| **Python** | 扫文件夹、解析 PDF 元数据、对齐 DB、状态机、调 `batch_worker` |

**仍半自动**：CNKI 验证码、非直链出版社页 → Console D11 上传兜底。

### 14.4 Zotero 定位（修订 D12/D40）

- **产线默认**：不用 Zotero
- **可选**：编辑个人文献库；与 AES **无自动同步**

---

## 15. 真源库与存储（2026-06-25 · 修订）

### 15.1 结论

- **DB 真源**：Mac mini 24/7 跑 **AES API :8301** + `aes_workflow.db`（元数据行小，可留本机）
- **PDF 真源**：**不宜**长期堆满 Mac mini 内置盘；开发期本地 OK，**产线需云端对象存储 + 备份**

### 15.2 推荐拓扑（Mac mini 磁盘紧张）

```text
Mac mini（24/7，轻磁盘）
├── AES API :8301 + aes_workflow.db   ← 元数据真源（须云端备份）
├── pdf_inbox/ pdf_ready/             ← 仅暂存，定期清空
├── batch_worker                      ← 处理时拉 PDF（见下）
└── cron / Miniflux / feed_reader 上游

对象存储（S3 / R2 / B2 / 阿里云 OSS）  ← PDF 长期真本
├── pdf/{article_key}.pdf
└── 生命周期规则 + 版本/异地备份

编辑机浏览器 + pdf-router  ──上传──► API 或直写 OSS（预签名 URL）
```

| 层 | Mac mini | 云端 |
|----|----------|------|
| `entries` / 状态机 | 主库 SQLite | **日备**（db dump → OSS） |
| PDF 正文 | 缓存/队列 only | **主存** `pdf/{article_key}.pdf` |
| XML 池 | Miniflux + GitHub | 已有 |

### 15.3 pdf-router 落盘策略

| 阶段 | 做法 |
|------|------|
| **开发期** | pdf-router → 本机/mini `pdf_inbox/`；可接受 |
| **产线** | 插件 **直传 API** → 服务端写 OSS；mini 不落永久 PDF |
| **batch_worker** | 处理前 `oss.get` 到临时目录 → L3 → 删临时文件 |

### 15.4 运维最小集

- DB：`sqlite3 .backup` 或 litestream → 对象存储
- PDF：OSS 默认开启版本/跨区域复制（按预算）
- Mac mini：监控磁盘；`pdf_inbox` 超时未处理告警

### 15.5 分阶段（2026-06-25 定）

| 阶段 | PDF | DB | 说明 |
|------|-----|-----|------|
| **测试/开发** | 本机 `pdf_inbox/`、`data/pdf/` 或 `~/Desktop/PDFs` | 本机 `aes_workflow.db` | 与现 `batch_worker` 一致；**不上 OSS** |
| **产线** | **阿里云 OSS 私有桶** `pdf/{article_key}.pdf` | mini 主库 + OSS `backup/db/` 日备 | mini 仅暂存；**接口层抽象 `pdf_store`**，切换不改业务 |

```text
# 开发
pdf-router → 本地文件夹 → pdf_watcher → batch_worker

# 产线（同一套 API，换 backend）
pdf-router → POST /api/fulltext/upload → OSS
batch_worker → pdf_store.get(article_key) → /tmp → L3
```

**估值**：全量 30 篇/天见上文；**仅产线阶段产生 OSS 费**，开发期 **¥0 云存储**。

---

---

## 17. Top3 开发计划（2026-06-25）

### 总目标

开发期闭环：**XML → entries → 本地 PDF → L3 写回 DB**（无 OSS、无 RSS 产线版）。

### #1 entries + ingest（约 3–5 天）

**新建**

- `schema.sql` / `db.py` — `entries`、`entry_identifiers`、状态列（`meta_status`、`fulltext_status`、`reading_note_status`、`doubao_status`）
- `xml_ingest.py` — 解析 `aes-feeds` item；normalize DOI/PMID/PII；`article_key`；dedup

**先做源**：KTN（URL 含 DOI）、LWW（citation DOI）  
**后做**：CNKI/CMA（`platform_id`）、`prs_video`（`lww_video:{v}`，无 L3）

**验收**

```bash
python3 xml_ingest.py --feed aes-feeds/ktn_blepharoplasty.xml --limit 10
sqlite3 aes_workflow.db "SELECT article_key, title, doi FROM entries LIMIT 5;"
```

### #2 本地全文链路（约 2–3 天，可与 #1 尾段并行）

**新建**

- `pdf_store.py` — `LocalPdfStore`（`pdf_inbox/` → `data/pdf/{article_key}.pdf`）
- `pdf_watcher.py` — 扫 inbox；`pypdf` 抽 DOI；lookup `entry_identifiers`；更新 `fulltext_status=PDF_HAS_FILE`

**验收**

```bash
cp test.pdf data/pdf_inbox/   # 或 pdf-router 落入
python3 pdf_watcher.py --once
# entries 对应行 fulltext_status=PDF_HAS_FILE
```

### #3 batch_worker ↔ DB（约 2 天，依赖 #1+#2）

**改动**

- `batch_worker.py` — `--article-key`；从 `data/pdf/{key}.pdf` 读；写 `reading_note_zh`、`doubao_read_url` 到 `entries`
- 保留 `*.aes_l3.json` 作调试日志（可选）

**验收**

```bash
python3 batch_worker.py --article-key <key>
sqlite3 aes_workflow.db "SELECT reading_note_zh, doubao_read_url FROM entries WHERE article_key=...;"
```

### 依赖图

```text
#1 ingest ──► #2 watcher（需 article_key 存在）
     └──────────► #3 batch_worker
```

### Top3 之后（P1）

| 序 | 项 |
|----|-----|
| 4 | 最小 FastAPI `:8301`（ingest / fulltext upload / entry GET） |
| 5 | pdf-router → API |
| 6 | `OssPdfStore` + 产线切换 |
| 7 | 自建 RSS 接 API |
| 8 | meta-enricher · tag_worker · prs_video · video_extractor |


```
Read 本文件 §14–§15 + D43–D44。
产线 PDF：插件下载 + pdf_watcher，默认不用 Zotero。
真源：Mac 24/7 API + DB；PDF 在磁盘；非笔记本本地。
```
