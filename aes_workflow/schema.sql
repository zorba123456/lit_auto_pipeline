-- AES workflow DB · Top3 #1
-- Apply: python3 -m aes_workflow.db init

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entries (
  article_key TEXT PRIMARY KEY,
  feed_id TEXT,
  ingest_source TEXT,
  lang TEXT DEFAULT 'en',
  title TEXT NOT NULL,
  title_zh_display TEXT,
  title_prefix TEXT,
  journal TEXT,
  authors TEXT,
  abstract TEXT,
  doi TEXT,
  pmid TEXT,
  pmcid TEXT,
  pii TEXT,
  platform TEXT,
  platform_id TEXT,
  source_url TEXT,
  publisher_url TEXT,
  issue TEXT,
  pages TEXT,
  pub_date TEXT,
  meta_status TEXT DEFAULT 'meta_pending',
  meta_tier TEXT,
  fulltext_status TEXT DEFAULT 'PDF_NONE',
  pdf_path TEXT,
  reading_note_status TEXT DEFAULT 'none',
  reading_note_zh TEXT,
  doubao_read_url TEXT,
  yuanbao_read_url TEXT,
  has_video INTEGER DEFAULT 0,
  screening_status TEXT,
  discovery_type TEXT DEFAULT 'rss_feed',
  wechat_discovery_sources TEXT,
  submitter_role TEXT,
  review_status TEXT DEFAULT 'auto_approved',
  ingest_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_identifiers (
  id_type TEXT NOT NULL,
  id_value TEXT NOT NULL,
  article_key TEXT NOT NULL REFERENCES entries(article_key) ON DELETE CASCADE,
  PRIMARY KEY (id_type, id_value)
);

CREATE INDEX IF NOT EXISTS idx_entry_identifiers_key ON entry_identifiers(article_key);
CREATE INDEX IF NOT EXISTS idx_entries_doi ON entries(doi);
CREATE INDEX IF NOT EXISTS idx_entries_pub_date ON entries(pub_date);
CREATE INDEX IF NOT EXISTS idx_entries_fulltext ON entries(fulltext_status);
CREATE INDEX IF NOT EXISTS idx_entries_screening ON entries(screening_status);

CREATE TABLE IF NOT EXISTS ingest_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingest_source TEXT,
  feed_file TEXT,
  id_type TEXT,
  id_value TEXT,
  article_key TEXT,
  duplicate INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);

-- ── 阶段0：唯一标识对象层（§标识符归一策略 §一两层ID / 《框架》§8.1/8.3/8.5/12.2）──
-- 幂等增量迁移的同款逻辑见 aes-workbench/schema_stage0.py（工作台侧入口）。
-- 本段是 DB 真源记录；老库由 migrate_schema() 增量补齐。

CREATE TABLE IF NOT EXISTS objects (
  object_id TEXT PRIMARY KEY,            -- DOI/PMID/cmaid/cnki/title_hash
  id_type TEXT NOT NULL
             CHECK (id_type IN ('doi','pmid','cmaid','cnki','title_hash')),
  stage TEXT NOT NULL DEFAULT 'discovered'
             CHECK (stage IN ('discovered','screened','fulltext','summarized','detailed')),
  is_final_version TEXT NOT NULL DEFAULT 'unknown'
             CHECK (is_final_version IN ('0','1','unknown')),
  has_video TEXT NOT NULL DEFAULT 'unknown'
             CHECK (has_video IN ('0','1','unknown')),
  video_available TEXT NOT NULL DEFAULT 'unknown'
             CHECK (video_available IN ('0','1','unknown')),
  human_finalized INTEGER NOT NULL DEFAULT 0 CHECK (human_finalized IN (0,1)),
  normalize_status TEXT,
  screen_status TEXT,
  tag_status TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_objects_stage ON objects(stage);
CREATE INDEX IF NOT EXISTS idx_objects_updated ON objects(updated_at);

-- 对象 ↔ 条目关联（一个 object 可挂多 entry；§8.2 同 DOI 多 key 常态）
CREATE TABLE IF NOT EXISTS entry_object_links (
  object_id TEXT NOT NULL REFERENCES objects(object_id) ON DELETE CASCADE,
  article_key TEXT NOT NULL REFERENCES entries(article_key) ON DELETE CASCADE,
  link_status TEXT NOT NULL DEFAULT 'linked'
             CHECK (link_status IN ('linked','candidate','broken')),
  PRIMARY KEY (object_id, article_key)
);
CREATE INDEX IF NOT EXISTS idx_eol_key ON entry_object_links(article_key);

-- 来源多值记录（§12.2：一对象多来源可回溯，RSS+微信+IMA）
CREATE TABLE IF NOT EXISTS object_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id TEXT NOT NULL REFERENCES objects(object_id) ON DELETE CASCADE,
  channel TEXT NOT NULL CHECK (channel IN ('rss','wechat','ima','manual')),
  source_detail TEXT,
  link TEXT,
  first_seen_at TEXT NOT NULL,
  UNIQUE (object_id, channel, source_detail)
);
CREATE INDEX IF NOT EXISTS idx_object_sources_obj ON object_sources(object_id);
