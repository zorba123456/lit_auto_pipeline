# CNKI 期刊新增规范

> **每次新增期刊，必须完整执行以下所有步骤，不得跳过任何一项。**
> 此文件是跨平台真理之源，`.cursor/rules/` 中的同名规则引用本文件。

---

## 步骤 1：配置 `aes-feeds/cnki_targets.json`

```json
"CODE": {
    "name": "期刊中文名",
    "rss_url": "https://rss.cnki.net/knavi/rss/CODE?pcode=CJFD,CCJD",
    "web_scrape": true
}
```

- `CODE`：知网期刊代码（大写，如 YLMR）
- `web_scrape: true` **必须**填写
- RSS cron 每 2h 只做探测，`web_scrape: true` 的期刊**不会写 XML**

---

## 步骤 2：注册 `feed_reader.html`

在 CNKI 区块末尾追加一行（filename 用小写 code）：

```js
{ id: "cnki_xxx", name: "期刊名", platform: "cnki", filename: "cnki_xxx.xml" },
```

---

## 步骤 3：深度爬取（⚠️ 必须，不得用 RSS 替代）

```bash
cd lit_auto_pipeline
source venv/bin/activate
python3 aes-feeds/cnki_downloader.py --mode web --journal CODE --reset-journal CODE
```

| 参数 | 说明 |
|------|------|
| `--mode web` | 启动 Playwright 深度抓取，产出**当期目录 + 网络首发** |
| `--journal CODE` | 只抓该期刊，不影响其他期刊 |
| `--reset-journal CODE` | 若之前误跑过 RSS，先清掉非标准 XML 和去重记录再抓 |

- 抓取过程会弹出 Edge 浏览器（非隐形）
- 遇到滑块验证码需人工滑动，等待上限 10 分钟
- 抓取完成后脚本自动 push 到 GitHub aes-feeds 仓库

---

## 步骤 4：XML 格式规范

参考样本：`aes-feeds/cnki_MRYX_cleaned.xml`

### Channel 字段

| 字段 | 正确值 | 禁止值 |
|------|--------|--------|
| `title` | `{期刊名} - CNKI Feeds` | ~~`CNKI - {期刊名}`~~ |
| `link` | `https://github.com/zorba123456/aes-feeds` | ~~navi.cnki.net URL~~ |
| `<image>` | **不要添加** | ~~知网封面 URL~~ |

> 图标由 `raw.githubusercontent.com` 的 GitHub favicon 自动提供，无需手动设置。

### Item 字段

| 字段 | 格式 |
|------|------|
| `title` | `[当期目录] [2026年XX期] 论文标题` 或 `[网络首发] 论文标题` |
| `description` | `<b>期数：</b>…<br><b>出版日期/页码：</b>…<br><b>作者：</b>…` |

- 禁止用 RSS 原始摘要作为 description
- 纯 RSS 产出的条目（无前缀、无结构化 description）视为**不合格**

---

## 步骤 5：Inoreader 订阅

**必须使用 `_cleaned` 后缀的 URL：**

```
https://raw.githubusercontent.com/zorba123456/aes-feeds/main/cnki_{code小写}_cleaned.xml
```

> **原因**：Inoreader 对每个 URL 有全局缓存。若曾订阅过 `cnki_xxx.xml`（即使已删除），
> 重订同一 URL 仍会读旧缓存，名称和图标不会更新。
> `_cleaned` URL 对 Inoreader 是全新地址，保证拉取最新格式。

---

## 步骤 6：验收清单

提交前逐项确认：

- [ ] `cnki_targets.json` 已添加，含 `web_scrape: true`
- [ ] `feed_reader.html` CNKI 区块已注册
- [ ] 已执行 `--mode web`（不是 `--mode rss`）
- [ ] XML 条目 title 均含 `[当期目录]` 或 `[网络首发]` 前缀
- [ ] description 含结构化三行元信息（期数、页码、作者）
- [ ] channel `title` 为 `{期刊名} - CNKI Feeds`
- [ ] channel `link` 为 `https://github.com/zorba123456/aes-feeds`
- [ ] channel 无 `<image>` 节点
- [ ] aes-feeds 已 push 到 GitHub
- [ ] Inoreader 使用 `_cleaned.xml` URL 订阅
