import json
from playwright.sync_api import sync_playwright

with open("svgs.json", "r") as f:
    svgs = json.load(f)

html = "<html><body><div style='display:flex; flex-wrap:wrap; gap: 20px;'>"
for i, item in enumerate(svgs):
    if not item["path"]: continue
    path_d = item["path"][0]
    html += f"""
    <div style='border:1px solid #ccc; padding:10px; text-align:center;'>
        <div>Index: {item['index']}</div>
        <svg width="40" height="40" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
            <path fill-rule="evenodd" clip-rule="evenodd" d="{path_d}"></path>
        </svg>
    </div>
    """
html += "</div></body></html>"

with open("render_svg.html", "w") as f:
    f.write(html)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{__file__.replace('render_svg.py', 'render_svg.html')}")
    page.screenshot(path="svg_rendered.png", full_page=True)
    browser.close()
