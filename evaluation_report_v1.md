# Laporan Evaluasi

Dokumen dievaluasi: **40** dari 40 di ground truth

## Akurasi per field

| Field | Benar | Akurasi |
|---|---|---|
| vendor_name | 40/40 | 100.0% |
| invoice_number | 40/40 | 100.0% |
| invoice_date | 40/40 | 100.0% |
| currency | 39/40 | 97.5% |
| subtotal | 40/40 | 100.0% |
| tax | 40/40 | 100.0% |
| total | 40/40 | 100.0% |
| num_items | 40/40 | 100.0% |

Dokumen dengan **semua field benar**: 39/40 (97.5%)

## Efektivitas routing (human-in-the-loop)

| Metrik | Hasil |
|---|---|
| Disetujui otomatis | 40/40 (100.0%) |
| Akurasi pada yang disetujui otomatis | 39/40 (97.5%) |
| Salah tapi lolos otomatis (paling berbahaya) | 1 |
| Dikirim ke review manusia | 0/40 (0.0%) |
| ...dari itu yang memang salah | 0 |
| ...dari itu yang sebenarnya benar (review tidak perlu) | 0 |

Dokumen salah yang lolos otomatis:
- invoice_014.pdf: salah pada currency

## Waktu pemrosesan

| Metrik | Hasil |
|---|---|
| Median | 2.9 dtk |
| P90 | 17.3 dtk |
| Rata-rata | 6.5 dtk |
| Tercepat / terlama | 1.6 / 30.2 dtk |
| Asumsi waktu manual | 240 dtk (asumsi, bukan hasil pengukuran) |
| Perbandingan terhadap asumsi manual | sekitar 84x lebih cepat (median) |

## Model yang dipakai

- gemini-3.5-flash-lite: 40 dokumen

## Catatan

- Evaluasi ini memakai data dummy yang dibuat otomatis (bersih dan rapi), sehingga akurasi cenderung tinggi.
- Hasil pada dokumen nyata (miring, buram, format beragam) perlu diuji terpisah.
- Waktu manual adalah asumsi, bukan pengukuran.
