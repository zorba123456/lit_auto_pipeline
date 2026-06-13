# AGENTS.md — AES-INTEL 项目 AI 操作规范

本文件供所有 AI 编码助手（Cursor、Claude、Codex 等）自动读取。
执行任何任务前，先检查是否命中下方规范。

---

## 新增 CNKI 期刊

> ⚠️ **命中条件**：用户说「新增期刊」「加一本知网」「CNKI 新期刊」等。
> 命中后**必须完整执行以下 7 步，不得跳过任何一项**。

### 第 1 步：写入 `aes-feeds/cnki_targets.json`

```json
"CODE": {
    "name": "期刊中文名",
    "rss_url": "https://rss.cnki.net/knavi/rss/CODE?pcode=CJFD,CCJD",
    "web_scrape": true
}
```

`web_scrape: true` 是必填项。有此标志的期刊在 RSS cron 里**不写 XML**（仅探测），XML 只由深度爬取写入。

### 第 2 步：注册到 `feed_reader.html`

```js
{ id: "cnki_xxx", name: "期刊名", platform: "cnki", filename: "cnki_xxx.xml" },
```

加在 CNKI 区块末尾，filename 用小写 code。

### 第 3 步：清理去重记录（防旧数据污染）

```bash
cd lit_auto_pipeline && source venv/bin/activate
python3 aes-feeds/cnki_downloader.py --mode web --journal CODE --reset-journal CODE
```

`--reset-journal CODE` 做三件事：
1. 删除 `cnki_{code}.xml` 和 `cnki_{CODE}_cleaned.xml`
2. 从 `cnki_dedup_log.json` 移除该期刊所有 hash 记录
3. 清理完成后立即进入深度爬取（第 4 步自动触发）

### 第 4 步：深度爬取（`--mode web`，⚠️ 禁止用 `--mode rss` 代替）

上一步命令已包含此步。深度爬取的完整流程：

```
弹出 Edge 浏览器 → 导航至期刊页
→ 爬取「当期目录」（含期数、页码、作者）
→ 爬取「网络首发」（若该刊无网络首发则自动跳过）
→ 与 cnki_dedup_log.json 比对 hash，过滤已抓条目
→ 新条目写入 XML，更新 dedup_log
→ 自动 git push 到 GitHub aes-feeds 仓库
```

遇到滑块验证码：等待人工滑动，上限 10 分钟。

**为什么禁止 `--mode rss`？**
RSS 产出的条目：无 `[当期目录]` 前缀、description 是原始摘要段落、去重 hash 与 web 模式不兼容。一旦用 RSS 初始化，后续 web 模式会因 hash 冲突跳过所有条目，导致 XML 永远是旧格式。

### 第 5 步：验证 XML 格式

生成的 XML 必须符合以下规范（参考 `aes-feeds/cnki_MRYX_cleaned.xml`）：

**Channel：**
```xml
<title>{期刊名} - CNKI Feeds</title>
<link>https://github.com/zorba123456/aes-feeds</link>
<!-- 无 <image> 节点 -->
```

**每条 Item：**
```xml
<title>[当期目录] [2026年XX期] 论文标题</title>
<!-- 或 -->
<title>[网络首发] 论文标题</title>

<description>&lt;b&gt;期数：&lt;/b&gt;2026年XX期&lt;br&gt;&lt;b&gt;出版日期/页码：&lt;/b&gt;1-6&lt;br&gt;&lt;b&gt;作者：&lt;/b&gt;张三;</description>
```

### 第 6 步：Inoreader 订阅（⚠️ 必须用 `_cleaned` URL）

```
https://raw.githubusercontent.com/zorba123456/aes-feeds/main/cnki_{code小写}_cleaned.xml
```

**必须用 `_cleaned` 后缀**：Inoreader 对每个 URL 全局缓存元数据。若曾订阅过 `cnki_xxx.xml`，删了重订同一 URL 仍读旧缓存，名称和图标不会更新。`_cleaned` URL 对 Inoreader 是全新地址。

### 第 7 步：验收清单（全部 ✓ 才算完成）

- [ ] `cnki_targets.json` 已添加，含 `web_scrape: true`
- [ ] `feed_reader.html` CNKI 区块已注册
- [ ] 已执行 `--reset-journal CODE` 清理去重记录
- [ ] 已执行 `--mode web`（非 `--mode rss`）
- [ ] XML 条目 title 含 `[当期目录]` 或 `[网络首发]` 前缀
- [ ] description 含三行结构化元信息（期数、页码、作者）
- [ ] channel `<title>` 为 `{期刊名} - CNKI Feeds`
- [ ] channel `<link>` 为 `https://github.com/zorba123456/aes-feeds`
- [ ] channel 无 `<image>` 节点
- [ ] aes-feeds 已 push 到 GitHub
- [ ] Inoreader 使用 `_cleaned.xml` URL 订阅

---

详细说明见 `docs/cnki_journal_onboarding.md`。
