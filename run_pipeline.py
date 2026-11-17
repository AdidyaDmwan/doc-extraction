import argparse
import logging

from src import db
from src.pipeline import process_folder

logging.basicConfig(level=logging.WARNING)

parser = argparse.ArgumentParser(description="Proses dokumen invoice secara batch")
parser.add_argument("--folder", default="data/samples", help="folder berisi dokumen")
parser.add_argument("--limit", type=int, default=None, help="proses maksimal N dokumen")
parser.add_argument("--force", action="store_true", help="proses ulang semua dokumen")
parser.add_argument("--delay", type=float, default=2.0, help="jeda antar dokumen (detik)")
args = parser.parse_args()

try:
    process_folder(args.folder, limit=args.limit, force=args.force, delay=args.delay)
except KeyboardInterrupt:
    print("\nDihentikan oleh pengguna. Hasil yang sudah diproses tetap tersimpan.")

s = db.get_summary()
print("\n=== RINGKASAN DATABASE ===")
print(f"Total dokumen        : {s['total']}")
for status, count in sorted(s["by_status"].items()):
    pct = count / s["total"] * 100 if s["total"] else 0
    print(f"  {status:16} : {count} ({pct:.0f}%)")
if s["median_seconds"] is not None:
    print(f"Waktu per dokumen    : median {s['median_seconds']:.1f} dtk, rata-rata {s['mean_seconds']:.1f} dtk")
