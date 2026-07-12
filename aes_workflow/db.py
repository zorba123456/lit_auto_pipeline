"""SQLite access for aes_workflow.db."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "aes_workflow.db"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def migrate_schema(conn: sqlite3.Connection) -> None:
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries'"
    ).fetchone() is None:
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(entries)")}
    if "screening_status" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN screening_status TEXT")
    if "yuanbao_read_url" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN yuanbao_read_url TEXT")
    if "related_wechat_links" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN related_wechat_links TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entries_screening ON entries(screening_status)"
    )


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate_schema(conn)
    return conn


def init_db(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        migrate_schema(conn)
        conn.commit()
    return path


@contextmanager
def db_session(db_path: Path | str | None = None):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def lookup_article_key(conn: sqlite3.Connection, identifiers: dict[str, str]) -> str | None:
    for id_type, id_value in identifiers.items():
        if not id_value:
            continue
        row = conn.execute(
            "SELECT article_key FROM entry_identifiers WHERE id_type = ? AND id_value = ?",
            (id_type, id_value),
        ).fetchone()
        if row:
            return row["article_key"]
    return None


def register_identifiers(
    conn: sqlite3.Connection, article_key: str, identifiers: dict[str, str]
) -> None:
    for id_type, id_value in identifiers.items():
        if not id_value:
            continue
        conn.execute(
            """
            INSERT INTO entry_identifiers (id_type, id_value, article_key)
            VALUES (?, ?, ?)
            ON CONFLICT(id_type, id_value) DO UPDATE SET article_key = excluded.article_key
            """,
            (id_type, id_value, article_key),
        )


def log_ingest(
    conn: sqlite3.Connection,
    *,
    ingest_source: str,
    feed_file: str,
    id_type: str,
    id_value: str,
    article_key: str,
    duplicate: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO ingest_log (ingest_source, feed_file, id_type, id_value, article_key, duplicate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ingest_source, feed_file, id_type, id_value, article_key, int(duplicate), utc_now()),
    )


def get_entry(conn: sqlite3.Connection, article_key: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM entries WHERE article_key = ?", (article_key,)).fetchone()


def update_entry_l3(
    conn: sqlite3.Connection,
    article_key: str,
    *,
    reading_note_zh: str | None = None,
    doubao_read_url: str | None = None,
    yuanbao_read_url: str | None = None,
    reading_note_status: str | None = None,
) -> None:
    fields: list[str] = []
    values: list[object] = []
    if reading_note_zh is not None:
        fields.append("reading_note_zh = ?")
        values.append(reading_note_zh)
    if doubao_read_url is not None:
        fields.append("doubao_read_url = ?")
        values.append(doubao_read_url)
    if yuanbao_read_url is not None:
        fields.append("yuanbao_read_url = ?")
        values.append(yuanbao_read_url)
    if reading_note_status is not None:
        fields.append("reading_note_status = ?")
        values.append(reading_note_status)
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(utc_now())
    values.append(article_key)
    conn.execute(
        f"UPDATE entries SET {', '.join(fields)} WHERE article_key = ?",
        values,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Initialize aes_workflow.db")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    path = init_db(args.db)
    print(f"✅ initialized {path}")


if __name__ == "__main__":
    main()
