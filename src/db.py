import json
import sqlite3
import statistics
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .schema import Invoice

DB_PATH = Path("data/documents.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    data_json TEXT,
    status TEXT NOT NULL,
    reasons TEXT,
    confidence REAL,
    model_used TEXT,
    processing_seconds REAL,
    processed_at TEXT NOT NULL
)
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        conn.execute(SCHEMA)
        conn.commit()


def save_document(
    filename: str,
    invoice: Optional[Invoice],
    status: str,
    reasons: List[str],
    model_used: Optional[str],
    seconds: float,
) -> None:
    """Simpan (atau perbarui) hasil pemrosesan satu dokumen."""
    data_json = invoice.model_dump_json() if invoice is not None else None
    confidence = invoice.confidence if invoice is not None else None
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO documents
                (filename, data_json, status, reasons, confidence,
                 model_used, processing_seconds, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                data_json = excluded.data_json,
                status = excluded.status,
                reasons = excluded.reasons,
                confidence = excluded.confidence,
                model_used = excluded.model_used,
                processing_seconds = excluded.processing_seconds,
                processed_at = excluded.processed_at
            """,
            (
                filename,
                data_json,
                status,
                json.dumps(reasons, ensure_ascii=False),
                confidence,
                model_used,
                round(seconds, 2),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def get_processed_filenames() -> set:
    """Nama file yang sudah berhasil diekstrak. Dokumen yang gagal tidak dihitung,
    sehingga akan dicoba lagi pada proses berikutnya."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT filename FROM documents WHERE data_json IS NOT NULL"
        ).fetchall()
    return {r["filename"] for r in rows}


def get_summary() -> dict:
    """Ringkasan jumlah dokumen per status dan statistik waktu proses."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT status, processing_seconds FROM documents"
        ).fetchall()

    by_status: dict = {}
    times = []
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        if r["processing_seconds"] is not None:
            times.append(r["processing_seconds"])

    return {
        "total": len(rows),
        "by_status": by_status,
        "mean_seconds": statistics.mean(times) if times else None,
        "median_seconds": statistics.median(times) if times else None,
    }
