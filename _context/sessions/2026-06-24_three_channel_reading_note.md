# 三通道导读比选 · 会话记录（living doc）

> **日期**: 2026-06-24（持续修订至 2026-06-25）  
> **目的**: 持久化决策与测试协议，避免跨对话 context 压缩丢信息。  
> **真源**: 管线交接见 `AES_PIPELINE_HANDOFF.md`；产品架构见 `docs/aes_workbench_design.md` D27。  
> **续写**: §9 Round 2 完成结论 · §10 API 比选 · §11 工程备忘

---

## 1. 已定决策

| 项 | 结论 |
|---|---|
| **测试期** | 三通道并行比选：**Gemini / 元宝 / 豆包导读** |
| **运行时** | 只保留 **一个赢家** 作 `reading_note_zh` 生产路径 |
| **豆包链** | **独立 job**：`doubao_read_url` 仍走 chip `share-link`，与导读比选无关 |
| **豆包导读 vs 豆包链** | **分开 RPA 跑**（串行、同一浏览器互斥）；导读用 `dev-brief --no-share`，禁止与公开 share 混用 |
| **豆包 RPA 账号（153）** | **复用既有测试登录** → profile `./doubao_profile`（豆包链历史测试已登录 **153**；**不是** 主力日常 **130**）。无需新注册 |
| **豆包链 + 豆包导读（测试期）** | 同一 profile、**串行**执行：`share-link` 与 `dev-brief` 均 `--profile ./doubao_profile`（**153**）；与 **130** 隔离 |
| **线路** | Gemini 弱项：**出海线路**（国内访问不稳）；元宝 / 豆包：**国内线路** |
| **Prompt 方向** | 弹性框架，非僵化五段式；`brief_adaptive` 为后续方向；当前 `brief_rpa.txt` 五段普适性不足 |
| **Gemini RPA** | commit `62ed240`；压测 `run_20260624_160120`：**share 1/1、brief 1/1、1141 字**、无 prompt 泄露 |
| **Gemini ⋮ 选择器** | `button[aria-label*="conversation actions"]`（见 `gemini_rpa_extract.py`） |

### 架构示意

```
PDF 就绪
  ├─ 豆包链（chip，153）  ./doubao_profile + --job share-link
  │
  └─ 导读比选（测试期三选一，日后单赢家）
        ├─ Gemini    gemini_playwright_profile
        ├─ 元宝      yuanbao_profile
        └─ 豆包导读  ./doubao_profile + dev-brief --no-share（与链串行，勿并行）
```

---

## 2. 三通道比选测试协议（待执行）

> ⚠️ **尚未跑批**（2026-06-24 仅文档化）。执行前确认各 profile 已登录。

### 2.1 PDF 样本集

- **来源**: `~/Desktop/PDFs`
- **数量**: 5–10 篇
- **类型混合**（人工标注 `paper_type` 写入 jsonl）:
  - **review** — 综述 / 观点（如 `why_cosmetic_surgery_is_prevalent_in_korea*.pdf`）
  - **rct** — 随机对照 / 临床试验
  - **case** — 病例 / 小样本观察
- **选篇建议**: 大小 spread（小 1–3 MB、中 5–15 MB、大 20+ MB 各 1–2 篇），避免全选同一期刊。

示例候选（执行时按实际文件名调整）:

```text
why_cosmetic_surgery_is_prevalent_in_korea__a.2278.pdf   # review
1-s2.0-S174868152300092X-main.pdf                        # 按标题判型
1-s2.0-S2666328724000099-main.pdf
… 再补 3–7 篇
```

### 2.2 统一 Prompt

- **首轮**: `prompts/brief_rpa.txt` + `style_guide`（与 Gemini 生产路径一致）
- **加载函数**: Gemini 用 `prompts.prompt_loader`；豆包/元宝/比选脚本用 `doubao_rpa.load_structured_prompt("brief")` — **同源**（`brief_rpa.txt` + 表述规范），约 **1171 字**
- **次轮**（比选结束后）: `brief_reader` / `brief_adaptive`（弹性框架，待编写）
- 三通道 **同一 prompt 文本**；禁止通道间改 wording。

### 2.2.1 模型档位（比选须记录 · 当前缺口）

| 通道 | 脚本是否选模型 | 本次试跑实际档位 | 备注 |
|------|----------------|------------------|------|
| **Gemini** | ✅ `--model`，默认 `3.5 Flash` | **3.5 Flash** | 压测 `run_20260624_160120` 有记录 |
| **豆包导读** | ❌ 未实现，沿用页面默认 | **未记录**（多为「快速」或上次手动选项） | 比选前须在 UI 固定或补 RPA 选档 |
| **元宝** | ❌ 未实现，沿用页面默认 | **未记录** | 入口 `https://yuanbao.tencent.com/` → `/chat` |

**比选协议（两档）**：

1. **Round A（快档）**：Gemini Flash / 豆包「快速」/ 元宝默认快模型 — 三通道对齐后再比质量  
2. **Round B（升一档）**：Gemini Pro（或 2.5 Pro）/ 豆包「专家」/ 元宝对应高档 — **元宝跑通 Round A 后再加测**

jsonl 新增字段：`model_label`（脚本选定或人工录入页面显示名）。

加载 brief（含表述规范）:

```bash
cd lit_auto_pipeline && source venv/bin/activate
export BRIEF_PROMPT="$(python3 -c "
from doubao_rpa import load_structured_prompt
print(load_structured_prompt('brief'), end='')
")"
```

### 2.3 执行顺序（浏览器互斥 · 串行）

同一时刻只开一个 Playwright persistent context：

