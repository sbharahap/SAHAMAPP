# 🗺️ Rencana & Status Pengembangan Sistem Saham AI

Dokumen ini mencakup peta jalan (*roadmap*) fitur hasil simulasi backtesting 3 tahun (2022–2025). Dokumen ini membagi fitur yang telah aktif di sistem saat ini dan fitur yang disimpan untuk pengembangan lanjutan di masa depan.

---

## ✅ 1. Fitur yang Telah Diimplementasikan (Sistem Saat Ini)

Berikut adalah penyempurnaan sistem scoring engine yang telah berhasil diimplementasikan agar sepenuhnya berbasis data dinamis (tidak lagi menggunakan batasan/threshold kaku/statis):

### 1️⃣ Relative PBV, Relative PE, & Relative ROE (Valuasi & Profitabilitas Sektoral Historis)
* **Konsep:** Valuasi (PE, PBV) dan profitabilitas (ROE) emiten dinilai secara dinamis berdasarkan posisi relatif terhadap rentang historis kuartil sektor industrinya selama 3 tahun terakhir (25th percentile, Median, dan 75th percentile).
* **Penerapan:**
  * Skor Maksimal (20 Poin): Valuasi berada di bawah Q25 sektor (terdiskon/undervalued), atau ROE berada di atas Q75 sektor (sangat menguntungkan).
  * Skor Menengah (12-16 Poin): Metrik berada di dekat median historis sektor.
  * Skor Minimal (4 Poin): Valuasi terlalu mahal (> Q75 sektor) atau ROE di bawah Q25 sektor.

### 2️⃣ Relative EPS (Earnings Per Share Emiten Historis)
* **Konsep:** Menghapus perbandingan nominal EPS antar emiten yang tidak adil (karena perbedaan jumlah saham beredar). EPS sekarang dinilai terhadap historis nominal emiten itu sendiri.
* **Penerapan:** Skor dinilai secara dinamis berdasarkan kuartil historis 3 tahun emiten sendiri (q25, median, q75).

### 3️⃣ DER Adaptif Sektoral (Leverage Risk)
* **Konsep:** Mengakhiri batas kaku DER absolut. Rasio utang emiten dinilai secara adil terhadap historis sektornya sendiri. 
* **Penerapan:** Sektor finansial (perbankan) yang secara alami memiliki leverage tinggi tidak lagi terkena penalti DER secara semena-mena, sementara sektor rendah utang seperti Healthcare diawasi secara ketat terhadap batas deviasi historisnya.

### 4️⃣ Batas Tren Laba Laba Kuartal (Dynamic QoQ Growth Modifier)
* **Konsep:** Memberikan bonus (+15 poin) atau penalti (-15 poin) pada skor fundamental secara dinamis berdasarkan pencapaian pertumbuhan kuartalan (QoQ) terhadap kuartil pertumbuhan aktif (non-zero) di sektornya masing-masing.

### 5️⃣ Skor Makroekonomi Dinamis (BI Rate, Inflasi, & Kurs)
* **Konsep:** Menghilangkan batasan suku bunga dan inflasi statis. Indikator makro terbaru dievaluasi secara dinamis terhadap rentang historis (q25, median, q75) dari data makro yang terekam di database.
* **Penerapan:** 
  * BI Rate dinilai positif jika berada di bawah median historis database.
  * Inflasi dinilai ideal jika terkendali di sekitar rentang historis (q25 hingga q75).
  * Pelemahan Rupiah jangka panjang dihitung jika Kurs USD/IDR menyimpang > 5% di atas median historis database.

### 6️⃣ Risiko Likuiditas & Sentimen Negatif Dinamis (Skor Risiko & Outlier Sentimen)
* **Konsep:** 
  * **Likuiditas:** Menghapus batas volume statis (seperti 100k/500k lot). Volume transaksi harian kini dibandingkan secara dinamis terhadap median volume historis 3 tahun emiten itu sendiri.
  * **Sentimen:** Batasan berita sangat negatif (`ada_berita_negatif_besar`) ditentukan secara dinamis berdasarkan batas 10th percentile (q10) sentimen historis emiten tersebut, alih-alih nilai kaku -0.7.

### 7️⃣ Indikator Teknikal SMA50 + RSI14
* **Konsep:** Menggabungkan tren harga jangka menengah (SMA50) dengan momentum jenuh beli/jenuh jual (RSI14) secara *live* menggunakan data dari Yahoo Finance.
* **Penerapan:** Disinergikan ke dalam Skor Risiko sebagai modifier keamanan teknikal (+25 poin untuk momentum sehat, penalti hingga -20 poin untuk jenuh jual/oversold ekstrem).

### 8️⃣ Normalisasi USD-Reporting
* **Konsep:** Mengatasi *currency mismatch* untuk emiten yang melaporkan keuangan dalam USD (seperti BYAN, ADRO, MEDC). Sistem mendeteksi otomatis dan menggunakan PE/PBV native dari Yahoo Finance yang sudah terkonversi secara akurat.

---

## ⏳ 2. Fitur untuk Pengembangan Lanjutan di Masa Depan

Dua fitur berikut disimpan untuk diaktifkan apabila Anda ingin mengembangkan sistem ini menjadi sistem **Manajemen Portofolio/Eksekusi Akun Trading Riil** (bukan hanya daftar urutan 20 rekomendasi murni):

### 1️⃣ Sector Cap (Batas Sektoral Portofolio)
* **Konsep:** Membatasi kepemilikan maksimal **2 saham per sektor** di dalam portofolio terpilih.
* **Mengapa ditunda:** Pada scope ranking mingguan statis saat ini, kita ingin melihat urutan murni 20 saham tanpa memanipulasi posisi peringkat asli akibat batas sektor.

### 2️⃣ Holding Buffer (Peredam Transaksi / Over-Trading)
* **Konsep:** Menerapkan toleransi peringkat (misal: peringkat toleransi = 8). Saham yang saat ini dimiliki tidak akan dijual/diganti kecuali peringkat skor mingguan barunya jatuh di bawah peringkat 8.
* **Mengapa ditunda:** Pada scope rekomendasi mingguan statis saat ini, peringkat murni harus selalu di-update berdasarkan data terbaru tanpa mempedulikan status kepemilikan masa lalu pengguna.
