# Panduan Lengkap Arsitektur & Alur Kerja Sistem AI Saham Indonesia

Dokumen ini menjelaskan secara rinci dan terstruktur mengenai arsitektur sistem **AI Saham Indonesia** dari hulu ke hilir. Panduan ini dirancang untuk membantu Anda memahami seluruh modul backend, teknologi yang digunakan, teknik pengolahan data, hingga alur penalaran AI (*Agentic RAG*).

---

## 🏗️ Gambaran Umum Arsitektur Sistem

Sistem ini terbagi menjadi dua bagian utama:
1. **Client (Frontend iOS SwiftUI)**: Antarmuka pengguna untuk melihat dashboard rekomendasi saham, detail analisis emiten, visualisasi breakdown skor, dan melakukan chatting interaktif dengan asisten AI.
2. **FastAPI Server (Backend Python)**: Mesin utama yang menangani pengumpulan data (scraping), pemrosesan awal (preprocessing), penyimpanan database relasional dan vektor, serta orkestrasi chatbot cerdas menggunakan **LangGraph** dan model bahasa lokal **Qwen2.5 3B (Ollama)**.

---

## 📡 1. Pipeline Pengumpulan Berita (*News Scraping*)

Sistem memperbarui informasi pasar secara otomatis menggunakan teknik penarikan RSS feeds berkala (setiap 30 menit).

### A. Sumber Data & Tools
* **Google News RSS**: Digunakan untuk mencari berita spesifik per emiten (contoh query: `"saham BBCA"`, `"saham TLKM"`) serta berita pasar modal Indonesia secara umum.
* **Kontan RSS Feed**: Portal berita keuangan terkemuka di Indonesia, digunakan untuk menyerap kabar ekonomi makro dan bursa efek terbaru.
* **httpx (Asynchronous HTTP Client)**: Melakukan HTTP requests secara non-blocking dengan custom *User-Agent* agar tidak terblokir oleh mekanisme proteksi server.
* **feedparser**: Library Python untuk mengurai (parse) dokumen XML RSS menjadi objek struktur Python yang siap olah.

### B. Mekanisme Rate Limiting & Pengamanan
* **Request Delay**: Memberikan jeda waktu (`_REQUEST_DELAY_SECONDS = 2.0`) antar-request untuk meminimalkan beban pada server sumber dan menghindari pemblokiran IP.
* **Time Check**: Menyaring hanya berita dalam rentang waktu terdekat (misalnya 3-7 hari terakhir) berdasarkan tanggal publikasi yang di-parse menggunakan zona waktu WIB (UTC+7).

---

## 🧹 2. Pembersihan & Pengolahan Awal (*Text Preprocessing & Cleaning*)

Setelah berita mentah didapatkan, teks melalui serangkaian tahap pembersihan sebelum disimpan:

```
[RSS Raw Data] ➔ [Hapus HTML & Entity] ➔ [Normalisasi Whitespace] ➔ [Deteksi Bahasa (ID/EN)] ➔ [Deduplikasi URL] ➔ [Sentimen Heuristic]
```

### A. Pembersihan Teks
1. **Hapus HTML Tags & Entities**: Menggunakan Regular Expression (`<[^>]+>`) untuk menghapus tag bold, italic, tabel, atau link sisa dari feed.
2. **Normalisasi Whitespace**: Mengganti tab, newline (`\n`), dan spasi ganda berturut-turut menjadi spasi tunggal yang bersih.
3. **Deteksi Bahasa**: Menggunakan frekuensi kata-kata umum Bahasa Indonesia (*stopwords* seperti: *dan, yang, di, untuk, saham, harga, naik*). Jika persentase kata-kata tersebut dalam judul berita $\ge 15\%$, bahasa ditandai sebagai `"id"`, jika tidak ditandai sebagai `"en"`.
4. **Deduplikasi URL**: Menghapus duplikat berita yang memiliki URL sama (misal Google News mengarahkan ke link Kontan yang sudah ditarik secara langsung).

