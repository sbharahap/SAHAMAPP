# Panduan Lengkap Arsitektur & Alur Kerja Sistem AI Saham Indonesia

Dokumen ini menjelaskan secara menyeluruh, terperinci, dan terstruktur mengenai arsitektur sistem **AI Saham Indonesia** dari hulu ke hilir. Panduan ini dirancang untuk mendokumentasikan seluruh modul backend, teknologi yang digunakan, teknik pengolahan data, perhitungan matematis scoring, hingga alur penalaran AI (*Agentic RAG*).

---

## 🏗️ 1. Gambaran Umum Arsitektur Sistem

Sistem AI Saham Indonesia terbagi menjadi dua bagian utama:
1. **Client (Frontend iOS SwiftUI)**: Antarmuka pengguna pada perangkat iPhone untuk melihat dashboard rekomendasi saham (Top 10), detail analisis emiten, visualisasi breakdown skor, riwayat notifikasi alert, serta melakukan chatting interaktif dengan asisten AI.
2. **FastAPI Server (Backend Python)**: Mesin utama yang menangani pengumpulan data (scraping), pemrosesan awal (preprocessing), penyimpanan database relasional dan vektor, serta orkestrasi chatbot cerdas menggunakan **LangGraph** dan model bahasa lokal **Qwen (Ollama)**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           iOS Client (SwiftUI)                          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (HTTP REST / SSE Stream)
┌────────────────────────────────────▼────────────────────────────────────┐
│                         FastAPI Server (Backend)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────┐   ┌───────────────────┐   ┌───────────────┐  │
│  │   Scraper & Cleaner   │   │   LangGraph Agent │   │  LlamaIndex   │  │
│  │  (Data Prep & Lexicon)│   │  (Scoring & Chat) │   │  (RAG Vector) │  │
│  └───────────┬───────────┘   └─────────┬─────────┘   └───────┬───────┘  │
│              │                         │                     │          │
└──────────────┼─────────────────────────┼─────────────────────┼──────────┘
               │ (Clean & Struct)        │ (Relational Read)   │ (Vector Search)
┌──────────────▼─────────────────────────▼─────────┐     ┌──────▼─────────┐
│               PostgreSQL (saham_db)              │     │    ChromaDB    │
│  (Saham, Fundamental, Makro, Berita, Scoring)   │     │  (Collections) │
└──────────────────────────────────────────────────┘     └────────────────┘
```

---

## 📡 2. Pipeline Pengumpulan & Preprocessing Data

Sistem memperbarui informasi pasar secara otomatis menggunakan teknik penarikan RSS feeds berkala dan API scraping.

### A. Pengumpulan Data (Scraping)
* **Google News RSS**: Digunakan untuk mencari berita spesifik per emiten (contoh query: `"saham BBCA"`, `"saham TLKM"`) serta berita pasar modal Indonesia secara umum.
* **Kontan RSS Feed**: Portal berita keuangan terkemuka di Indonesia, digunakan untuk menyerap kabar ekonomi makro dan bursa efek terbaru.
* **httpx (Asynchronous HTTP Client)**: Melakukan HTTP requests secara non-blocking dengan custom *User-Agent* agar tidak terblokir oleh mekanisme proteksi server.
* **feedparser**: Library Python untuk mengurai (parse) dokumen XML RSS menjadi objek struktur Python yang siap olah.
* **Request Delay**: Memberikan jeda waktu (`_REQUEST_DELAY_SECONDS = 2.0`) antar-request untuk meminimalkan beban pada server sumber dan menghindari pemblokiran IP.
* **Time Check**: Menyaring hanya berita dalam rentang waktu terdekat (misalnya 7 hari terakhir) berdasarkan tanggal publikasi yang di-parse menggunakan zona waktu WIB (UTC+7).

### B. Normalisasi Data Fundamental
Data fundamental yang ditarik dari Yahoo Finance (.JK ticker) atau IDX API seringkali memiliki format yang tidak seragam (menggunakan simbol Rp, tanda baca ribuan yang berbeda, atau nilai None/NaN). Fungsi `normalize_fundamental` melakukan normalisasi sebagai berikut:
1. **Pembersihan Simbol**: Menghapus string "Rp", "Rp.", serta simbol persen (`%`) atau mata uang lainnya menggunakan regular expression.
2. **Standardisasi Format Desimal**: Mendeteksi secara dinamis apakah string menggunakan format Indonesia (titik sebagai ribuan, koma sebagai desimal, misal `1.234.567,89`) atau format internasional (koma sebagai ribuan, titik sebagai desimal, misal `1,234,567.89`). Nilai ini kemudian dikonversi menjadi tipe data `Float` standar Python.
3. **Pembulatan & Casting**: Nilai volume dibulatkan menjadi integer (`BigInteger` pada database untuk menampung transaksi bernilai milyaran lembar saham), sedangkan rasio keuangan (ROE, EPS, PBV, DER, PER, Dividend Yield) dibulatkan menjadi 2 desimal. Data bersih ini kemudian disimpan ke dalam tabel `fundamental` di PostgreSQL.

### C. Pembersihan Teks Berita & Deteksi Bahasa
Teks berita mentah yang di-parse dari RSS melalui fungsi pembersihan teks:
1. **Hapus HTML Tags & Entities**: Menggunakan Regular Expression (`<[^>]+>`) untuk menghapus seluruh tag HTML, dan regex `&[a-zA-Z]+;|&#\d+;` untuk menghapus entitas karakter HTML (seperti `&amp;` atau `&nbsp;`).
2. **Normalisasi Whitespace**: Regex `\s+` mendeteksi baris baru (`\n`), tab, dan spasi ganda berturut-turut untuk digantikan dengan satu spasi tunggal yang bersih.
3. **Deteksi Bahasa (Stopwords-Based)**: Menggunakan frekuensi kata-kata umum Bahasa Indonesia (*stopwords* seperti: *dan, yang, di, dari, untuk, dengan, saham, harga, naik, laba, rupiah*). Jika persentase kata-kata tersebut dalam judul berita $\ge 15\%$, bahasa ditandai sebagai `"id"` (Indonesia), jika di bawah itu ditandai sebagai `"en"` (Inggris). Hal ini penting untuk memastikan model embedding memproses teks dengan konteks bahasa yang tepat.