1. **Gemini** → 2. **元宝** → 3. **豆包导读**（`dev-brief --no-share`）→ 4. **豆包链**（`share-link`）  
步骤 3–4 **串行**、共用 `./doubao_profile`（**153**）；勿用 **130**。同一时刻只开一个 Playwright context。

### 2.4 单篇命令模板

设 `PDF=~/Desktop/PDFs/<stem>.pdf`，`STEM` 为不含扩展名的文件名。

#### Gemini（`gemini_playwright_profile`）

```bash
python3 gemini_rpa.py --pdf "$PDF" \
  -o "${PDF%.pdf}_gemini_reading_note.txt"
```

首次登录: `python3 gemini_login.py`

#### 元宝（`yuanbao_profile`）

```bash
python3 yuanbao_rpa.py --pdf "$PDF" \
  --prompt "$BRIEF_PROMPT" \
  --mode silent
# 脚本默认写 ${PDF%.pdf}_result.txt → 手动或脚本重命名为:
#   ${STEM}_yuanbao_reading_note.txt
```

元宝首次登录: 弹出 Chrome 打开 `https://yuanbao.tencent.com/chat`，在 `yuanbao_profile` 内完成腾讯账号登录。

#### 豆包导读（`./doubao_profile` · **153**）

```bash
python3 doubao_rpa.py --pdf "$PDF" \
  --job dev-brief \
  --prompt-type brief \
  --no-share \
  --profile ./doubao_profile
# 默认写 ${PDF%.pdf}_doubao_result.txt → 重命名为:
#   ${STEM}_doubao_brief_reading_note.txt
```

#### 豆包链（chip · 不参与导读打分 · 同 **153** profile 串行）

```bash
python3 doubao_rpa.py --pdf "$PDF" \
  --job share-link \
  --profile ./doubao_profile
```

### 2.5 Profile 确认：`./doubao_profile`

- **已决策**：无需新注册；豆包链早期测试已在 `./doubao_profile` 登录 **153**（测试/RPA 账号）。
- 执行比选前确认该 profile 仍能正常对话；若失效，用 **153** 重新登录（**勿** 换成主力日常 **130**）：

```bash
cd lit_auto_pipeline && source venv/bin/activate
python3 - <<'PY'
import asyncio
from playwright.async_api import async_playwright

PROFILE = "./doubao_profile"
URL = "https://www.doubao.com/chat/"

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE, headless=False, channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded")
        print("确认【153 测试账号】已登录豆包并能对话，否则在此登录后按 Enter…")
        await asyncio.get_event_loop().run_in_executor(None, input)
        await ctx.close()
    print(f"✅ 登录态已写入 {PROFILE}")

asyncio.run(main())
PY
```

**勿** 用主力日常 **130** 登录 `./doubao_profile`。

### 2.6 输出布局

每篇 PDF、每通道一份导读 + 一份汇总 jsonl：

```text
~/Desktop/PDFs/
  {stem}_gemini_reading_note.txt
  {stem}_yuanbao_reading_note.txt
  {stem}_doubao_brief_reading_note.txt

lit_auto_pipeline/logs/three_channel_compare/
  run_YYYYMMDD_HHMMSS.jsonl      # 每行一篇×通道指标
  run_YYYYMMDD_HHMMSS_summary.json
```

**jsonl 字段建议**:

```json
{
  "run_id": "20260624_…",
  "pdf": "/path/to/file.pdf",
  "stem": "file",
  "paper_type": "review|rct|case",
  "channel": "gemini|yuanbao|doubao_brief",
  "profile": "gemini_playwright_profile|yuanbao_profile|doubao_profile",
  "prompt_version": "brief_rpa",
  "ok": true,
  "reading_note_len": 1141,
  "elapsed_sec": 142.3,
  "error": null,
  "scores": {
    "structure_fill": 4,
    "no_fabrication": 5,
    "terminology": 4,
    "fluency": 4,
    "route_issue": false
  },
  "notes": ""
}
```

### 2.7 评分量表（人工 · 每篇每通道 1–5 分）

| 维度 | 说明 |
|------|------|
| **结构空填** | 五段/弹性框架是否填满；「文中未报告」是否合理 vs 空洞 |
| **编造数字** | 是否出现 PDF 中不存在的 P 值、样本量、率（**一票否决** 倾向） |
| **术语** | 是否符合 `style_guide` / 医美临床中文习惯 |
| **流畅度** | 可读性、逻辑链、无机器腔 |
| **耗时** | `elapsed_sec` 记录；大 PDF 超时记 fail |
| **失败率** | 登录、上传、超时、分享/抠字失败 → `ok: false` |
| **线路问题** | Gemini 是否因出海/验证码/断连失败（单独标记 `route_issue`） |

**汇总**: 按通道算均分 + 失败率；分 `paper_type` 分层看赢家是否一致。

### 2.8 批跑骨架（参考，不自动执行）

```bash
PDF_DIR=~/Desktop/PDFs
OUT_LOG=logs/three_channel_compare/run_$(date +%Y%m%d_%H%M%S).jsonl
mkdir -p logs/three_channel_compare

for pdf in "$PDF_DIR"/<selected>.pdf; do
  stem="${pdf%.pdf}"
  # 1 Gemini
  python3 gemini_rpa.py --pdf "$pdf" -o "${stem}_gemini_reading_note.txt"
  # 2 Yuanbao
  python3 yuanbao_rpa.py --pdf "$pdf" --prompt "$BRIEF_PROMPT" --mode silent
  mv "${stem}_result.txt" "${stem}_yuanbao_reading_note.txt" 2>/dev/null || true
  # 3 Doubao brief（test profile）
  python3 doubao_rpa.py --pdf "$pdf" --job dev-brief --prompt-type brief \
    --no-share --profile ./doubao_profile
  mv "${stem}_doubao_result.txt" "${stem}_doubao_brief_reading_note.txt" 2>/dev/null || true
  # 4 Doubao share-link（同 profile 串行）
  python3 doubao_rpa.py --pdf "$pdf" --job share-link --profile ./doubao_profile
done
```

