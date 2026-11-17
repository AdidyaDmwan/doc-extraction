"""Simulasikan berbagai threshold confidence pada hasil yang sudah ada (tanpa panggilan API).

Menjawab: kalau threshold dinaikkan, berapa dokumen salah yang tertangkap, dan berapa
review yang sebenarnya tidak perlu?

Pemakaian:
    python threshold_sweep.py --suffix hard
    python threshold_sweep.py --both        (set bersih + set sulit digabung)
"""
import argparse
import json

from evaluate import evaluate_document, load_ground_truth, load_results

THRESHOLDS = [0.85, 0.90, 0.95, 0.96, 0.98, 1.00]

parser = argparse.ArgumentParser()
parser.add_argument("--suffix", default="", help="misalnya 'hard'")
parser.add_argument("--both", action="store_true", help="gabungkan set bersih dan set 'hard'")
args = parser.parse_args()

suffixes = ["", "hard"] if args.both else [args.suffix]
results = load_results()

docs = []
for suffix in suffixes:
    gt_path = f"data/ground_truth_{suffix}.csv" if suffix else "data/ground_truth.csv"
    truth = load_ground_truth(gt_path)
    for name in sorted(results):
        if name not in truth:
            continue
        row = results[name]
        ev = evaluate_document(row, truth[name])
        reasons = json.loads(row["reasons"]) if row["reasons"] else []
        # Alasan review selain confidence (validasi aturan, field diragukan, gagal ekstrak)
        ev["other_reasons"] = [r for r in reasons if not r.startswith("confidence rendah")]
        docs.append(ev)

n = len(docs)
total_wrong = sum(not d["all_correct"] for d in docs)
print(f"Dokumen: {n} | Dokumen yang memang salah: {total_wrong}\n")
print("| Threshold | Disetujui otomatis | Salah tapi lolos | Dikirim ke review | Review yang memang perlu | Review tidak perlu |")
print("|---|---|---|---|---|---|")

for t in THRESHOLDS:
    auto = review = false_ok = needed = unneeded = 0
    for d in docs:
        to_review = bool(d["other_reasons"]) or d["confidence"] is None or d["confidence"] < t
        if to_review:
            review += 1
            if d["all_correct"]:
                unneeded += 1
            else:
                needed += 1
        else:
            auto += 1
            if not d["all_correct"]:
                false_ok += 1
    print(f"| {t:.2f} | {auto}/{n} ({auto / n * 100:.0f}%) | {false_ok} "
          f"| {review}/{n} ({review / n * 100:.0f}%) | {needed} | {unneeded} |")

print("\nCatatan: memilih threshold berdasarkan tabel ini berarti menyetel pada data yang sama,")
print("jadi hasilnya perlu dikonfirmasi pada set uji baru sebelum dijadikan klaim.")
