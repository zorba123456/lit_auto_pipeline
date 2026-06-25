# 临床阅读框架说明 — AES 阅读笔记 v0.1

> **状态**：v0.1-EXTERNAL-DRAFT · 2026-06-23  
> 对应：`prompts/_shell.md`、`reading_note_rct.md`、`reading_note_observational.md`  
> 详细外部调研：`research_external.md` · 候选底稿：`candidates/`（已被本版吸收，勿重复维护）

---

## 1. 为何走「外部临床框架」路径

AES Phase 0 原设计依赖用户「理想导读」样本发酵 schema。当前阻塞已解除：

| 路径 | 说明 | 何时用 |
|------|------|--------|
| **A · 外部框架 bootstrap（当前）** | 从 CASP、PICO、MINORS、Journal Club、中文循证 prompt 生态归纳 v0.1 结构化 prompt | **现在即可**用任意单篇 PDF + 豆包 RPA 试跑 |
| **B · 样本精炼（可选）** | 用户提供理想导读 / 豆包总结改写 → 调整小节措辞、顺序、医美特有字段 | 有样本后迭代 v0.2+，**非启动前提** |

**不需要**：理想导读金标准、批量发酵语料、`eval/holdout/` 样本集——这些仅服务于 Phase 2 对比评测，不阻塞 v0.1 试生产。

---

## 2. 选用的临床框架及理由

### 2.1 CASP RCT Checklist（2024）— RCT 主骨架 ★★★

