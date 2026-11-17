import re
from datetime import datetime
from typing import List, Tuple

from .schema import Invoice

# Toleransi selisih hitungan (dalam satuan mata uang, misalnya rupiah)
TOLERANCE = 1.0

# Di bawah angka ini, dokumen selalu ditinjau manusia.
# Dipilih 0.96 dari analisis threshold_sweep.py pada set 'hard' (sebelumnya 0.85):
# model sering melaporkan 0.95 saat kurang yakin. Nilai ini spesifik untuk model yang dipakai
# dan belum dikonfirmasi pada set uji baru.
CONFIDENCE_THRESHOLD = 0.96

AUTO_APPROVED = "auto_approved"
NEEDS_REVIEW = "needs_review"


def _close(a: float, b: float, tol: float = TOLERANCE) -> bool:
    return abs(a - b) <= tol


def validate(inv: Invoice) -> List[str]:
    """Periksa hasil ekstraksi dengan aturan deterministik.

    Mengembalikan daftar masalah. List kosong berarti semua aturan lolos.
    """
    errors: List[str] = []

    # 1. Field wajib harus terisi
    required = [
        ("vendor_name", "nama vendor"),
        ("invoice_number", "nomor invoice"),
        ("invoice_date", "tanggal"),
        ("currency", "mata uang"),
        ("total", "total"),
    ]
    for field, label in required:
        if getattr(inv, field) in (None, ""):
            errors.append(f"{label} kosong")

    # 2. Format dan kewajaran tanggal
    if inv.invoice_date:
        try:
            d = datetime.strptime(inv.invoice_date, "%Y-%m-%d")
            if not (2000 <= d.year <= 2100):
                errors.append("tahun pada tanggal tidak masuk akal")
        except ValueError:
            errors.append("format tanggal salah (harus YYYY-MM-DD)")

    # 2b. Mata uang harus kode 3 huruf besar (misalnya IDR), bukan simbol seperti 'Rp'
    if inv.currency and not re.fullmatch(r"[A-Z]{3}", inv.currency):
        errors.append("format mata uang tidak valid (harus kode 3 huruf, misalnya IDR)")

    # 3. Total harus positif
    if inv.total is not None and inv.total <= 0:
        errors.append("total harus lebih dari 0")

    # 4. Subtotal + pajak harus sama dengan total
    if None not in (inv.subtotal, inv.tax, inv.total):
        if not _close(inv.subtotal + inv.tax, inv.total):
            errors.append("subtotal + pajak tidak sama dengan total")

    # 5. Item-item invoice
    if not inv.line_items:
        errors.append("tidak ada item pada invoice")
    else:
        amounts = [item.amount for item in inv.line_items]
        if any(a is None for a in amounts):
            errors.append("ada item tanpa jumlah harga")
        elif inv.subtotal is not None and not _close(sum(amounts), inv.subtotal):
            errors.append("jumlah semua item tidak sama dengan subtotal")

        for n, item in enumerate(inv.line_items, start=1):
            if None not in (item.quantity, item.unit_price, item.amount):
                if not _close(item.quantity * item.unit_price, item.amount):
                    errors.append(f"item {n}: qty x harga satuan tidak sama dengan jumlah")

    return errors


def route(
    inv: Invoice, errors: List[str], threshold: float = CONFIDENCE_THRESHOLD
) -> Tuple[str, List[str]]:
    """Tentukan nasib dokumen: auto_approved atau needs_review.

    Mengembalikan (status, alasan). Alasan kosong jika auto_approved.
    """
    reasons = list(errors)

    if inv.confidence < threshold:
        reasons.append(f"confidence rendah ({inv.confidence:.2f} < {threshold})")

    if inv.uncertain_fields:
        reasons.append("field diragukan AI: " + ", ".join(inv.uncertain_fields))

    status = NEEDS_REVIEW if reasons else AUTO_APPROVED
    return status, reasons
