"""Hitung ulang status (auto_approved / needs_review) dari data yang SUDAH tersimpan,
memakai aturan validasi dan threshold terbaru. Tidak memanggil API.

Jalankan setiap kali aturan validasi atau threshold diubah:
    python reroute.py

Dokumen yang sudah dikoreksi/disetujui manusia tidak disentuh.
"""
import json
import sqlite3
from contextlib import closing

from src.db import DB_PATH
from src.schema import Invoice
from src.validate import CONFIDENCE_THRESHOLD, route, validate


def main():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT filename, data_json, status FROM documents "
            "WHERE data_json IS NOT NULL AND status IN ('auto_approved', 'needs_review')"
        ).fetchall()

        to_review = to_auto = 0
        for r in rows:
            invoice = Invoice.model_validate_json(r["data_json"])
            status, reasons = route(invoice, validate(invoice))
            if status != r["status"]:
                if status == "needs_review":
                    to_review += 1
                else:
                    to_auto += 1
            conn.execute(
                "UPDATE documents SET status = ?, reasons = ? WHERE filename = ?",
                (status, json.dumps(reasons, ensure_ascii=False), r["filename"]),
            )
        conn.commit()

    print(f"Threshold confidence : {CONFIDENCE_THRESHOLD}")
    print(f"Dokumen dihitung ulang: {len(rows)}")
    print(f"  auto_approved -> needs_review : {to_review}")
    print(f"  needs_review -> auto_approved : {to_auto}")


if __name__ == "__main__":
    main()
