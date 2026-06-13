# CNKI 期刊新增规范

> ⚠️ **每次新增期刊，必须完整执行以下所有步骤，不得跳过任何一项。**
> 此文件是跨平台真理之源，`.cursor/rules/` 中的同名规则自动引用本文件。

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
- `web_scrape: true` **必须**填写；RSS cron 对该标志的期刊**不写 XML**，仅做探测

---

## 步骤 2：注册 `feed_reader.html`

在 CNKI 区块末尾追加一行（filename 用小写 code）：

```js
{ id: "cnki_xxx", name: "期刊名", platform: "cnki", filename: "cnki_xxx.xml" },
```

---

## 步骤 3：清理去重记录（防止历史污染）

> ⚠️ **新期刊首次接入前必须执行此步**，确保去重日志里没有同代码的旧垃圾数据（尤其是误跑 RSS 留下的非标准条目）。

```bash
cd lit_auto_pipeline && source venv/bin/activate
python3 aes-feeds/cnki_downloader.py --mode web --journal CODE --reset-journal CODE
```

`--reset-journal CODE` 会做三件事：
1. **删除** `cnki_{code}.xml` 和 `cnki_{CODE}_cleaned.xml`
2. **从 `cnki_dedup_log.json` 移除** 该期刊所有 hash 记录
3. 清理完成后立即进入深度抓取

---

## 步骤 4：深度爬取（⚠️ 必须，不得用 RSS 替代）

> ⚠️ **RSS 模式（`--mode rss`）产出的 XML 格式不合规**，条目无 `[当期目录]` 前缀、description 为原始摘要，禁止用于初始化新期刊。

步骤 3 的命令同时完成深度爬取。若需单独运行：

```bash
python3 aes-feeds/cnki_downloader.py --mode web --journal CODE
```

执行过程：
- 弹出 Edge 浏览器（非后台隐形）导航至期刊页
- 抓取**当期目录**（`[当期目录] [期数] 标题`）
- 抓取**网络首发**（`[网络首发] 标题`），若该刊暂无则自动跳过
- 抓取完成后自动 push 到 GitHub `aes-feeds` 仓库
- 遇到滑块验证码：等待人工滑动，上限 10 分钟

---

## 步骤 5：XML 格式规范

参考样本：`aes-feeds/cnki_MRYX_cleaned.xml`

### Channel 字段

| 字段 | 正确值 | 禁止值 |
|------|--------|--------|
| `title` | `{期刊名} - CNKI Feeds` | ~~`CNKI - {期刊名}`~~ |
| `link` | `https://github.com/zorba123456/aes-feeds` | ~~`navi.cnki.net` URL~~ |
| `<image>` | **不添加** | ~~知网封面 URL~~ |

图标由 `raw.githubusercontent.com` 的 GitHub favicon 自动提供。

### Item 字段

| 字段 | 格式 |
|------|------|
| `title` | `[当期目录] [2026年XX期] 论文标题` 或 `[网络首发] 论文标题` |
| `description` | `<b>期数：</b>…<br><b>出版日期/页码：</b>…<br><b>作者：</b>…` |

纯 RSS 产出的条目（无前缀、description 为摘要段落）视为**不合规**。

---

## 步骤 6：Inoreader 订阅

> ⚠️ **必须使用 `_cleaned` 后缀 URL**，不得使用 `cnki_xxx.xml`。

```
https://raw.githubusercontent.com/zorba123456/aes-feeds/main/cnki_{code小写}_cleaned.xml
```

原因：Inoreader 按 URL 全局缓存 feed 元数据。订阅过 `cnki_xxx.xml`（即使已删除）再重订，仍读旧缓存，名称和图标不更新。`_cleaned` URL 对 Inoreader 是全新地址，保证拉取最新格式。

---

## 步骤 7：验收清单

提交前逐项确认，全部通过才算完成：

- [ ] `cnki_targets.json` 已添加，含 `web_scrape: true`
- [ ] `feed_reader.html` CNKI 区块已注册
- [ ] 已执行 `--reset-journal CODE` 清理去重记录
- [ ] 已执行 `--mode web`（**不是** `--mode rss`）
- [ ] XML 条目 title 均含 `[当期目录]` 或 `[网络首发]` 前缀
- [ ] description 含结构化三行元信息（期数、页码、作者）
- [ ] channel `title` 为 `{期刊名} - CNKI Feeds`
- [ ] channel `link` 为 `https://github.com/zorba123456/aes-feeds`
- [ ] channel 无 `<image>` 节点
- [ ] aes-feeds 已 push 到 GitHub
- [ ] Inoreader 使用 `_cleaned.xml` URL 订阅
