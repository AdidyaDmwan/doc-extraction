# Laporan Evaluasi

Dokumen dievaluasi: **40** dari 40 di ground truth

## Akurasi per field

| Field | Benar | Akurasi |
|---|---|---|
| vendor_name | 40/40 | 100.0% |
| invoice_number | 40/40 | 100.0% |
| invoice_date | 40/40 | 100.0% |
| currency | 40/40 | 100.0% |
| subtotal | 40/40 | 100.0% |
| tax | 40/40 | 100.0% |
| total | 40/40 | 100.0% |
| num_items | 40/40 | 100.0% |

Dokumen dengan **semua field benar**: 40/40 (100.0%)

## Efektivitas routing (human-in-the-loop)

| Metrik | Hasil |
|---|---|
| Disetujui otomatis | 40/40 (100.0%) |
| Akurasi pada yang disetujui otomatis | 40/40 (100.0%) |
| Salah tapi lolos otomatis (paling berbahaya) | 0 |
| Dikirim ke review manusia | 0/40 (0.0%) |
| ...dari itu yang memang salah | 0 |
| ...dari itu yang sebenarnya benar (review tidak perlu) | 0 |

## Kalibrasi confidence (apakah keyakinan AI bisa dipercaya?)

| Confidence | Dokumen | Semua field benar | Persentase benar |
|---|---|---|---|
| 1.00 | 40 | 40/40 | 100.0% |

Jika dokumen yang salah muncul di nilai confidence tinggi, angka itu tidak bisa menjadi satu-satunya dasar persetujuan otomatis.

## Waktu pemrosesan

| Metrik | Hasil |
|---|---|
| Median | 2.5 dtk |
| P90 | 11.3 dtk |
| Rata-rata | 8.9 dtk |
| Tercepat / terlama | 1.4 / 131.5 dtk |
| Asumsi waktu manual | 240 dtk (asumsi, bukan hasil pengukuran) |
| Perbandingan terhadap asumsi manual | sekitar 96x lebih cepat (median) |

## Model yang dipakai

- gemini-3.5-flash-lite: 39 dokumen
- gemini-3.1-flash-lite: 1 dokumen

## Catatan

- Evaluasi ini memakai data dummy yang dibuat otomatis (bersih dan rapi), sehingga akurasi cenderung tinggi.
- Hasil pada dokumen nyata (miring, buram, format beragam) perlu diuji terpisah.
- Yang dievaluasi: 8 field tingkat dokumen. Isi detail tiap item (deskripsi, harga satuan, jumlah) belum dibandingkan dengan ground truth.
- Waktu manual adalah asumsi, bukan pengukuran.
