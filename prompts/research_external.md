# 外部阅读笔记 Prompt / Skill 调研

> **Phase 0 产物** · 2026-06-23  
> 对应设计：[`docs/aes_workbench_design.md` §20.6](../docs/aes_workbench_design.md)  
> **状态**：调研与组织完成；**未**对 Doubao「详细总结」做 live A/B（见文末评测计划）。

---

## 1. 调研结论（Executive Summary）

AES 需要的不是「再写一份摘要」，而是 **按 `paper_type` 路由的固定骨架 + 表述纪律**（C36）。外部资源中：

| 优先级 | 来源 | 最值得借什么 |
|--------|------|--------------|
| ★★★ | **CASP RCT Checklist** + Duke PICO | RCT 三节结构（有效性 / 结果 / 本地适用性）；P/I/C/O 与问题类型→研究设计对照 |
| ★★★ | **Mizoreww `paper-reading` skill** | **paper_type 路由**（实证/综述/理论/系统）；深度写作纪律；实证模板中「结果事实 vs 解读」分层 |
| ★★★ | **agent2research 医学综述 Prompt 包**（中文） | 可核验字段、证据表列、禁止编造 PMID/DOI、`待核验` 标注 |
| ★★☆ | **research-agora `paper-summarizer`** | 深度档位（TLDR/Standard/Deep）；结果表格式；质量自检清单；**明确声明不评真伪** |
| ★★☆ | **castlen3 `ebm-researcher`** | PICO 拆解、证据与推论分离、停损不硬凑、Directness Gate |
| ★☆☆ | **Shikhar-S `paper-reading`（Granny）** | 分节导读流程可参考；**人设与叙事不适合 AES 中间页** |
| ★☆☆ | **MCP-KnowS-AI SYSTEM_PROMPT** | 按主题综合、证据等级分层、呈现矛盾——适合 **综述类 P2+**，不适合单篇 RCT 笔记 |

**与 AES §20.6 占位 schema 的对齐**：外部 RCT 框架普遍覆盖 `研究问题 → 设计/人群 → 干预对照 → 主要结果 → 安全性 → 局限 → 临床启示`；CASP 额外强调 **效应量精度（CI/p）** 与 **外推性**，agent2research 强调 **字段可核验**，Mizoreww 强调 **禁止浅层套话**。

---

## 2. 来源清单

### 2.1 Agent Skills / Cursor·Claude 生态

