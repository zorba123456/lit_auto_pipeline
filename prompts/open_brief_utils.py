"""开放导读 prompt（brief_open）抠字与 UI chip 剥离 — 不计入质量评分。"""

from __future__ import annotations

import re

OPEN_PROMPT_ANCHORS = (
    "不做跨文献评判。",
    "不做跨文献评判",
)

# 产品 UI 追问 chip（非模型正文）
CHIP_CUT_MARKERS = (
    "用自己的话总结",
    "请再提供",
    "文档中提到的",
    "AI Reading",
    "已完成思考",
)

_CHIP_LINE = re.compile(r"^.{8,60}？\s*$")
_UI_TAIL_LINES = frozenset({
    "专家", "快速", "PPT 生成", "AI 表格", "图像生成", "帮我写作", "视频生成", "更多",
})

OPEN_MIN_CHARS = 400
OPEN_READY_CHARS = 600

INNOVATION_ANCHORS = (
    "对「中文报道价值」给出简要理由",
    "禁止编造文献或 PMID",
    "交叉验证这些技术细节",
)

INNOVATION_MIN_CHARS = 400

# 豆包专家档内联思考 / 规划语句（非导读正文）
_EXPERT_THINKING_LINE = re.compile(
    r"^(我将|用户需|我需要|我发现|完善导读|分析实验|补充引言|分析实验数据|开头阐述|接着介绍|实验设计分|详述体外|分析数据提出)"
)
_UI_HEADER_LINE = frozenset({
    "分析实验结果及假阴性原因",
    "完善导读内容与开头",
    "补充引言完善字数",
    "分析实验数据得出结论",
    "强调回抽操作及细节调整",
    "详述体外实验设计与结果",
    "分析数据提出临床建议",
})
_META_TAIL = re.compile(
    r"(最后对内容进行字数|经字数统计|检查内容无编造|最后对语句进行微调)"
)

# 元宝 DT：折叠区标题（CoT 与正式回复分区）
_YUANBAO_DT_HEADER = re.compile(
    r"^(?:已深度思考[^\n]*|Deep thinking completed[^\n]*)$",
    re.I,
)
_YUANBAO_COT_PLAN_LINE = re.compile(
    r"^(?:嗯[，,]|用户给的是|用户需要|先梳理|可以从|需要注意|整体语气|字数控制|任务是写|我将按|先搭结构)"
)
_YUANBAO_REPLY_START = re.compile(
    r"^(?:本文为|本文报告|本文聚焦|本文刊发于|这篇是|在面部|透明质酸|重睑|作者采用|本研究|研究设计与材料|主要结果|作者结论)"
)
_YUANBAO_SECTION_NOISE = frozenset({
    "研究设计与材料",
    "主要结果",
    "作者结论与操作提示",
    "局限与文中未报告项",
})


def thinking_noise_ratio(text: str) -> float:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 1.0
    noisy = sum(
        1
        for ln in lines
        if _EXPERT_THINKING_LINE.match(ln.strip()) or ln.strip() in _UI_HEADER_LINE
    )
    return noisy / len(lines)


def _clean_thinking_line(line: str) -> str:
    t = line.strip()
    if not t or t in _UI_HEADER_LINE:
        return ""
    if _META_TAIL.search(t):
        return ""
    if _EXPERT_THINKING_LINE.match(t):
        # 「我会…。」仅为规划句时整行丢弃；否则剥掉规划前缀保留正文
        if t.startswith("我会") and "。" in t[:120]:
            t = re.sub(r"^我会[^。]{0,150}。", "", t, count=1).strip()
            if not t:
                return ""
        else:
            return ""
    t = re.sub(r"^我将[^。]{0,120}。", "", t, count=1).strip()
    t = re.sub(r"。我将[^。]{0,120}。", "。", t)
    t = re.sub(r"。我将对已写好的[^。]+。", "。", t)
    t = re.sub(r"。我发现[^。]+。", "。", t)
    return t.strip()


def strip_expert_thinking(text: str) -> str:
    """去掉豆包专家档的规划/反思行，保留临床转述段落。"""
    if not text:
        return ""
    lines = [_clean_thinking_line(ln) for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return strip_chip_tail(text)
    return strip_chip_tail("\n\n".join(lines))


def strip_chip_tail(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"^已完成思考\s*\n?", "", text.strip())
    for m in CHIP_CUT_MARKERS:
        idx = text.find(m)
        if idx != -1:
            text = text[:idx]
    lines = text.splitlines()
    while lines:
        t = lines[-1].strip()
        if not t:
            lines.pop()
            continue
        if t.endswith("->") or t in _UI_TAIL_LINES:
            lines.pop()
            continue
        if _CHIP_LINE.match(t):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def extract_after_innovation_prompt(full_text: str) -> str:
    """创新性交叉验证 prompt 抠字（豆包/元宝 chip 尾部剥离）。"""
    if not full_text:
        return ""
    for anchor in INNOVATION_ANCHORS:
        if anchor in full_text:
            body = full_text.split(anchor, 1)[-1]
            return strip_expert_thinking(strip_chip_tail(body))
    marker = "是否具有向同行做中文报道的价值"
    if marker in full_text:
        return strip_expert_thinking(strip_chip_tail(full_text.split(marker, 1)[-1]))
    return strip_expert_thinking(strip_chip_tail(full_text))


def innovation_is_ready(text: str) -> bool:
    cleaned = strip_expert_thinking(text)
    return len(cleaned) >= INNOVATION_MIN_CHARS and cleaned.rstrip()[-1:] in "。！？）」》"


def extract_after_open_prompt(full_text: str) -> str:
    if not full_text:
        return ""
    for anchor in OPEN_PROMPT_ANCHORS:
        if anchor in full_text:
            body = full_text.split(anchor, 1)[-1]
            return strip_expert_thinking(strip_chip_tail(body))
    # fallback：跳过 brief_open 首句
    marker = "为便于向同行快速了解要点和关键细节"
    if marker in full_text:
        return strip_expert_thinking(strip_chip_tail(full_text.split(marker, 1)[-1]))
    return strip_expert_thinking(strip_chip_tail(full_text))


def strip_yuanbao_deep_thinking_fold(text: str) -> str:
    """元宝 DT：去掉「已深度思考」折叠区 CoT，只保留正式回复正文。"""
    if not text:
        return ""
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _YUANBAO_DT_HEADER.match(lines[i].strip()):
        i += 1
    while i < len(lines):
        t = lines[i].strip()
        if not t:
            i += 1
            continue
        if _YUANBAO_REPLY_START.match(t):
            break
        if _YUANBAO_COT_PLAN_LINE.match(t):
            i += 1
            continue
        if t in _YUANBAO_SECTION_NOISE:
            break
        break
    body = "\n".join(lines[i:]).strip()
    if not body:
        return strip_chip_tail(text)
    return strip_chip_tail(body)


def open_brief_is_ready(text: str) -> bool:
    cleaned = strip_expert_thinking(text)
    if len(cleaned) < OPEN_READY_CHARS:
        return False
    if thinking_noise_ratio(cleaned) >= 0.25:
        return False
    return cleaned.rstrip()[-1:] in "。！？）」》"
