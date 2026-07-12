"""Local PDF storage backend (Top3 #2)."""

from __future__ import annotations

import shutil
from pathlib import Path

from aes_workflow.paths import PDF_INBOX, PDF_STORE_DIR, pdf_store_path, rel_pdf_path


class LocalPdfStore:
    def __init__(
        self,
        *,
        inbox: Path | str | None = None,
        store_dir: Path | str | None = None,
    ) -> None:
        self.inbox = Path(inbox) if inbox else PDF_INBOX
        self.store_dir = Path(store_dir) if store_dir else PDF_STORE_DIR

    def ensure_dirs(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def dest_path(self, article_key: str) -> Path:
        return pdf_store_path(article_key) if self.store_dir == PDF_STORE_DIR else self.store_dir / f"{article_key}.pdf"

    def rel_path(self, article_key: str) -> str:
        if self.store_dir == PDF_STORE_DIR:
            return rel_pdf_path(article_key)
        return str(self.dest_path(article_key))

    def get(self, article_key: str) -> Path | None:
        path = self.dest_path(article_key)
        return path if path.is_file() else None

    def commit(self, src: Path, article_key: str, *, replace: bool = True) -> Path:
        """Move inbox PDF into canonical store."""
        dest = self.dest_path(article_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = src.resolve()
        if dest.is_file():
            if not replace:
                if src != dest:
                    src.unlink(missing_ok=True)
                return dest
            dest.unlink()
        if src == dest:
            return dest
        shutil.move(str(src), str(dest))
        return dest
