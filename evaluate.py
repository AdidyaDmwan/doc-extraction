import argparse
import csv
import json
import sqlite3
import statistics
from contextlib import closing
from pathlib import Path

DB_PATH = "data/documents.db"

TEXT_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "currency"]
NUM_FIELDS = ["subtotal", "tax", "total"]
FIELDS = TEXT_FIELDS + NUM_FIELDS + ["num_items"]
DIFFICULTY_ORDER = ["ringan", "sedang", "berat"]

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


def load_ground_truth(path: str) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
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
        "difficulty": truth.get("difficulty"),
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
    parser.add_argument(
        "--suffix", default="",
        help="Nama set data tambahan, misalnya 'hard' -> data/ground_truth_hard.csv",
    )
    args = parser.parse_args()

    if args.suffix:
        gt_path = f"data/ground_truth_{args.suffix}.csv"
        report_path = f"evaluation_report_{args.suffix}.md"
        details_path = f"data/evaluation_details_{args.suffix}.csv"
    else:
        gt_path = "data/ground_truth.csv"
        report_path = "evaluation_report.md"
        details_path = "data/evaluation_details.csv"

    truth = load_ground_truth(gt_path)
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

    out("# Laporan Evaluasi" + (f" ({args.suffix})" if args.suffix else "") + "\n")
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

    # 3. Hasil per tingkat kesulitan (hanya jika ground truth punya kolom 'difficulty')
    levels = [lv for lv in DIFFICULTY_ORDER if any(r["difficulty"] == lv for r in evaluated)]
    if levels:
        out("## Hasil per tingkat kesulitan\n")
        out("| Tingkat | Dokumen | Semua field benar | Disetujui otomatis | Salah tapi lolos otomatis |")
        out("|---|---|---|---|---|")
        for lv in levels:
            grp = [r for r in evaluated if r["difficulty"] == lv]
            g_exact = sum(r["all_correct"] for r in grp)
            g_auto = [r for r in grp if r["status"] == "auto_approved"]
            g_false = sum(not r["all_correct"] for r in g_auto)
            out(f"| {lv} | {len(grp)} | {g_exact}/{len(grp)} ({pct(g_exact, len(grp))}) "
                f"| {len(g_auto)}/{len(grp)} ({pct(len(g_auto), len(grp))}) | {g_false} |")
        out("")

    # 4. Daftar dokumen yang salah (untuk analisis error)
    wrong_docs = [r for r in evaluated if not r["all_correct"]]
    if wrong_docs:
        out("## Dokumen yang salah (untuk analisis error)\n")
        for r in wrong_docs[:20]:
            tag = f" [{r['difficulty']}]" if r["difficulty"] else ""
            out(f"- {r['filename']}{tag}: status {r['status']}, salah pada {', '.join(r['wrong_fields'])}")
        if len(wrong_docs) > 20:
            out(f"- ... dan {len(wrong_docs) - 20} dokumen lain (lihat {details_path})")
        out("")

    # 5. Waktu
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

    # 6. Model yang dipakai
    models = {}
    for r in evaluated:
        key = r["model"] or "(gagal)"
        models[key] = models.get(key, 0) + 1
    out("## Model yang dipakai\n")
    for m, c in sorted(models.items(), key=lambda x: -x[1]):
        out(f"- {m}: {c} dokumen")
    out("")

    out("## Catatan\n")
    if levels:
        out("- Set data ini adalah dokumen sintetis yang sengaja dirusak (dimiringkan, diburamkan, diberi noise dan bayangan).")
        out("- Ini masih simulasi kondisi nyata, bukan foto dokumen asli.")
    else:
        out("- Evaluasi ini memakai data dummy yang dibuat otomatis (bersih dan rapi), sehingga akurasi cenderung tinggi.")
        out("- Hasil pada dokumen nyata (miring, buram, format beragam) perlu diuji terpisah.")
    out("- Waktu manual adalah asumsi, bukan pengukuran.")

    report = "\n".join(lines)
    print(report)
    Path(report_path).write_text(report + "\n", encoding="utf-8")

    # Detail per dokumen untuk analisis error
    with open(details_path, "w", newline="", encoding="utf-8") as f:
        cols = ["filename", "difficulty", "status", "model", "seconds", "all_correct", "wrong_fields"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in evaluated:
            row = {c: r[c] for c in cols if c != "wrong_fields"}
            row["wrong_fields"] = ";".join(r["wrong_fields"])
            w.writerow(row)

    print(f"\n(Laporan disimpan di {report_path}, detail per dokumen di {details_path})")


if __name__ == "__main__":
    main()
