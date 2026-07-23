# AES 中台设计 · 来源与微信公众号处理

> 本文件记录 2026-07-23 对话的框架决策，供后续开发接续。
> 相关对话：20260722_162448_6dab56 → 20260723_011129_08c516

---

## 文献三大来源

| 来源 | 入口 | 标识符情况 | 审核 |
|---|---|---|---|
| **① 期刊 RSS / 爬虫** | FreshRSS 自动拉取 | 多有 DOI/PMID/PII | 自动入库 |
| **② 微信公众号** | FreshRSS 拉取 wechat-rss | 因号而异 | 自动入库，但分类处理 |
| **③ 用户推荐** | 浏览器插件 / 企微转发 / 后台录入 | 可能有无 | 编辑→自动；非编辑→待审核 |

## 微信公众号三亚类

| 类型 | 示例 | 处理方式 |
|---|---|---|
| **A. 行业资讯** | 医与美前沿、梅斯医学 | `discovery_type=wechat_news`，不进学术文献流 |
| **B. 文献解读** | 取名太麻烦、肉毒毒素btxa | 正文扫描 DOI/PMID，截图 OCR（P2+） |
| **C. 临床/病例** | 优麦会讯、皮科Online | 有则提取，无则普通内容 |

## 桥接层边界（已实现）

- ✅ 读 FreshRSS entry 表（增量 `id > last_seen_id`）
- ✅ 提取 DOI/PMID/PII/platform_id
- ✅ 计算 `article_key` → dedup → 写入 entries
- ✅ 记录 `ingest_log`
- ❌ 不调外部 API（CrossRef/PubMed）
- ❌ 不打标、不筛选
- ❌ 不处理截图 OCR（P2+）

## 微信公众号发现来源记录（待实现）

新增字段：
- `discovery_type`: rss_feed / wechat_news / wechat_discovery / user_submit
- `wechat_discovery_sources`: JSON 数组，记录从哪些微信文章发现了这篇文献
- `submitter_role`: editor / user（仅 user_submit）
- `review_status`: auto_approved / pending_review / rejected

## 系统状态（2026-07-23）

- ✅ aes_workflow.db 已清空并重建
- ✅ Django 项目初始化和运行（8301）
- ✅ 桥接层已写，全量导入 17,990 条（去重后）
- ✅ 首页状态面板可看
| ⏳ reader app 尚未建
| - ✅ schema.sql 和桥接层已加发现来源字段并重导
| - ⏳ Inoreader 扩展积累的学习集/提示词/关键词黑名单 → 留到中台筛选环节再迁移（不持续同步）

## Inoreader → 新系统过渡策略

- 两套系统**独立运行**，不打通
- Inoreader 扩展继续独立运行，不做数据写入 aes_workflow.db
- 新中台 Reader 建好后逐步替代 Inoreader 的阅读/筛选功能
- Inoreader 的 learningSet / system-prompt / keywordBlacklist / 蒸馏规则 在**中台筛选开发阶段**一次性迁移为冷启动基础，不做持续同步
