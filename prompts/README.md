# AES 中间页 AI 导读 Prompt

> 规范：[`docs/aes_workbench_design.md` §20.6](../docs/aes_workbench_design.md)

## 产品边界（已定）

| 能力 | 方案 |
|------|------|
| **中间页 AI 导读** | `reading_note_brief.md` + `_shell_brief.md` + **`data/style_guide.json`** |
| **深读全文** | 豆包外链；**chip**「详细总结」起句（公开 thread 安全） |
| **术语表 G** | **跳过**（无人工审核则易错，不如 brief 内首现附英文） |
| **AB / MSDC / FUL** | 编辑翻译链，**不进**中间页 → 见 [`editor/`](editor/) |
| **导读生产** | **Gemini Web RPA** + 上述 brief（`gemini_rpa.py`）；**不用**豆包分享链（会暴露 prompt） |
| **豆包 RPA** | 仅 `doubao_read_url`（`--job share-link`，chip） |

## 主模板（v0.2）

| 文件 | 说明 |
|------|------|
| [`_shell_brief.md`](_shell_brief.md) | 纪律：1000 字上限、反编造、读者视角、不伪检索 |
| [`reading_note_brief.md`](reading_note_brief.md) | 五节：为什么值得读 · 概要 · 结果 · 安全与局限 · 深读提示 |

**「为什么值得读」**：由编辑选题版创新性 prompt 改为**读者阅读价值**（本文新在哪、读完多知道什么）。

## 中文表述规范（D28）

| 资源 | 说明 |
|------|------|
| [`data/style_guide.json`](../data/style_guide.json) | 用词轮换、术语、句法（真源） |
| [`docs/aes_writing_style.md`](../docs/aes_writing_style.md) | 人类可读说明 |
| 8300「文档维护」→ 中文表述规范 | 在线编辑，保存直写 JSON（不单独开端口） |
| [`admin/style_guide.html`](../admin/style_guide.html) | 仅 8300 不可用时的离线备用 |

`style_guide_loader.py` 每次生成时读磁盘 JSON 并渲染 prompt 块；8300 保存后下次 worker 即生效。

## 维护（8300 文档维护）

| 页面 | 真源 |
|------|------|
| 中间页短导读 Prompt | `_shell_brief.md` · `reading_note_brief.md` |
| 中文表述规范 | `data/style_guide.json` |

均由 8300 托管 HTML + API，**无独立端口**；保存写回仓库文件，流水线直接读取。

## 试跑

```bash
# 豆包公开链（chip）
python doubao_rpa.py --pdf path/to/paper.pdf --job share-link

# 本地试 brief（勿点分享）
python doubao_rpa.py --pdf path/to/paper.pdf --job dev-brief --no-share

# Gemini 导读（产链待实现；可先抠已有 share）
python gemini_rpa.py --pdf path/to/paper.pdf --fetch-only "https://gemini.google.com/share/..." -o note.txt
```

```bash
cat prompts/_shell_brief.md prompts/reading_note_brief.md
```

## 归档（非中间页默认）

| 文件 | 说明 |
|------|------|
| `reading_note_rct.md` / `observational.md` | v0.1 长模板（CASP 七节），过长已弃用为默认 |
| `research_external.md` | 外部调研索引 |
| `CLINICAL_FRAMEWORK.md` | 临床框架说明 |

## 基线对比（可选）

`详细总结这篇文章内容` / 豆包「一句话总结」——用于评估 brief 是否更利于快读。