---

## 💭 3. Analisis Sentimen Berbasis Kamus Kata (Lexicon-Based)

Sebelum data dianalisis lebih lanjut oleh LLM, backend menghitung sentimen secara cepat berbasis kamus kata (*heuristics*) menggunakan fungsi `hitung_sentimen_sederhana` di [data_cleaner.py](file:///Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/data/preprocessors/data_cleaner.py).

### A. Cakupan Analisis (Judul vs Isi Berita)
Pada arsitektur saat ini, analisis sentimen berbasis kamus kata dijalankan **hanya pada Judul Berita (Headline)**. 
* *Rasional Desain*: Judul berita portal finansial (seperti Kontan atau CNBC Indonesia) dirancang untuk meringkas peristiwa utama secara padat dan langsung ke poin inti (contoh: *"Laba Bersih BBRI Melonjak 15%"*). Menganalisis isi berita yang sangat panjang seringkali menurunkan akurasi metode kamus kata karena banyaknya kata-kata latar belakang atau iklan yang bisa dianggap negatif secara keliru ( noise kata), serta membutuhkan komputasi yang jauh lebih besar.

### B. Mekanisme Kamus Kata & Bobot
Sistem mendefinisikan kamus kata positif (`_KATA_POSITIF`) dan negatif (`_KATA_NEGATIF`) dengan bobot kekuatan tertentu:
* **Kata Positif**: *naik (1), menguat (1), melonjak (2), meroket (2), laba (1), untung (1), dividen (1), buyback (1), beli/buy (1), outperform (1)*.
* **Kata Negatif**: *turun (1), melemah (1), anjlok (2), jatuh (2), rugi (2), default/gagal bayar (2), fraud (2), PHK (2), jual/sell (1)*.

### C. Alur Kerja & Penanganan Modifikator
Untuk menghindari kesalahan pembacaan karena pembalikan makna kalimat, sistem menerapkan jendela deteksi (*window-based contexts*):
1. **Deteksi Bigram & Trigram**: Memeriksa kecocokan frasa multi-kata terlebih dahulu (seperti *"right issue"* atau *"gagal bayar"*) sebelum memproses kata tunggal.
2. **Kata Negasi (Negation Modifier)**: Memeriksa kata tepat sebelum kata kunci bersentimen. Jika ditemukan kata negasi (`_KATA_NEGASI` seperti *tidak, bukan, belum, tak, gagal*), nilai sentimen akan dibalik dengan kekuatan $0.7$ (misal: *"tidak naik"* dikonversi menjadi nilai sentimen negatif).
3. **Kata Penguat (Intensifier Modifier)**: Memeriksa apakah ada kata penguat (`_KATA_PENGUAT` seperti *sangat, amat, signifikan, tajam, drastis, jumbo*) dalam radius $\pm 2$ kata dari kata kunci. Jika ada, bobot kata tersebut dikalikan dengan multiplier $1.5$ (contoh: *"laba naik tajam"* mendapat skor positif yang lebih tinggi).
4. **Normalisasi Tanh-like Scaling**: Skor total dihitung dengan membagi selisih skor positif dan negatif dengan jumlah total kecocokan kata:
   $$\text{Skor Normal} = \frac{\text{Skor Positif} - \text{Skor Negatif}}{\max(\text{Skor Positif} + \text{Skor Negatif}, 1.0)}$$
   Hasil akhirnya dipastikan berada pada rentang absolut **`[-1.0, 1.0]`** (sangat negatif hingga sangat positif, dengan 0.0 sebagai netral).

---

## ✂️ 4. Penyimpanan Database & RAG Embedding Pipeline

Aplikasi memisahkan penyimpanan data menjadi data relasional terstruktur (PostgreSQL) dan data vektor tidak terstruktur (ChromaDB) demi efisiensi pencarian semantik.

```
[Clean Text Chunk] ➔ [BGE-M3 Encoder] ➔ [1024-Dim Vector] ➔ [ChromaDB upsert()]
                                                                   ▲
[Metadata Serialization] ──────────────────────────────────────────┘
```

### A. Database Relasional: PostgreSQL
Menyimpan seluruh data transaksional dan metrik numerik terstruktur:
* **`saham`**: Master data emiten (Kode emiten, nama perusahaan, sektor, sub-sektor).
* **`fundamental`**: Metrik keuangan harian (ROE, EPS, PBV, DER, PER, Market Cap, Dividend Yield, Harga Terakhir).
* **`makro`**: Indikator makroekonomi (BI Rate, Inflasi YoY, Kurs USD/IDR, Nilai IHSG).
* **`berita`**: Metadata berita (Judul, URL, sumber, tanggal rilis, skor sentimen, status embedding).
* **`scoring_mingguan`**: Hasil scoring mingguan terhitung (Total skor 0-100, skor per komponen, label BUY/HOLD/SELL, dan alasan analisis tertulis dari AI).

### B. Database Vektor: ChromaDB
Menggunakan 3 *Collections* terpisah (`berita`, `laporan_keuangan`, dan `data_makro`) yang berjalan secara lokal untuk melayani pencarian semantik (RAG).

### C. Alur Pemotongan Teks (Chunking)
Sistem memotong dokumen teks panjang menggunakan **`SentenceSplitter`** dari **LlamaIndex**:
* **Chunk Size**: Diatur maksimum **`512 token`** per potongan.
* **Chunk Overlap**: Diatur sebesar **`64 token`** di ujung potongan. Overlap ini berfungsi agar konteks informasi antar potongan yang bersebelahan tidak terputus secara kasar.
* *SentenceSplitter* memotong teks tepat pada batas kalimat (tanda titik atau tanda tanya) alih-alih memotong di tengah kata secara acak, sehingga makna bahasa tetap terjaga dengan baik.

### D. Model Embedding & Penyimpanan
1. **Model BGE-M3**: Menggunakan model open-source lokal **`BAAI/bge-m3`** untuk mengubah chunk teks menjadi representasi vektor berdimensi **1024**. Model ini di-load sekali di memori sebagai *Singleton* untuk efisiensi RAM.
2. **Deduplikasi via SHA-256 Fingerprint**: Untuk mencegah penyimpanan potongan teks yang sama berulang kali di database vektor, sistem membuat **Doc ID** berbasis hash **SHA-256** dari kombinasi:
   ```
   Doc ID = SHA-256(kode_saham + sumber + tanggal + url + 200_karakter_pertama_teks)
   ```
   Hash ini kemudian dipotong menjadi 16 karakter awal.
3. **Serialisasi & Upsert**: Metadata diserialisasi ke format primitif yang diterima ChromaDB. Vektor embedding, teks dokumen asli (chunk), dan metadata disimpan ke ChromaDB menggunakan metode `collection.upsert()`. Jika Doc ID sudah ada di DB, ChromaDB akan menimpa data lama untuk menghindari redundansi data.

---

## 📈 5. Orkestrasi Scoring Agent (LangGraph)

Setiap Senin pagi pukul 06:00 WIB, scheduler memicu **Scoring Agent** yang diorkestrasi menggunakan **LangGraph StateGraph** untuk menilai seluruh emiten dalam daftar pantau dan merumuskan Top 10 rekomendasi saham mingguan.

```
    ┌──────────────────────────┐
    │          START           │
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │ 1. Analisis Kondisi Pasar│ ➔ Tentukan Bobot Adaptif berdasarkan Volatilitas & Lapkeu
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │      2. Hitung Skor      │ ➔ Hitung 5 komponen (Fund, Sent, Sekt, Makro, Riko) per Saham
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │      3. Self-Check       │ ➔ Cek Kelengkapan Data & Tandai Data Terbatas
    └────────────┬─────────────┘
                 │ (lanjut)
    ┌────────────▼─────────────┐
    │    4. Generate Alasan    │ ➔ LlamaIndex Retrieve Context + Panggil Qwen via Ollama
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────┐
    │           END            │
    └──────────────────────────┘
```

### Node 1: Analisis Kondisi Pasar & Penentuan Bobot Adaptif
Agent membaca indikator makroekonomi terbaru dari database PostgreSQL.
1. **Deteksi Volatilitas**: Volatilitas pasar dinilai tinggi jika Kurs USD/IDR bergerak $>2.0\%$ (Rupiah melemah/menguat tajam) atau nilai IHSG turun $>3.0\%$ dalam seminggu terakhir.
2. **Deteksi Rilis Laporan Keuangan (Earnings Season)**: Mengabaikan noise, sistem mencari berita dalam 7 hari terakhir yang judulnya mengandung kata kunci laporan keuangan (*"laporan keuangan"*, *"laba bersih"*, *"earnings"*, *"kuartal"*). Jika terdeteksi $\ge 3$ berita terkait, pasar dinilai sedang berada di musim rilis laporan keuangan.
3. **Penentuan Bobot Adaptif**:
   * **Musim Laporan Keuangan**: Bobot fundamental ditingkatkan menjadi **$40\%$** karena kinerja laba nyata emiten menjadi penggerak utama pasar (Fundamental: 40%, Sentimen: 20%, Sektor: 15%, Makro: 15%, Risiko: 10%).
   * **Volatilitas Tinggi (Bearish/Krisis)**: Bobot makroekonomi ditingkatkan menjadi **$30\%$** dan bobot risiko ditingkatkan menjadi **$15\%$** untuk memprioritaskan keamanan portofolio (Fundamental: 20%, Sentimen: 20%, Sektor: 15%, Makro: 30%, Risiko: 15%).
   * **Kondisi Normal**: Menggunakan bobot default terkonfigurasi (Fundamental: 30%, Sentimen: 25%, Sektor: 20%, Makro: 15%, Risiko: 10%).

### Node 2: Perhitungan Skor per Komponen (Kuantitatif 0-100)
Untuk setiap saham, sistem mengalkulasi skor pada 5 pilar komponen utama:
1. **Skor Fundamental**: Diestimasi dari rasio keuangan terstruktur (ROE, EPS, PBV, DER) yang disimpan di PostgreSQL menggunakan aturan klasifikasi poin (lihat Bab 2 Bagian A). Skor akhir dinormalisasi ke skala 0-100 berdasarkan jumlah metrik rasio yang tersedia.
2. **Skor Sentimen**: Rata-rata skor sentimen berita 7 hari terakhir yang ditarik dari PostgreSQL. Skor rata-rata $[-1.0, 1.0]$ dikonversi menjadi $[0.0, 100.0]$. Jika tidak ada berita, diset netral (50.0).
3. **Skor Sektor**: Membandingkan perubahan mingguan sektor industri emiten terhadap perubahan indeks IHSG. Jika sektor mengungguli (*outperform*) IHSG $\ge +5\%$, skor bernilai 100. Jika tertinggal (*underperform*) $\le -5\%$, skor bernilai 0. Jika sama, bernilai 50.
4. **Skor Makro**: Mengukur dampak kondisi ekonomi makro (BI Rate, inflasi YoY, pergerakan Rupiah, IHSG) terhadap bisnis emiten. Sektor perbankan dan properti memiliki penyesuaian khusus (sensitivitas tinggi terhadap tingkat suku bunga).
5. **Skor Risiko**: Skor tinggi menunjukkan risiko RENDAH (aman). Nilai dimulai dari asumsi dasar 80.0, lalu dikurangi jika tingkat utang terlalu tinggi (DER $>1.5$), volume transaksi harian terlalu kecil (saham tidak likuid), atau terdapat berita sangat negatif ($< -0.7$).
*Kalkulasi Akhir: Skor Total = $\sum (\text{Skor Komponen} \times \text{Bobot Adaptif})$*

### Node 3: Self-Check Kelengkapan Data
Sistem mengevaluasi kualitas data masukan untuk setiap saham:
* **Kriteria Data Lengkap**: Data fundamental tersedia (minimal ROE & PBV), memiliki minimal 2 berita dengan sentimen terhitung, dan nilai keyakinan data (*confidence score*) $\ge 0.3$.
* **Penanganan Data Terbatas**: Saham yang tidak memenuhi kriteria di atas akan ditandai dengan flag `data_terbatas = True` beserta catatan masalahnya (misal: *"data fundamental tidak tersedia; berita kurang"*).
* *Rasional Mengapa Proses Tetap Dilanjutkan*: Di bursa saham riil, emiten berkapitalisasi kecil (*second/third liner*) atau yang baru saja IPO seringkali tidak memiliki cakupan liputan media yang luas (berita kurang dari 2) atau data rasio keuangan historis yang lengkap. Jika sistem menolak memproses saham yang kekurangan data, pengguna akan kehilangan peluang investasi pada saham-saham potensial baru tersebut. Dengan tetap melanjutkan proses (namun menandai datanya terbatas dan menurunkan confidence score-nya), sistem bersikap transparan kepada pengguna sembari tetap menyajikan hasil scoring yang adil.

### Node 4: Generasi Alasan & Integrasi Model AI
1. **Retrieval Konteks Latar Belakang (LlamaIndex)**: Untuk 10 saham teratas dengan skor tertinggi, sistem memanggil fungsi `retrieve_context_for_scoring` dari LlamaIndex untuk melakukan query ke database vektor ChromaDB guna menarik 3 berita terpenting dan 2 kutipan laporan keuangan terbaru yang relevan.
2. **Prompts Engineering ke Qwen**: Menyusun prompt terstruktur yang menggabungkan:
   * Skor total dan skor per komponen emiten.
   * Rasio keuangan kuantitatif (ROE, EPS, PBV, DER, PER, Dividend Yield).
   * Konteks teks berita dan laporan keuangan hasil retrieval LlamaIndex.
   * Catatan kelengkapan data (jika datanya terbatas).
3. **Pemanggilan Model**: Prompt dikirimkan ke model **Qwen** via **Ollama**. Qwen membaca data tersebut, menyusun analisis setebal 3-4 kalimat Bahasa Indonesia yang merangkum faktor positif utama dan risiko utama, serta memberikan keputusan akhir (BUY, HOLD, atau SELL).
4. **Penyimpanan**: Hasil analisis tertulis dan label rekomendasi di-parse oleh regex, lalu disimpan ke tabel `scoring_mingguan` di PostgreSQL agar dapat diakses oleh client iOS.

---

## 💬 6. Orkestrasi Chatbot Agent (LangGraph)

Saat pengguna mengajukan pertanyaan di dalam menu asisten AI, backend FastAPI menyalurkan request ke **Chatbot Agent** yang diorkestrasi melalui LangGraph StateGraph.

### Node 1: Klasifikasi Pertanyaan & Ekstraksi Saham (Hybrid Method)
Proses klasifikasi pertanyaan tidak menggunakan LlamaIndex, melainkan menggunakan metode gabungan (*hybrid*):
1. **Rule-Based (Regex & Kamus)**: Mengidentifikasi kode emiten 4 huruf kapital (Regex: `\b[A-Z]{4}\b`) atau mendeteksi nama alias populer dari kamus internal `_ALIAS_SAHAM` (contoh: kata *"BCA"* atau *"bank bca"* dipetakan ke kode *"BBCA"*).
2. **Zero-Shot Classifier (Ollama)**: Jika pencarian teks gagal menemukan emiten, pertanyaan dikirim ke model **Qwen** dengan instruksi sistem yang ketat untuk mengembalikan satu kata kategori saja:
   * `spesifik`: membahas tentang kinerja satu saham tertentu.
   * `perbandingan`: membandingkan performa antara dua saham atau lebih.
   * `umum`: bertanya mengenai kondisi pasar modal, ekonomi makro, atau daftar rekomendasi Top 10.
   * `ambigu`: pertanyaan di luar konteks saham atau tidak jelas maksudnya. Jika ambigu, asisten langsung merespons dengan meminta klarifikasi.

### Node 2: Ambil Konteks & Cosine Similarity
1. **Database Vektor (ChromaDB)**: Query pencarian pengguna diubah menjadi vektor 1024-dimensi oleh model BGE-M3. Vektor query ini digunakan untuk mencari data di ChromaDB.
2. **Cosine Similarity**: ChromaDB secara native menghitung jarak sudut (*cosine similarity*) antara vektor query dengan seluruh vektor chunk dokumen di dalam collection terkait. Metrik jarak tersebut dikonversi ke persentase kecocokan:
   $$\text{Relevansi} = 1.0 - \text{Cosine Distance}$$
   Sistem menyaring 5 dokumen teratas dengan kecocokan tertinggi untuk dijadikan sebagai konteks jawaban.
3. **Database Relasional (PostgreSQL)**: Secara paralel, jika pertanyaan mendeteksi adanya kode saham, sistem melakukan query ke PostgreSQL untuk mengambil rasio fundamental terbaru serta skor mingguan terhitung emiten tersebut. Jika pertanyaan mendeteksi permintaan rekomendasi mingguan/top 10 secara umum, sistem secara otomatis melakukan query ke PostgreSQL untuk menarik data 10 saham dengan skor tertinggi pada minggu tersebut.

### Node 3: Generasi Jawaban & Pengelolaan Riwayat Obrolan
* **Pengelolaan Riwayat (Chat Memory)**: Asisten tidak melakukan chunking atau embedding pada riwayat obrolan atau pertanyaan pengguna saat ini. Riwayat percakapan (maksimal 6 pesan sebelumnya) disimpan dan disusun sebagai untaian teks terstruktur dalam format:
  ```
  User: [Pertanyaan sebelumnya]
  Asisten: [Jawaban asisten sebelumnya]
  ```
* **Prompt Assembly**: Riwayat obrolan tersebut, bersama dengan data kuantitatif dari PostgreSQL (atau data Top 10), dan 5 dokumen teks pendukung dari ChromaDB dimasukkan langsung sebagai teks string ke dalam Prompt Context LLM.
* **Inference**: Seluruh prompt dikirim ke jendela konteks model Qwen. Model membaca seluruh informasi yang disediakan dan men-generate jawaban yang faktual tanpa berhalusinasi, diakhiri dengan tag tingkat keyakinan (contoh: `[CONFIDENCE: 0.90]`).

---

## 📱 7. Modul Alert & Monitoring Agent

Modul ini ([alert_agent.py](file:///Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/agents/alert_agent.py)) berfungsi sebagai pengawas pasar (*market watchdog*) untuk mendeteksi perubahan sentimen secara mendadak.

1. **Deteksi Pergeseran Sentimen**: Setiap kali batch berita baru selesai ditarik (tiap 30 menit), sistem menghitung rata-rata skor sentimen berita terbaru per emiten. Skor rata-rata baru ini dibandingkan dengan rata-rata skor sentimen historis emiten tersebut di database PostgreSQL.
2. **Perhitungan Selisih Poin (Delta)**: Selisih perubahan dihitung menggunakan persamaan matematika sederhana:
   $$\Delta_{\text{Sentimen}} = \text{Sentimen Batch Baru} - \text{Sentimen Historis}$$
3. **Pemicu Peringatan (Alert Trigger)**: Jika nilai absolut delta sentimen melebihi ambang batas ($\ge 0.5$ poin perubahan pada skala $[-1, 1]$), peristiwa ini diidentifikasi sebagai lonjakan sentimen ekstrim (misalnya, kemunculan berita skandal keuangan yang menyebabkan sentimen jatuh dari $+0.2$ menjadi $-0.6$, delta $= -0.8$).
4. **Notifikasi ke iPhone**: Sistem mencatat peristiwa ini ke dalam database relasional tabel `alert`, kemudian mengirimkan HTTP POST payload ke `/api/alerts/push` yang menyimulasikan pengiriman push notification langsung ke perangkat iPhone pengguna sehingga investor dapat mengambil keputusan preventif dengan cepat.

---

## 🧪 8. Evaluasi & Validasi Model vs Performa Pasar Real

Untuk menjamin bahwa rekomendasi investasi yang dihasilkan oleh model AI bernilai akurat dan tidak menyesatkan, sistem menerapkan modul evaluasi kinerja berbasis **Metode Backtesting & Real-Price Comparison**:

```
[Senin: AI Rekomendasi Top 10] ➔ Simpan Baseline Harga (T+0)
                                        │
                                        ▼ (Tunggu 1 / 4 / 12 Minggu)
[Evaluasi: Tarik Harga Nyata Terbaru] ➔ Hitung Return & Bandingkan vs IHSG
```

1. **Perekaman Baseline Price (T+0)**: Setiap kali proses scoring mingguan selesai pada hari Senin pagi, sistem merekam daftar Top 10 saham yang direkomendasikan beserta harga penutupan pasar saham ril (*real close price*) pada hari tersebut di database PostgreSQL sebagai harga dasar (*baseline price*).
2. **Pencocokan Data Pasar Nyata ($T+N$)**: Setelah rentang waktu evaluasi tercapai (misalnya $T+1$ minggu, $T+4$ minggu, atau $T+12$ minggu), sistem secara otomatis menarik data harga penutupan nyata terbaru emiten terkait dari database (yang selalu diperbarui harian dari Yahoo Finance).
3. **Perhitungan Return Nyata**: Persentase keuntungan atau kerugian riil dihitung untuk masing-masing saham menggunakan rumus:
   $$\text{Return Real} = \frac{\text{Harga Penutupan Nyata } (T+N) - \text{Harga Baseline } (T+0)}{\text{Harga Baseline } (T+0)} \times 100\%$$
4. **Metrik Evaluasi Benar/Salah**:
   * **True Positive (Akurasi Rekomendasi)**: Jika AI melabeli emiten dengan status `BUY`, dan pada periode evaluasi harga saham emiten tersebut naik secara nyata (atau minimal persentase kenaikannya melampaui persentase pergerakan IHSG), maka analisis AI diklasifikasikan sebagai **Benar (True Positive)**.
   * **False Positive**: Jika AI melabeli emiten dengan status `BUY`, namun harga sahamnya justru turun secara signifikan dibanding IHSG, analisis diklasifikasikan sebagai **Salah (False Positive)**.
   * **Portofolio Alpha vs IHSG**: Menggabungkan ke-10 rekomendasi saham AI menjadi satu portofolio terbobot imajiner, menghitung rata-rata return portofolio tersebut, dan membandingkannya secara langsung dengan persentase pergerakan indeks IHSG pada periode yang sama. Jika return portofolio AI lebih tinggi dari return IHSG, model dinyatakan berhasil menghasilkan **Alpha (Outperform)**.
5. **Penyempurnaan Bobot**: Hasil evaluasi historis ini dapat digunakan oleh developer untuk melakukan kalibrasi bobot parameter scoring kuantitatif di masa mendatang agar semakin presisi mengikuti karakteristik pasar modal Indonesia.
