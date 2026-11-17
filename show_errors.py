"""Tampilkan rincian dokumen yang salah atau masuk review: nilai yang benar vs
nilai yang dibaca AI, confidence, dan alasan routing.

Pemakaian:
    python show_errors.py               -> set data asli (bersih)
    python show_errors.py --suffix hard -> set data sulit
"""
import argparse
import json

from evaluate import FIELDS, is_correct, load_ground_truth, load_results

parser = argparse.ArgumentParser()
parser.add_argument("--suffix", default="", help="misalnya 'hard'")
args = parser.parse_args()

gt_path = f"data/ground_truth_{args.suffix}.csv" if args.suffix else "data/ground_truth.csv"
truth = load_ground_truth(gt_path)
results = load_results()

shown = 0
for name in sorted(results):
    if name not in truth:
        continue
    row = results[name]
    expected = truth[name]
    data = json.loads(row["data_json"]) if row["data_json"] else None
    reasons = json.loads(row["reasons"]) if row["reasons"] else []

    mismatches = []
    if data is not None:
        for field in FIELDS:
            got = len(data.get("line_items") or []) if field == "num_items" else data.get(field)
            if not is_correct(field, got, expected[field]):
                mismatches.append((field, expected[field], got))

    if not mismatches and row["status"] == "auto_approved":
        continue  # benar dan lolos otomatis: tidak perlu ditampilkan

    shown += 1
    level = f" [{expected['difficulty']}]" if expected.get("difficulty") else ""
    print(f"\n{name}{level}")
    print(f"  status      : {row['status']}")
    if data is not None:
        print(f"  confidence  : {data.get('confidence')}")
        print(f"  AI ragu pada: {data.get('uncertain_fields') or '-'}")
    print(f"  alasan      : {reasons or '-'}")
    for field, want, got in mismatches:
        print(f"  SALAH {field:15} benar={want!r}  dibaca AI={got!r}")
    if data is not None and not mismatches:
        print("  (hasil ekstraksinya sebenarnya benar semua)")

print(f"\n{shown} dokumen ditampilkan.")
