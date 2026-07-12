# holdout — Phase 2 专用留评样本

## 目的

本目录样本 **只用于 Phase 2 对比评测**，**绝不参与 Phase 0 发酵**。

若样本曾用于归纳 `paper_type`、小节标题或修订 `_shell.md` / `reading_note_{type}.md`，则不得放入 holdout。

## 何时划分

在 Phase 0 发酵**开始之前**，从待处理库中划出 holdout（建议首批总量的 **20–30%**，至少 **5 篇**）。

记录清单（示例 `manifest.json` 或 `manifest.md`）：

```markdown
| article_key | DOI | paper_type（若已知） | 划入日期 | 备注 |
|-------------|-----|----------------------|----------|------|
```

## 目录建议

```
eval/holdout/
├── README.md          ← 本文件
├── manifest.md        ← holdout 清单（发酵前创建）
├── pdfs/              ← 留评 PDF（可选，或指向 data/pdf/）
└── results/           ← Phase 2 评测记录（见 prompts/eval_rubric.md）
```

发酵样本请放在 **`eval/fermentation/`**（需自行创建），不要与 holdout 混放。

## Phase 2 流程

1. 对 holdout 中每篇分别跑：**结构化 prompt** vs **「详细总结这篇文章内容」**
2. 用 `prompts/eval_rubric.md` 打分
3. 汇总后修订 prompt，再跑 holdout（同一批，直到达标或发版）

## 当前状态

⬜ holdout 尚未划分 — 请在提供第一批发酵样本时同步划定 holdout 清单。