---

## 3. Gemini RPA 实现备忘

- **Commit**: `62ed240` — `feat(gemini): add Web RPA for brief extraction and share links`
- **压测**: `logs/gemini_stress/run_20260624_160120.jsonl` — share 1/1, brief 1/1, 1141 字
- **分享菜单**: conversation panel 右上 ⋮ → `button[aria-label*="conversation actions"]`
- **模型**: 默认 3.5 Flash（`gemini_rpa_extract.DEFAULT_MODEL_LABEL`）

---

## 4. 待办 / 未决

- [ ] 执行三通道 5–10 篇比选，填 jsonl + 人工打分
- [ ] 根据比选结果选定运行时单通道赢家
- [ ] 编写 `brief_adaptive` / `brief_reader` prompt（见 §6 方向）
- [ ] `batch_worker.py` 双轨：豆包 share-link → 赢家导读
- [x] `three_channel_compare.py` 单篇/批跑封装

---

## 6. 导读 Prompt 方向（2026-06-24 定调 · 持续打磨）

> **误区纠正**：中间页导读 **不是**「深读」入口文案，不要直白写成深读；目的是帮 **读者快速把握原文精华**。

### 6.1 与「创新性评估」prompt 的关系

| 原用途（编辑选题） | 中间页导读调整 |
|-------------------|----------------|
| 评估创新性 + 是否值得报道 | **报道必要性本身已蕴含阅读价值**；改为读者视角的「这篇有什么看点」 |
| 批判性交叉验证（PRS/ASJ 等） | **不使用** — 标准过高、准确性未检验、易翻车 |
| 评判式措辞 | **立足原文转述**，创新/贡献用「作者认为 / 本文报告」 |
| 深读导向 | 自成一体的精华摘要，读完知道「多知道什么」 |

**可保留的挖掘角度**：创新性、贡献价值、临床问题 — 这些都是「看点」的核心，但表述是 **转述而非评判**。

### 6.2 与僵化五段式的关系

- 五段 `brief_rpa` 普适性不足，测试轮仍可用作 **三通道统一 baseline**。
- 下一轮 prompt：`brief_reader` / `brief_adaptive` — 弹性结构，有则写、无则省；文风参考创新性 prompt 的 **流畅与扎实**，纪律保留（不编造、术语规范、≤1000 字）。

### 6.3 修订记录（prompt）

| 日期 | 变更 |
|------|------|
| 2026-06-24 | 定调：读者精华 / 作者陈述视角 / 无交叉验证 / 非深读话术 |

---

## 7. 修订

| 日期 | 变更 |
|------|------|
| 2026-06-24 | 初稿：决策 + 三通道测试协议 + Gemini 62ed240 状态 |
| 2026-06-24 | 豆包：链+导读串行共用 `./doubao_profile`（**153**）；与主力 **130** 隔离；无需新注册 |
| 2026-06-24 | §6 导读 prompt 定调；`three_channel_compare.py` 单篇试跑 |
| 2026-06-24 | `six_sample_compare.py`：六样本（快+Pro/专家/深度思考）+ 报告 |
| 2026-06-24 | **Round 1 结论**：五段 `brief_rpa` 仅作 baseline，**下轮放弃**；豆包追问 chip / 元宝 `AI Reading` **不计入质量分**（RPA 剥离即可） |
| 2026-06-24 | **Round 2 升档观测**：Gemini Pro 日志有 `✅ 已选 Pro` 可采信；豆包生成中 UI 常回显「快速」≠ 后端降档；元宝英文 UI 为 **Deep Thinking** 高亮才算真开（旧 selector 只搜中文导致假开） |
| 2026-06-24 | 元宝 **Deep Thinking 会话记忆**：profile 保留上次关闭时的开关；开窗即绿=已开，RPA **禁止再点**（会关掉）。比选快档时需显式 `set_deep_thinking(False)` 并确认变灰 |
| 2026-06-25 | **Round 2 跑完**：12 份 `brief_open` 样本（2 篇×6 档）；§9 质量/稳定结论；`rpa_tier.py` + 豆包上传前选档；元宝 DT 折叠区抠字 |
| 2026-06-25 | **评分原则**：工程成本（chip/PDF 角标/思考链泄露）**不计入文本质量分**；6 档各自两篇均分，**禁止**把 Gemini Flash+Pro 合并成「通道分」 |
| 2026-06-25 | **API 配置**：`.env.api_compare` + `--verify`；Gemini 2.5/3.5、DeepSeek、豆包 lite-32k ep |

---

## 8. Round 2 比选协议（2026-06-24 定 · 2026-06-25 已执行）

> 执行结果见 **§9**；本节保留协议真源。

### 8.1 对 Round 1 的修正

| 项 | 结论 |
|---|---|
| **UI 杂质** | 豆包末尾「用自己的话总结…」类 **追问 chip**、元宝 **AI Reading** — 属产品 UI，**非模型回复**；RPA 后处理剥离，**不因「术语/流畅/硬凑」扣分** |
| **五段 prompt** | Round 1 偏离真实场景；**下轮不用** `brief_rpa.txt` |
| **样本类型** | Round 1 仅 market/review（韩国价值观述评）；Round 2 补 **手术类** + **注射/非手术类** |

### 8.2 Prompt（开放导读）

**主用**：`prompts/brief_open.txt`

