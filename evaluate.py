import argparse
import csv
import json
import sqlite3
import statistics
from contextlib import closing
from pathlib import Path

DB_PATH = "data/documents.db"
GT_PATH = "data/ground_truth.csv"
DETAILS_PATH = "data/evaluation_details.csv"
REPORT_PATH = "evaluation_report.md"

TEXT_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "currency"]
NUM_FIELDS = ["subtotal", "tax", "total"]
FIELDS = TEXT_FIELDS + NUM_FIELDS + ["num_items"]

NUM_TOLERANCE = 1.0  # selisih angka yang dianggap sama (misalnya pembulatan)


def norm(value) -> str:
    """Samakan spasi dan huruf besar/kecil sebelum membandingkan teks."""
    return " ".join(str(value).split()).casefold()


def is_correct(field: str, got, expected) -> bool:
    if got is None:
        return False
    if field in NUM_FIELDS or field == "num_items":
        try:
            return abs(float(got) - float(expected)) <= NUM_TOLERANCE
        except (TypeError, ValueError):
            return False
    return norm(got) == norm(expected)


def load_ground_truth() -> dict:
    with open(GT_PATH, newline="", encoding="utf-8") as f:
        return {row["filename"]: row for row in csv.DictReader(f)}


def load_results() -> dict:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM documents").fetchall()
    return {r["filename"]: r for r in rows}


def evaluate_document(row, truth) -> dict:
    """Bandingkan satu dokumen dengan ground truth."""
    data = json.loads(row["data_json"]) if row["data_json"] else None
    result = {
        "filename": row["filename"],
        "status": row["status"],
        "model": row["model_used"],
        "seconds": row["processing_seconds"],
        "extracted": data is not None,
    }
    for field in FIELDS:
        if data is None:
            result[field] = False
        elif field == "num_items":
            result[field] = is_correct(field, len(data.get("line_items") or []), truth[field])
        else:
            result[field] = is_correct(field, data.get(field), truth[field])
    result["all_correct"] = all(result[f] for f in FIELDS)
    result["wrong_fields"] = [f for f in FIELDS if not result[f]]
    return result


def pct(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "-"


def percentile(values, q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def main():
    parser = argparse.ArgumentParser(description="Evaluasi akurasi ekstraksi")
    parser.add_argument(
        "--manual-seconds", type=float, default=240,
        help="ASUMSI waktu input manual per dokumen (detik). Default 240 = 4 menit.",
    )
    args = parser.parse_args()

    truth = load_ground_truth()
    results = load_results()

    evaluated = [
        evaluate_document(results[name], truth[name])
        for name in sorted(results)
        if name in truth
    ]
    missing = sorted(set(truth) - set(results))
    n = len(evaluated)
    if n == 0:
        print("Tidak ada dokumen untuk dievaluasi. Jalankan run_pipeline.py dulu.")
        return

    lines = []
    out = lines.append

    out("# Laporan Evaluasi\n")
    out(f"Dokumen dievaluasi: **{n}** dari {len(truth)} di ground truth")
    if missing:
        out(f"Belum diproses: {len(missing)} dokumen ({', '.join(missing[:5])}{'...' if len(missing) > 5 else ''})")
    failed = [r for r in evaluated if not r["extracted"]]
    if failed:
        out(f"Gagal diekstrak: {len(failed)} dokumen (dihitung sebagai salah)")
    out("")

    # 1. Akurasi per field
    out("## Akurasi per field\n")
    out("| Field | Benar | Akurasi |")
    out("|---|---|---|")
    for field in FIELDS:
        ok = sum(r[field] for r in evaluated)
        out(f"| {field} | {ok}/{n} | {pct(ok, n)} |")
    exact = sum(r["all_correct"] for r in evaluated)
    out(f"\nDokumen dengan **semua field benar**: {exact}/{n} ({pct(exact, n)})\n")

    # 2. Efektivitas routing
    auto = [r for r in evaluated if r["status"] == "auto_approved"]
    review = [r for r in evaluated if r["status"] != "auto_approved"]
    auto_ok = sum(r["all_correct"] for r in auto)
    false_approved = [r for r in auto if not r["all_correct"]]
    review_wrong = sum(not r["all_correct"] for r in review)
    review_fine = len(review) - review_wrong

    out("## Efektivitas routing (human-in-the-loop)\n")
    out("| Metrik | Hasil |")
    out("|---|---|")
    out(f"| Disetujui otomatis | {len(auto)}/{n} ({pct(len(auto), n)}) |")
    out(f"| Akurasi pada yang disetujui otomatis | {auto_ok}/{len(auto)} ({pct(auto_ok, len(auto))}) |")
    out(f"| Salah tapi lolos otomatis (paling berbahaya) | {len(false_approved)} |")
    out(f"| Dikirim ke review manusia | {len(review)}/{n} ({pct(len(review), n)}) |")
    out(f"| ...dari itu yang memang salah | {review_wrong} |")
    out(f"| ...dari itu yang sebenarnya benar (review tidak perlu) | {review_fine} |")
    if false_approved:
        out("\nDokumen salah yang lolos otomatis:")
        for r in false_approved:
            out(f"- {r['filename']}: salah pada {', '.join(r['wrong_fields'])}")
    out("")

    # 3. Waktu
    times = [r["seconds"] for r in evaluated if r["seconds"] is not None]
    if times:
        median = statistics.median(times)
        out("## Waktu pemrosesan\n")
        out("| Metrik | Hasil |")
        out("|---|---|")
        out(f"| Median | {median:.1f} dtk |")
        out(f"| P90 | {percentile(times, 0.9):.1f} dtk |")
        out(f"| Rata-rata | {statistics.mean(times):.1f} dtk |")
        out(f"| Tercepat / terlama | {min(times):.1f} / {max(times):.1f} dtk |")
        out(f"| Asumsi waktu manual | {args.manual_seconds:.0f} dtk (asumsi, bukan hasil pengukuran) |")
        out(f"| Perbandingan terhadap asumsi manual | sekitar {args.manual_seconds / median:.0f}x lebih cepat (median) |")
        out("")

    # 4. Model yang dipakai
    models = {}
    for r in evaluated:
        models[r["model"] or "(gagal)"] = models.get(r["model"] or "(gagal)", 0) + 1
    out("## Model yang dipakai\n")
    for m, c in sorted(models.items(), key=lambda x: -x[1]):
        out(f"- {m}: {c} dokumen")
    out("")

    out("## Catatan\n")
    out("- Evaluasi ini memakai data dummy yang dibuat otomatis (bersih dan rapi), sehingga akurasi cenderung tinggi.")
    out("- Hasil pada dokumen nyata (miring, buram, format beragam) perlu diuji terpisah.")
    out("- Waktu manual adalah asumsi, bukan pengukuran.")

    report = "\n".join(lines)
    print(report)
    Path(REPORT_PATH).write_text(report + "\n", encoding="utf-8")

    # Detail per dokumen untuk analisis error
    with open(DETAILS_PATH, "w", newline="", encoding="utf-8") as f:
        cols = ["filename", "status", "model", "seconds", "all_correct", "wrong_fields"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in evaluated:
            w.writerow({**{c: r[c] for c in cols if c != "wrong_fields"},
                        "wrong_fields": ";".join(r["wrong_fields"])})

    print(f"\n(Laporan disimpan di {REPORT_PATH}, detail per dokumen di {DETAILS_PATH})")


if __name__ == "__main__":
    main()
