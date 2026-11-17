import logging
import sys
import time

import pandas as pd

from src.extract import extract_invoice_with_model

logging.basicConfig(level=logging.WARNING)

# Pemakaian:
#   python test_extract.py                    -> invoice_001.pdf
#   python test_extract.py invoice_007.pdf    -> file tertentu
filename = sys.argv[1] if len(sys.argv) > 1 else "invoice_001.pdf"
path = f"data/samples/{filename}"

print(f"Memproses {path} ...")
t0 = time.time()
inv, model_used = extract_invoice_with_model(path)
elapsed = time.time() - t0

print(f"\n=== HASIL EKSTRAKSI AI ({elapsed:.1f} detik, model: {model_used}) ===")
print(inv.model_dump_json(indent=2))

# Bandingkan dengan ground truth
gt = pd.read_csv("data/ground_truth.csv")
row = gt[gt["filename"] == filename]
if row.empty:
    print("\n(Tidak ada ground truth untuk file ini)")
    sys.exit()

row = row.iloc[0]
print("\n=== PERBANDINGAN DENGAN GROUND TRUTH ===")
fields = ["vendor_name", "invoice_number", "invoice_date", "currency", "subtotal", "tax", "total"]
for f in fields:
    expected = row[f]
    got = getattr(inv, f)
    # Bandingkan angka sebagai angka, sisanya sebagai teks
    if f in ("subtotal", "tax", "total"):
        ok = got is not None and abs(float(got) - float(expected)) < 1
    else:
        ok = got is not None and str(got).strip() == str(expected).strip()
    mark = "OK   " if ok else "BEDA "
    print(f"{mark} {f:15} benar={expected!s:35} AI={got}")