### B. Analisis Sentimen Awal (*Rule-Based Heuristics*)
Sebelum data dianalisis lebih lanjut oleh LLM, backend menghitung sentimen secara cepat berbasis kamus kata (*dictionary matching*):
* **Kamus Kata Positif/Negatif**: Berisi kata berserta bobot kekuatannya (contoh positif: *laba (1)*, *meroket (2)*, *rebound (1)*; contoh negatif: *rugi (2)*, *anjlok (2)*, *koreksi (1)*).
* **Kata Negasi (Negation Modifier)**: Deteksi kata seperti *tidak*, *belum*, *bukan* di depan kata bersentimen untuk membalikkan maknanya (misal: `"tidak naik"` diubah menjadi sentimen negatif).
* **Kata Penguat (Intensifier Modifier)**: Kata seperti *sangat*, *drastis*, *masif* melipatgandakan bobot sentimen.
* **Skala Normalisasi**: Hasil skor mentah dinormalisasi menggunakan scaling mirip fungsi *tanh* ke dalam rentang **`[-1.0, 1.0]`** (sangat negatif hingga sangat positif).

---

## ✂️ 3. Pemotongan Teks & Penyimpanan Vektor (*Chunking & Embedding*)

Agar dokumen berita dan laporan keuangan dapat dicari oleh RAG secara efisien, dokumen yang panjang harus dipotong-potong menjadi bagian kecil (*chunking*) dan diubah menjadi representasi matematika (*embedding*).

### A. Metode Chunking (Sentence Splitter)
Sistem menggunakan **`SentenceSplitter`** dari **LlamaIndex**:
* **Chunk Size**: Diatur maksimum **`512 token`** per potongan.
* **Chunk Overlap**: Diatur sebesar **`64 token`** di ujung potongan. Overlap ini berfungsi agar konteks antar potongan tidak terputus secara kasar.
* *SentenceSplitter* secara cerdas memotong teks tepat pada batas kalimat (tanda titik) alih-alih memotong di tengah kata atau kalimat secara acak.

### B. Model Embedding (BGE-M3)
Untuk mengubah kata menjadi vektor angka, sistem menggunakan model open-source lokal **`BAAI/bge-m3`** (melalui library `SentenceTransformers`):
* Model ini dimuat ke memori server (menggunakan memori MPS/Metal GPU jika di Apple Silicon, atau CPU) sebagai *Singleton* agar tidak memakan RAM berulang kali.
* Menghasilkan representasi vektor berdimensi **1024**.
* Sangat andal untuk pengolahan multibahasa (*multilingual*), khususnya Bahasa Indonesia dan Bahasa Inggris dalam konteks finansial.

### C. Sidik Jari Dokumen & Deduplikasi Vektor
Untuk mencegah penyimpanan potongan teks yang sama berulang kali di database vektor, sistem membuat **Doc ID** berbasis hash **SHA-256** dari kombinasi:
```
Doc ID = SHA-256(kode_saham + sumber + tanggal + 200_karakter_pertama_teks)
```
Jika hash ini sudah ada di database, ChromaDB akan menimpanya (*Upsert*) untuk menghindari duplikasi data.

---

## 🗄️ 4. Infrastruktur Database

Sistem memisahkan penyimpanan data menjadi dua kategori utama demi performa pencarian yang optimal:

### A. Database Relasional: PostgreSQL
Digunakan untuk data transaksi dan data tabular terstruktur. Didefinisikan menggunakan ORM **SQLAlchemy** dengan tabel-tabel berikut:
1. **`saham`**: Master data emiten saham (Kode, nama perusahaan, sektor, sub-sektor).
2. **`fundamental`**: Laporan keuangan periodik emiten (ROE, EPS, PBV, DER, PER, Market Cap, Dividend Yield, Harga Saham Terakhir).
3. **`makro`**: Indikator makroekonomi (BI Rate, Inflasi YoY, Kurs USD/IDR, Nilai IHSG).
4. **`berita`**: Metadata berita (Judul, URL, sumber, tanggal rilis, skor sentimen awal, status embedding).
5. **`scoring_mingguan`**: Skor rekomendasi mingguan terhitung (Total skor 0-100, skor per komponen, label BUY/HOLD/SELL, dan alasan analisis tertulis dari AI).
6. **`alert`**: Log notifikasi peringatan fluktuasi sentimen tajam.

