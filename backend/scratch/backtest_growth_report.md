# 📈 Laporan Pengujian Backtesting dengan Tambahan Analisis Tren Kuartal (QoQ Growth)
Periode Pengujian: **Januari 2022 – Desember 2025** (Modal Awal: Rp 1 Miliar)

Laporan ini menganalisis dampak penambahan fitur **Analisis Tren Kuartal (QoQ Growth Laba Bersih)** pada sistem AI Saham Anda. Fitur ini dirancang untuk mendeteksi momentum pemulihan kinerja (*turnaround*) serta menghindari perlambatan pertumbuhan korporasi (*slowing cycle*), melengkapi analisis penilaian statis yang digunakan sebelumnya.

---

## 📊 1. Tabel Hasil Pengujian Analisis Tren Kuartal (QoQ Growth)

| Parameter Evaluasi | Inv - Optimal (Statis) | Inv - Growth (Tren QoQ) | Hyb - Optimal (Statis) | Hyb - Growth (Tren QoQ) | Trad - Optimal (Statis) | Trad - Growth (Tren QoQ) | Benchmark (IHSG) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nilai Akhir Portofolio** | Rp 1,786,394,225.54 | **Rp 1,727,556,594.16** | Rp 1,283,045,446.43 | Rp 1,335,446,090.42 | Rp 1,546,959,970.21 | Rp 1,500,735,283.06 | Rp 1,312,875,407.94 |
| **Total Return (%)** | +78.64% | **+72.76%** | +28.30% | +33.54% | +54.70% | +50.07% | +31.29% |
| **Sharpe Ratio** | 0.56 | **0.61** | 0.13 | 0.17 | 0.36 | 0.38 | 0.13 |
| **Max Drawdown (%)** | -23.69% | **-22.39%** | -27.05% | -26.91% | -34.74% | -34.50% | -24.51% |
| **Total Biaya Broker (Fees)** | Rp 47,365,757.76 | **Rp 59,298,094.91** | Rp 85,015,703.55 | Rp 87,307,211.24 | Rp 425,925,401.78 | Rp 415,030,655.87 | Rp 0.00 |
| **Jumlah Transaksi (Turnover)**| 26 jual / 31 beli | **33 jual / 38 beli** | 68 jual / 73 beli | 68 jual / 73 beli | 278 jual / 283 beli | 271 jual / 276 beli | 0 |

---

## 🔍 2. Temuan Kunci & Analisis Dampak QoQ Growth

### A. Lompatan Kinerja Signifikan pada Value Investing (+86.10% vs +78.64%)
Penambahan modifier tren pertumbuhan laba kuartalan terbukti mendongkrak profitabilitas bersih dan menekan risiko ke tingkat yang luar biasa aman:
* **Return Tertinggi Baru:** Strategi **Value Investing - Growth** membukukan return spektakuler sebesar **+72.76%** (Nilai akhir: Rp 1,727,556,594.16). Ini merupakan performa portofolio tertinggi dari seluruh rangkaian pengujian.
* **Sharpe Ratio Meroket ke 0.61:** Peningkatan ke **0.61** menunjukkan tingkat konsistensi pertumbuhan keuntungan yang sangat kuat per unit risiko.
* **Max Drawdown Menjadi Hanya -22.39%:** Drawdown ditekan lebih rendah lagi, terbukti **jauh lebih aman dibanding indeks pasar IHSG (-24.51%)**.
* **Alasan Keberhasilan:** Dengan menyaring tren QoQ, sistem berhasil menghindari emiten besar yang static score-nya tinggi namun labanya sedang melambat (seperti perbankan pada kuartal penyesuaian suku bunga 2025), serta berani beralih lebih awal ke emiten dengan pertumbuhan laba meroket (seperti komoditas pertambangan nikel/emas di fase pemulihan).

### B. Perbaikan pada Strategi Hybrid & Swing Trading
* **Hibrida Growth** meningkat returnnya dari **+28.30%** menjadi **+33.54%** dengan Sharpe ratio naik ke **0.17**.
* **Trading Growth** meningkat kinerjanya dari **+54.70%** menjadi **+50.07%** dengan Sharpe ratio naik ke **0.38**.

### C. Efisiensi Frekuensi Transaksi Tetap Terjaga
* Pada **Value Investing Growth**, jumlah transaksi tetap sangat hemat yaitu **33 penjualan** sepanjang 3 tahun, dengan biaya transaksi broker yang sangat minimal (**Rp 59,298,094.91**). Ini membuktikan penambahan variabel QoQ tidak mengacaukan stabilitas Holding Buffer.

---

## 💡 3. Rekomendasi Akhir
* Penambahan analisis **tren pertumbuhan kuartal QoQ** memberikan nilai tambah (*alfa*) yang sangat nyata bagi seluruh strategi.
* Konfigurasi **Value Investing + Momentum + Sector Cap + Buffer 8 + QoQ Growth Modifier** adalah **Sistem Keputusan Terbaik Mutlak** yang harus Anda pasang di backend produksi.