```text
这篇文章比较长。为便于向同行快速了解要点和关键细节，请用简体中文输出一份约一千字的导读。
（+ 不编造、术语习惯、转述纪律 — 见文件全文）
```

**次选**（Round 2 通过后）：`brief_reader` / `brief_adaptive` 弹性版（§6 方向），有则写、无则省。

### 8.3 样本（实际执行：2 篇 × 6 档 = 12 份）

| # | paper_type | PDF（`~/Desktop/PDFs`） | 状态 |
|---|------------|-------------------------|------|
| 1 | surgical | `less_is_better__full_incision_double_eyelid.18.pdf` | ✅ |
| 2 | injection | `J of Cosmetic Dermatology - 2023 - Peng - …`（HA 回抽） | ✅ |
| — | review/market | `why_cosmetic_surgery…korea*.pdf` | 未纳入本轮 |

### 8.4 评分维度（编辑）

- **要点准确性** — 设计/样本/主要终点/关键数字是否可回溯原文
- **全面性** — 临床读者关心的信息是否遗漏（AE、局限、适应证等）
- **表述** — 流畅、术语、不编造、不评判
- **字数** — 约千字为目标；**超过优于不足**，超千字不算缺点
- **不计分** — UI chip 是否混入（工程剥离项，非模型质量）

### 8.5 Round 1 三通道一句话（五段 baseline · 已修正）

| 通道 | 一句话 |
|------|--------|
| **Gemini** | 理解最深、临床切口与引文语境最好；**排 1** |
| **豆包** | 数字与理论抓得准、信息密度高，句式偏密；**排 2** |
| **元宝** | 版式友善、结构稳，深度思考升档无效、偶漏引文数字；**排 3** |

### 8.6 执行

```bash
cd lit_auto_pipeline && source venv/bin/activate
python3 open_compare.py   # 默认：重睑 + HA 两篇
python3 open_compare.py --skip-existing   # 断点续跑
```

输出：`{stem}_*_open_reading_note.txt`（6 档命名）+ `logs/open_compare/run_*.jsonl`

---

## 9. Round 2 开放导读 · 已完成（2026-06-25）

### 9.1 样本矩阵（12/12）

**Prompt**: `prompts/brief_open.txt`  
**篇目**: 重睑 `less_is_better__full_incision_double_eyelid.18.pdf` · HA 回抽 `J of Cosmetic Dermatology - 2023 - Peng - …`

| 档位 | 重睑 | HA | 两篇均分（质量） |
|------|:---:|:---:|:---:|
| **元宝 DT** | 4.5 | 5.0 | **4.75** |
| **Gemini Flash** | 4.5 | 5.0 | **4.75** |
| Gemini Pro | 4.5 | 4.5 | 4.50 |
| 豆包快 | 4.0 | 4.5 | 4.25 |
| 元宝快 | 4.0 | 4.0 | 4.00 |
| 豆包专家 | 3.5 | 3.5 | 3.50 |

**计分规则**: 仅文本（准确/全面/表述）；UI 杂质不扣分；超千字不扣分。  
**HA 豆包专家**曾截断，已补跑（上传前确认「专家」+ 等待/剥离逻辑修复）。

### 9.2 质量结论（编辑向）

- **并列第一**: 元宝 DT ≈ Gemini Flash（4.75）；DT 局限段更全，Flash 结构更顺
- **Gemini Pro**: 未优于 Flash（HA 略短）；**档位高 ≠ 导读更好**
- **豆包快 > 豆包专家**: 专家有思考链/重复/提纲腔，无升档收益
- **元宝快**: 可读性好，深度逊于 DT
- **正式比选 4 档即可**: Flash / Pro / 豆包快 / 元宝快；专家与 DT 作附录对照

### 9.3 稳定性（RPA，与质量分分开）

| 排名 | 档位 | 说明 |
|:---:|------|------|
| 1 | Gemini Flash | 无截断、无思考链；仅 PDF 角标 |
| 2 | 豆包快 | 偶发验证码；chip 剥离；`ensure_model_before_upload` |
| 3 | 元宝快 | DT 关灰确认；`AI Reading` 剥离 |
| 3 | 元宝 DT | **折叠区抠字已修**（§9.4）后升至与快档同级 |
| 4 | Gemini Pro | 模型下拉偶发未点到 |
| 5 | 豆包专家 | 截断/思考链/重复，最折腾 |

**产线默认（RPA）**: **Gemini Flash**；备选豆包快；元宝 DT 在抠字稳定后可并列考虑。

### 9.4 工程修复（2026-06-25）

| 模块 | 变更 |
|------|------|
| `rpa_tier.py` | 统一 `tier_requested` / `tier_observed` / `tier_verified` |
| `doubao_rpa.py` | `ensure_model_before_upload`：**先选档再上传** |
| `doubao_rpa_extract.py` | 开放导读：保留最长正文、等生成结束、专家思考句剥离 |
| `yuanbao_rpa.py` | `_extract_ai_text`：DOM 去掉 think 节点 + `strip_yuanbao_deep_thinking_fold()` |
| `prompts/open_brief_utils.py` | 元宝 DT 折叠头 `已深度思考`；豆包专家 `我会…` 剥离 |
| `open_compare.py` | jsonl 写入 tier 字段 |

**元宝 DT UX**: 产品侧 CoT 在 **「已深度思考(用时N秒)」折叠区**，与正式回复分区；此前 RPA 整泡 `inner_text` 误捞 CoT，**非模型质量问题**。

### 9.5 环境与并发（澄清）

