import time
from pathlib import Path
from typing import List, Optional, Tuple

from . import db
from .extract import extract_invoice_with_model
from .validate import NEEDS_REVIEW, route, validate

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def process_file(path: Path) -> Tuple[str, List[str], float]:
    """Proses satu dokumen: ekstrak, validasi, tentukan status, lalu simpan.

    Kegagalan satu dokumen tidak boleh menghentikan seluruh batch, jadi semua
    error ditangkap dan dokumen yang gagal dialihkan ke antrean review.
    """
    t0 = time.time()
    try:
        invoice, model_used = extract_invoice_with_model(str(path))
        errors = validate(invoice)
        status, reasons = route(invoice, errors)
    except Exception as e:  # noqa: BLE001 - sengaja menangkap semua error
        invoice, model_used = None, None
        status = NEEDS_REVIEW
        reasons = [f"extraction_failed: {type(e).__name__}: {str(e)[:200]}"]

    seconds = time.time() - t0
    db.save_document(path.name, invoice, status, reasons, model_used, seconds)
    return status, reasons, seconds


def process_folder(
    folder: str = "data/samples",
    limit: Optional[int] = None,
    force: bool = False,
    delay: float = 2.0,
) -> None:
    """Proses semua dokumen di sebuah folder.

    - Dokumen yang sudah berhasil diproses dilewati (kecuali force=True),
      jadi proses bisa dilanjutkan kalau terputus.
    - delay: jeda antar dokumen (detik) agar tidak menabrak batas free tier.
    """
    db.init_db()

    files = sorted(
        p for p in Path(folder).iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not force:
        done = db.get_processed_filenames()
        files = [p for p in files if p.name not in done]
    if limit:
        files = files[:limit]

    total = len(files)
    if total == 0:
        print("Tidak ada dokumen baru untuk diproses.")
        return

    print(f"Memproses {total} dokumen dari {folder} ...\n")
    for i, path in enumerate(files, start=1):
        status, reasons, seconds = process_file(path)
        note = f"  <- {reasons[0]}" if reasons else ""
        print(f"[{i}/{total}] {path.name:20} {status:14} {seconds:5.1f} dtk{note}")
        if i < total and delay > 0:
            time.sleep(delay)
