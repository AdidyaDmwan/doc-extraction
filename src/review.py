"""Logika di balik UI review (tanpa Streamlit), supaya mudah diuji."""
import json
import math
from pathlib import Path
from typing import List, Optional

from .schema import Invoice, LineItem

STATUS_APPROVED = "approved"    # manusia memeriksa, hasil AI benar
STATUS_CORRECTED = "corrected"  # manusia memeriksa dan mengoreksi

SEARCH_DIRS = [Path("data/samples"), Path("data/hard_samples"), Path("data/uploads")]

TEXT_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "currency"]
NUM_FIELDS = ["subtotal", "tax", "total"]
ITEM_NUM_FIELDS = ["quantity", "unit_price", "amount"]
NUM_TOLERANCE = 0.005


def find_file(filename: str) -> Optional[Path]:
    for folder in SEARCH_DIRS:
        path = folder / filename
        if path.exists():
            return path
    return None


def final_data(row) -> Optional[dict]:
    """Data akhir sebuah dokumen: koreksi manusia jika ada, selain itu hasil AI."""
    raw = row["corrected_json"] or row["data_json"]
    return json.loads(raw) if raw else None


def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and not v.strip()


def _same_text(a, b) -> bool:
    if _blank(a) and _blank(b):
        return True
    if _blank(a) or _blank(b):
        return False
    return " ".join(str(a).split()) == " ".join(str(b).split())


def _same_num(a, b) -> bool:
    if _blank(a) and _blank(b):
        return True
    if _blank(a) or _blank(b):
        return False
    try:
        return abs(float(a) - float(b)) <= NUM_TOLERANCE
    except (TypeError, ValueError):
        return False


def invoice_differs(original: Optional[dict], corrected: dict) -> bool:
    """True jika koreksi manusia berbeda dari hasil ekstraksi AI."""
    if original is None:
        return True
    for f in TEXT_FIELDS:
        if not _same_text(original.get(f), corrected.get(f)):
            return True
    for f in NUM_FIELDS:
        if not _same_num(original.get(f), corrected.get(f)):
            return True
    old_items = original.get("line_items") or []
    new_items = corrected.get("line_items") or []
    if len(old_items) != len(new_items):
        return True
    for a, b in zip(old_items, new_items):
        if not _same_text(a.get("description"), b.get("description")):
            return True
        for f in ITEM_NUM_FIELDS:
            if not _same_num(a.get(f), b.get(f)):
                return True
    return False


def _num_or_none(v) -> Optional[float]:
    return None if _blank(v) else float(v)


def clean_items(records: List[dict]) -> List[dict]:
    """Rapikan baris item dari tabel editor: NaN menjadi None, baris kosong dibuang."""
    items = []
    for rec in records:
        item = {
            "description": None if _blank(rec.get("description")) else str(rec["description"]).strip(),
            "quantity": _num_or_none(rec.get("quantity")),
            "unit_price": _num_or_none(rec.get("unit_price")),
            "amount": _num_or_none(rec.get("amount")),
        }
        if all(v is None for v in item.values()):
            continue
        items.append(item)
    return items


def build_invoice(values: dict, items: List[dict], confidence: float) -> Invoice:
    """Susun objek Invoice dari isian formulir (untuk validasi ulang dan penyimpanan)."""
    return Invoice(
        vendor_name=None if _blank(values.get("vendor_name")) else str(values["vendor_name"]).strip(),
        invoice_number=None if _blank(values.get("invoice_number")) else str(values["invoice_number"]).strip(),
        invoice_date=None if _blank(values.get("invoice_date")) else str(values["invoice_date"]).strip(),
        currency=None if _blank(values.get("currency")) else str(values["currency"]).strip().upper(),
        subtotal=_num_or_none(values.get("subtotal")),
        tax=_num_or_none(values.get("tax")),
        total=_num_or_none(values.get("total")),
        line_items=[LineItem(**i) for i in items],
        confidence=confidence,
        uncertain_fields=[],
    )
