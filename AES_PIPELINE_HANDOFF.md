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
| `yuanbao_rpa.py` | ✅ 上传+prompt；比选时 `--mode silent` |
| `doubao_stress_test.py` | ✅ 只测 chip 分享链 |
| `open_compare.py` | ✅ Round 2 开放导读 RPA 批跑（6 档×PDF） |
| `open_compare_api.py` | ✅ Round 2 API 比选；**产线导读**接 `deepseek-v4-flash` |
| `innovation_compare.py` | ✅ 创新交叉验证比选（非 MVP 导读） |
| `innovation_round2_quick.py` | ✅ 遮 ref + v2 prompt 快测 |
| `rpa_tier.py` | ✅ 三通道 tier_requested/observed/verified 日志 |
| `pdf_figure_extract.py` | ⬜ C32 本地抽插图（待开发） |
| `batch_worker.py` | ✅ L3 三轨：DS API 导读 + 豆包 share-link；`*.aes_l3.json` 清单 |

```bash
# L3 产线（导读 + 豆包链，默认并行）
python3 batch_worker.py --pdf paper.pdf
python3 batch_worker.py --pdf paper.pdf --skip-existing
python3 batch_worker.py --pdf paper.pdf --note-only    # 仅 DeepSeek 导读
python3 batch_worker.py --pdf paper.pdf --doubao-only  # 仅豆包链
python3 batch_worker.py --sequential                   # 串行

# 深读单跑
python3 doubao_rpa.py --pdf paper.pdf --job share-link --profile ./doubao_profile
```

---

## 3. 浏览器 Profile

| 任务 | 浏览器 | Profile |
|------|--------|---------|
| CNKI | Edge | `cnki_playwright_profile` |
| 豆包链（深读） | Chrome | `doubao_profile`（**153**） |
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

1. ~~**`batch_worker.py`**~~ ✅  
2. **`pdf_figure_extract.py`** — C32 本地抽图 → `figure_candidates` → Console 选 `hero_image_url`  
3. **`brief_adaptive`** — 弹性导读框架（`paper_type` 路由）  
4. XML 注入 / PDF 匹配  
5. 创新查新（P2+）：元宝 DT / Gemini Web + PubMed 后验；**非**导读 MVP

---

## 5. 压测记录

- 2026-06-24：Gemini `run_20260624_160120` share 1/1、brief 1/1、1141 字（commit `62ed240`）
- 2026-06-24：brief 上豆包 thread → **发现 prompt 公开泄露** → 改 chip  
- 早期 4/4 share+brief thread 抠字（已废止作导读路径）

---

## 6. 新对话接续

```text
Read AES_PIPELINE_HANDOFF.md + session §15。
定型：深读=豆包 Web chip · 导读=DeepSeek V4 Flash API · 插图=本地 Python+编辑选图。
待：pdf_figure_extract.py。
```
