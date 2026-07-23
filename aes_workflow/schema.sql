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