- **Chrome 导读 + Edge 知网**: 不同 profile、不同进程，**无需为错峰而互斥**
- **必须串行**: 同 profile（如 `doubao_profile` 链+导读）、同 Playwright context
- **验证码**: 仅 CNKI 有 10min 等待；导读三通道尚无等价逻辑（豆包见过 1 次）

### 9.6 产出路径

```
~/Desktop/PDFs/*_open_reading_note.txt          # 12 份 RPA
logs/open_compare/run_*.jsonl
open_compare.py --skip-existing
```

---

## 10. API 比选（2026-06-25 起）

### 10.1 动机

RPA 免费额度/稳定性 vs API 可编程；与 Web 档位 **不一一对应**，须分开测。

### 10.2 模型对照（勿混淆）

| 讨论名 | API `model` / 配置 | 与 RPA 关系 |
|--------|-------------------|-------------|
| Gemini 2.5 Flash | `gemini-2.5-flash` | **须单独测**；≠ 3.5；价更低 |
| Gemini 3.5 Flash | `gemini-3.5-flash` | RPA UI 药丸常标 3.5；价更高 |
| DeepSeek Flash DT | `deepseek-v4-flash` + thinking | 粗对元宝 DT |
| DeepSeek Pro DT | `deepseek-v4-pro` + thinking | 粗对深档质量 |
| 豆包 lite-32k | `ep-20250525113859-xmhhh`（aas-lite-32k） | **≠** Web「快速」 |
| 豆包 Seed-Evolving | 另建 `ep-…` 接入点 | 与 lite-32k 二选一 |

**Gemini 免费额度**：Google AI Studio（Pro 账号）常有免费请求/RPM 配额 → 控制台 **Quotas** 查看；比选 **2.5 与 3.5 各跑一遍**，不可混为一档。

**豆包 API 定价（Seed-Evolving 参考 · 2026-06）**：输入 ¥0.006/千 token · 输出 ¥0.03/千 token · 新接入点常送 50 万 token。lite-32k 接入点按控制台计费。

### 10.3 配置与验证

```bash
cd lit_auto_pipeline && source venv/bin/activate
cp .env.api_compare.example .env.api_compare
# 编辑填入：GEMINI_API_KEY、DEEPSEEK_API_KEY、ARK_API_KEY
# ARK_ENDPOINT 示例已预填 ep-20250525113859-xmhhh

python3 open_compare_api.py --setup      # 各平台获取步骤
python3 open_compare_api.py --verify     # Ping 五档
python3 scripts/verify_api_compare.py    # 同上

python3 open_compare_api.py --list-models
python3 open_compare_api.py --skip-existing   # 五档×2 篇默认 PDF
```

**Key 获取**：
- **Gemini**：https://aistudio.google.com/apikey
- **DeepSeek**：https://platform.deepseek.com → API Keys → 创建 → `DEEPSEEK_API_KEY`
- **豆包**：https://console.volcengine.com/ark → API Key + 推理接入点 `ep-`

产出：`{stem}_api_{slug}_open_reading_note.txt` · `logs/open_compare_api/run_*.jsonl`

### 10.4 状态

- [x] RPA Round 2 十二样本 + 编辑评语  
- [x] 元宝 DT 折叠抠字  
- [x] `open_compare_api.py` + `config/api_compare.env` + `--verify`  
- [x] API 四档批跑（2 篇；豆包 `NO_PROXY` 补跑）  
- [x] API vs Web 横纵对照 §12  
- [ ] gemini-3.5-flash API 补跑（503）  
- [ ] 选定运行时赢家 → `batch_worker.py`

---

## 12. API vs Web 横纵对比（2026-06-25）

### 12.1 样本清单

**Web RPA**（12 份，`open_compare.py`）· **API**（8 份，`run_20260625_120818` + 豆包 `121252`）

| 对照轴 | Web 文件后缀 | API slug |
|--------|-------------|----------|
| Gemini Flash | `_gemini_open_` | `gemini-2.5-flash` |
| Gemini Pro | `_gemini_pro_open_` | —（3.5 API 503 未跑） |
| 豆包快 | `_doubao_open_` | `doubao-lite-32k`（ep=Seed-Evolving） |
| 豆包专家 | `_doubao_expert_open_` | — |
| 元宝快 | `_yuanbao_open_` | — |
| 元宝 DT | `_yuanbao_deepthink_open_` | 粗对 `deepseek-v4-flash` |
| — | — | `deepseek-v4-pro` |

### 12.2 字数（纵向：同篇不同档）

| 档位 | 重睑 | HA |
|------|:---:|:---:|
| **Web** 元宝 DT | 2168 | 2892 |
| **Web** Gemini Flash | 1626 | 2245 |
| **API** Gemini 2.5 | 1754 | **3521** |
| **API** DeepSeek Flash | 1553 | 1601 |
| **Web** 元宝快 | 1582 | 1684 |
| **API** DeepSeek Pro | 1257 | 1438 |
| **Web** Gemini Pro | 1392 | 1985 |
| **Web** 豆包快 | 1369 | 1421 |
| **Web** 豆包专家 | 1364 | 1111 |
| **API** 豆包 Seed | 1190 | 1404 |

### 12.3 质量分（1–5，同 Round 2 规则；工程杂质不扣分）

#### 横向（同档两篇均分）

