import argparse
import asyncio
import os

from playwright.async_api import async_playwright

from doubao_rpa_extract import (
    capture_assistant_reply,
    get_doubao_visible_model,
    log_doubao_model_state,
    select_doubao_model,
    send_prompt,
    start_new_chat,
    wait_for_reply_stable,
    wait_pdf_ready,
)
from rpa_tier import make_tier_meta

# 豆包公开分享链只用 chip 起句；自定义 brief 含编辑策略，不宜出现在 thread 里
CHIP_PROMPT = "详细总结这篇文章内容"


async def ensure_model_before_upload(page, model_label: str) -> None:
    """先选档、确认页面显示后再上传 PDF（专家档必须上传前锁定）。"""
    for attempt in range(3):
        await select_doubao_model(page, model_label)
        visible = await get_doubao_visible_model(page)
        await log_doubao_model_state(page, expected=model_label, phase="上传前")
        if visible == model_label:
            print(f"✅ 上传前档位已确认: {model_label}")
            return
        print(f"⚠️ 档位仍为 {visible!r}，重选 {model_label}（{attempt + 1}/3）")
        await page.wait_for_timeout(600)
    print(f"⚠️ 上传前未能确认 {model_label!r}，仍继续上传（请人工核对）")


async def upload_pdf(page, pdf_path: str, *, model_label: str | None = None) -> None:
    print("🔗 正在打开豆包对话页...")
    await page.goto("https://www.doubao.com/chat/", wait_until="domcontentloaded")
    await page.wait_for_selector("textarea", timeout=15000)
    await page.wait_for_timeout(2000)
    await start_new_chat(page)
    if model_label:
        print(f"🎛️ 上传前选档: {model_label}")
        await ensure_model_before_upload(page, model_label)
    print(f"📄 正在上传 PDF 文件: {os.path.basename(pdf_path)}")
    await page.set_input_files("input[type='file']", pdf_path)
    await wait_pdf_ready(page)


async def upload_and_chip_share(page, pdf_path: str) -> None:
    """产公开豆包链：chip prompt + 等回复 + 分享（不提取导读）。"""
    await upload_pdf(page, pdf_path)
    print(f"🏷️ 使用 chip 起句: {CHIP_PROMPT!r}")
    sent = await send_prompt(page, CHIP_PROMPT)
    if not sent:
        print("⚠️ 发送未确认，仍等待回复…")
    await wait_for_reply_stable(page)


async def upload_and_chat(
    page,
    pdf_path: str,
    prompt: str,
    *,
    model_label: str | None = None,
    structured: bool = True,
    prompt_kind: str = "brief",
) -> tuple[str, dict]:
    """开发试跑：自定义 prompt + 抠导读（勿用于公开分享）。"""
    await upload_pdf(page, pdf_path, model_label=model_label)
    if model_label:
        await log_doubao_model_state(page, expected=model_label, phase="上传后")
    sent = await send_prompt(page, prompt)
    if not sent:
        print("⚠️ 发送未确认，仍尝试等待回复…")
    if model_label:
        await log_doubao_model_state(page, expected=model_label, phase="发送后")
    summary = await capture_assistant_reply(
        page, prompt, pdf_path, structured=structured, prompt_kind=prompt_kind
    )
    observed = await log_doubao_model_state(
        page, expected=model_label, phase="完成后"
    )
    tier_meta = make_tier_meta(
        channel="doubao_brief",
        tier_requested=model_label or "页面默认",
        tier_observed=observed,
        extra={"tier_note": "生成中 UI 可能回显快速，以完成后读数为准"},
    )
    return summary, tier_meta


async def get_share_link(page):
    intercepted_share_id = None

    async def on_response(response):
        nonlocal intercepted_share_id
        if "/im/message/share/share_token" in response.url and response.status == 200:
            try:
                data = await response.json()
                if "data" in data and "share_token" in data["data"]:
                    token = data["data"]["share_token"]
                    print(f"🔥 截获核心 Token: {token[:20]}...")
                    import base64
                    import json

                    payload = token.split(".")[1]
                    payload += "=" * ((4 - len(payload) % 4) % 4)
                    decoded = base64.b64decode(payload).decode("utf-8")
                    payload_data = json.loads(decoded)
                    if "share_id" in payload_data:
                        intercepted_share_id = payload_data["share_id"]
            except Exception:
                pass

    page.on("response", on_response)

    print("📤 锁定并点击右上角『分享』按钮...")
    share_btn = page.locator('button:has(svg path[d^="M11.052 3.80762"])').first
    try:
        await share_btn.click(timeout=5000)
    except Exception:
        print("⚠️ 未找到全局分享按钮！")
        return None

    print("⏳ 等待分享面板弹出...")
    await page.wait_for_timeout(1500)

    print("👆 点击『确认分享』按钮...")
    await page.evaluate(
        """() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const primaryBtns = buttons.filter(b => b.className.includes('semi-button-primary'));
        const textBtns = buttons.filter(b => b.innerText && (b.innerText.includes('复制链接') || b.innerText.includes('创建') || b.innerText.includes('分享')));
        if (primaryBtns.length > 0) {
            primaryBtns[primaryBtns.length - 1].click();
        } else if (textBtns.length > 0) {
            textBtns[textBtns.length - 1].click();
        }
    }"""
    )

    await page.wait_for_timeout(3000)

    if intercepted_share_id:
        return f"https://www.doubao.com/thread/{intercepted_share_id}"
    return None


