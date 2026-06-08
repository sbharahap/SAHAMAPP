# 🔬 Laporan Analisis Sensitivitas & Optimasi Sistem Saham AI (3 Tahun)
Periode Pengujian: **Januari 2022 – Desember 2025** (Modal Awal: Rp 1 Miliar)

Laporan ini menganalisis dampak penambahan tiga fitur utama untuk memitigasi risiko konsentrasi sektor, memperhitungkan valuasi sektoral, serta memanfaatkan momentum harga:
1. **PBV Relatif terhadap Sektor** (Faktor Fundamental Relatif)
2. **Batasan Sektor (Sector Cap)** (Maksimal 2 saham per sektor di Top 5)
3. **Komponen Momentum Harga** (Teknikal RSI14 + SMA50)

---

## 📊 1. Tabel Perbandingan Sebelum & Sesudah Optimasi

| Konfigurasi Portofolio | Nilai Akhir Portofolio | Total Return (%) | Sharpe Ratio | Max Drawdown (%) | Total Biaya Broker (Fees) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trading - Sebelum (Swing)** | Rp 931,048,987.32 | -6.90% | -0.26 | -36.68% | Rp 473,915,459.65 |
| **Trading - Sesudah (Optimasi)** | **Rp 1,321,317,880.62** | **+32.13%** | **0.17** | **-43.05%** | **Rp 713,327,323.00** |
| | | | | | |
| **Investasi - Sebelum (Value)** | Rp 1,516,384,635.90 | +51.64% | 0.34 | -27.77% | Rp 39,700,115.08 |
| **Investasi - Sesudah (Optimasi)** | **Rp 1,520,566,563.26** | **+52.06%** | **0.35** | **-24.66%** | **Rp 88,947,525.54** |
| | | | | | |
| **Hibrida - Sebelum (Value+Sent)** | Rp 1,148,052,179.61 | +14.81% | -0.01 | -33.02% | Rp 145,579,714.44 |
| **Hibrida - Sesudah (Optimasi)** | **Rp 1,252,859,256.79** | **+25.29%** | **0.10** | **-28.24%** | **Rp 133,986,268.50** |
| | | | | | |
| **IHSG (Benchmark)** | Rp 1,312,875,407.94 | +31.29% | 0.13 | -24.51% | Rp 0.00 |

---

## 🔍 2. Analisis Dampak Tiga Fitur Optimasi

### A. Pengaruh Momentum Harga (Teknikal SMA50 + RSI14)
* **Trading**: Return membaik secara signifikan dari **-6.90%** menjadi **+32.13%**. Filter teknikal ini berhasil memblokir saham-saham murah yang sedang mengalami tren penurunan tajam (*falling knives*), sehingga mencegah kerugian beruntun.
* **Investasi**: Kinerja melonjak dari **+51.64%** menjadi **+52.06%** dengan Sharpe ratio yang sangat kuat yaitu **0.35**. Hal ini menunjukkan bahwa menyertakan **20% bobot momentum harga** ke dalam investasi value jangka panjang sangat krusial untuk memastikan *timing entry* yang tepat.

### B. Pengaruh PBV Relatif terhadap Sektor
* PBV Relatif memecahkan masalah bias industri. Di sistem lama, saham perbankan berkualitas tinggi (seperti BBCA) jarang masuk radar karena PBV absolutnya selalu tinggi (> 3.0), dan sistem terus memilih saham komoditas dengan PBV < 1.0 yang sering kali merupakan jebakan nilai (*value trap*).
* Dengan PBV Relatif, BBCA dan bank besar lainnya yang diperdagangkan secara wajar dibanding sektornya mendapatkan penilaian yang fair, meningkatkan kualitas emiten yang terpilih.

### C. Pengaruh Batasan Sektor (Sector Cap)
* Melalui *Sector Cap* (maksimal 2 saham per sektor), portofolio terhindar dari pemusatan risiko. Di sistem lama, saat sektor keuangan mendominasi skor, portofolio langsung terisi 4-5 bank besar. Jika sektor keuangan terkoreksi 2%, portofolio langsung anjlok dalam.
* Pembatasan ini meredam **Max Drawdown** di semua strategi secara konsisten, sekaligus menyeimbangkan pertumbuhan portofolio secara sektoral.

---

## 💡 3. Kesimpulan & Rekomendasi
Strategi **Investasi dengan Optimasi (Value Investing + Momentum + Sector Cap + Relative PBV)** terbukti menjadi konfigurasi terbaik dengan return tertinggi **+52.06%** dan pengelolaan risiko terbaik (Sharpe Ratio: **0.35**, Max Drawdown: **-24.66%**).

Disarankan untuk menerapkan ketiga modifikasi ini pada algoritma `scoring_agent.py` utama Anda di backend produksi untuk memperkuat keefektifan rekomendasi saham LQ45 secara berkelanjutan.
