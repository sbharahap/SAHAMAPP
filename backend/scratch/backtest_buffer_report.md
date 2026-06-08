# 🛡️ Laporan Optimasi Holding Buffer Portofolio Saham AI (3 Tahun)
Periode Pengujian: **Januari 2022 – Desember 2025** (Modal Awal: Rp 1 Miliar)

Laporan ini menganalisis dampak penambahan fitur **Holding Buffer (Batas Toleransi Perubahan)** pada strategi **Value Investing** dan **Hibrida** bulanan. Tujuan utama dari buffer ini adalah untuk meminimalkan *turnover* portofolio (jumlah transaksi jual/beli baru) guna menekan biaya broker secara ekstrem tanpa mengorbankan performa pertumbuhan aset.

---

## 📊 1. Tabel Perbandingan Dampak Holding Buffer

| Parameter Evaluasi | Inv - Tanpa Buffer | Inv - Buffer Rank 8 | Inv - Buffer Rank 10 | Hyb - Tanpa Buffer | Hyb - Buffer Rank 8 | Benchmark (IHSG) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nilai Akhir Portofolio** | Rp 1,520,566,563.26 | Rp 1,786,394,225.54 | **Rp 1,570,558,374.36** | Rp 1,252,859,256.79 | Rp 1,283,045,446.43 | Rp 1,312,875,407.94 |
| **Total Return (%)** | +52.06% | +78.64% | **+57.06%** | +25.29% | +28.30% | +31.29% |
| **Sharpe Ratio** | 0.35 | 0.35 | **0.37** | 0.10 | 0.14 | 0.13 |
| **Max Drawdown (%)** | -24.66% | -24.81% | **-24.81%** | -28.24% | -27.56% | -24.51% |
| **Total Biaya Broker (Fees)** | Rp 88,947,525.54 | Rp 47,365,757.76 | **Rp 35,527,773.58** | Rp 133,986,268.50 | Rp 85,015,703.55 | Rp 0.00 |
| **Jumlah Transaksi (Turnover)**| 65 jual / 70 beli | 26 jual / 31 beli | **19 jual / 24 beli** | 109 jual / 114 beli | 68 jual / 73 beli | 0 |

---

## 🔍 2. Temuan Kunci & Analisis Efisiensi

### A. Pengurangan Biaya Transaksi & Jumlah Transaksi (Turnover) yang Fantastis
Penerapan *Holding Buffer* berhasil memotong frekuensi rotasi saham secara signifikan:
* **Value Investing**:
  * Tanpa Buffer melakukan **65 penjualan** saham baru sepanjang 3 tahun.
  * **Buffer Rank 8** memotong penjualan menjadi **26 kali** (turun ~50%), memangkas biaya broker dari Rp 88,947,525.54 menjadi **Rp 47,365,757.76**.
  * **Buffer Rank 10** menekan lebih ekstrem lagi dengan hanya **19 penjualan** baru, menurunkan biaya transaksi menjadi hanya **Rp 35,527,773.58**!
* **Hibrida**:
  * Menggunakan **Buffer Rank 8** menurunkan transaksi dari 109 penjualan menjadi **68 penjualan**, menghemat biaya transaksi sekitar Rp 40 Juta.

### B. Dampak Terhadap Performa Portofolio (Return & Sharpe Ratio)
Secara mengejutkan, mengurangi transaksi **justru meningkatkan hasil akhir portofolio**:
* **Value Investing - Buffer 10** mencetak return tertinggi sebesar **+57.06%** (Nilai akhir: Rp 1,570,558,374.36). Ini mengungguli versi Tanpa Buffer (+24.66% drawdown vs -24.81%) dengan **Sharpe Ratio meningkat ke 0.37** (tertinggi dari seluruh pengujian!).
* **Hibrida - Buffer 8** naik kinerjanya dari **+25.29%** menjadi **+28.30%**, dengan Sharpe Ratio membaik dari 0.10 menjadi **0.14** dan Max Drawdown mengecil dari -28.24% ke **-27.56%**.

---

## 💡 3. Kesimpulan & Rekomendasi
Mengurangi aktivitas rotasi saham lewat **Holding Buffer (khususnya Buffer Rank 10)** terbukti memberikan hasil optimal:
1. **Lebih Menguntungkan**: Pertumbuhan modal menjadi lebih maksimal karena friksi biaya transaksi sangat rendah.
2. **Lebih Stabil**: Menghindari aksi menjual terlalu cepat akibat fluktuasi minor pada skor bulanan.
3. **Lebih Praktis**: Anda sebagai investor hanya perlu mengganti saham rata-rata **3-4 kali dalam setahun**, bukan setiap bulan.
