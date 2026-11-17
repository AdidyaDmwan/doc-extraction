import sys

from src.normalize import normalize_currency
from src.schema import Invoice, LineItem
from src.validate import AUTO_APPROVED, NEEDS_REVIEW, route, validate


def make_valid() -> Invoice:
    """Invoice yang benar secara hitungan, sebagai bahan dasar tes."""
    return Invoice(
        vendor_name="PT Contoh Abadi",
        invoice_number="INV-2026-1234",
        invoice_date="2026-03-15",
        currency="IDR",
        subtotal=250000,
        tax=27500,
        total=277500,
        line_items=[
            LineItem(description="Mouse Wireless", quantity=2, unit_price=100000, amount=200000),
            LineItem(description="Flashdisk 64GB", quantity=1, unit_price=50000, amount=50000),
        ],
        confidence=0.95,
        uncertain_fields=[],
    )


def variant(**changes) -> Invoice:
    return make_valid().model_copy(update=changes)


# (nama kasus, invoice, status yang diharapkan)
bad_item = [
    LineItem(description="Mouse Wireless", quantity=2, unit_price=100000, amount=190000),
    LineItem(description="Flashdisk 64GB", quantity=1, unit_price=50000, amount=50000),
]

CASES = [
    ("Invoice benar dan yakin", make_valid(), AUTO_APPROVED),
    ("Total salah", variant(total=300000), NEEDS_REVIEW),
    ("Tanggal kosong", variant(invoice_date=None), NEEDS_REVIEW),
    ("Format tanggal salah", variant(invoice_date="15/03/2026"), NEEDS_REVIEW),
    ("Hitungan item salah", variant(line_items=bad_item), NEEDS_REVIEW),
    ("Tidak ada item", variant(line_items=[]), NEEDS_REVIEW),
    ("Mata uang ditulis Rp", variant(currency="Rp"), NEEDS_REVIEW),
    ("Mata uang kosong", variant(currency=None), NEEDS_REVIEW),
    ("Confidence rendah", variant(confidence=0.6), NEEDS_REVIEW),
    ("AI ragu pada field", variant(uncertain_fields=["total"]), NEEDS_REVIEW),
]


def run_offline_tests():
    print("=== TES ATURAN VALIDASI (tanpa API) ===\n")
    failed = 0
    for name, inv, expected in CASES:
        errors = validate(inv)
        status, reasons = route(inv, errors)
        ok = status == expected
        failed += 0 if ok else 1
        print(f"{'LULUS' if ok else 'GAGAL'}  {name:28} -> {status}")
        for r in reasons:
            print(f"         - {r}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} kasus sesuai harapan")


def run_normalization_tests():
    print("\n=== TES NORMALISASI MATA UANG ===\n")
    expected = {
        "Rp": "IDR", "Rp.": "IDR", "Rupiah": "IDR", "idr": "IDR", " IDR ": "IDR",
        "usd": "USD", "EUR": "EUR", "": None, None: None, "$": "$", "mata uang aneh": "mata uang aneh",
    }
    failed = 0
    for raw, want in expected.items():
        got = normalize_currency(raw)
        ok = got == want
        failed += 0 if ok else 1
        print(f"{'LULUS' if ok else 'GAGAL'}  {raw!r:18} -> {got!r}")
    print(f"\n{len(expected) - failed}/{len(expected)} kasus sesuai harapan")


def run_on_real_file(filename: str):
    from src.extract import extract_invoice_with_model

    print(f"\n=== TES PADA DOKUMEN ASLI: {filename} ===")
    inv, model = extract_invoice_with_model(f"data/samples/{filename}")
    errors = validate(inv)
    status, reasons = route(inv, errors)
    print(f"Model   : {model}")
    print(f"Status  : {status}")
    print("Alasan  :", reasons if reasons else "-")


if __name__ == "__main__":
    run_offline_tests()
    run_normalization_tests()
    if len(sys.argv) > 1:
        run_on_real_file(sys.argv[1])
