#!/usr/bin/env python3
"""Dump Gemini conversation-panel ⋮ candidates from live DOM."""
from __future__ import annotations

import asyncio
import json
import os

from playwright.async_api import async_playwright

GEMINI_PROFILE = "./gemini_playwright_profile"
GEMINI_URL = "https://gemini.google.com/app"


DUMP_JS = """() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const out = { vw, vh, topRight: [], allOverflow: [], shareParents: [] };

  function describe(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return null;
    const aria = (el.getAttribute('aria-label') || '').trim();
    const text = (el.innerText || '').trim().slice(0, 40);
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role') || '';
    const cls = (el.className && typeof el.className === 'string') ? el.className.slice(0, 120) : '';
    const matIcon = el.querySelector('mat-icon, .material-icons, .google-symbols');
    const iconText = matIcon ? (matIcon.textContent || '').trim() : '';
    const parent = el.parentElement;
    const parentTag = parent ? parent.tagName.toLowerCase() : '';
    const parentCls = parent && typeof parent.className === 'string' ? parent.className.slice(0, 80) : '';
    return {
      tag, role, aria, text, iconText, cls,
      parentTag, parentCls,
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      right: Math.round(r.x + r.width),
    };
  }

  const selectors = 'button, [role="button"], mat-icon-button, .mat-mdc-icon-button';
  for (const el of document.querySelectorAll(selectors)) {
    const d = describe(el);
    if (!d) continue;
    const ariaL = d.aria.toLowerCase();
    const iconL = d.iconText.toLowerCase();
    if (
      ariaL.includes('conversation actions') ||
      ariaL.includes('more options') ||
      iconL.includes('more_vert') ||
      iconL === 'more_vert'
    ) {
      out.allOverflow.push(d);
    }
    if (d.x >= 72 && d.right > vw - 150 && d.y >= 8 && d.y <= 240) {
      out.topRight.push(d);
    }
  }

  out.topRight.sort((a, b) => b.right - a.right || a.y - b.y);

  for (const el of document.querySelectorAll('*')) {
    const t = (el.innerText || '').trim();
    if (t === 'Share conversation' || t === '分享对话') {
      const p = el.closest('button, [role="menuitem"], mat-menu-item') || el;
      const d = describe(p);
      if (d) out.shareParents.push({ menuText: t, ...d });
    }
  }
  return out;
}"""


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            GEMINI_PROFILE,
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        if "gemini.google.com" not in page.url:
            await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

        print(f"URL: {page.url}\n")

        data = await page.evaluate(DUMP_JS)
        print("=== topRight (x>=72, right>vw-150, y 8-240) ===")
        for i, b in enumerate(data["topRight"][:15]):
            print(f"\n[{i}] {json.dumps(b, ensure_ascii=False, indent=2)}")

        print("\n=== allOverflow (conversation/more_vert) ===")
        for i, b in enumerate(data["allOverflow"][:10]):
            print(f"\n[{i}] {json.dumps(b, ensure_ascii=False, indent=2)}")

        print("\n=== shareParents ===")
        for b in data["shareParents"][:5]:
            print(json.dumps(b, ensure_ascii=False))

        # Test selectors
        tests = [
            ('aria-label*="conversation actions" i', 'button[aria-label*="conversation actions" i]'),
            ('get_by_role conversation actions', None),
            ('mat-icon more_vert in panel', 'mat-icon:has-text("more_vert")'),
        ]
        print("\n=== selector counts ===")
        for name, sel in tests:
            if sel:
                n = await page.locator(sel).count()
                print(f"  {name}: {n}")
            else:
                n = await page.get_by_role(
                    "button", name="Open menu for conversation actions"
                ).count()
                print(f"  {name}: {n}")

        # Try click
        loc = page.locator('button[aria-label*="conversation actions" i]').first
        if await loc.count() > 0:
            print("\n=== click test ===")
            try:
                await loc.click(timeout=5000)
                await page.wait_for_timeout(800)
                menu = await page.evaluate("""() => {
                  const items = [...document.querySelectorAll(
                    '.cdk-overlay-container *, [role="menuitem"], mat-menu-item'
                  )].map(e => (e.innerText||'').trim()).filter(t => t.length < 60);
                  return [...new Set(items)].slice(0, 12);
                }""")
                print(f"  menu items after click: {menu}")
            except Exception as e:
                print(f"  click failed: {e}")

        out_path = "logs/gemini_stress/overflow_dom_dump.json"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {out_path}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
