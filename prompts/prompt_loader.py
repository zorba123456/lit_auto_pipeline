"""Load structured reading-note prompts for RPA (Gemini / Doubao)."""

from __future__ import annotations

import os


def load_structured_prompt(prompt_type: str) -> str:
    base = os.path.join(os.path.dirname(__file__))
    if prompt_type == "brief":
        rpa_compact = os.path.join(base, "brief_rpa.txt")
        if os.path.exists(rpa_compact):
            with open(rpa_compact, encoding="utf-8") as f:
                text = f.read().strip()
        else:
            shell = os.path.join(base, "_shell_brief.md")
            body = os.path.join(base, "reading_note_brief.md")
            with open(shell, encoding="utf-8") as f:
                text = f.read().strip()
            with open(body, encoding="utf-8") as f:
                text += "\n\n" + f.read().strip()
        try:
            import sys

            if base not in sys.path:
                sys.path.insert(0, base)
            from style_guide_loader import render_for_prompt

            text += "\n\n" + render_for_prompt()
        except Exception as e:
            print(f"⚠️ 未注入表述规范: {e}")
        return text + "\n"
    shell = os.path.join(base, "_shell.md")
    body = os.path.join(base, f"reading_note_{prompt_type}.md")
    for path in (shell, body):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(shell, encoding="utf-8") as f:
        parts = [f.read().strip()]
    with open(body, encoding="utf-8") as f:
        parts.append(f.read().strip())
    return "\n\n".join(parts) + "\n"
