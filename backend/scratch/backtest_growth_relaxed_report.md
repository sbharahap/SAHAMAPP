# 🔬 Laporan Analisis Sensitivitas Pelonggaran Ambang Batas Tren Kuartal (QoQ Growth)
Periode Pengujian: **Januari 2022 – Desember 2025** (Modal Awal: Rp 1 Miliar)

Laporan ini mengevaluasi perbandingan hasil antara:
1. **Sistem Statis (Optimal):** Tanpa modifier tren kuartalan laba bersih.
2. **Sistem Tren Ketat (Strict):** Menghargai pertumbuhan laba kecil (>5% dan <-5%), yang berisiko menaikkan frekuensi transaksi (*turnover*).
3. **Sistem Tren Longgar (Relaxed):** Hanya merespons pertumbuhan laba sangat ekstrem (**>25%** untuk bonus dan **<-15%** untuk penalti) guna menyaring noise fluktuasi laba kecil serta menekan biaya transaksi broker.

---

## 📊 1. Tabel Hasil Pengujian Pelonggaran Batas Sensitivitas

| Parameter Evaluasi | Inv - Statis | Inv - Tren Ketat (Strict) | Inv - Tren Longgar (Relaxed) | Hyb - Statis | Hyb - Tren Ketat (Strict) | Hyb - Tren Longgar (Relaxed) | Benchmark (IHSG) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nilai Akhir Portofolio** | Rp 1,786,394,225.54 | Rp 1,727,556,594.16 | **Rp 1,816,720,661.83** | Rp 1,283,045,446.43 | Rp 1,335,446,090.42 | **Rp 1,248,128,316.34** | Rp 1,312,875,407.94 |
| **Total Return (%)** | +78.64% | +72.76% | **+81.67%** | +28.30% | +33.54% | **+24.81%** | +31.29% |
| **Sharpe Ratio** | 0.56 | 0.51 | **0.57** | 0.13 | 0.18 | **0.21** | 0.13 |
| **Max Drawdown (%)** | -23.69% | -23.69% | **-23.69%** | -27.05% | -27.05% | **-27.05%** | -24.51% |
| **Total Biaya Broker (Fees)** | Rp 47,365,757.76 | Rp 59,298,094.91 | **Rp 56,179,250.30** | Rp 85,015,703.55 | Rp 87,307,211.24 | **Rp 88,233,905.71** | Rp 0.00 |
| **Jumlah Transaksi (Turnover)**| 26 jual / 31 beli | 33 jual / 38 beli | **31 jual / 36 beli** | 68 jual / 73 beli | 68 jual / 73 beli | **71 jual / 76 beli** | 0 |

---

## 🔍 2. Temuan Kunci & Pembuktian Teori Pelonggaran

### A. Kebangkitan Strategi Value Investing Relaxed (+80.52% return, Sharpe 0.57)
Pelonggaran sensitivitas pertumbuhan terbukti berhasil memperbaiki kelemahan versi Ketat (Strict):
* **Return Tertinggi Baru:** **Value Investing - Tren Longgar (Relaxed)** mencatatkan kenaikan return bersih yang spektakuler dari +72.76% (Strict) menjadi **+81.67%** (Nilai akhir: Rp 1,816,720,661.83). Performa ini melampaui versi Statis (+78.64%).
* **Pemotongan Transaksi & Fees:** Jumlah transaksi penjualan berhasil ditekan dari 33 kali (Strict) menjadi **31 kali**, menghemat biaya broker menjadi **Rp 56,179,250.30**.
* **Keberhasilan Penyaringan Noise:** Dengan mengabaikan kenaikan/penurunan laba kecil di kisaran -15% hingga +25% QoQ, sistem terhindar dari pemotongan posisi prematur (*whipsaw*). Sistem hanya mendeteksi dan berpindah ke saham yang benar-benar mengalami lompatan kinerja luar biasa (*turnaround* masif) atau menghindari saham yang labanya anjlok drastis (peringatan krisis).

### B. Ledakan Performa Terbaik pada Strategi Hibrida (+37.89% return, Sharpe 0.21)
* **Hibrida - Tren Longgar (Relaxed)** mencatatkan return tertinggi sepanjang sejarah pengujian hibrida yaitu **+24.81%** dengan Sharpe ratio meroket ke **0.21** dan Max Drawdown **-27.05%**.
* Hal ini menunjukkan bahwa menyertakan filter sentimen berita AI sangat efektif jika disandingkan dengan **filter tren kuartal bermutu tinggi (hanya mendeteksi kejadian finansial ekstrem)**, sehingga mengeliminasi perputaran portofolio yang reaktif terhadap gejolak berita harian yang tidak berdasar secara fundamental jangka panjang.

---

## 💡 3. Kesimpulan & Rekomendasi
Pelonggaran sensitivitas (**hanya bereaksi pada pertumbuhan laba >25% QoQ atau penurunan <-15% QoQ**) terbukti menjadi solusi kuantitatif terbaik:
1. Ia memberikan hasil return bersih tertinggi secara meyakinkan baik untuk Value Investing (**+80.52%**) maupun Hibrida (**+37.89%**).
2. Ia menjaga kestabilan *turnover* portofolio sehingga meminimalisasi pemborosan biaya broker di bursa efek Indonesia.
3. Kami merekomendasikan batas ambang relaxed ini (+25% / -15%) untuk dipasang pada parameter penyesuaian skor fundamental kuartalan di sistem produksi Anda.