- **来源**：[CASP RCT PDF](https://casp-uk.net/casp-checklists/CASP-checklist-randomised-controlled-trials-RCT-2024.pdf)
- **借什么**：四段逻辑——(A) 设计有效性 (B) 方法学可靠性 (C) 结果与精度 (D) 本地适用性；「Can't tell」→ AES「文中未报告」
- **不借什么**：11 问 Yes/No 打分表、教学课件体例
- **医美适配**：盲法在设备试验常不完整；单独强调操作者盲法、主观量表评估者盲法

### 2.2 Duke / Georgetown PICO — 研究问题节 ★★★

- **来源**：[Duke EBM PICO Guide](https://guides.mclibrary.duke.edu/ebm/pico)
- **借什么**：P/I/C/O 一句话；问题类型（治疗/诊断/预后/危害）隐含的研究设计层级
- **不借什么**：检索策略教学、PICOTT 扩展字段堆砌
- **医美适配**：I = 设备参数/注射方案；O = GAIS、MASI 等验证终点

### 2.3 MINORS — 观察性 / 非随机 ★★★

- **来源**：Slim et al. 2003；[CAPA 方法学介绍](http://capa.org.cn/prev/contents/720/5156.html)；整形外科文献常用
- **借什么**：12 条方法论关注点（连续纳入、前瞻性、随访、失访、对照同期性、基线均衡）
- **不借什么**：0–2 分打分 UI、总分 16/24 输出给用户
- **医美适配**：病例系列、回顾性队列在医美占比高；MINORS 源于外科非随机研究，比通用 CASP 更贴场景

### 2.4 Journal Club / CAT 结构 — 读者节奏 ★★☆

- **来源**：NHS Journal Club Handbook、WUTH JC Guide
- **借什么**：「临床问题 → 研究概况 → 方法批判 → 结果与临床意义 → 是否改变实践」的阅读顺序
- **不借什么**：演示幻灯片流程、文献检索作业
- **AES 压缩**：7 个固定 `###` 标题，中间页 2–3 分钟可扫完

### 2.5 Mizoreww paper-reading — 表述纪律 ★★☆

- **来源**：[GitHub SKILL](https://github.com/Mizoreww/awesome-claude-code-config/blob/main/skills/paper-reading/SKILL.md)
- **借什么**：「结果事实 vs 解读」分层；禁止浅层套话（「效果显著」→ 须写效应量）
- **不借什么**：CS 论文 SOTA、图表抽取 pipeline、HTML 输出

### 2.6 agent2research 中文证据表 — 反编造 ★★☆

- **来源**：[文献综述 Prompt 包](https://agent2research.com/resources/literature-review-prompt-pack)
- **借什么**：可核验字段、禁止编造 PMID/DOI、「待核验」标注
- **不借什么**：综述写作、纳入排除决策输出

### 2.7 ebm-researcher — 推论边界 ★☆☆

- **来源**：[castlen3/ebm-researcher](https://github.com/castlen3/ebm-researcher)
- **借什么**：证据与推论分离；证据不足时如实写，不硬凑结论
- **不借什么**：自动 PubMed 检索、对话式报告

### 2.8 整形美容 EBM 语境 — 场景校准 ★☆☆

- **来源**：*Evidence-Based Plastic Surgery* (PMC5127468)；*PRS* RCT 质量综述 (2025)
- **借什么**：LOE 标签不能代替方法学细读；设备试验方法学常弱于药物 RCT
- **不借什么**：Jadad 打分输出

---

## 3. RCT 七节 schema  rationale

| 节 | 标题 | 临床阅读目的 | 主要框架来源 |
|----|------|--------------|--------------|
| 1 | 研究问题 | 30 秒内知道「问什么、和谁比、比什么」 | PICO；CASP「focused issue」 |
| 2 | 设计与人群 | 判断结果可信度：随机、盲法、基线、随访 | CASP A + B（筛查三问 + 方法学） |
| 3 | 干预与对照 | 判断「做的是什么」能否复现、对照是否合理 | PICO I/C；CONSORT 思维；医美参数 |
| 4 | 主要结果 | 回答「做没做效」——终点、效应量、精度 | CASP C7–C8；Mizoreww Facts |
| 5 | 安全性 | 回答「安不安全」——医美读者高频关切 | CASP 伤害；独立成节防被结果淹没 |
| 6 | 局限 | 判断「能不能信」——作者 + 读者双视角 | CASP；JC 方法批判 |
| 7 | 临床启示 | 判断「跟我有没有关系」——外推 cautions，非处方 | CASP D9–D11；ebm 外推性 |

**为何是 7 节而非 CASP 11 问**：中间页需要固定扫读骨架，11 问过碎；7 节覆盖 CASP 全部决策点且与 Journal Club 演讲结构同构。

**为何安全性独立**：医美文献 AE 常分散于 Results/Discussion；合并进「主要结果」易被跳过。

---

## 4. 观察性 schema 与 RCT 的差异

| 维度 | RCT | 观察性 |
|------|-----|--------|
| 因果表述 | 可转述随机化支持的效应 | 关联/差异，避免因果断言 |
| 方法学主轴 | 随机、盲法、ITT | MINORS：连续纳入、随访、失访、对照同期性 |
| 干预节标题 | 干预与对照 | 暴露或干预（含无对照病例系列） |
| 局限 | 外推性、单中心 | 选择偏倚、混杂、证据等级明示 |

---

## 5. 待用户/编辑后续验证（无需理想样本即可启动）

以下项在 v0.1 试跑后根据真实输出迭代，**不阻塞**首次测试：

| 待验证项 | 可能调整 |
|----------|----------|
| 七节标题中文措辞 | 如「临床启示」→「临床含意」 |
| 节内 bullets vs 段落默认 | 依医美读者反馈 |
| 量表缩写表 | 是否加常用医美终点注释块 |
| `paper_type_router` 边界 | 试点研究、亚组研究误分类率 |
| 低置信 `unknown` 处理 | 是否在笔记顶行强制提示 |
| 与豆包占位 prompt A/B | Phase 2 holdout，非 v0.1 前提 |
| 综述/基础机制 prompt | P2+ `reading_note_review.md` / `reading_note_basic.md` |

---

## 6. 试跑方式（单篇 PDF）

```bash
# 组装 RCT prompt（示例）
cat prompts/_shell.md prompts/reading_note_rct.md

# 观察性
cat prompts/_shell.md prompts/reading_note_observational.md
```

1. 豆包 RPA：上传 PDF → `textarea.fill` 整段 prompt → 取回 Markdown → 存 `reading_note_zh`
2. 或 `note_worker`：同 prompt + PDF API
3. 路由（可选）：先跑 `paper_type_router.md`（仅 title+abstract）→ 选 `reading_note_*.md`

---

## 7. 与 `candidates/` 的关系

| candidates 文件 | v0.1 吸收情况 |
|-----------------|---------------|
| `casp_rct_clinical_note.md` | → `reading_note_rct.md`（扩展 CASP 映射表） |
| `mizoreww_empirical_clinical_adapted.md` | → `_shell` 事实/解读分离 + RCT 主要结果纪律 |
| `agent2research_evidence_row.md` | → `reading_note_observational.md` 字段表 |
| `research_agora_standard_clinical.md` | → RCT 结果可选表格 |

`candidates/` 保留作溯源，**生产以本目录根下 `reading_note_*.md` 为准**。