### B. Database Vektor: ChromaDB
Database vektor lokal berkecepatan tinggi, digunakan khusus untuk menyimpan representasi matematika (*embedding*) teks dokumen untuk pencarian semantik (RAG). Terdiri dari 3 *Collections* terpisah:
1. **`berita`**: Menyimpan embedding teks dari judul dan ringkasan berita RSS.
2. **`laporan_keuangan`**: Menyimpan embedding teks laporan keuangan kuartalan/tahunan (PDF extraction).
3. **`data_makro`**: Menyimpan embedding narasi ekonomi makro.

---

## 🔍 5. Alur Retrieval & Orkestrasi Agen (*RAG & LangGraph Agent*)

Saat pengguna mengajukan pertanyaan lewat fitur RAG Chatbot (misalnya: *"Bagaimana prospek BBCA setelah BI Rate naik kemarin?"*), backend memprosesnya melalui alur pipa LangGraph StateGraph berikut:

```
                  ┌──────────────────────────────┐
                  │          USER QUERY          │
                  └──────────────┬───────────────┘
                                 │
                   [Node 1: Klasifikasi & Ekstraksi]
                    - Tentukan tipe pertanyaan
                    - Ekstrak ticker (contoh: "BBCA")
                                 │
                     (Apakah Pertanyaan Jelas?)
                      ├── Tidak ➔ [Tanya Klarifikasi] ➔ END
                      └── Ya
                           │
                     [Node 2: Ambil Konteks Parallel]
                      ├── ChromaDB ➔ Vektor Cosine Query (top_k)
                      └── PostgreSQL ➔ Metrik Fundamental & Skor
                           │
                     [Node 3: Generasi Jawaban]
                      - Prompt engineering + Context injection
                      - Panggil Qwen2.5:3b (Ollama local LLM)
                           │
                     [Node 4: Evaluasi Kualitas]
                      ├── Skor Confidence < 0.5 ➔ Retry (top_k diperbesar)
                      └── Skor Confidence ≥ 0.5 ➔ [Jawaban Akhir] ➔ END
```

### A. Node 1: Klasifikasi Pertanyaan & Ekstraksi Saham
* **Rule-based extraction**: Mengidentifikasi kode saham 4 huruf besar (Regex: `\b[A-Z]{4}\b`) atau mencocokkannya dengan kamus alias (seperti *"bank bca"*, *"bri"*, *"astra"*).
* **Context memory**: Jika tidak ada nama saham di pertanyaan sekarang, sistem melihat riwayat percakapan sebelumnya untuk menjaga benang merah konteks.
* **LLM Classification**: Mengelompokkan jenis pertanyaan menjadi:
  * `spesifik`: tentang satu emiten (misal: *"Skor ROE BBCA berapa?"*).
  * `perbandingan`: membandingkan dua saham atau lebih (misal: *"Pilih BBCA atau BMRI?"*).
  * `umum`: membahas IHSG, sektor, atau ekonomi secara umum.
  * `ambigu`: tidak jelas dan memerlukan masukan lebih lanjut dari pengguna.

### B. Node 2: Ambil Konteks (Parallel Retrieval)
Sistem melakukan pengambilan data secara asinkron (parallel) dari dua sumber:
1. **Pencarian Semantik ChromaDB**: Teks pertanyaan di-embed menjadi vektor oleh BGE-M3. Vektor query dicocokkan dengan vektor di ChromaDB menggunakan metrik **Cosine Similarity**. Skor jarak (*distance*) dikonversi menjadi persentase relevansi (`relevansi = 1.0 - distance`). Hanya data dengan skor relevansi terbaik yang diambil.
2. **Kueri Tabular PostgreSQL**: Menarik data fundamental historis terbaru, sektor industri, serta data rekomendasi/skor mingguan terbaru dari tabel relasional.

