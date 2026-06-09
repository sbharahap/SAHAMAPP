# 🚀 Panduan Setup & Konfigurasi Sistem SahamAI

Panduan ini dirancang untuk developer yang ingin memasang dan menjalankan seluruh ekosistem **AI Saham Indonesia** (Backend Python/FastAPI & iOS Client SwiftUI) dari nol.

---

## 📋 1. Prasyarat (*Prerequisites*)

Pastikan komputer pengembangan Anda (disarankan macOS dengan Apple Silicon) sudah memiliki program berikut:
1. **Docker Desktop**: Untuk menjalankan database relasional (PostgreSQL) dan database vektor (ChromaDB).
2. **Python 3.10+**: Mesin pengeksekusi backend Python.
3. **Ollama**: Aplikasi untuk menjalankan LLM lokal secara gratis.
4. **Xcode (v15+)**: Untuk membangun dan menjalankan aplikasi client iOS di Simulator atau perangkat iPhone fisik.

---

## 🛠️ 2. Konfigurasi Backend (FastAPI & Database)

Buka **Terminal** Anda dan masuk ke direktori proyek utama:

### Langkah A: Jalankan Container Database
1. Jalankan layanan docker-compose di latar belakang (*background*):
   ```bash
   docker compose up -d
   ```
2. Pastikan kedua container berjalan normal:
   ```bash
   docker compose ps
   ```
   *Anda akan melihat container `saham_postgres` (port 5432) dan `saham_chromadb` (port 8000) berjalan.*

### Langkah B: Setup Virtual Environment Python
1. Buat virtual environment baru:
   ```bash
   python3 -m venv venv
   ```
2. Aktifkan virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Pasang semua dependensi library:
   ```bash
   pip install -r requirements.txt
   ```

### Langkah C: Konfigurasi Environment Variables (`.env`)
1. Salin file template konfigurasi:
   ```bash
   cp .env.example .env
   ```
2. Buka file `.env` dan pastikan konfigurasi host database sudah benar:
   * `POSTGRES_HOST=localhost`
   * `CHROMA_HOST=localhost`
   * `OLLAMA_BASE_URL=http://localhost:11434`

### Langkah D: Inisialisasi Database Relasional
Buat skema tabel awal di database PostgreSQL:
```bash
python -m backend.db.init_db
```

### Langkah E: Setup Ollama (Solusi Error Crash Metal di macOS Sequoia / Chip M5)
1. Unduh model ke dalam aplikasi Ollama lokal Anda:
   ```bash
   ollama pull qwen2.5:3b
   ```
2. **Penting (untuk stabilitas macOS Sequoia / Apple Silicon)**:
   Matikan aplikasi Ollama dari menu bar atas (klik ikon koin Ollama ➔ *Quit Ollama*). Jalankan server Ollama secara manual via terminal untuk menghindari bug kompiler:
   ```bash
   # Matikan launcher otomatis jika masih tersisa
   launchctl bootout gui/$(id -u)/com.ollama.ollama 2>/dev/null
   
   # Jalankan server dengan menonaktifkan fitur bfloat16 kompiler Metal yang bermasalah
   GGML_METAL_BF16_DISABLE=1 OLLAMA_HOST=127.0.0.1:11434 ollama serve
   ```
   *Biarkan jendela terminal ini tetap terbuka.*

### Langkah F: Jalankan Server FastAPI
Buka **tab terminal baru**, aktifkan kembali virtual environment, lalu jalankan server uvicorn FastAPI:
```bash
source venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```
*Server FastAPI sekarang aktif dan mendengarkan request di port `8080`.*

---

## 📱 3. Konfigurasi iOS Client (SwiftUI)

### Langkah A: Buka Proyek di Xcode
1. Buka aplikasi **Xcode**.
2. Pilih menu **Open a project or file...**
3. Buka folder **`SahamIndo`** (pilih file `/SahamIndo/SahamIndo.xcodeproj`).
4. Xcode akan mengunduh dependencies Swift Package secara otomatis di latar belakang.

### Langkah B: Sesuaikan Alamat IP Server Backend
1. Buka file [Services.swift](file:///Users/satriabaladewaharahap/Downloads/SAHAMAPP/SahamIndo/SahamIndo/Services.swift) di panel navigasi Xcode.
2. Cari baris konstanta `baseURL` (sekitar baris 26):
   ```swift
   static let baseURL = "http://MacBook-Pro-Satria.local:8080"
   ```
3. Sesuaikan nilai tersebut berdasarkan lingkungan Anda:
   * **Menggunakan iOS Simulator**: Ubah menjadi `"http://localhost:8080"`.
   * **Menggunakan iPhone Fisik**: Ubah ke alamat IP lokal Mac Anda (misalnya `"http://192.168.1.50:8080"`) dan pastikan HP serta Mac tersambung ke jaringan Wi-Fi yang sama.

### Langkah C: Kompilasi & Jalankan Aplikasi
1. Pada toolbar atas Xcode, pilih target Simulator target (contoh: *iPhone 16 Pro*).
2. Klik tombol **Play** (atau tekan shortcut `Cmd + R`) untuk mengompilasi dan meluncurkan aplikasi di Simulator.

---

## 📥 4. Pengisian Data Awal (Ingestion) & Verifikasi

Saat pertama kali dijalankan, database Anda akan kosong. Ikuti langkah pengisian data berikut:

1. Buka browser di Mac Anda dan masuk ke halaman web kontrol dashboard:
   👉 **[http://localhost:8080](http://localhost:8080)**
2. Masuk ke tab **System & Control** di halaman web tersebut, lalu klik tugas berikut berurutan:
   1. **Scrape Berita**: Mengunduh berita ke PostgreSQL dan ChromaDB vector embeddings.
   2. **Scrape Makro**: Mengunduh indikator makroekonomi terkini.
   3. **Scrape Fundamental**: Menarik laporan finansial harian emiten.
   4. **Run Scoring**: Menghitung analisis rekomendasi mingguan.
3. *Alternatif (Menggunakan Terminal)*:
   ```bash
   curl -X POST "http://localhost:8080/api/jobs/trigger?job_name=scrape_news"
   curl -X POST "http://localhost:8080/api/jobs/trigger?job_name=scrape_makro"
   curl -X POST "http://localhost:8080/api/jobs/trigger?job_name=scrape_fundamental"
   curl -X POST "http://localhost:8080/api/jobs/trigger?job_name=run_scoring"
   ```
4. Tunggu 1–2 menit hingga semua proses pengunduhan selesai. Lakukan gesture **pull-to-refresh** di aplikasi iOS untuk memuat rekomendasi, chart analisis, dan ringkasan obrolan RAG AI.
