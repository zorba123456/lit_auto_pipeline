#!/usr/bin/env python3
"""Round 2 开放导读 · API 比选（同 brief_open.txt + PDF 抽文本）。

环境变量（推荐写入 .env.api_compare，见 .env.api_compare.example）
--------
GEMINI_API_KEY          Google AI Studio / Gemini API
DEEPSEEK_API_KEY        platform.deepseek.com
ARK_API_KEY             火山方舟 API Key（豆包）
ARK_ENDPOINT            推理接入点 ID，形如 ep-xxxx

用法
----
  cp .env.api_compare.example .env.api_compare   # 填入 key
  python3 open_compare_api.py --verify
  python3 open_compare_api.py --list-models
  python3 open_compare_api.py --models gemini-2.5-flash,gemini-3.5-flash
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from api_compare_env import ark_endpoint, load_api_compare_env, print_verify_report, verify_api_compare
from doubao_rpa import load_structured_prompt

LOG_DIR = Path("logs/open_compare_api")
DEFAULT_PDFS = [
    "less_is_better__full_incision_double_eyelid.18.pdf",
    (
        "J of Cosmetic Dermatology - 2023 - Peng - Aspiration before tissue "
        "filling with hyaluronic acid‐safety enhancement by using.pdf"
    ),
]
MAX_PDF_CHARS = 120_000

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
ARK_API = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


@dataclass(frozen=True)
class ApiModel:
    slug: str
    provider: str
    model_id: str
    thinking: bool = False
    note: str = ""


# slug 用于比选表；model_id 为 API 真实 model 参数
API_MODELS: dict[str, ApiModel] = {
    "gemini-2.5-flash": ApiModel(
        "gemini-2.5-flash",
        "gemini",
        "gemini-2.5-flash",
        note="便宜快；RPA 药丸标 3.5 时 API 仍须单独测 2.5",
    ),
    "gemini-3.5-flash": ApiModel(
        "gemini-3.5-flash",
        "gemini",
        "gemini-3.5-flash",
        note="2026-05 GA；对齐 Web 默认 3.5 Flash",
    ),
    "gemini-3.1-flash-lite": ApiModel(
        "gemini-3.1-flash-lite",
        "gemini",
        "gemini-3.1-flash-lite",
        note="对齐 Web 3.1 Flash-Lite；轻量低价",
    ),
    "deepseek-v4-flash": ApiModel(
        "deepseek-v4-flash",
        "deepseek",
        "deepseek-v4-flash",
        thinking=True,
        note="thinking 默认开；reasoning 计 output tokens",
    ),
    "deepseek-v4-pro": ApiModel(
        "deepseek-v4-pro",
        "deepseek",
        "deepseek-v4-pro",
        thinking=True,
        note="对标元宝 DT / 豆包专家档深度",
    ),
    "doubao-lite-32k": ApiModel(
        "doubao-lite-32k",
        "ark",
        "",
        note="方舟接入点 aas-lite-32k；Web「快速」≠ API",
    ),
    "doubao-seed-evolving": ApiModel(
        "doubao-seed-evolving",
        "ark",
        "",
        note="方舟推荐新模型；与 lite-32k 共用 ARK_ENDPOINT",
    ),
}


def _extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("请先安装: pip install pypdf") from e
    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError(f"PDF 抽文本为空: {pdf_path}")
    if len(text) > MAX_PDF_CHARS:
        text = text[:MAX_PDF_CHARS] + "\n\n[…文本已截断…]"
    return text


def _user_message(prompt: str, pdf_text: str) -> str:
    return (
        f"{prompt.strip()}\n\n"
        "——— 以下为论文全文（请仅依据此文写导读）———\n\n"
        f"{pdf_text}"
    )


def _call_gemini(model_id: str, user_text: str) -> tuple[str, dict]:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("未设置 GEMINI_API_KEY")
    url = GEMINI_API.format(model=model_id)
    payload = {
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {"temperature": 0.3},
    }
    r = requests.post(url, params={"key": key}, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    return text.strip(), {
        "prompt_tokens": usage.get("promptTokenCount"),
        "completion_tokens": usage.get("candidatesTokenCount"),
        "thoughts_tokens": usage.get("thoughtsTokenCount"),
    }


def _call_deepseek(spec: ApiModel, user_text: str) -> tuple[str, dict]:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")
    body: dict = {
        "model": spec.model_id,
        "messages": [{"role": "user", "content": user_text}],
        "temperature": 0.3,
    }
    if spec.thinking:
        body["extra_body"] = {"thinking": {"type": "enabled"}}
    r = requests.post(
        DEEPSEEK_API,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    msg = data["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    usage = data.get("usage", {})
    meta = {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": usage.get("completion_tokens_details", {}).get(
            "reasoning_tokens"
        ),
    }
    return text, meta


def _call_ark(user_text: str) -> tuple[str, dict]:
    key = os.environ.get("ARK_API_KEY", "")
    ep = ark_endpoint()
    if not key:
        raise RuntimeError("未设置 ARK_API_KEY")
    if not ep:
        raise RuntimeError("未设置 ARK_ENDPOINT（ep- 开头的接入点 ID）")
    body = {
        "model": ep,
        "messages": [{"role": "user", "content": user_text}],
        "temperature": 0.3,
    }
    r = requests.post(
        ARK_API,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    return text, {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }


def _call_model(spec: ApiModel, user_text: str) -> tuple[str, dict]:
    if spec.provider == "gemini":
        return _call_gemini(spec.model_id, user_text)
    if spec.provider == "deepseek":
        return _call_deepseek(spec, user_text)
    if spec.provider == "ark":
        return _call_ark(user_text)
    raise ValueError(spec.provider)


def _out_path(pdf: Path, slug: str) -> Path:
    safe = slug.replace(".", "_")
    return pdf.parent / f"{pdf.stem}_api_{safe}_open_reading_note.txt"


def _print_setup() -> None:
    print(
        """