### C. Node 3: Generasi Jawaban (Local LLM via Ollama)
Sistem menyusun prompt gabungan yang berisi:
* **System Instruction**: Aturan gaya menjawab (harus sopan, faktual, tidak bertele-tele, maksimal 200 kata, menggunakan Bahasa Indonesia, dan menyertakan disclaimer investasi).
* **Context Injection**: Dokumen referensi berita, data angka fundamental terstruktur, dan riwayat percakapan sebelumnya.
* **Prompt Akhir**: Pertanyaan yang diajukan pengguna.
* **Confidence Format**: Memerintahkan LLM menuliskan tingkat keyakinannya di akhir jawaban, contoh: `[CONFIDENCE: 0.85]`.

Model **`qwen2.5:3b`** di dalam Ollama memproses prompt tersebut dan menghasilkan draf jawaban. Backend akan menyaring tag `[CONFIDENCE: ...]` untuk dievaluasi oleh node kualitas.

### D. Node 4: Cek Kualitas & Evaluasi Ulang
Sistem memeriksa nilai confidence yang diberikan oleh LLM pada tahap sebelumnya:
* Jika confidence bernilai rendah ($< 0.5$) dan server belum pernah melakukan pengulangan, sistem akan kembali memicu **Node 2** dengan memperbesar jumlah dokumen pencarian (`top_k` diubah dari 5 menjadi 10) untuk memberikan informasi lebih kaya bagi LLM.
* Jika jawaban dinilai sudah memenuhi kualitas ($\ge 0.5$) atau kuota pengulangan habis, jawaban dikirim langsung ke pengguna dalam bentuk **Streaming Response** (kata demi kata dikirim bertahap dengan jeda 30 milidetik agar memunculkan efek mengetik yang mulus di aplikasi iOS).

---

## 🎯 6. Ringkasan Contoh Alur Nyata

Misalkan pengguna mengetik pertanyaan: **"Bagaimana sentimen berita ASII sekarang?"**

1. **Scraper & Cleaner (Sebelumnya)**: Setiap 30 menit, scraper menarik berita RSS ASII dari Google News. Berita dibersihkan, dihitung skor sentimennya (misal: *ASII cetak untung* $\rightarrow +0.65$), metadata disimpan ke Postgres, dan ringkasan di-embed oleh BGE-M3 ke ChromaDB collection `berita`.
2. **FastAPI Route**: SwiftUI mengirimkan payload POST ke `/chat` dengan teks pertanyaan tersebut.
3. **Klasifikasi**: Agen mendeteksi kata kunci `"ASII"` (kode saham) dan mengklasifikasikan pertanyaan sebagai tipe `spesifik`.
4. **Retrieval**: 
   - Backend memicu pencarian semantik vektor di ChromaDB pada collection `berita` disaring khusus untuk metadata `kode_saham = "ASII"`. Menghasilkan 5 berita teratas tentang sentimen ASII.
   - Backend memicu pencarian DB relasional di Postgres untuk memuat performa fundamental dan rasio ASII terbaru.
5. **Generasi LLM**: Prompt disusun rapi dengan data relevan dari database. `qwen2.5:3b` di Ollama membaca data tersebut, meringkas sentimennya (positif/negatif), menyertakan disclaimer, dan menandai `[CONFIDENCE: 0.9]`.
6. **Streaming**: Client SwiftUI menerima potongan string kata demi kata, merender teks berjalan secara dramatis, dan menampilkan tameng tingkat risiko serta status BI Rate secara dinamis pada dashboard pengguna.

---

Dengan memahami alur kerja terintegrasi di atas, Anda sekarang memiliki gambaran utuh tentang bagaimana data mengalir di dalam aplikasi **AI Saham Indonesia** dari proses awal scraping hingga dijawab secara cerdas oleh asisten AI lokal.