| 档位 | 重睑 | HA | 均分 | 备注 |
|------|:---:|:---:|:---:|------|
| **API Gemini 2.5** | 5.0 | 4.5 | **4.75** | 无 PDF 角标；HA 偏长 |
| **API DeepSeek Flash** | 5.0 | 4.5 | **4.75** | 局限段全；无思考链泄露 |
| Web 元宝 DT | 4.5 | 5.0 | 4.75 | 重睑文件或含历史 CoT 头 |
| Web Gemini Flash | 4.5 | 5.0 | 4.75 | 正文好；有 Gemini said/PDF 角标 |
| Web Gemini Pro | 4.5 | 4.5 | 4.50 | |
| **API 豆包 Seed** | 4.0 | 4.5 | **4.25** | 句式密；数字准 |
| Web 豆包快 | 4.0 | 4.5 | 4.25 | |
| **API DeepSeek Pro** | 4.5 | 4.0 | **4.25** | 偏短，HA 略漏随访细节 |
| Web 元宝快 | 4.0 | 4.0 | 4.00 | |
| Web 豆包专家 | 3.5 | 3.5 | 3.50 | |

#### 纵向（同篇跨 Web+API 要点）

**重睑**：API Gemini 2.5 / DS Flash ≥ Web Flash/DT；局限与「文中未报告」更完整。Web Gemini 有引用角标（不计质量分）。  
**HA**：Web 元宝 DT 与 API Gemini 2.5 信息最全；API Gemini 2.5 **过长**（3521 字）。DS Flash 结构最均衡。豆包 API ≈ Web 快。

### 12.4 API vs Web 同通路结论

| 通路 | 结论 |
|------|------|
| **Gemini** | API 2.5 ≈ Web Flash **质量同级**（4.75）；API 文本更干净；Web 胜在已登录免 key |
| **豆包** | API Seed-Evolving ≈ Web **快档**（4.25）；≠ lite-32k 旧名；≠ 专家 |
| **DeepSeek** | Flash **对齐元宝 DT 档**（4.75）；国内 API、无 RPA 抠字成本 |
| **元宝** | 无 API 直连；DS Flash 为最接近 API 参照 |

### 12.5 工程与成本

| 项 | 说明 |
|----|------|
| 豆包 API | 长 PDF 易触发代理超时；批跑加 `NO_PROXY='*'` |
| Gemini 3.5 API | 账号可见模型，但 503 高负载；待补跑 |
| Gemini 2.5 thoughts_tokens | 有内部思考计费；比选时关注账单 |
| 豆包 output tokens | HA 篇 completion ~5677（偏高） |

### 12.6 产线倾向（API 视角 · 待 Gemini 3.5 补测）

1. **质量并列**：API Gemini 2.5 ≈ API DeepSeek Flash ≈ Web Flash/元宝 DT  
2. **API 首选**：**DeepSeek Flash**（质量顶、国内、无 RPA）或 **Gemini 2.5**（略长但干净）  
3. **Web 首选**（已有结论）：Gemini Flash RPA（稳定）  
4. **豆包**：API 仅作国内备选，不优于 Web 快档  
5. **未跑**：gemini-3.5-flash API、DeepSeek vs 元宝 DT 同模型细抠

### 12.7 产出路径

```
~/Desktop/PDFs/*_api_*_open_reading_note.txt
logs/open_compare_api/run_20260625_120818.jsonl
logs/open_compare_api/run_20260625_121252.jsonl  # 豆包补跑
```

---

## 11. 新对话接续（复制用）

```text
Read AES_PIPELINE_HANDOFF.md + session §9–§12。
Web Round2 12 份 + API 8 份（4 档×2 篇）已完成。
质量顶：API Gemini 2.5 / DS Flash / Web Flash / 元宝 DT 均 ~4.75。
API 产线倾向 DS Flash 或 Gemini 2.5；Web 仍 Gemini Flash RPA。
待补：gemini-3.5-flash API 重睑篇（503）。
```

---

## 13. Top3 稳定性·价格·Gemini 补跑（2026-06-25）

### 13.1 角标 = UX，非质量障碍

Gemini Web 上传 PDF 后，回复中 **「PDF +N」「Gemini said」** 来自产品 **Grounding/附件引用 UI**，与模型理解无关。比选 **不计入质量分**；产线用 `strip_gemini_pdf_citations()` 后处理即可（与豆包 chip、元宝 AI Reading 同类）。

### 13.2 质量 Top3（已定，§12 延用）

1. **API DeepSeek V4 Flash** — 4.75  
2. **Web 元宝 DT** — 4.75  
3. **Web Gemini 3.5 Flash** — 4.75  

### 13.3 过程时长（`elapsed_sec`，2 篇均值）

| 档位 | 平均耗时 | 稳定性初判 |
|------|:---:|:---|
| **API DS Flash** | **17.5s** | ★★★★★ 无浏览器；两次均成功 |
| API Gemini 3.1 Lite | 4.8s | 快但**导读过短**（823/934 字） |
| API Gemini 2.5 | 21.3s | ★★★★☆ |
| API Gemini 3.5 | 29.6s（仅 HA 1 篇） | ★★☆☆☆ **重睑 503×2** |
| Web Gemini 3.5 Flash | 59.4s | ★★★★★ |
| Web 元宝 DT | 86.3s | ★★★★☆ |
| Web Gemini 3.1 Lite | **176.6s** | ★★☆☆☆ 重睑 **240s 超时**截断 |
| API 豆包 Seed | 91.8s | ★★★☆☆ 首跑代理失败需 `NO_PROXY` |

**稳定性排序（Top3 候选）**：API DS Flash > Web Gemini 3.5 > Web 元宝 DT

### 13.4 API 两篇费用粗算（USD，官方单价近似）

| 模型 | 2 篇合计 | 备注 |
|------|:---:|------|
| 豆包 Seed | ~$0.05 | ¥0.006/0.03·千 token；50 万免费额内 $0 |
| DeepSeek Flash | ~$0.003 | 极低 |
| Gemini 3.1 Lite | ~$0.001 | 极便宜，**不适合导读** |
| Gemini 2.5 | ~$0.024 | 含 thoughts 计费 |
| Gemini 3.5 | ~$0.06+ | 仅 1 篇；含 thoughts 3847 |

