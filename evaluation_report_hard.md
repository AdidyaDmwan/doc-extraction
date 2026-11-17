# Laporan Evaluasi (hard)

Dokumen dievaluasi: **40** dari 40 di ground truth

## Akurasi per field

| Field | Benar | Akurasi |
|---|---|---|
| vendor_name | 40/40 | 100.0% |
| invoice_number | 39/40 | 97.5% |
| invoice_date | 39/40 | 97.5% |
| currency | 40/40 | 100.0% |
| subtotal | 40/40 | 100.0% |
| tax | 40/40 | 100.0% |
| total | 40/40 | 100.0% |
| num_items | 40/40 | 100.0% |

Dokumen dengan **semua field benar**: 38/40 (95.0%)

## Efektivitas routing (human-in-the-loop)

| Metrik | Hasil |
|---|---|
| Disetujui otomatis | 39/40 (97.5%) |
| Akurasi pada yang disetujui otomatis | 37/39 (94.9%) |
| Salah tapi lolos otomatis (paling berbahaya) | 2 |
| Dikirim ke review manusia | 1/40 (2.5%) |
| ...dari itu yang memang salah | 0 |
| ...dari itu yang sebenarnya benar (review tidak perlu) | 1 |

Dokumen salah yang lolos otomatis:
- hard_invoice_009.jpg: salah pada invoice_date
- hard_invoice_030.jpg: salah pada invoice_number

## Hasil per tingkat kesulitan

| Tingkat | Dokumen | Semua field benar | Disetujui otomatis | Salah tapi lolos otomatis |
|---|---|---|---|---|
| ringan | 14 | 14/14 (100.0%) | 14/14 (100.0%) | 0 |
| sedang | 13 | 13/13 (100.0%) | 13/13 (100.0%) | 0 |
| berat | 13 | 11/13 (84.6%) | 12/13 (92.3%) | 2 |

## Dokumen yang salah (untuk analisis error)

- hard_invoice_009.jpg [berat]: status auto_approved, salah pada invoice_date
- hard_invoice_030.jpg [berat]: status auto_approved, salah pada invoice_number

## Waktu pemrosesan

| Metrik | Hasil |
|---|---|
| Median | 4.0 dtk |
| P90 | 11.4 dtk |
| Rata-rata | 7.2 dtk |
| Tercepat / terlama | 2.1 / 55.2 dtk |
| Asumsi waktu manual | 240 dtk (asumsi, bukan hasil pengukuran) |
| Perbandingan terhadap asumsi manual | sekitar 59x lebih cepat (median) |

## Model yang dipakai

- gemini-3.5-flash-lite: 40 dokumen

## Catatan

- Set data ini adalah dokumen sintetis yang sengaja dirusak (dimiringkan, diburamkan, diberi noise dan bayangan).
- Ini masih simulasi kondisi nyata, bukan foto dokumen asli.
- Waktu manual adalah asumsi, bukan pengukuran.