async def process_pdf_with_doubao(
    pdf_path: str,
    prompt: str | None = None,
    mode: str = "share",
    *,
    job: str = "share-link",
    profile: str = "./doubao_profile",
    model_label: str | None = None,
    structured_brief: bool = True,
    prompt_kind: str = "brief",
):
    """
    job=share-link  产 doubao_read_url（chip，公开安全）
    job=dev-brief   本地试 prompt + 抠导读（默认不分享，见 --no-share）
    """
    async with async_playwright() as p:
        user_data_dir = profile
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await browser.new_page()
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 800);")

        summary = ""
        tier_meta: dict = {}
        if job == "share-link":
            await upload_and_chip_share(page, pdf_path)
        else:
            if not prompt:
                raise ValueError("dev-brief 需要 prompt")
            summary, tier_meta = await upload_and_chat(
                page,
                pdf_path,
                prompt,
                model_label=model_label,
                structured=structured_brief,
                prompt_kind=prompt_kind,
            )

        share_link = None
        if mode == "share":
            if job != "share-link" and prompt and prompt != CHIP_PROMPT:
                print(
                    "⚠️ 警告：公开分享将暴露自定义 prompt；产链请用 --job share-link（chip）"
                )
            share_link = await get_share_link(page)

        await browser.close()
        return summary, share_link, tier_meta


def load_structured_prompt(prompt_type: str) -> str:
    base = os.path.join(os.path.dirname(__file__), "prompts")
    if prompt_type == "open":
        path = os.path.join(base, "brief_open.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, encoding="utf-8") as f:
            return f.read().strip() + "\n"
    if prompt_type == "innovation":
        path = os.path.join(base, "brief_innovation_audit.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, encoding="utf-8") as f:
            return f.read().strip() + "\n"
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

            prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
            if prompts_dir not in sys.path:
                sys.path.insert(0, prompts_dir)
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


def main():
    parser = argparse.ArgumentParser(description="Doubao PDF RPA Pipeline")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--prompt", default=None, help="Raw prompt text (overrides --prompt-type)")
    parser.add_argument(
        "--job",
        choices=["share-link", "dev-brief"],
        default="share-link",
        help="share-link=公开豆包链(chip); dev-brief=本地试自定义导读(勿分享)",
    )
    parser.add_argument(
        "--prompt-type",
        choices=["baseline", "brief", "rct", "observational"],
        default="baseline",
        help="仅 dev-brief 有效；share-link 固定 chip",
    )
    parser.add_argument("--mode", choices=["silent", "share"], default="share")
    parser.add_argument(
        "--no-share",
        action="store_true",
        help="dev-brief：只抠导读不分享",
    )
    parser.add_argument(
        "--profile",
        default="./doubao_profile",
        help="Chrome persistent profile 目录（默认 doubao_profile；导读比选用 doubao_profile_brief）",
    )
    args = parser.parse_args()

    if args.job == "share-link":
        if args.prompt or args.prompt_type != "baseline":
            print("ℹ️ share-link 忽略 --prompt / --prompt-type，固定 chip 起句")
        prompt = CHIP_PROMPT
    elif args.prompt:
        prompt = args.prompt
    elif args.prompt_type == "baseline":
        prompt = CHIP_PROMPT
    else:
        prompt = load_structured_prompt(args.prompt_type)

    abs_pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(abs_pdf_path):
        print(f"❌ 文件不存在: {abs_pdf_path}")
        return

    print("===== 🚀 启动豆包 RPA =====")
    print(f"📄 Target: {abs_pdf_path}")
    print(f"🔧 Job: {args.job}")
    if args.job == "dev-brief":
        print(f"📝 Prompt: {args.prompt_type if not args.prompt else 'custom'} ({len(prompt)} chars)")

    mode = "silent" if args.no_share else args.mode
    summary, share_link, _tier = asyncio.run(
        process_pdf_with_doubao(
            abs_pdf_path, prompt, mode, job=args.job, profile=args.profile
        )
    )

    out_file = abs_pdf_path + "_doubao_result.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        if share_link:
            f.write(f"Share Link: {share_link}\n\n")
        if summary:
            f.write("Summary:\n")
            f.write(summary)

    if summary:
        print("\n" + "=" * 40 + " SUMMARY " + "=" * 40)
        print(summary[:500] + "..." if len(summary) > 500 else summary)
        print("=" * 89 + "\n")
    if share_link:
        print(f"🔗 专属分享链接: {share_link}")

    print(f"✅ 结果已保存至: {out_file}")


if __name__ == "__main__":
    main()