Web RPA：**$0 按量**，但占用浏览器 ~1–3 min/篇 + 偶发 profile 锁。

### 13.5 Gemini Flash 补跑结论（3.5 vs 3.1 Lite）

| | Web 3.5 Flash | Web 3.1 Lite | API 3.5 | API 3.1 Lite |
|--|:---:|:---:|:---:|:---:|
| 重睑字数 | 1626 | 1322（超时） | ❌503 | 823 |
| HA 字数 | 2245 | 1190 | 1722 | 934 |
| 质量估 | **4.75** | **~3.75** | HA **~4.5** | **~3.5** |

**结论**：导读任务 **应用 3.5 Flash**；3.1 Flash-Lite 官方定位轻量抽取，样本证实**偏短、漏局限**，不适合作 `reading_note_zh`。

### 13.6 综合产线倾向（质量→稳定→价）

| 优先级 | 路径 | 理由 |
|:---:|------|------|
| 1 | **API DeepSeek Flash** | 质量顶 + 最快 + 最便宜 + 最稳 |
| 2 | **Web Gemini 3.5 Flash** | 质量顶 + 多模态 PDF；免费额度 |
| 3 | Web 元宝 DT | 质量顶；略慢；RPA 维护 |

待办：API `gemini-3.5-flash` 重睑篇 503 恢复后补跑 → 真·同模型 Web/API 对照。

---

## 14. 创新性交叉验证比选（2026-06-25 起）

**目的**：测英文文献 **检索/交叉验证效力**（Gemini vs 国内模型），非开放导读。

**Prompt**：`prompts/brief_innovation_audit.txt`

**档位（每家族 1 档）**：

| lane | 档位 |
|------|------|
| `gemini_web` | 3.5 Flash（Web，或可触发 Google 检索） |
| `deepseek_api` | v4-flash（API） |
| `yuanbao_web` | Deep Thinking |
| `doubao_web` | 快速 |

**样本**：Round 2 两篇英文 PDF（重睑 PRS 技术稿 · HA/JCD 实验稿）

```bash
python3 innovation_compare.py
python3 innovation_compare.py --lanes gemini_web,deepseek_api --skip-existing
```

产出：`{stem}_innovation_{suffix}.txt` · `logs/innovation_compare/run_*.jsonl`

**评分维度（待跑后填）**：原文创新提炼准确度 · 是否真检索/给出处 · 交叉验证是否诚实 · 有无编造 PRS/ASJ 引文 · 中文报道价值判断是否合理

### 14.1 比选报告（2026-06-25）

**样本**：重睑 PRS 2024 Ideas · HA 回抽 JCD 2023  
**档位**：Gemini Web 3.5 / DeepSeek API v4-flash / 元宝 DT / 豆包快

#### A. 总表（两篇综合 · 1–5）

| 档位 | 创新提炼 | 检索/交叉验证 | 学术诚实 | 报道价值判断 | 综合 |
|------|:---:|:---:|:---:|:---:|:---:|
| **元宝 DT** | 4.5 | **4.5** | **5.0** | 4.5 | **4.6** |
| **Gemini 3.5 Web** | 4.5 | 4.0 | 4.5 | 4.5 | **4.4** |
| **豆包快** | 4.0 | 4.0 | 3.5 | 4.0 | **3.9** |
| **DeepSeek API** | 4.5 | 3.0 | 4.0 | 4.0 | **3.9** |

#### B. 检索效力（核心差异）

| 能力 | Gemini Web | 元宝 DT | 豆包快 | DeepSeek API |
|------|:---:|:---:|:---:|:---:|
| 点名 Kogan 2020 JCD（盐水预充） | ✅ HA | ✅ HA | ✅ HA | ❌ HA 写「未检索到」 |
| 点名 Torbeck 2019 Derm Surg | ✅ | ✅ | ✅ | ✅ 带完整引文 |
| PRS Ideas 栏目语境（重睑） | 部分 | ✅ DOI+栏目 | 部分 | 部分 |
| 显式「未能核实/未检索到」 | 隧道术式 | ✅ 多处 | 局限段有 | 较少 |
| 产品「搜索 N 篇」痕迹 | 无 | 无 | **「21/24 篇」** | 无 |
| 疑似编造/过度推断 | PDF 角标 | CoT 头（工程） | 中华整形**2026**？ | HA 新颖性误判 |

**结论**：  
- **真检索 + 诚实交叉验证**：元宝 DT ≈ Gemini Web > 豆包（有搜索 UI 但引文待核）> DeepSeek（**HA 漏 Kogan，误判利多卡因为首创**）。  
- **Gemini vs 国内**：Gemini Web 在 HA 篇与元宝同级（均抓到 Kogan 先行）；DeepSeek **不如** Gemini/元宝；豆包搜索量大但诚实度略逊。  
- **无模型**在 API 纯文本模式下真联网；Gemini/豆包 Web 或有 Grounding/搜索 UI，元宝靠长上下文+参考文献链推理。

#### C. 分篇要点

**重睑（incremental 共识一致）**  
- 四路均判：**保 OOM + 点状固定 = 前人已有**；微隧道量化 = 有限组合创新；25 例无对照 = 证据弱。  
- **元宝**最佳：PRS *Ideas and Innovations* 定位、Shen 2021/JCD 前身、DOI 核实。  
- **Gemini**：隧道 1.5–2mm「未检索到完全一致」— 诚实且细腻。  
- **豆包**：结构最工整，但「2014 PRS Muscle-Sparing…」「中华整形 2026」需人工核实是否 hallucination。

