# AES-Intel 管线研发交接文档 (V3)

> **更新**: 2026-06-25  
> **真源**: 产品架构见 `docs/aes_workbench_design.md`（D27、§20.6）  
> **三通道比选**: `_context/sessions/2026-06-24_three_channel_reading_note.md`（**§9–§15**）  
> **阶段性定型（2026-06-25）**: 深读=豆包 Web · 导读=DeepSeek V4 Flash API · 插图=本地 Python

---

## 1. 三轨架构（已定 · 2026-06-25）

```
PDF 就绪
  ├─ 深读 doubao_read_url
  │     豆包 Web RPA · --job share-link · chip
  │     profile: doubao_profile（153）；与导读 API 无浏览器冲突
  │
  ├─ 导读 reading_note_zh
  │     DeepSeek V4 Flash API · pypdf 抽文本
  │     prompt: brief_open.txt · config/api_compare.env
  │
  └─ 插图 hero_image（C32 · 待实现）
        本地 Python 从 PDF 抽 figure 候选
        → 后台 Console 展示全部插图 → 编辑择一 → 前台头图
        （排版视觉优化；导读 LLM 不读图）
```

| 字段 | 引擎 | 输入 / Prompt |
|------|------|----------------|
| `doubao_read_url` | **豆包 Web RPA**（chip） | 整 PDF 上传 · `doubao_profile` |
| `yuanbao_read_url` | **元宝 AI 阅读 RPA** | `deep-reading-detail` 直链（非 `yb.tencent.com/s/` 对话卡） |
| `reading_note_zh` | **DeepSeek V4 Flash API** | `pypdf` 纯文本 · `brief_open.txt` |
| `hero_image_url` | **本地抽图** + 编辑 Console | 多图候选；编辑选前台展示 |

---

## 2. 脚本

| 文件 | 状态 |
|------|------|
| `doubao_rpa.py` | ✅ `--job share-link`（chip）；`dev-brief --no-share` 导读试跑；`--profile` 默认 `doubao_profile` |
| `fetch_thread_brief.py` | ✅ 技术可用；**不**再作导读生产路径 |
| `gemini_rpa.py` | ✅ PDF + brief + 3.5 Flash + share 抠字（commit `62ed240`） |
| `fetch_gemini_share_brief.py` | ✅ 从 share URL 抠导读 |
| `yuanbao_ai_read_rpa.py` | ✅ AI 阅读上传+分享链（`yb.tencent.com/s/…`） |
| `yuanbao_rpa.py` | ✅ 上传+prompt；比选时 `--mode silent` |
| `doubao_stress_test.py` | ✅ 只测 chip 分享链 |
| `open_compare.py` | ✅ Round 2 开放导读 RPA 批跑（6 档×PDF） |
| `open_compare_api.py` | ✅ Round 2 API 比选；**产线导读**接 `deepseek-v4-flash` |
| `innovation_compare.py` | ✅ 创新交叉验证比选（非 MVP 导读） |
| `innovation_round2_quick.py` | ✅ 遮 ref + v2 prompt 快测 |
| `rpa_tier.py` | ✅ 三通道 tier_requested/observed/verified 日志 |
| `pdf_figure_extract.py` | ⬜ C32 本地抽插图（待开发） |
| `batch_worker.py` | ✅ L3：DS 导读 + 豆包 + 元宝 AI 阅读；`*.aes_l3.json` 清单 |

```bash
# L3 产线（导读 + 豆包，默认；元宝用 --with-yuanbao 或 --links-only）
python3 batch_worker.py --article-key <64-hex>
python3 batch_worker.py --article-key <key> --with-yuanbao      # + 元宝 AI 阅读
python3 batch_worker.py --article-key <key> --links-only        # 仅豆包 + 元宝外链
python3 batch_worker.py --article-key <key> --skip-existing
python3 batch_worker.py --article-key <key> --note-only
python3 batch_worker.py --article-key <key> --doubao-only
python3 batch_worker.py --article-key <key> --yuanbao-only
python3 batch_worker.py --sequential                            # 导读与豆包串行（元宝始终串行）

# 深读单跑
python3 doubao_rpa.py --pdf paper.pdf --job share-link --profile ./doubao_profile
python3 yuanbao_ai_read_rpa.py --pdf data/pdf/<key>.pdf --entry direct
```

---

## 3. 浏览器 Profile

| 任务 | 浏览器 | Profile |
|------|--------|---------|
| CNKI | Edge | `cnki_playwright_profile` |
| 豆包链（深读） | Chrome | `doubao_profile`（**153**） |
| 元宝 AI 阅读 | Chrome | `yuanbao_profile` |

