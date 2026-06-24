"""Load AES style guide and render prompt injection block."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "style_guide.json"


def load_style_guide(path: Path | None = None) -> dict:
    p = path or DEFAULT_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def render_for_prompt(data: dict | None = None, *, max_terms: int = 12) -> str:
    """Compact block for LLM system/user prompt injection."""
    d = data if data is not None else load_style_guide()
    lines = [
        "## AES 中文表述规范（必须遵守）",
        "",
        "### 用词：避免滥用，灵活换说",
    ]
    for item in d.get("word_variants", []):
        limit = "、".join(item.get("limit") or [])
        prefer = "、".join(item.get("prefer") or [])
        if limit:
            lines.append(f"- 少用「{limit}」→ 可改用：{prefer}")
        elif prefer:
            lines.append(f"- {prefer}（{item.get('note', '')}）")

    lines.extend(["", "### 术语（固定译法）"])
    for item in d.get("terminology", [])[:max_terms]:
        avoid = "、".join(item.get("avoid") or [])
        prefer = item.get("prefer", "")
        if avoid:
            lines.append(f"- 不用「{avoid}」→ 用「{prefer}」")
        else:
            lines.append(f"- 「{prefer}」")

    lines.extend(["", "### 句法"])
    for block in d.get("syntax_rules", []):
        lines.append(f"**{block.get('title', '')}**：")
        for r in block.get("rules", []):
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    print(render_for_prompt())