**HA（Kogan 2020 是试金石）**  
- **元宝/Gemini/豆包**：均指出利多卡因预充 ≈ Kogan 盐水法的 **介质替换**，创新 = incremental。  
- **DeepSeek**：称利多卡因预充「未检索到直接描述」— **与原文 ref 13 及领域文献不符**，检索效力明显短板。  
- **报道价值**：四路均认 **HA 篇中文报道价值高于重睑**（临床可落地、并发症痛点）。

#### D. 耗时（`elapsed_sec`）

| 档位 | 重睑 | HA |
|------|:---:|:---:|
| DeepSeek API | 18s | 27s |
| Gemini Web | 72s | ~240s（顶满） |
| 元宝 DT | 100s | 99s |
| 豆包快 | ~200s | ~205s |

#### E. 产线建议（创新性审计任务）

| 场景 | 推荐 |
|------|------|
| **英文文献创新/查新审计** | **元宝 DT Web** 或 **Gemini 3.5 Web** |
| 批量 API、低成本 | DeepSeek **需人工复核** Kogan/先行文献 |
| 国内搜索 UI 参考 | 豆包可作补充，**引文必须人工核实** |

#### F. 产出

`~/Desktop/PDFs/*_innovation_*.txt` · `logs/innovation_compare/run_*.jsonl`

### 14.2 Round 1 样本局限 · Round 2 查新设计（2026-06-25）

**Round 1 结论：两篇都不太适合测「真检索」**

| 篇目 | 为何混淆 |
|------|----------|
| **HA JCD 2023** | PDF **References 已含** Torbeck 2019、Kogan 2020；模型读 ref 即可「交叉验证」，无需 PubMed |
| **重睑 PRS 2024** | 领域常识饱和（Cho/Liu/Shen/Fagien）；Ideas 短篇 + 文内引文；测的是**记忆+读 ref** |

**记忆 vs 真查库（本轮判定）**

| 通道 | 是否真查 PubMed/Scholar |
|------|-------------------------|
| **Gemini API** | ❌ 默认不联网 |
| **Gemini Web** | ⚠️ 可能 **Google Search/Grounding**，**≠** 保证 PubMed/ Scholar API |
| **豆包 Web** | ⚠️ 产品「搜索 N 篇」≈ **通用联网**，非 PubMed 专用 |
| **元宝 DT** | ❌ 未见外搜痕迹；强在 **PDF+ref 推理** |
| **DeepSeek API** | ❌ 纯记忆（HA 漏 Kogan 为证） |

**英文查新真源**：**PubMed**（E-utilities / Europe PMC）；Scholar 无稳定 API，仅作人工辅证。

**Round 2 样本选取原则**（体现 prompt 第 2 点区分度）：

1. **遮住或剔除 PDF References**（只给 title/abstract/methods）→ 逼外搜  
2. 选 **冷门术式 / 非美容外科主战场** 或 **2024–2026 新发文**，减少训练记忆  
3. 预先用 PubMed 建 **金标准**：2–5 篇必命中先行文献（含 DOI/PMID）  
4. 设 **陷阱**：原文未引但 PubMed 可搜到的同义词术式（测相关度）  
5. **仅 Web 比搜索**；API 单列标注「无检索能力」

**Prompt 增补（待写 `brief_innovation_audit_v2.txt`）**：

- 强制输出：`检索式` / `命中篇目（刊名+年+PMID 或 DOI）` / `未能核实`  
- 禁止仅复述 PDF References（若输入已遮 ref）

**候选换篇方向**：非整形热门（如罕见并发症个案）、或你们库内 **无 ref 页的预印本/内部稿**；勿再用 HA/重睑类「参考文献即答案」文。

---

## 15. 阶段性定型结论（2026-06-25）✅

**比选收束**：三通道 Web 导读比选结束；运行时按三轨拆分，不再追求「一个模型包打天下」。

| 轨 | 字段 / 能力 | 定型方案 | 输入 | 备注 |
|----|-------------|----------|------|------|
| **深读** | `doubao_read_url` | **豆包 Web** · `share-link` chip | 整 PDF 上传 | profile `doubao_profile`（153）；与导读 **解耦**（API 无浏览器冲突） |
| **导读** | `reading_note_zh` | **DeepSeek V4 Flash API** | `pypdf` 纯文本 | `brief_open.txt`；~¥0.009/篇；质量 4.75；**不读图** |
| **插图** | `hero_image_url`（C32） | **本地 Python 抽图** + 编辑 Console | PDF raster 提取 | 后台展示**全部**插图候选；编辑择一 → 前台头图；**排版视觉**，非导读输入 |

### 架构图

```
PDF 就绪
  ├─ 豆包 Web RPA     → doubao_read_url（深读外链）
  ├─ DeepSeek API     → reading_note_zh（中间页导读）
  └─ pdf_figure_extract（待开发）→ figure_candidates → 编辑选 hero_image_url
```

### 明确不做

- 导读不走豆包 / Gemini / 元宝 Web RPA（比选归档，回归抽检可用）
- 插图不进 DeepSeek prompt（MVP）
- 创新交叉验证不进 `batch_worker` MVP（P2+ 另议）

### 待开发（按优先级）

1. ~~`batch_worker.py`~~ ✅（`--pdf` · 并行/串行 · `*.aes_l3.json`）
2. `pdf_figure_extract.py` + Console 选头图 UI
3. `brief_adaptive` / `paper_type` 路由

### 成本备忘

- DeepSeek 导读：典型 **< ¥0.01/篇**；¥100 充值可用很久
- 豆包链：Web **$0 按量**；占用 Chrome ~1–3 min/篇