| 来源 | URL | 适用文献类型 | 可借元素 | 勿照搬（AES） | 医美临床导读适配 |
|------|-----|--------------|----------|---------------|------------------|
| **Mizoreww paper-reading** | [GitHub SKILL.md](https://github.com/Mizoreww/awesome-claude-code-config/blob/main/skills/paper-reading/SKILL.md) | 实证/RCT≈Empirical；综述=Survey | 类型识别路由；Basic Info + Research Problem；实证模板「Experimental Results: Facts vs Analysis」；深度写作对照表；质量检查 | 图抽取 pipeline（pymupdf4llm）；HTML+SVG 输出；CS 基准/SOTA 叙事 | 将 Empirical 映射为 `reading_note_rct`；结果节强制 **主要终点 + 效应量 + CI/p**；安全性单列；设备/能量参数入「干预」 |
| **research-agora paper-summarizer** | [GitHub command](https://github.com/rpatrik96/research-agora/blob/main/plugins/academic/commands/paper-summarizer.md) | 通用；偏 CS/ML triage | TLDR/Standard/Deep；结果 Markdown 表；Limitations 作者陈述 vs 未陈述；Relevance read/skip；交付前 quality checks | arXiv MCP 检索；「Read if / Skip if」个人科研队列；评 SOTA/复现性（医美临床弱相关） | 保留 **Standard 深度** 与 **结果表**；删 relevance triage；加 **临床适用性** 替代 read/skip |
| **Shikhar-S academic-skills** | [paper-reading](https://github.com/Shikhar-S/academic-skills/tree/main/paper-reading) | 通用科普 | 五步：一句话贡献→分节导读→故事化→公式图→专家点评 | 繁中奶奶人设、动漫类比、叙事占大头 | 仅借 **分节顺序**（Abstract/Intro/Methods/Results/Discussion）与 **Step 5 批判维度** |
| **cocoafun paperskills** | [GitHub](https://github.com/cocoafun/paperskills) | 写作/检索工作流 | `/abstract` IMRaD 变体；`/peer-review` 八维评分 | 面向写论文而非读单篇；token 预算大 | P2+ 写 `eval_rubric` 时可参考 peer-review 维度 |
| **K-Dense scientific-agent-skills** | [GitHub](https://github.com/K-Dense-AI/scientific-agent-skills) | 泛科研 | Literature Review、Paper Lookup 工具链 | 147 skills 过载；非临床笔记 schema | 仅作生态参考，不引入 |

### 2.2 循证医学 / 临床框架（英文）

| 来源 | URL | 适用文献类型 | 可借元素 | 勿照搬（AES） | 医美临床导读适配 |
|------|-----|--------------|----------|---------------|------------------|
| **CASP RCT Checklist (2024)** | [casp-uk.net PDF](https://casp-uk.net/casp-checklists/CASP-checklist-randomised-controlled-trials-RCT-2024.pdf) | RCT | A 有效性（随机、盲法、基线、除干预外是否同等）；B 结果（效应大小、精度）；C 本地适用；「Can't tell」纪律 | 11 问 Yes/No 表格原样给用户；eLearning 课件体例 | 压缩为 7 个 `###` 中文标题；盲法在医美设备试验常「Can't tell」→ 写清原因 |
| **Duke PICO Guide** | [LibGuide](https://guides.mclibrary.duke.edu/ebm/pico) | 临床问题拆解 | P/I/C/O 定义；问题类型→研究设计层级（Therapy→RCT） | 检索策略教学；非单篇笔记模板 | 「研究问题」节用 PICO 一句话 + 研究设计标签 |
| **Springer PICO extraction (GPT-4o)** | [Pharm Med 2024](https://link.springer.com/article/10.1007/s40290-024-00539-6) | 摘要级 PICO | 分元素零样本抽取 prompt（Population 要 disease/line/severity） | 批量 SLR 生产线；摘要而非全文 | 作 **L1 abstract 预分类** 参考，非终态笔记 prompt |
| **Costello AI-PICOS JSON** | [PDF](https://costellomedicalen-1c385.kxcdn.com/wp-content/uploads/2024/12/ai-picos-summaries.pdf) | 摘要筛选 | JSON 键值 PICOS；temperature 0.2 | 审稿筛选 UI；非读者笔记 | 内部 worker 可选 JSON 中间表示，用户只见 Markdown |
| **ScreenPrompt / SR screening** | [ResearchGate](https://www.researchgate.net/publication/389317532) | 系统综述筛选 | 五元 prompt：目标、纳排、CoT、摘要、ACCEPT/REJECT | 筛选决策输出 | 不用于 AES 用户笔记；`reading_note_review` P2+ 可借「纳排标准」小节 |
| **LinkedIn Hani Simo LR prompt** | [Article](https://www.linkedin.com/pulse/llm-prompt-research-paper-analysis-simplifying-academic-hani-simo-rp24f) | 综述摘录 | RQ 对齐；每条 finding 附 **原文短引**；禁止无证据推断 | 面向写 literature review 段落 | 可选：关键结论后附「原文依据句」（短引，非全文复制） |

### 2.3 中文医学 / 综述 Prompt

| 来源 | URL | 适用文献类型 | 可借元素 | 勿照搬（AES） | 医美临床导读适配 |
|------|-----|--------------|----------|---------------|------------------|
| **agent2research 文献综述 Prompt 包** | [资源页](https://agent2research.com/resources/literature-review-prompt-pack) | 综述选题+单篇证据表 | 证据表字段（设计、N、人群、干预、对照、结局、统计、局限、是否纳入）；禁止编造引用；不确定性标注 | 整包面向 **写综述** 而非中间页 1 篇笔记 | **证据表字段** 直接映射 observational/RCT 各节；与 `_shell` 纪律高度一致 |
| **aitoolsguidebook 文献矩阵** | [中文指南](https://aitoolsguidebook.com/zh/articles/literature-matrix-prompts/) | 系统综述矩阵 | 角色/上下文/限制/输出格式五元；矩阵→综合段；PRISMA 列 | 15 个 prompt 面向 Notion/Excel 矩阵 | P2+ `reading_note_review`：检索策略、纳入排除、综合结论 |
| **Mason AI Lab 医学文献** | [PubMed 工作流](https://masonailab.com/career/ai-med-research/) | 多文献检索+JC | 批判性阅读预习单（设计、N、偏倚、外推）；必须标注 PMID/DOI | Deep Research 多文献；台湾临床语境 | JC 预习单 → `eval_rubric` 评分维度 |
| **castlen3 ebm-researcher** | [GitHub](https://github.com/castlen3/ebm-researcher) | 临床 PICO 问答 | PICO 报告结构；Directness Gate；证据限制与推论分离；停损 | 自动 PubMed 检索+繁中报告；用户对话式 | 借 **推论分离** 与 **证据不足时如实写**；不做自动检索 |
| **MCP-KnowS-AI** | [SYSTEM_PROMPT](https://github.com/PancrePal-xiaoyibao/MCP-KnowS-AI/blob/main/SYSTEM_PROMPT.md) | 多文献调研报告 | 按主题综合；证据等级；呈现矛盾；STUDY_TYPE 等 auto_tag | 长篇调研报告；多轮检索 MCP | 仅 **review 类** 笔记；单篇 RCT 不用 |
| **CAPA 整形美容协会（方法学）** | [MINORS 介绍](http://capa.org.cn/prev/contents/720/5156.html) | 非随机外科研究 | MINORS 12 条；医美多为非随机/病例系列 | 完整量表打分 UI | `reading_note_observational` 局限节可参考 MINORS 关注点（盲法、随访、偏倚） |

### 2.4 其他

| 来源 | URL | 适用文献类型 | 可借元素 | 勿照搬 | 适配 |
|------|-----|--------------|----------|--------|------|
| **paper-notion-summarizer (ClawHub)** | [ClawHub](https://clawhub.ai/lococaeco/paper-notion-summarizer) | CS 深度总结 | 8 段 seminar 结构（Problem→Method→Experiments→Ablation→Assessment） | Notion 上传；偏 ML 论文 | 观察性/机制论文 P2+ 可参考 Ablation→敏感性分析 |
| **PromptSmith Research Assistant** | [Template](https://galfrevn-promptsmith.mintlify.app/templates/research-assistant) | 通用 | 身份+领域上下文；摘要前询问关注点 | 对话式；无固定输出骨架 | 仅作 _shell 「角色句」参考 |

---

## 3. 结构对照：外部 → AES `reading_note_{type}`

### 3.1 RCT（MVP 优先）

| AES 占位节（§20.6.2） | 主要外部来源 |
|----------------------|--------------|
| 研究问题 | Duke PICO；CASP Q1（focused issue） |
| 设计与人群 | CASP A（随机、盲法、基线、随访/失访）；CONSORT 思维 |
| 干预与对照 | PICO I/C；设备参数、疗程、随访点 |
| 主要结果 | CASP B7–B8；research-agora 结果表；**主要终点优先** |
| 安全性 | 医美常独立；AE 类型/发生率/严重程度 |
| 局限 | CASP + Mizoreww「作者承认 vs 读者观察」 |
| 临床启示 | CASP C9–C11；ebm 外推性；**非治疗建议**（助手定位） |

### 3.2 观察性 / 病例（MVP 第二）

| AES 节 | 外部来源 |
|--------|----------|
| 研究问题 | PICO（I=暴露）；CASP Cohort/Case-Control checklist |
| 设计与人群 | MINORS；随访、匹配、失访 |
| 暴露/干预 | agent2research 证据表「干预或暴露」 |
| 主要结果 | 效应量 + 调整因素 |
| 偏倚与局限 | Mason JC 预习单；RoB 思维（不必写量表分） |
| 临床启示 | 证据等级标注（低于 RCT） |

### 3.3 综述（P2+）

| AES 节 | 外部来源 |
|--------|----------|
| 检索与纳排 | ScreenPrompt；PRISMA 思维 |
| 纳入研究概况 | 文献矩阵行 |
| 综合结论 | MCP-KnowS 按主题综合 |
| 证据缺口 | agent2research 研究空白分析 |

---

## 4. AES 统一纪律（发酵 `_shell` 时应固化）

综合多来源，建议 _shell 包含（与 §20.6.2 一致）：

1. **语言**：简体中文；专业术语首次可附英文缩写  
2. **结构**：固定 `###` 标题，不得增删，无开场白/结语  
3. **真实性**：未报告 → `文中未报告`；禁止编造 N、p、CI、DOI  
4. **数字**：主要终点优先；报告效应量 + 95%CI 或 p（文中有则写）  
5. **分离**：事实（结果）与解读（临床启示）分节  
6. **边界**：笔记是阅读辅助，**不构成治疗建议**  
7. **不对抗 L1**：不覆盖 title/authors/abstract（§20.6.5）

**明确不引入**：

- 人设叙事（Granny）、动漫类比  
- Read/Skip 个人科研 triage（非 AES 用户场景）  
- 多轮对话 / 用户追问  
- 图表截图嵌入（中间页无此需求；C32 头图另轨）  
- 八股「创新点」「国内外研究现状」

---

## 5. 候选草稿（`candidates/`）

| 文件 | 来源 | 说明 |
|------|------|------|
| [`candidates/casp_rct_clinical_note.md`](candidates/casp_rct_clinical_note.md) | CASP + §20.6 占位 | RCT 七节中文骨架 + 纪律 |
| [`candidates/mizoreww_empirical_clinical_adapted.md`](candidates/mizoreww_empirical_clinical_adapted.md) | Mizoreww Template A | 实证模板临床化（Facts/Analysis 分层） |
| [`candidates/research_agora_standard_clinical.md`](candidates/research_agora_standard_clinical.md) | research-agora | Standard 深度 + 临床结果表 |
| [`candidates/agent2research_evidence_row.md`](candidates/agent2research_evidence_row.md) | agent2research | 单篇证据表字段 → observational 变体 |

均为 **CANDIDATE / UNTESTED**，未经样本发酵与 holdout 评测。

---

## 6. A/B 评测计划（vs 豆包「详细总结」）

> **未执行**：以下仅为计划；需 Phase 0 样本与 `eval_rubric.md` 定稿后实施。

### 6.1 目标

在 **holdout 样本**（未参与发酵）上比较：

- **A**：`prompts/reading_note_{paper_type}.md` + `_shell.md`（1× LLM，附 PDF 或抽取正文）  
- **B**：豆包 RPA 占位 prompt `详细总结这篇文章内容`（现有基线）

输出均存入 `reading_note_zh` 同字段，**盲评**（评分人不知来源）。

### 6.2 样本集

| 分层 | 数量（建议） | 要求 |
|------|--------------|------|
| RCT | ≥8 | 激光/能量源/注射/光电；含中英文源 |
| 观察性 | ≥6 | 队列、回顾、病例系列 |
| 综述 | ≥4（P2+） | 系统综述或叙述性综述 |
| **合计** | 20–30 | 来自 `eval/holdout/`；与发酵集 **零重叠** |

每篇备：**PDF**、L1 元信息、（可选）编辑「理想笔记」金标准、（可选）已有豆包总结。

### 6.3 流程

```
1. 锁定 holdout 列表 → eval/holdout/manifest.json
2. 对每篇：
   - run A：note_worker + reading_note_{type}.md
   - run B：doubao_rpa +「详细总结这篇文章内容」
3. 双栏 Markdown 导出 → eval/runs/{article_key}_{A|B}.md
4. 2 名评分人（至少 1 名编辑）按 eval_rubric.md 盲评
5. 汇总：节级均分、总分、胜率、典型失败模式
6. 修订 prompt → 仅用小样本 dev 集迭代 → 再次 holdout 验证
```

### 6.4 Rubric 维度（草案，与 schema 同步定稿）

| 维度 | 1–5 分要点 |
|------|------------|
| **结构合规** | 是否严格固定标题、无开场白 |
| **事实准确** | N、终点、效应量、AE 与 PDF 一致 |
| **临床可读** | 医美读者 2–3 分钟能抓住「做没做效、安不安全」 |
| **完整性** | 是否覆盖安全性、局限、外推性 |
| **克制性** | 无编造、无过度推荐、无堆砌摘要 |
| **相对豆包** | 同篇 A vs B 强制二选一或「相当」 |

### 6.5 统计与决策

- 报告 **节级** 与 **总分** 均值差（A−B）  
- 决策规则（建议）：holdout 上 A 在「事实准确+结构合规」**显著优于** B，且「临床可读」不劣于 B → 替换豆包占位 prompt  
- 若某 `paper_type` 子类 A 落败 → 单独发酵该子类，不拖累全局上线  

### 6.6 工具与成本

- A 路：与生产 `note_worker` 相同 API（模型、温度待定；SR 文献建议 temperature≤0.3）  
- B 路：现有 RPA；仅评测阶段跑 holdout，不必全库重跑  
- **不做** BLEU/ROUGE 对笔记自动打分（临床笔记人工评更可靠；见 SR LLM 可行性研究结论）

---

## 7. 下一步（建议顺序）

1. **你提供 10–20 篇样本**（PDF + 可选理想改写 + 现有豆包总结）→ 发酵真 schema，非沿用本文件占位  
2. 从 `candidates/casp_rct_clinical_note.md` 与 `agent2research_evidence_row.md` **挑一版 RCT/观察性底稿**合并进 `_shell`  
3. 定稿 `eval_rubric.md` + `eval/holdout/manifest.json`  
4. 执行 §6 A/B（需 RPA + note_worker 可跑）  
5. 评测通过后，`reading_note_{type}.md` 替换豆包占位 prompt（§20.6.7 终态）

---

## 8. 参考链接（速查）

- Mizoreww paper-reading: https://github.com/Mizoreww/awesome-claude-code-config/blob/main/skills/paper-reading/SKILL.md  
- research-agora paper-summarizer: https://github.com/rpatrik96/research-agora/blob/main/plugins/academic/commands/paper-summarizer.md  
- CASP RCT 2024: https://casp-uk.net/casp-checklists/CASP-checklist-randomised-controlled-trials-RCT-2024.pdf  
- Duke PICO: https://guides.mclibrary.duke.edu/ebm/pico  
- agent2research Prompt 包: https://agent2research.com/resources/literature-review-prompt-pack  
- ebm-researcher: https://github.com/castlen3/ebm-researcher  
- AES §20.6: ../docs/aes_workbench_design.md  
