from bs4 import BeautifulSoup
import json

with open("doubao_chat_dump.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

buttons = soup.find_all("button")
res = []
for i, b in enumerate(buttons):
    svg = b.find("svg")
    if svg:
        paths = svg.find_all("path")
        path_data = [p.get("d") for p in paths]
        res.append({
            "index": i,
            "class": b.get("class"),
            "disabled": b.has_attr("disabled"),
            "path": path_data,
            "aria-label": b.get("aria-label"),
            "title": b.get("title")
        })

with open("svgs.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