> **阻塞（2026-06-27）**：`yuanbao_profile` 账号冻结（申诉页）。元宝 RPA **暂停**。解冻/换号后：`--yuanbao-only` 重跑。重试策略：见 `读取失败` 即 DOM click「重试」，失败再刷新（不用 pyautogui）。

| ~~Gemini / 元宝导读~~ | — | **比选结束**；产线不再用 Web 导读 |

### 首次登录（一次性）

日常 Chrome 的 Google 登录 **不会** 自动继承到 RPA。Playwright 使用独立目录（与 `doubao_profile` 同理）。

```bash
cd lit_auto_pipeline && source venv/bin/activate
python3 gemini_login.py
# 弹出 Chrome → 登录 Google → 确认能进 gemini.google.com/app → 回终端按 Enter
```

豆包 profile 确认见 session 文档 §2.5（复用 `./doubao_profile` · **153**，无需新注册）。

之后 RPA **一般免登录**，除非：删了 profile、平台强制重登、或长时间未用。

**不要**让 RPA 直接复用主 Chrome 的 `~/Library/Application Support/Google/Chrome`：日常 Chrome 开着时会锁 profile，且自动化与手工浏览混在一起。

---

## 4. 待开发

### Top3（开发期 · 本地真源 · 2026-06-25）

| # | 模块 | 交付物 | 验收 |
|---|------|--------|------|
| **1** | **entries + ingest** | `aes_workflow.db` · `xml_ingest.py` | KTN/LWW XML → `entries` + `entry_identifiers`；`article_key` 稳定；dedup 可测 |
| **2** | **本地全文链路** | `pdf_store.py`（Local）· `pdf_watcher.py` | pdf-router/手放 `pdf_inbox/` → 对齐 `article_key` → `data/pdf/{key}.pdf`；`fulltext_status` |
| **3** | **batch_worker ↔ DB** | 改 `batch_worker.py` · `note_worker_cli.py` 或等价 | `--article-key` 读本地 PDF → 写 `reading_note_zh` + `doubao_read_url` 回 `entries` |

**显式不在 Top3**：自建 RSS 产线版 · OSS · Zotero · Console UI · `prs_video` ingest · `video_extractor` · C32 头图

**Top3 后**：最小 API `:8301`（upload/list）→ 接 pdf-router → 产线切 OSS backend

---

1. ~~**`batch_worker.py`**~~ ✅  
2. **`pdf_figure_extract.py`** — C32 本地抽图 → `figure_candidates` → Console 选 `hero_image_url`  
3. **`brief_adaptive`** — 弹性导读框架（`paper_type` 路由）  
4. ~~XML 注入~~ → **Top3#1 ingest + #3 写 DB**（XML 注入降为可选）  
5. 创新查新（P2+）：元宝 DT / Gemini Web + PubMed 后验；**非**导读 MVP

---

## 5. 压测记录

- 2026-06-24：Gemini `run_20260624_160120` share 1/1、brief 1/1、1141 字（commit `62ed240`）
- 2026-06-24：brief 上豆包 thread → **发现 prompt 公开泄露** → 改 chip  
- 早期 4/4 share+brief thread 抠字（已废止作导读路径）

---

## 6. 新对话接续

```text
Read AES_PIPELINE_HANDOFF.md + _context/sessions/2026-06-24_three_channel_reading_note.md §15–§16。

【已定 · C37】
  深读 doubao_read_url  → 豆包 Web share-link chip（doubao_profile/153）
  导读 reading_note_zh  → DeepSeek V4 Flash API（pypdf + brief_open.txt）
  头图 hero_image_url   → 本地抽图 + Console 编辑选图（待开发）

【已落地】
  batch_worker.py（并行/串行 · *.aes_l3.json）
  open_compare_api.py · api_compare_env.py · config/api_compare.env（本地，未入库）
  git main @ 81ce8ee（2026-06-25 push）

【待办优先级 · Top3 开发期】
  1. entries + xml_ingest（KTN/LWW 先行）
  2. pdf_store(Local) + pdf_watcher + fulltext_status
  3. batch_worker --article-key 回写 entries
  → 其后：API :8301 · pdf-router 上传 · OSS backend · 自建 RSS

【原待办】
  · batch_worker 本机全轨验收
  · pdf_figure_extract.py（C32）
  · brief_adaptive / paper_type 路由
  · 创新查新 P2+

【常用命令】
  python3 batch_worker.py --pdf paper.pdf
  python3 batch_worker.py --pdf paper.pdf --note-only
  python3 doubao_rpa.py --pdf paper.pdf --job share-link --profile ./doubao_profile
  python3 open_compare_api.py --verify
```
