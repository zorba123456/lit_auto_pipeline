"""API 比选环境：加载 .env.api_compare、连通性验证。"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
# 可见路径优先（左侧文件树 config/）；兼容旧 .env.api_compare
ENV_CANDIDATES = (
    ROOT / "config" / "api_compare.env",
    ROOT / ".env.api_compare",
)
ENV_FILE = ENV_CANDIDATES[0]

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
ARK_API = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

VERIFY_SLUGS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "doubao-lite-32k",
)


def load_api_compare_env(path: Path | None = None) -> Path | None:
    """从 config/api_compare.env 或 .env.api_compare 加载（不覆盖已 export 的值）。"""
    if path is not None:
        candidates = (path,)
    else:
        candidates = ENV_CANDIDATES
    env_path = next((p for p in candidates if p.is_file()), None)
    if env_path is None:
        return None
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
    return env_path


def mask_secret(value: str) -> str:
    if not value:
        return "(unset)"
    if len(value) <= 8:
        return "***"
    return f"…{value[-4:]}"


def ark_endpoint() -> str:
    return os.environ.get("ARK_ENDPOINT", "") or os.environ.get("ARK_ENDPOINT_LITE_32K", "")


@dataclass
class VerifyResult:
    slug: str
    ok: bool
    detail: str
    elapsed_sec: float | None = None


def _verify_gemini(model_id: str) -> VerifyResult:
    slug = model_id
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return VerifyResult(slug, False, "GEMINI_API_KEY 未设置")
    t0 = time.time()
    try:
        url = GEMINI_API.format(model=model_id)
        r = requests.post(
            url,
            params={"key": key},
            json={"contents": [{"parts": [{"text": "ping"}]}]},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return VerifyResult(
            slug,
            True,
            f"reply {len(text)} chars · key {mask_secret(key)}",
            round(time.time() - t0, 2),
        )
    except Exception as e:
        return VerifyResult(slug, False, str(e)[:200], round(time.time() - t0, 2))


def _verify_deepseek(model_id: str, *, thinking: bool) -> VerifyResult:
    slug = model_id
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return VerifyResult(slug, False, "DEEPSEEK_API_KEY 未设置")
    body: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 32,
    }
    if thinking:
        body["extra_body"] = {"thinking": {"type": "enabled"}}
    t0 = time.time()
    try:
        r = requests.post(
            DEEPSEEK_API,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=90,
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        return VerifyResult(
            slug,
            True,
            f"reply {len(text)} chars · thinking={'on' if thinking else 'off'} · key {mask_secret(key)}",
            round(time.time() - t0, 2),
        )
    except Exception as e:
        return VerifyResult(slug, False, str(e)[:200], round(time.time() - t0, 2))


def _verify_ark(slug: str) -> VerifyResult:
    key = os.environ.get("ARK_API_KEY", "")
    ep = ark_endpoint()
    if not key:
        return VerifyResult(slug, False, "ARK_API_KEY 未设置")
    if not ep:
        return VerifyResult(slug, False, "ARK_ENDPOINT 未设置")
    t0 = time.time()
    try:
        r = requests.post(
            ARK_API,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": ep,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 16,
            },
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        return VerifyResult(
            slug,
            True,
            f"ep {ep[:12]}… reply {len(text)} chars · key {mask_secret(key)}",
            round(time.time() - t0, 2),
        )
    except Exception as e:
        return VerifyResult(slug, False, str(e)[:200], round(time.time() - t0, 2))


def verify_api_compare(*, include_pro: bool = True) -> list[VerifyResult]:
    """Ping 各 provider；不打印完整 key。"""
    slugs = list(VERIFY_SLUGS)
    if not include_pro:
        slugs = [s for s in slugs if s != "deepseek-v4-pro"]

    results: list[VerifyResult] = []
    for slug in slugs:
        if slug.startswith("gemini-"):
            results.append(_verify_gemini(slug))
        elif slug == "deepseek-v4-flash":
            results.append(_verify_deepseek("deepseek-v4-flash", thinking=True))
        elif slug == "deepseek-v4-pro":
            results.append(_verify_deepseek("deepseek-v4-pro", thinking=True))
        elif slug.startswith("doubao-"):
            results.append(_verify_ark(slug))
        else:
            results.append(VerifyResult(slug, False, "未知 slug"))
    return results


def print_verify_report(results: list[VerifyResult], *, env_path: Path | None) -> int:
    if env_path:
        print(f"env: {env_path}")
    else:
        print(f"env: (未找到 {ENV_FILE.name}，仅用当前 shell 环境变量)")
    print()
    fails = 0
    for r in results:
        mark = "✅" if r.ok else "❌"
        sec = f" ({r.elapsed_sec}s)" if r.elapsed_sec is not None else ""
        print(f"{mark} {r.slug:22}{sec}  {r.detail}")
        if not r.ok:
            fails += 1
    print()
    if fails:
        print(f"失败 {fails}/{len(results)} — 检查 .env.api_compare 或 export 后重试")
    else:
        print(f"全部通过 ({len(results)}/{len(results)})")
    return fails