API 比选配置
============
1. 复制模板：
      cp .env.api_compare.example .env.api_compare

2. Gemini（须分别测 2.5 与 3.5 Flash）
   https://aistudio.google.com/apikey → GEMINI_API_KEY
   Pro 账号常有免费请求额度（控制台 → Quotas）

3. DeepSeek
   https://platform.deepseek.com → API Keys → DEEPSEEK_API_KEY
   模型：deepseek-v4-flash（thinking 开）、deepseek-v4-pro

4. 豆包 / 火山方舟
   https://console.volcengine.com/ark → ARK_API_KEY
   推理接入点 → 复制 ep- ID → ARK_ENDPOINT
   示例：aas-lite-32k → ep-20250525113859-xmhhh

5. 验证：
      python3 open_compare_api.py --verify

6. 五档批跑（2 篇 PDF）：
      python3 open_compare_api.py --skip-existing
"""
    )


def main() -> None:
    env_path = load_api_compare_env()

    parser = argparse.ArgumentParser(description="开放导读 API 比选")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--setup", action="store_true", help="打印各平台 Key 配置步骤")
    parser.add_argument("--doubao-setup", action="store_true", help="同 --setup")
    parser.add_argument("--verify", action="store_true", help="Ping 各 API（不暴露完整 key）")
    parser.add_argument(
        "--verify-no-pro",
        action="store_true",
        help="--verify 时跳过 deepseek-v4-pro",
    )
    parser.add_argument(
        "--models",
        default="gemini-2.5-flash,gemini-3.5-flash,deepseek-v4-flash,deepseek-v4-pro,doubao-lite-32k",
    )
    parser.add_argument("--pdf-dir", default="~/Desktop/PDFs")
    parser.add_argument("--pdf", action="append")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.setup or args.doubao_setup:
        _print_setup()
        return

    if args.verify:
        results = verify_api_compare(include_pro=not args.verify_no_pro)
        fails = print_verify_report(results, env_path=env_path)
        raise SystemExit(1 if fails else 0)

    if args.list_models:
        for slug, spec in API_MODELS.items():
            ep = "ARK_ENDPOINT" if spec.provider == "ark" else spec.model_id
            print(f"{slug:22} {spec.provider:10} {ep:28} {spec.note}")
        return

    pdf_dir = Path(args.pdf_dir).expanduser()
    pdfs = [Path(p).expanduser() for p in args.pdf] if args.pdf else [pdf_dir / n for n in DEFAULT_PDFS]
    slugs = [s.strip() for s in args.models.split(",") if s.strip()]
    for s in slugs:
        if s not in API_MODELS:
            raise SystemExit(f"未知 model slug: {s}（--list-models 查看）")

    prompt = load_structured_prompt("open")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== API 比选 {run_id} =====")
    print(f"模型: {slugs}")
    print(f"日志: {log_path}\n")

    for pdf in pdfs:
        if not pdf.exists():
            raise SystemExit(f"不存在: {pdf}")
        print(f"######## {pdf.name} ########")
        pdf_text = _extract_pdf_text(pdf)
        user_text = _user_message(prompt, pdf_text)
        print(f"PDF 文本 {len(pdf_text)} 字\n")

        for slug in slugs:
            spec = API_MODELS[slug]
            out = _out_path(pdf, slug)
            row = {
                "run_id": run_id,
                "slug": slug,
                "model_id": spec.model_id or ark_endpoint(),
                "pdf": str(pdf),
                "path": str(out),
                "ok": False,
                "chars": 0,
                "usage": {},
                "error": None,
            }
            if args.skip_existing and out.exists() and out.stat().st_size > 400:
                row["ok"] = True
                row["chars"] = len(out.read_text(encoding="utf-8"))
                row["skipped"] = True
                print(f"⏭️ {slug} 已有 ({row['chars']} 字)")
            else:
                t0 = time.time()
                try:
                    print(f"→ {slug} …")
                    text, usage = _call_model(spec, user_text)
                    out.write_text(text, encoding="utf-8")
                    row["chars"] = len(text)
                    row["usage"] = usage
                    row["ok"] = len(text) >= 400
                    row["elapsed_sec"] = round(time.time() - t0, 1)
                    print(f"✅ {slug} → {out.name} ({len(text)} 字) {usage}")
                except Exception as e:
                    row["error"] = str(e)
                    row["elapsed_sec"] = round(time.time() - t0, 1)
                    print(f"❌ {slug}: {e}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成 → {log_path}")


if __name__ == "__main__":
    main()
