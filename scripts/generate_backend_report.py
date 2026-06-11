"""
Generator laporan PDF detail implementasi backend AI Saham Indonesia
beserta integrasi ke iOS SwiftUI app. Output file: laporan_backend_implementasi_detail.pdf

Cara menjalankan:
    /Users/virafitriyani/miniforge3/bin/python3 scripts/generate_backend_report.py
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# Konfigurasi Output
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "laporan_backend_implementasi_detail.pdf"

# ============================================================
# Styling
# ============================================================
styles = getSampleStyleSheet()

# Warna brand
COLOR_PRIMARY = colors.HexColor("#FFA500")  # oranye
COLOR_DARK = colors.HexColor("#1E293B")
COLOR_ACCENT = colors.HexColor("#0F766E")
COLOR_GRAY = colors.HexColor("#475569")
COLOR_LIGHT_BG = colors.HexColor("#F1F5F9")

# Override style heading
H1 = ParagraphStyle(
    "H1Custom",
    parent=styles["Heading1"],
    fontSize=20,
    leading=24,
    textColor=COLOR_DARK,
    spaceAfter=10,
    spaceBefore=18,
    fontName="Helvetica-Bold",
)
H2 = ParagraphStyle(
    "H2Custom",
    parent=styles["Heading2"],
    fontSize=15,
    leading=19,
    textColor=COLOR_ACCENT,
    spaceAfter=8,
    spaceBefore=14,
    fontName="Helvetica-Bold",
)
H3 = ParagraphStyle(
    "H3Custom",
    parent=styles["Heading3"],
    fontSize=12,
    leading=16,
    textColor=COLOR_DARK,
    spaceAfter=6,
    spaceBefore=10,
    fontName="Helvetica-Bold",
)
BODY = ParagraphStyle(
    "BodyCustom",
    parent=styles["BodyText"],
    fontSize=10,
    leading=14,
    alignment=TA_JUSTIFY,
    textColor=COLOR_DARK,
    spaceAfter=6,
    fontName="Helvetica",
)
BULLET = ParagraphStyle(
    "BulletCustom",
    parent=BODY,
    leftIndent=18,
    bulletIndent=6,
)
CODE = ParagraphStyle(
    "CodeCustom",
    parent=styles["Code"],
    fontSize=8.5,
    leading=11,
    textColor=COLOR_DARK,
    backColor=COLOR_LIGHT_BG,
    borderPadding=6,
    leftIndent=10,
    rightIndent=10,
    spaceAfter=10,
    fontName="Courier",
)
QUESTION = ParagraphStyle(
    "QuestionStyle",
    parent=BODY,
    fontSize=10.5,
    textColor=COLOR_ACCENT,
    fontName="Helvetica-Bold",
    spaceBefore=8,
    spaceAfter=2,
)
ANSWER = ParagraphStyle(
    "AnswerStyle",
    parent=BODY,
    leftIndent=12,
    spaceAfter=10,
)
TITLE_BIG = ParagraphStyle(
    "TitleBig",
    parent=styles["Title"],
    fontSize=26,
    leading=32,
    textColor=COLOR_DARK,
    alignment=TA_CENTER,
    spaceAfter=12,
    fontName="Helvetica-Bold",
)
SUBTITLE = ParagraphStyle(
    "SubTitle",
    parent=styles["BodyText"],
    fontSize=13,
    leading=17,
    textColor=COLOR_GRAY,
    alignment=TA_CENTER,
    spaceAfter=8,
    fontName="Helvetica",
)
COVER_LABEL = ParagraphStyle(
    "CoverLabel",
    parent=styles["BodyText"],
    fontSize=10,
    leading=14,
    textColor=COLOR_GRAY,
    alignment=TA_CENTER,
    fontName="Helvetica-Oblique",
)

# ============================================================
# Helper Functions
# ============================================================


def para(text, style=BODY):
    return Paragraph(text, style)


def heading1(text):
    return Paragraph(text, H1)


def heading2(text):
    return Paragraph(text, H2)


def heading3(text):
    return Paragraph(text, H3)


def bullet_list(items):
    """Render list of bullet items."""
    flow = []
    for item in items:
        flow.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", BULLET))
    return flow


def code_block(text):
    """Render preformatted code block."""
    escaped = (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    # ganti newline ke <br/>
    escaped = escaped.replace("\n", "<br/>")
    # ganti spasi ganda dengan non-breaking space
    escaped = escaped.replace("  ", "&nbsp;&nbsp;")
    return Paragraph(escaped, CODE)


def qa(q, a):
    """Render Q&A block."""
    return [
        Paragraph(f"Q: {q}", QUESTION),
        Paragraph(f"A: {a}", ANSWER),
    ]


def info_table(rows, col_widths=None):
    """Render two-column info table."""
    table_data = []
    for label, value in rows:
        table_data.append([
            Paragraph(f"<b>{label}</b>", BODY),
            Paragraph(value, BODY),
        ])
    t = Table(
        table_data,
        colWidths=col_widths or [4.5 * cm, 11.5 * cm],
    )
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), COLOR_LIGHT_BG),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, COLOR_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    return t


def comparison_table(headers, rows):
    """Render comparison table with header row."""
    data = [headers] + rows
    n_cols = len(headers)
    col_w = (16.0 / n_cols) * cm
    t = Table(data, colWidths=[col_w] * n_cols, repeatRows=1)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, COLOR_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return t


# ============================================================
# Build Story
# ============================================================
story = []

# ============================================================
# COVER
# ============================================================
story.append(Spacer(1, 5 * cm))
story.append(para("LAPORAN TEKNIS DETAIL", SUBTITLE))
story.append(Spacer(1, 0.3 * cm))
story.append(para("Implementasi Backend AI Saham Indonesia<br/>&amp; Integrasi ke iOS SwiftUI Environment", TITLE_BIG))
story.append(Spacer(1, 0.8 * cm))
story.append(para(
    "Dokumen ini menjelaskan arsitektur lengkap sistem, teknik yang digunakan,<br/>"
    "rationale di balik setiap design decision, serta cara komunikasi backend ke<br/>"
    "aplikasi iOS native (SwiftUI). Dilengkapi sesi Q&amp;A general dan spesifik.",
    SUBTITLE,
))
story.append(Spacer(1, 2.5 * cm))
story.append(para(
    f"Disusun: {datetime.now().strftime('%d %B %Y')}<br/>"
    "Stack: FastAPI &middot; LangGraph &middot; Ollama (Qwen3) &middot; "
    "BGE-M3 &middot; ChromaDB &middot; PostgreSQL &middot; SwiftUI",
    COVER_LABEL,
))
story.append(PageBreak())

# ============================================================
# DAFTAR ISI
# ============================================================
story.append(heading1("Daftar Isi"))
toc_items = [
    "BAB 1 &mdash; Ringkasan Eksekutif &amp; Filosofi Desain",
    "BAB 2 &mdash; Arsitektur Tinggi (High-Level Architecture)",
    "BAB 3 &mdash; Pipeline Pengumpulan &amp; Preprocessing Data",
    "BAB 4 &mdash; Database Hybrid: PostgreSQL + ChromaDB",
    "BAB 5 &mdash; RAG Pipeline (Retrieval-Augmented Generation)",
    "BAB 6 &mdash; Scoring Agent (LangGraph StateGraph)",
    "BAB 7 &mdash; Chatbot Agent (LangGraph StateGraph)",
    "BAB 8 &mdash; RAG Triad Evaluation (LLM-as-a-Judge)",
    "BAB 9 &mdash; Background Scheduler &amp; Alert System",
    "BAB 10 &mdash; FastAPI Endpoints (Public API)",
    "BAB 11 &mdash; Integrasi Backend ke iOS SwiftUI",
    "BAB 12 &mdash; Q&amp;A General (Umum)",
    "BAB 13 &mdash; Q&amp;A Specific (Teknis Mendalam)",
    "BAB 14 &mdash; Decisions Recap &amp; Rationale",
]
for item in toc_items:
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", BULLET))
story.append(PageBreak())

# ============================================================
# BAB 1 — RINGKASAN EKSEKUTIF
# ============================================================
story.append(heading1("BAB 1 &mdash; Ringkasan Eksekutif &amp; Filosofi Desain"))

story.append(heading2("1.1 Apa itu AI Saham Indonesia?"))
story.append(para(
    "AI Saham Indonesia adalah sistem rekomendasi saham berbasis Artificial Intelligence "
    "yang menggabungkan tiga teknik utama: <b>Retrieval-Augmented Generation (RAG)</b>, "
    "<b>Multi-Agent Orchestration</b> berbasis LangGraph, dan <b>quantitative scoring engine</b> "
    "5 pilar (fundamental, sentimen, sektor, makro, risiko). Sistem berjalan 100% lokal "
    "(on-premise) tanpa dependensi pada API LLM komersial seperti OpenAI atau Anthropic, "
    "sehingga lebih cocok untuk data finansial yang sensitif privacy-wise."
))

story.append(heading2("1.2 Tiga Filosofi Inti Desain"))
story.append(para(
    "<b>Filosofi 1 &mdash; Locality First.</b> Semua model AI (LLM Qwen3 dan embedding BGE-M3) "
    "berjalan lokal melalui Ollama dan sentence-transformers, sehingga: (a) tidak ada biaya "
    "per-token, (b) tidak ada latensi network ke cloud LLM provider, (c) data rasio "
    "keuangan dan sentimen berita tidak meninggalkan mesin developer."
))
story.append(para(
    "<b>Filosofi 2 &mdash; Hybrid Database (Polyglot Persistence).</b> Data terstruktur "
    "(harga saham, rasio fundamental, scoring numerik) disimpan di PostgreSQL untuk query "
    "transaksional ACID; data tidak terstruktur (teks berita, laporan keuangan, ringkasan makro) "
    "disimpan di ChromaDB sebagai vector embedding untuk semantic search. Pemisahan ini bukan "
    "redundansi, tetapi optimasi: query SQL agregat untuk angka, query cosine similarity untuk "
    "teks natural language."
))
story.append(para(
    "<b>Filosofi 3 &mdash; Explainable AI (XAI).</b> Setiap rekomendasi BUY/HOLD/SELL disertai "
    "<i>alasan tertulis</i> yang dihasilkan LLM berdasarkan dokumen referensi yang dapat ditelusuri "
    "(grounded reasoning). Skor total juga di-breakdown menjadi 5 komponen, sehingga user dapat "
    "melihat mengapa saham X mendapat skor 78 (misal: fundamental 85, sentimen 70, sektor 60, "
    "makro 80, risiko 75) alih-alih menerima &lsquo;black box prediction&rsquo;."
))

story.append(heading2("1.3 Technology Stack Summary"))
story.append(info_table([
    ("Backend Framework", "FastAPI 0.115+ (async ASGI server, lifespan events, dependency injection)"),
    ("Database Relasional", "PostgreSQL 16 + SQLAlchemy 2.0 async (asyncpg driver)"),
    ("Database Vektor", "ChromaDB 0.6+ (HTTP server mode dengan persistent volume)"),
    ("LLM Local", "Ollama (Qwen3:latest, 8.2B parameter, Q4_K_M quantization)"),
    ("Embedding Model", "BAAI/bge-m3 (1024-dim bilingual ID/EN)"),
    ("Agent Framework", "LangGraph 0.2+ (StateGraph dengan conditional edges)"),
    ("RAG Framework", "LlamaIndex 0.12+ (SentenceSplitter untuk chunking)"),
    ("Scheduler", "APScheduler AsyncIO (timezone Asia/Jakarta WIB)"),
    ("HTTP Client", "httpx + aiohttp (async scraping ke RSS feeds &amp; Yahoo Finance)"),
    ("iOS Client", "SwiftUI iOS 17+ dengan URLSession async/await + AsyncThrowingStream"),
]))

story.append(PageBreak())

# ============================================================
# BAB 2 — ARSITEKTUR TINGGI
# ============================================================
story.append(heading1("BAB 2 &mdash; Arsitektur Tinggi (High-Level Architecture)"))

story.append(heading2("2.1 Diagram Arsitektur"))
story.append(code_block(
    "+--------------------------------------------------+\n"
    "|              iOS Client (SwiftUI)                |\n"
    "|  - HomeView (Top 10)                             |\n"
    "|  - ChatbotView (streaming)                       |\n"
    "|  - PortfolioView, NotificationView               |\n"
    "+--------------------------------------------------+\n"
    "                       |\n"
    "          HTTP REST + SSE Stream (port 8080)\n"
    "                       |\n"
    "+--------------------------------------------------+\n"
    "|         FastAPI Server (Backend Python)          |\n"
    "+--------------------------------------------------+\n"
    "| Routes:                                          |\n"
    "| /chat (SSE)  /rekomendasi  /stocks  /alerts ...  |\n"
    "|                                                  |\n"
    "| Agents (LangGraph):                              |\n"
    "|   - ScoringAgent (weekly cron)                   |\n"
    "|   - ChatbotAgent (per request)                   |\n"
    "|   - AlertAgent  (every 30 min)                   |\n"
    "|                                                  |\n"
    "| RAG: indexer.py / retriever.py / evaluator.py    |\n"
    "| Workers: scraping, scoring, alert                |\n"
    "+--------------------------------------------------+\n"
    "         |                              |\n"
    "         v                              v\n"
    "  +-------------+              +----------------+\n"
    "  | PostgreSQL  |              |    ChromaDB    |\n"
    "  | (saham_db)  |              | (3 collections)|\n"
    "  +-------------+              +----------------+\n"
    "         ^                              ^\n"
    "         |                              |\n"
    "   +----------------+        +---------------------+\n"
    "   | Yahoo Finance  |        |  RSS Feeds (Kontan, |\n"
    "   |  Bank Indo,BPS |        |  Google News)       |\n"
    "   +----------------+        +---------------------+"
))

story.append(heading2("2.2 Lapisan Sistem (Layered Design)"))
story.extend(bullet_list([
    "<b>Presentation Layer</b>: iOS SwiftUI app dengan environment objects (PortfolioViewModel, "
    "ChatbotViewModel, NotificationViewModel) yang merepresentasikan state aplikasi.",
    "<b>API Layer</b>: FastAPI APIRouter dipecah per domain (rekomendasi, chatbot, data, rag_eval). "
    "Setiap router di-mount dua kali (dengan dan tanpa prefix /api) agar kompatibel dengan SwiftUI "
    "client dan curl manual.",
    "<b>Business Logic / Agent Layer</b>: LangGraph StateGraph yang membungkus chain LLM, "
    "RAG retrieval, dan database query. Dipisah jadi node-node dengan single responsibility.",
    "<b>RAG Layer</b>: Modul indexer (write path), retriever (read path), dan evaluator "
    "(quality assurance) di backend/rag/.",
    "<b>Data Access Layer</b>: SQLAlchemy 2.0 declarative models async, ChromaDB collection client, "
    "dan data collector (scraper).",
    "<b>Infrastructure Layer</b>: Docker Compose (PostgreSQL + ChromaDB), Ollama (host-native), "
    "APScheduler sebagai cron in-process.",
]))

story.append(heading2("2.3 Mengapa Memilih FastAPI sebagai Backend?"))
story.extend(bullet_list([
    "<b>Native async/await</b>: cocok untuk workload IO-heavy (LLM inference, DB query, HTTP "
    "scraping) tanpa thread blocking.",
    "<b>Pydantic v2</b>: validasi request/response model langsung di signature route handler, "
    "berkurang banyak boilerplate.",
    "<b>OpenAPI auto-generated</b>: setiap endpoint terdokumentasi di /docs (Swagger) sehingga "
    "frontend developer iOS bisa lihat schema response tanpa baca kode Python.",
    "<b>Lifespan events</b>: idiomatis untuk warm-up model BGE-M3 sekali saja saat startup, "
    "lalu dipakai untuk semua request berikutnya.",
    "<b>StreamingResponse</b>: out-of-the-box support untuk Server-Sent Events (SSE), yang "
    "dipakai untuk efek typing animation di chatbot SwiftUI.",
]))

story.append(PageBreak())

# ============================================================
# BAB 3 — PIPELINE DATA
# ============================================================
story.append(heading1("BAB 3 &mdash; Pipeline Pengumpulan &amp; Preprocessing Data"))

story.append(heading2("3.1 Sumber Data Eksternal"))
story.append(info_table([
    ("Yahoo Finance", "Library yfinance, ticker IDX dengan suffix &lsquo;.JK&rsquo; (contoh: BBCA.JK). "
                       "Sumber data harga harian, volume, rasio fundamental (ROE, EPS, PBV, DER, PE)."),
    ("Google News RSS", "Query per saham: &lsquo;saham [KODE]&rsquo;. Format XML, di-parse via feedparser."),
    ("Kontan RSS", "Berita pasar modal Indonesia umum dari portal Kontan."),
    ("Bank Indonesia", "BI Rate dan inflasi YoY dari API publik bi.go.id."),
    ("BPS API", "Indikator makroekonomi Indonesia (GDP, neraca perdagangan, dll)."),
]))

story.append(heading2("3.2 Teknik Scraping &amp; Kenapa Dipilih"))
story.append(para(
    "Scraping berjalan asynchronously menggunakan <b>httpx</b> dan <b>aiohttp</b> dengan custom "
    "<b>User-Agent</b> header agar tidak diblokir mekanisme proteksi server. Antar request "
    "diberikan jeda <code>_REQUEST_DELAY_SECONDS = 2.0</code> detik untuk menghormati rate limit "
    "server sumber. Filter waktu: hanya berita dalam 7 hari terakhir yang diambil, ditimestamp "
    "dengan zona Asia/Jakarta (WIB UTC+7) agar konsisten dengan jam buka bursa IDX."
))

story.append(heading2("3.3 Normalisasi Data Fundamental"))
story.append(para(
    "Fungsi <code>normalize_fundamental</code> menangani inkonsistensi format angka dari Yahoo "
    "Finance/IDX yang kadang berformat Indonesia (titik=ribuan, koma=desimal: 1.234.567,89) "
    "atau internasional (koma=ribuan, titik=desimal: 1,234,567.89):"
))
story.extend(bullet_list([
    "Strip simbol &lsquo;Rp&rsquo;, &lsquo;%&rsquo;, &lsquo;Rp.&rsquo; via regex.",
    "Deteksi heuristic format desimal: jika koma muncul setelah titik, asumsikan koma=desimal "
    "(format Indonesia); sebaliknya format internasional.",
    "Cast ke Float untuk rasio (rounded 2 desimal), BigInteger untuk volume (saham IDX bisa "
    "trading miliaran lembar/hari).",
    "Null handling: NaN dan None dipertahankan sebagai NULL di PostgreSQL, scoring engine "
    "tetap berjalan dengan flag <code>data_terbatas=True</code>.",
]))

story.append(heading2("3.4 Lexicon-Based Sentiment Analysis"))
story.append(para(
    "<b>Mengapa lexicon-based, bukan fine-tuned model?</b> Karena: (a) running fast (&lt;1ms per "
    "headline) tanpa GPU, (b) deterministik dan dapat diaudit (developer bisa lihat kamus kata), "
    "(c) cukup akurat untuk headline berita finansial Indonesia yang biasanya ringkas dan langsung "
    "ke poin. Algoritma:"
))
story.extend(bullet_list([
    "Kamus positif: <i>naik(1), menguat(1), melonjak(2), meroket(2), laba(1), untung(1), "
    "dividen(1), outperform(1)</i>.",
    "Kamus negatif: <i>turun(1), melemah(1), anjlok(2), jatuh(2), rugi(2), default(2), fraud(2), "
    "PHK(2)</i>.",
    "Bigram/trigram check terlebih dahulu (contoh: &lsquo;gagal bayar&rsquo;, &lsquo;right issue&rsquo;) "
    "sebelum unigram.",
    "Negasi modifier: kata sebelum keyword dicek; jika negasi (tidak, bukan, belum), nilai dibalik "
    "dengan kekuatan 0.7.",
    "Intensifier modifier: kata &lsquo;sangat&rsquo;, &lsquo;tajam&rsquo;, &lsquo;drastis&rsquo; "
    "dalam radius +- 2 kata multiply weight x1.5.",
    "Output range [-1.0, +1.0] via tanh-like normalization: skor = (pos &minus; neg) / max(pos+neg, 1).",
]))

story.append(PageBreak())

# ============================================================
# BAB 4 — DATABASE HYBRID
# ============================================================
story.append(heading1("BAB 4 &mdash; Database Hybrid: PostgreSQL + ChromaDB"))

story.append(heading2("4.1 PostgreSQL Schema (7 Tabel)"))
story.append(comparison_table(
    ["Tabel", "Purpose", "Key Columns"],
    [
        ["saham", "Master data emiten", "kode (PK), nama_perusahaan, sektor"],
        ["fundamental", "Rasio keuangan harian", "kode_saham, tanggal, roe, eps, pbv, der, pe_ratio"],
        ["makro", "Indikator ekonomi", "tanggal, indikator, nilai, satuan, sumber"],
        ["berita", "Metadata berita", "kode_saham, judul, url, skor_sentimen, sudah_diembedding"],
        ["scoring_mingguan", "Hasil scoring", "kode_saham, tanggal_scoring, skor_total, rekomendasi, alasan"],
        ["alert", "Push notif history", "kode_saham, pesan, delta, dikirim"],
        ["rag_evaluation", "RAG Triad scores", "batch_id, query, context_relevance, groundedness, answer_relevance"],
    ]
))

story.append(heading2("4.2 Kenapa SQLAlchemy 2.0 Async Style?"))
story.extend(bullet_list([
    "Menggunakan <code>Mapped[]</code> type annotations &mdash; type-safe dan IDE auto-complete bekerja.",
    "Driver asyncpg (bukan psycopg2) &mdash; tidak ada GIL blocking saat banyak request paralel.",
    "Connection pool: pool_size=10, max_overflow=20, pool_pre_ping=True. Cocok untuk workload "
    "burst dari scheduler + chatbot + iOS client.",
    "<code>expire_on_commit=False</code>: objek tetap accessible setelah commit, tidak ada lazy "
    "reload yang trigger I/O tak terduga.",
]))

story.append(heading2("4.3 ChromaDB 3 Collections"))
story.append(info_table([
    ("berita", "Chunks teks berita per emiten. ~294 docs (aktual saat ini), digunakan untuk "
                "menjawab pertanyaan kualitatif seperti &lsquo;Bagaimana sentimen BBCA?&rsquo;"),
    ("laporan_keuangan", "Chunks teks PDF laporan keuangan (saat ini 0 docs &mdash; perlu di-scrape). "
                          "Digunakan untuk pertanyaan rinci tentang post-pos laporan."),
    ("data_makro", "Chunks ringkasan analisis makroekonomi. Digunakan untuk pertanyaan tentang "
                    "kondisi pasar umum."),
]))

story.append(heading2("4.4 Kenapa Pisah ke 3 Collection?"))
story.append(para(
    "Bisa saja semua chunks digabung di satu collection, tetapi separation ini punya beberapa "
    "keuntungan teknis:"
))
story.extend(bullet_list([
    "<b>Targeted retrieval</b>: chatbot bisa filter ke collection spesifik berdasarkan tipe "
    "pertanyaan. Contoh: pertanyaan tentang laporan keuangan langsung query ke "
    "<code>laporan_keuangan</code>, tidak terdistraksi oleh berita.",
    "<b>Independent re-indexing</b>: jika BGE-M3 di-upgrade ke versi baru, bisa re-embed satu "
    "collection saja tanpa downtime untuk yang lain.",
    "<b>Metadata schema fleksibel</b>: <code>berita</code> punya field <code>skor_sentimen</code>, "
    "<code>laporan_keuangan</code> punya <code>kuartal</code>, <code>tahun_fiskal</code>. Tidak "
    "perlu nullable di mana-mana.",
]))

story.append(heading2("4.5 Chunking Strategy"))
story.append(para(
    "Menggunakan <b>LlamaIndex SentenceSplitter</b> dengan parameter:"
))
story.append(code_block(
    "_CHUNK_SIZE = 512   # token (~2048 karakter Bahasa Indonesia)\n"
    "_CHUNK_OVERLAP = 64  # token overlap antar chunk"
))
story.append(para(
    "Sentence-boundary splitting (bukan fixed-window) memastikan chunk tidak terputus di tengah "
    "kalimat. Overlap 64 token menjaga continuity konteks: jika satu fakta penting jatuh di "
    "perbatasan chunk, ia tetap muncul utuh di salah satu chunk."
))

story.append(heading2("4.6 Deduplikasi via SHA-256 Doc ID"))
story.append(para(
    "Untuk mencegah chunk berita yang sama disimpan dua kali (misal karena re-scrape Google News "
    "yang sering serve berita yang sama), Doc ID dibuat deterministic:"
))
story.append(code_block(
    "doc_id = SHA-256(\n"
    "    kode_saham + sumber + tanggal + url + teks[:200]\n"
    ")[:16]"
))
story.append(para(
    "Saat <code>collection.upsert()</code> dipanggil dengan ID yang sudah ada, ChromaDB akan "
    "overwrite, bukan duplicate. Pola idempotent ini membuat re-scrape aman dijalankan kapan saja."
))

story.append(PageBreak())

# ============================================================
# BAB 5 — RAG PIPELINE
# ============================================================
story.append(heading1("BAB 5 &mdash; RAG Pipeline (Retrieval-Augmented Generation)"))

story.append(heading2("5.1 Apa itu RAG?"))
story.append(para(
    "<b>Retrieval-Augmented Generation</b> adalah teknik dimana LLM diberikan konteks tambahan "
    "(dokumen relevan dari knowledge base eksternal) sebelum diminta menghasilkan jawaban. "
    "Tujuannya: mengurangi hallucination dan grounding jawaban LLM ke data faktual yang dapat "
    "ditelusuri sumbernya."
))

story.append(heading2("5.2 Tiga Komponen Utama RAG"))
story.append(comparison_table(
    ["Komponen", "File", "Fungsi"],
    [
        ["Indexer", "rag/indexer.py", "Write path: text -&gt; chunk -&gt; embed -&gt; upsert ke Chroma"],
        ["Retriever", "rag/retriever.py", "Read path: query -&gt; embed -&gt; cosine search -&gt; top-k docs"],
        ["Evaluator", "rag/evaluator.py", "Quality control: RAG Triad scoring via LLM-as-Judge"],
    ]
))

story.append(heading2("5.3 Embedding Model: Kenapa BGE-M3?"))
story.extend(bullet_list([
    "<b>Bilingual (ID + EN)</b>: BBCA punya konten berita campuran Indonesia (Kontan) dan Inggris "
    "(IDX in English). BGE-M3 trained pada keduanya, tidak butuh translation step.",
    "<b>1024 dimensi</b>: cukup untuk capture semantic granular tanpa boros storage. "
    "Bandingkan: text-embedding-3-small OpenAI = 1536 dim, tapi remote dan berbayar.",
    "<b>Open source</b>: bisa di-deploy di laptop developer, license MIT.",
    "<b>Apple Silicon support</b>: bisa pakai MPS backend (<code>EMBEDDING_DEVICE=mps</code>) "
    "untuk akselerasi GPU di MacBook Pro M-series.",
    "<b>Singleton load</b>: <code>get_embedder()</code> di <code>embedder.py</code> hanya "
    "load weights satu kali ke RAM (~2GB), reused untuk semua request.",
]))

story.append(heading2("5.4 Retrieval: Cosine Similarity Math"))
story.append(para(
    "ChromaDB native menyimpan vektor dan menghitung jarak cosine antara query embedding "
    "dengan semua chunk dalam collection:"
))
story.append(code_block(
    "cosine_distance = 1 - (q . d) / (||q|| * ||d||)\n"
    "similarity_score = 1 - cosine_distance   # range [0, 1]\n"
    "top_k = collection.query(\n"
    "    query_embeddings=[query_vec],\n"
    "    n_results=5,\n"
    "    where={'kode_saham': 'BBCA'}   # metadata filter\n"
    ")"
))
story.append(para(
    "<b>Metadata filter</b> dipakai untuk pre-filter (server-side di ChromaDB) sebelum cosine "
    "search dijalankan. Ini lebih efisien daripada filter di Python setelah dapat top_k."
))

story.append(heading2("5.5 Hybrid Retrieval untuk Pertanyaan Perbandingan"))
story.append(para(
    "Untuk query seperti &lsquo;Bandingkan BBCA vs BMRI&rsquo;, sistem menggunakan "
    "<code>retrieve_multi_saham()</code> yang menjalankan retrieval per emiten secara paralel "
    "(<code>asyncio.gather</code>), lalu menggabungkan hasilnya. Ini memastikan chatbot punya "
    "konteks seimbang dari kedua saham, bukan didominasi salah satu."
))

story.append(PageBreak())

# ============================================================
# BAB 6 — SCORING AGENT
# ============================================================
story.append(heading1("BAB 6 &mdash; Scoring Agent (LangGraph StateGraph)"))

story.append(heading2("6.1 Mengapa Pakai LangGraph?"))
story.append(para(
    "Scoring melibatkan langkah yang ada urutan logikanya (sequential dengan side-effects ke "
    "database), namun juga punya conditional branching (data lengkap vs terbatas). "
    "<b>LangGraph StateGraph</b> menyediakan abstraksi yang tepat: setiap node membaca/menulis "
    "shared <code>TypedDict</code> state, edge bisa conditional, dan retry logic built-in."
))
story.extend(bullet_list([
    "Alternatif: monolithic Python function &mdash; sulit di-test per langkah dan tidak visualizable.",
    "Alternatif: Celery task chain &mdash; overkill untuk pipeline single-process tanpa worker pool.",
    "Alternatif: LangChain SequentialChain &mdash; tidak support conditional branching dengan baik.",
]))

story.append(heading2("6.2 Empat Node Scoring Agent"))
story.append(comparison_table(
    ["Node", "Input State", "Output Update", "LLM dipanggil?"],
    [
        ["analisis_kondisi_pasar", "Daftar saham", "Bobot adaptif 5 komponen", "Tidak"],
        ["hitung_skor", "Saham + bobot", "5 skor komponen + total", "Tidak"],
        ["self_check", "Skor + data flags", "data_terbatas True/False", "Tidak"],
        ["generate_alasan", "Top 10 + context", "Alasan tertulis + label", "Ya (Qwen3)"],
    ]
))

story.append(heading2("6.3 Adaptive Weight Logic (Node 1)"))
story.append(para(
    "Bobot tidak hardcoded, tetapi <b>adaptive</b> berdasarkan kondisi pasar yang dibaca otomatis "
    "dari tabel <code>makro</code> dan <code>berita</code>:"
))
story.append(comparison_table(
    ["Kondisi Pasar", "Fundamental", "Sentimen", "Sektor", "Makro", "Risiko"],
    [
        ["Earnings Season (>=3 berita lapkeu)", "40%", "20%", "15%", "15%", "10%"],
        ["Volatilitas Tinggi (krisis)", "20%", "20%", "15%", "30%", "15%"],
        ["Normal (default)", "30%", "25%", "20%", "15%", "10%"],
    ]
))
story.append(para(
    "<b>Rationale</b>: saat musim laporan keuangan, fundamental jadi driver utama harga "
    "(angka laba bersih yang dirilis langsung dampak). Saat krisis (volatility tinggi seperti "
    "tapering, geopolitical event), risiko makro lebih dominan dari analisis fundamental "
    "individual."
))

story.append(heading2("6.4 5-Pillar Scoring Math"))
story.extend(bullet_list([
    "<b>Skor Fundamental</b>: rule-based scoring dari rasio ROE/EPS/PBV/DER. Contoh: ROE >= 20% "
    "+ 25 poin, PBV &lt; 1.5 + 20 poin. Dinormalisasi ke 0-100.",
    "<b>Skor Sentimen</b>: rata-rata <code>skor_sentimen</code> berita 7 hari terakhir di "
    "PostgreSQL. [-1, +1] di-map ke [0, 100]. Default 50 jika tidak ada berita.",
    "<b>Skor Sektor</b>: perubahan mingguan IHSG-sektor vs IHSG total. Outperform +5% = 100, "
    "underperform -5% = 0, linear di antara.",
    "<b>Skor Makro</b>: kombinasi BI Rate, inflasi, kurs USD/IDR. Sektor banking/properti "
    "mendapat penyesuaian khusus (sensitif suku bunga).",
    "<b>Skor Risiko</b>: <i>inverted</i>, tinggi = aman. Mulai dari 80, dikurangi jika DER &gt; 1.5, "
    "volume rendah (likuiditas), atau berita sangat negatif (&lt; -0.7).",
]))
story.append(para(
    "<b>Skor Total = sum(skor_komponen[i] * bobot_adaptif[i])</b>. Range 0-100."
))

story.append(heading2("6.5 Self-Check Node: Kenapa Tetap Lanjut Walau Data Tidak Lengkap?"))
story.append(para(
    "Saham IDX second/third liner (small-cap) atau IPO baru kadang minim coverage berita dan "
    "tidak punya laporan keuangan lengkap. Jika scoring agent menolak proses, user kehilangan "
    "peluang investasi. Solusinya: tetap proses, tetapi:"
))
story.extend(bullet_list([
    "Tandai dengan flag <code>data_terbatas = True</code>.",
    "Catat detail kekurangannya: &lsquo;data fundamental tidak tersedia&rsquo;, &lsquo;berita kurang&rsquo;.",
    "Turunkan <code>confidence</code> score (bukan menolak rekomendasi).",
    "LLM diberitahu di prompt agar menyertakan caveat di alasan tertulis.",
]))

story.append(heading2("6.6 Generate Alasan (Node 4): Prompt Engineering"))
story.append(para(
    "Untuk top 10 saham dengan skor tertinggi, dipanggil LlamaIndex retrieval untuk 3 berita "
    "+ 2 chunk laporan keuangan, lalu disusun prompt terstruktur ke Qwen3:"
))
story.append(code_block(
    "[Data Saham {kode}]\n"
    "Skor Total: 82.5 / 100\n"
    "Breakdown: F=85, S=80, K=75, M=78, R=88\n"
    "Fundamental: ROE=21.3%, PBV=2.1x, DER=0.8x\n"
    "\n"
    "[Konteks Berita 7 Hari Terakhir]\n"
    "1. (sentimen +0.6) BBCA cetak laba Rp 12.1T...\n"
    "2. (sentimen +0.4) Analis nilai BBCA undervalued...\n"
    "\n"
    "Tugas: tulis 3-4 kalimat analisis Bahasa Indonesia +\n"
    "tag rekomendasi [RECOMMENDED|NEUTRAL|NEGATIVE]."
))
story.append(para(
    "Output LLM di-parse via regex untuk ekstrak label rekomendasi, lalu disimpan ke tabel "
    "<code>scoring_mingguan</code> bersama 5 skor komponen dan bobot adaptif yang dipakai "
    "(untuk auditability)."
))

story.append(PageBreak())

# ============================================================
# BAB 7 — CHATBOT AGENT
# ============================================================
story.append(heading1("BAB 7 &mdash; Chatbot Agent (LangGraph StateGraph)"))

story.append(heading2("7.1 Empat Node Chatbot Pipeline"))
story.append(comparison_table(
    ["Node", "Fungsi", "Tools"],
    [
        ["klasifikasi_pertanyaan", "Deteksi kode saham + tipe query", "Regex + LLM zero-shot"],
        ["ambil_konteks", "Retrieve docs + read PostgreSQL", "BGE-M3 + ChromaDB + SQL"],
        ["generate_jawaban", "Susun prompt + call LLM", "Qwen3 via Ollama"],
        ["cek_kualitas", "Confidence check + retry decision", "Conditional edge"],
    ]
))

story.append(heading2("7.2 Hybrid Classification (Node 1)"))
story.append(para(
    "Klasifikasi pertanyaan tidak murni LLM (yang lambat dan bisa wrong) tapi tidak juga murni "
    "regex (yang missed alias informal). Pipeline:"
))
story.extend(bullet_list([
    "<b>Step 1 (Regex)</b>: deteksi kode 4 huruf kapital via pattern <code>\\b[A-Z]{4}\\b</code>.",
    "<b>Step 2 (Alias dictionary)</b>: lookup di kamus <code>_ALIAS_SAHAM</code> seperti "
    "&lsquo;bca&rsquo;-&gt;BBCA, &lsquo;mandiri&rsquo;-&gt;BMRI, &lsquo;telkom&rsquo;-&gt;TLKM. "
    "Sorted by length descending agar &lsquo;bank central asia&rsquo; cocok sebelum &lsquo;bank&rsquo;.",
    "<b>Step 3 (Chat history)</b>: jika tidak ada saham di pertanyaan saat ini, scan history "
    "(reverse) untuk ambil kode terakhir disebut. Ini mendukung percakapan &lsquo;...bandingkan "
    "dengan BMRI&rsquo; di turn ke-3.",
    "<b>Step 4 (LLM zero-shot fallback)</b>: jika rule-based tidak match, kirim ke Qwen3 dengan "
    "prompt klasifikasi yang strict: jawab 1 kata saja (spesifik/perbandingan/umum/ambigu).",
]))

story.append(heading2("7.3 Ambil Konteks (Node 2): Paralel Source"))
story.append(para(
    "Mengambil dari 3 sumber paralel:"
))
story.extend(bullet_list([
    "<b>ChromaDB</b>: RAG retrieval menggunakan <code>retrieve()</code> atau "
    "<code>retrieve_multi_saham()</code> tergantung jenis query.",
    "<b>PostgreSQL fundamental</b>: ambil rasio ROE/EPS/PBV/DER terbaru per saham. Ada fallback: "
    "jika row terbaru memiliki ROE NULL, ambil row sebelumnya yang punya data lengkap.",
    "<b>PostgreSQL scoring_mingguan</b>: ambil skor + rekomendasi minggu terakhir.",
    "<b>Special case</b>: jika kata kunci &lsquo;rekomendasi&rsquo; / &lsquo;top 10&rsquo; / "
    "&lsquo;saham terbaik&rsquo; muncul, otomatis ambil daftar top 10 mingguan terbaru.",
]))

story.append(heading2("7.4 Generate Jawaban: Anti-Hallucination Prompt"))
story.append(para(
    "Setelah hasil RAG Triad evaluation menunjukkan Groundedness rendah (1.33/5), system prompt "
    "diperketat dengan aturan eksplisit anti-hallucination:"
))
story.append(code_block(
    "ATURAN UTAMA - WAJIB DIPATUHI:\n"
    "1. Jawab HANYA berdasarkan DOKUMEN REFERENSI dan DATA SAHAM\n"
    "   yang diberikan di bawah.\n"
    "2. DILARANG KERAS mengarang data angka (harga, ROE, PBV, dll)\n"
    "   yang tidak tercantum dalam konteks.\n"
    "3. Jika data tidak ada, katakan eksplisit: 'Data X tidak tersedia\n"
    "   dalam referensi saat ini.'\n"
    "4. Jangan gunakan pengetahuan umum di luar dokumen.\n"
    "\n"
    "INGAT: confidence tinggi (>0.7) HANYA jika dokumen relevan."
))

story.append(heading2("7.5 Cek Kualitas (Node 4): Self-Reflection Retry"))
story.append(para(
    "LLM diminta menulis <code>[CONFIDENCE: 0.X]</code> di akhir respon. Node 4 mem-parse confidence "
    "ini. Jika &lt; 0.5 dan belum retry, loop kembali ke <code>ambil_konteks</code> dengan "
    "<code>top_k</code> lebih besar (5 -&gt; 10). Maksimal 1x retry agar tidak infinite loop."
))

story.append(PageBreak())

# ============================================================
# BAB 8 — RAG TRIAD EVALUATION
# ============================================================
story.append(heading1("BAB 8 &mdash; RAG Triad Evaluation (LLM-as-a-Judge)"))

story.append(heading2("8.1 Apa itu RAG Triad?"))
story.append(para(
    "Framework evaluasi kualitas RAG yang diperkenalkan TruEra/TruLens. Mengukur 3 dimensi "
    "(skala 1-5) yang bersama-sama memetakan kualitas pipeline end-to-end:"
))
story.append(comparison_table(
    ["Metrik", "Mengukur Apa", "Diagnosa Masalah"],
    [
        ["Context Relevance", "Apakah retrieved docs relevan dengan query?", "Retrieval salah / data kurang"],
        ["Groundedness", "Apakah answer didukung 100% oleh docs?", "LLM halusinasi"],
        ["Answer Relevance", "Apakah answer menjawab query secara langsung?", "LLM melebar / off-topic"],
    ]
))

story.append(heading2("8.2 Kenapa LLM-as-a-Judge?"))
story.extend(bullet_list([
    "<b>Tidak butuh ground truth manual</b>: tidak perlu manusia label tiap jawaban yang benar.",
    "<b>Skalabel</b>: bisa evaluasi ratusan query otomatis.",
    "<b>Konsisten</b>: dengan temperature=0, LLM judge memberikan skor yang reproducible.",
    "<b>Trade-off</b>: kualitas evaluasi terbatas oleh kualitas LLM judge. Untuk lebih akurat, "
    "judge harus model yang lebih kuat dari yang dievaluasi (di sini sama-sama Qwen3, jadi ada "
    "self-bias risk).",
]))

story.append(heading2("8.3 Implementasi di Codebase"))
story.extend(bullet_list([
    "<code>backend/rag/evaluator.py</code>: function <code>evaluasi_rag_triad()</code> yang "
    "panggil Qwen3 dengan structured JSON output.",
    "<code>backend/scripts/run_rag_eval.py</code>: batch runner dengan 15 test questions "
    "(spesifik, perbandingan, umum) dan summary report ke terminal.",
    "<code>backend/db/postgres.py</code>: tabel <code>rag_evaluation</code> menyimpan setiap "
    "eval result dengan batch_id untuk tracking history.",
    "<code>backend/api/routes/rag_eval.py</code>: endpoints REST untuk trigger evaluation "
    "(<code>POST /api/rag-eval/run</code>) dan view results (<code>GET /api/rag-eval/summary</code>).",
    "Live evaluation: setiap chat response juga otomatis dievaluasi dengan batch_id=&lsquo;live&rsquo; "
    "(fire-and-forget <code>asyncio.create_task</code>).",
]))

story.append(heading2("8.4 Contoh Hasil &amp; Interpretasi"))
story.append(comparison_table(
    ["Question", "CR", "G", "AR", "Avg", "Diagnosa"],
    [
        ["Kinerja BBCA Q terakhir", "2.0", "1.0", "3.0", "2.00", "Doc OK, LLM halusinasi"],
        ["ROE+PBV TLKM saat ini", "1.0", "1.0", "3.0", "1.67", "Doc TLKM kurang"],
        ["Rekomendasi BMRI minggu ini", "5.0", "2.0", "3.0", "3.33", "Doc bagus, partial halusinasi"],
    ]
))

story.append(PageBreak())

# ============================================================
# BAB 9 — SCHEDULER + ALERT
# ============================================================
story.append(heading1("BAB 9 &mdash; Background Scheduler &amp; Alert System"))

story.append(heading2("9.1 APScheduler Setup"))
story.append(para(
    "<code>scheduler.py</code> mendefinisikan <code>AsyncIOScheduler</code> singleton dengan "
    "timezone WIB (Asia/Jakarta). Job-job ini berjalan in-process bersama FastAPI server, "
    "<b>tidak butuh Celery atau Redis</b>:"
))
story.append(comparison_table(
    ["Job", "Schedule", "Action"],
    [
        ["scoring_mingguan", "Senin 06:00 WIB", "Run scoring_agent untuk semua saham"],
        ["scrape_news", "Setiap 30 menit", "Pull RSS + index ke ChromaDB"],
        ["alert_monitoring", "Setiap 30 menit", "Cek delta sentimen, push notif jika &gt; 0.5"],
        ["scrape_fundamental", "Harian 07:00 WIB", "Update ROE/EPS/PBV dari Yahoo Finance"],
        ["scrape_makro", "Harian 07:00 WIB", "Update BI Rate, inflasi, kurs dari API"],
        ["warm_up_candles_cache", "Startup + harian", "Pre-fetch chart data untuk iOS"],
    ]
))

story.append(heading2("9.2 Kenapa In-Process Scheduler?"))
story.extend(bullet_list([
    "<b>Simplicity</b>: single deployment unit (FastAPI process), tidak perlu deploy worker terpisah.",
    "<b>State sharing</b>: bisa langsung akses async_session() dan ChromaDB client tanpa duplicate "
    "config.",
    "<b>Trade-off</b>: jika FastAPI crash, scheduled jobs juga ikut hilang. Acceptable karena "
    "scheduler stateless dan akan recover pada next restart.",
]))

story.append(heading2("9.3 Alert Agent: Delta Sentiment Watchdog"))
story.append(para(
    "Tujuan: deteksi shift sentimen mendadak yang menandakan event material (skandal, earnings "
    "surprise, perubahan rating). Algoritma:"
))
story.append(code_block(
    "for emiten in watchlist:\n"
    "  sentimen_baru  = avg(berita_30_menit_terakhir)\n"
    "  sentimen_lama  = avg(berita_historis)\n"
    "  delta = sentimen_baru - sentimen_lama\n"
    "\n"
    "  if abs(delta) >= 0.5:  # ambang 0.5 di skala [-1, +1]\n"
    "     simpan ke tabel alert\n"
    "     POST /api/alerts/push (push notif iPhone)"
))

story.append(PageBreak())

# ============================================================
# BAB 10 — FASTAPI ENDPOINTS
# ============================================================
story.append(heading1("BAB 10 &mdash; FastAPI Endpoints (Public API)"))

story.append(heading2("10.1 Route Modules"))
story.append(comparison_table(
    ["Module", "Prefix", "Key Endpoints"],
    [
        ["chatbot.py", "/chat, /chatbot/chat", "POST chat dengan SSE streaming"],
        ["rekomendasi.py", "/rekomendasi", "GET /mingguan (top 10)"],
        ["data.py", "/stocks, /makro, /ai", "GET candles, summary, indicators, insights"],
        ["rag_eval.py", "/rag-eval", "POST /run, GET /results, GET /summary"],
        ["main.py", "/api/status, /api/alerts/...", "Server status + push notif simulator"],
    ]
))

story.append(heading2("10.2 Sample Endpoint: Chatbot Streaming"))
story.append(code_block(
    "@router.post('/chat')\n"
    "async def post_chat(payload: ChatPayload):\n"
    "    return StreamingResponse(\n"
    "        generate_response_stream(\n"
    "            payload.pertanyaan, payload.riwayat\n"
    "        ),\n"
    "        media_type='text/event-stream'\n"
    "    )\n"
    "\n"
    "async def generate_response_stream(pertanyaan, riwayat):\n"
    "    result = await chat(pertanyaan, riwayat)\n"
    "    for kata in result['jawaban'].split(' '):\n"
    "        yield kata + ' '\n"
    "        await asyncio.sleep(0.03)  # typing effect"
))

story.append(heading2("10.3 Dependency Injection Pattern"))
story.append(para(
    "Pattern <code>db: AsyncSession = Depends(get_db_session)</code> menjamin: (a) session "
    "dibuat baru per request, (b) di-close otomatis di finally block, (c) bisa di-mock untuk "
    "unit testing tanpa container PostgreSQL real."
))

story.append(PageBreak())

# ============================================================
# BAB 11 — INTEGRASI iOS SWIFTUI
# ============================================================
story.append(heading1("BAB 11 &mdash; Integrasi Backend ke iOS SwiftUI"))

story.append(heading2("11.1 Arsitektur SwiftUI App"))
story.append(para(
    "App iOS menggunakan SwiftUI dengan pattern <b>MVVM + EnvironmentObject</b>. Empat "
    "@StateObject di-inject di root <code>SahamIndoApp</code>:"
))
story.append(code_block(
    "@main\n"
    "struct SahamIndoApp: App {\n"
    "    @StateObject private var portfolioVM = PortfolioViewModel()\n"
    "    @StateObject private var router     = Router()\n"
    "    @StateObject private var chatbotVM  = ChatbotViewModel()\n"
    "    @StateObject private var notifVM    = NotificationViewModel()\n"
    "\n"
    "    var body: some Scene {\n"
    "        WindowGroup {\n"
    "            MainTabView()\n"
    "                .environmentObject(portfolioVM)\n"
    "                .environmentObject(router)\n"
    "                .environmentObject(chatbotVM)\n"
    "                .environmentObject(notifVM)\n"
    "        }\n"
    "    }\n"
    "}"
))

story.append(heading2("11.2 APIClient: Smart Base URL Resolution"))
story.append(para(
    "Salah satu tantangan iOS app berkomunikasi ke backend lokal adalah <b>IP address yang berubah</b> "
    "(Wi-Fi network berpindah, atau iPhone connect via Tailscale). <code>APIClient.getBaseURL()</code> "
    "menyelesaikan ini dengan parallel race probing:"
))
story.append(code_block(
    "let candidates = [\n"
    "    'http://10.67.50.204:8080',\n"
    "    'http://10.67.51.0:8080',\n"
    "    'http://localhost:8080',\n"
    "    'http://127.0.0.1:8080',\n"
    "    'http://MacBook-Pro-Satria.local:8080',\n"
    "]\n"
    "\n"
    "// Parallel ping /api/status, return URL pertama yg success\n"
    "let resolved = await withTaskGroup(of: String?.self) { group in\n"
    "    for candidate in candidates {\n"
    "        group.addTask { ping(candidate) }\n"
    "    }\n"
    "    for await result in group {\n"
    "        if let url = result {\n"
    "            group.cancelAll()\n"
    "            return url\n"
    "        }\n"
    "    }\n"
    "}\n"
    "verifiedBaseURL = resolved   // cache untuk request berikutnya"
))

story.append(heading2("11.3 Custom Date Decoding Strategy"))
story.append(para(
    "PostgreSQL bisa kembalikan timestamp dalam 4 format berbeda. <code>APIClient.decoder</code> "
    "mencoba semuanya secara berurutan:"
))
story.extend(bullet_list([
    "ISO8601 + fractional seconds: <code>2026-06-06T09:00:00.000000+07:00</code>",
    "ISO8601 plain: <code>2026-06-06T09:00:00+07:00</code>",
    "PostgreSQL tanpa timezone: <code>2026-06-06T09:00:00</code>",
    "Sama tapi dengan microseconds: <code>2026-06-06T09:00:00.000000</code>",
]))
story.append(para(
    "Jika semua gagal, throw <code>DecodingError.dataCorruptedError</code>. Pattern ini mencegah "
    "crash di production saat backend dideploy versi PostgreSQL berbeda."
))

story.append(heading2("11.4 Chatbot Streaming: AsyncThrowingStream"))
story.append(para(
    "Untuk dapat efek typing animation, SwiftUI consume SSE stream dari backend dengan "
    "<code>URLSession.bytes(for:)</code> yang return <code>AsyncBytes</code>, lalu di-bridge ke "
    "<code>AsyncThrowingStream&lt;String, Error&gt;</code>:"
))
story.append(code_block(
    "let (bytes, response) = try await URLSession.shared.bytes(for: request)\n"
    "\n"
    "return AsyncThrowingStream { continuation in\n"
    "    Task {\n"
    "        var buffer = Data()\n"
    "        for try await byte in bytes {\n"
    "            buffer.append(byte)\n"
    "            if let str = String(data: buffer, encoding: .utf8) {\n"
    "                continuation.yield(str)\n"
    "                buffer.removeAll()\n"
    "            }\n"
    "        }\n"
    "        continuation.finish()\n"
    "    }\n"
    "}"
))
story.append(para(
    "<b>Mengapa byte-level streaming?</b> Karena response Bahasa Indonesia bisa mengandung "
    "karakter multi-byte (UTF-8 emoji, &lsquo;Rp&rsquo;). Buffering byte sampai dapat string "
    "valid mencegah karakter terpotong di tengah."
))

story.append(heading2("11.5 Data Models: DTO Pattern"))
story.append(para(
    "Setiap response endpoint di backend punya counterpart DTO di Swift dengan "
    "<code>Decodable</code>:"
))
story.append(code_block(
    "struct RekomendasiItemDTO: Decodable {\n"
    "    let rank: Int\n"
    "    let kode_saham: String       // snake_case dari Python\n"
    "    let nama_perusahaan: String?\n"
    "    let sektor: String?\n"
    "    let rekomendasi: String      // 'RECOMMENDED' | 'NEUTRAL' | 'NEGATIVE'\n"
    "    let alasan: String?\n"
    "}\n"
    "\n"
    "// Mapping ke domain model:\n"
    "extension RekomendasiItemDTO {\n"
    "    func toDomainModel() -> RekomendasiItem {\n"
    "        return RekomendasiItem(\n"
    "            rank: rank,\n"
    "            symbol: kode_saham,\n"
    "            name: nama_perusahaan ?? kode_saham,\n"
    "            sector: sektor ?? '-',\n"
    "            recommendation: Recommendation(rawValue: rekomendasi) ?? .neutral\n"
    "        )\n"
    "    }\n"
    "}"
))

story.append(heading2("11.6 View &lt;-&gt; ViewModel &lt;-&gt; Service Flow"))
story.append(code_block(
    "View                ViewModel              Service                Backend\n"
    "-----               -----------            ---------              ----------\n"
    "HomeView    --bind--> PortfolioViewModel\n"
    "                       .fetchTop10()  --call--> RealStockService\n"
    "                                                  .fetchRekomendasi() ---> GET /rekomendasi/mingguan\n"
    "                                                                       <--- JSON DTO\n"
    "                       @Published   <--update-- [RekomendasiItem]\n"
    "  <--re-render-- via Combine\n"
    "ChatbotView --bind--> ChatbotViewModel\n"
    "                       .send(msg)    --stream--> APIClient.sendChatMessageStream\n"
    "                                                                       ---> POST /chat (SSE)\n"
    "                                                                       <--- byte chunks\n"
    "                       @Published   <--token-- AsyncThrowingStream\n"
    "  <--per-token re-render-- (typing effect)"
))

story.append(heading2("11.7 CORS Configuration"))
story.append(para(
    "Backend FastAPI mengaktifkan CORS terbuka karena iOS Simulator dan device physical "
    "punya origin berbeda, dan diakses via IP:port langsung bukan domain:"
))
story.append(code_block(
    "app.add_middleware(\n"
    "    CORSMiddleware,\n"
    "    allow_origins=['*'],\n"
    "    allow_credentials=True,\n"
    "    allow_methods=['*'],\n"
    "    allow_headers=['*'],\n"
    ")"
))

story.append(PageBreak())

# ============================================================
# BAB 12 — Q&A GENERAL
# ============================================================
story.append(heading1("BAB 12 &mdash; Q&amp;A General (Umum)"))

general_qa = [
    ("Apa bedanya sistem ini dengan robo-advisor seperti Bibit atau Ajaib?",
     "Bibit dan Ajaib adalah platform investasi <i>retail-facing</i> yang fokus pada execution "
     "(beli/jual reksadana atau saham langsung) dan menggunakan profil risiko user untuk "
     "rekomendasi. AI Saham Indonesia ini adalah <b>research assistant</b> yang fokus pada "
     "analisis fundamental + sentimen + makro, dengan transparansi tinggi (breakdown 5 skor + "
     "alasan tertulis). Tidak ada integrasi broker, output-nya pure insight yang user bisa "
     "pakai untuk decision sendiri. Selain itu sistem ini berjalan lokal sehingga data analisis "
     "tidak meninggalkan device user."),
    ("Kenapa pilih Qwen3 sebagai LLM, bukan Llama atau Mistral?",
     "Tiga alasan: (1) Qwen3 punya <b>multilingual support yang kuat untuk Bahasa Indonesia</b> "
     "dan Mandarin (penting untuk berita pasar IDX yang ada referensi ke China A-share). "
     "(2) Quantization Q4_K_M sekitar 5.2GB cocok untuk laptop developer dengan 16GB RAM. "
     "(3) Memiliki mode <code>/no_think</code> yang lebih ringkas untuk production use case. "
     "Llama 3.1 juga sudah di-install di Ollama sebagai backup, dan switching antar model "
     "tinggal ubah <code>OLLAMA_MODEL</code> di .env tanpa code change."),
    ("Apakah sistem ini sudah production-ready?",
     "<b>Belum sepenuhnya</b>. Production-ready berarti: HA deployment, monitoring (Prometheus/"
     "Grafana), proper logging aggregation (ELK), security hardening (rate limiting, API key auth), "
     "dan backup strategy. Saat ini sistem masih dalam tahap research/MVP yang fokus membuktikan "
     "konsep RAG + Multi-Agent untuk domain finansial Indonesia. Untuk production perlu juga "
     "ditambah unit test coverage yang lebih dari 80%, integration test, dan stress test."),
    ("Kenapa pakai PostgreSQL + ChromaDB, bukan satu database saja seperti Postgres dengan pgvector?",
     "Pertimbangan utama: (a) ChromaDB punya API yang lebih simple untuk semantic search "
     "(<code>collection.query()</code>), (b) Lebih ringan untuk development lokal "
     "(tidak butuh tuning HNSW index manual), (c) Pemisahan storage memungkinkan re-index vektor "
     "tanpa mengganggu OLTP load PostgreSQL. Trade-off: kita kelola 2 database services. Untuk "
     "scale yang lebih besar (jutaan dokumen), kombinasi Postgres + pgvector atau Qdrant/Milvus "
     "mungkin lebih cost-effective."),
    ("Bagaimana sistem update setelah model AI baru rilis?",
     "Stateless model loading: cukup ubah <code>OLLAMA_MODEL</code> di .env file dan restart "
     "FastAPI server. Untuk embedding model (BGE-M3) lebih hati-hati karena vektor lama di "
     "ChromaDB tidak compatible dengan vektor baru &mdash; perlu re-index semua dokumen "
     "(pekerjaan ~1-2 jam untuk ~300 docs). Solusi proper: versioning collection name (contoh: "
     "<code>berita_v2_bge_large</code>), index ulang, lalu switch alias."),
    ("Bagaimana dengan data security?",
     "Karena sistem 100% lokal: (a) data sensitif tidak pernah ke cloud, (b) password "
     "PostgreSQL diset di .env (jangan commit ke git), (c) ChromaDB authn opsional bisa diaktifkan. "
     "Untuk deployment iOS app ke TestFlight/App Store, ada beberapa langkah security: "
     "implement API key authentication, rate limiting per IP, dan HTTPS dengan cert (Let&rsquo;s Encrypt) "
     "atau Tailscale untuk private network."),
    ("Apakah sistem ini bisa untuk forecasting harga saham?",
     "<b>Tidak</b>. Sistem ini intentionally bukan price predictor. Forecasting harga saham "
     "secara probabilistik sangat sulit (efficient market hypothesis) dan rawan misleading user. "
     "Sistem ini hanya memberi <b>recommendation</b> berdasarkan kondisi fundamental + sentimen "
     "+ makro saat ini, dengan asumsi: saham dengan fundamental kuat + sentimen positif + sektor "
     "outperform cenderung outperform IHSG dalam jangka pendek-menengah. Validasi via backtesting."),
    ("Berapa biaya operasional sistem ini per bulan?",
     "Jika di-host di MacBook dev sendiri: $0 selain listrik. Jika di-deploy ke VPS: butuh "
     "minimum 16GB RAM untuk Qwen3 8B + BGE-M3 + PostgreSQL + ChromaDB. Hetzner CCX23 (4 vCPU, "
     "16GB RAM) sekitar EUR 30/bulan. Untuk skala lebih besar, bisa pakai GPU server (RTX 4090) "
     "atau switch ke API LLM komersial (trade-off: biaya per-token vs setup overhead)."),
]
for q, a in general_qa:
    story.extend(qa(q, a))

story.append(PageBreak())

# ============================================================
# BAB 13 — Q&A SPECIFIC
# ============================================================
story.append(heading1("BAB 13 &mdash; Q&amp;A Specific (Teknis Mendalam)"))

specific_qa = [
    ("Kenapa chunk size 512 dan overlap 64, bukan misalnya 1024 dan 128?",
     "512 token dipilih karena: (a) BGE-M3 default training context-length cocok di range ini, "
     "(b) berita finansial Indonesia rata-rata 200-800 kata (~ 500-1500 token), sehingga "
     "1 artikel = 1-3 chunks yang masih bisa dipahami sebagai unit semantik utuh. "
     "Overlap 64 (12.5% dari chunk size) cukup untuk menjaga continuity di boundary tanpa "
     "duplicate storage berlebihan. Eksperimen dengan chunk lebih besar (1024) meningkatkan "
     "context coverage tapi menurunkan precision retrieval karena chunk jadi terlalu generic."),
    ("Kenapa cosine similarity, bukan dot product atau euclidean distance?",
     "BGE-M3 di-train dengan contrastive learning objective yang optimize cosine similarity, jadi "
     "vector embeddings sudah ter-normalize. Dot product akan ekuivalen jika norm = 1 (dan untuk "
     "BGE-M3 memang demikian). Euclidean tidak cocok karena dimensi 1024 -- curse of dimensionality "
     "membuat semua jarak Euclidean cenderung sama. Cosine fokus pada arah (semantik), bukan magnitude."),
    ("Bagaimana handling concurrent request saat banyak user buka iOS app?",
     "FastAPI + uvicorn async runtime menangani concurrency lewat single-thread event loop. "
     "Bottleneck biasanya di LLM inference (Ollama serialize request per model instance). Untuk "
     "throughput tinggi: (a) jalankan multiple Ollama instances dengan load balancer di depannya, "
     "(b) atau batching request di backend dengan <code>asyncio.Queue</code> + worker pool. "
     "Saat ini sistem cocok untuk &lt; 10 concurrent users."),
    ("Kenapa pakai LangGraph StateGraph, bukan LangChain Expression Language (LCEL)?",
     "LCEL bagus untuk linear chains (prompt -&gt; LLM -&gt; parser -&gt; output). LangGraph "
     "lebih powerful untuk: (a) conditional branching berdasarkan state (contoh: retry jika "
     "confidence rendah), (b) cyclic graph (retry loop), (c) shared state TypedDict yang explicit "
     "(IDE auto-complete bekerja). Chatbot agent kita punya kedua kasus ini, jadi LangGraph "
     "fitting pilihannya."),
    ("Bagaimana cara invalidasi cache jika data fundamental berubah?",
     "Tidak ada caching layer eksplisit di backend &mdash; setiap chat request selalu query "
     "PostgreSQL dan ChromaDB. Caching dilakukan di client iOS dengan <code>StockCache</code> "
     "yang punya TTL (Time-To-Live). Cache invalidation manual: ada endpoint "
     "<code>POST /api/jobs/trigger?job_name=scrape_fundamental</code> yang langsung re-fetch "
     "dan overwrite tabel. Cache iOS akan stale sampai TTL habis (~5 menit), trade-off untuk "
     "menghindari thundering herd ke backend."),
    ("Apa yang terjadi jika Ollama down saat user kirim pesan ke chatbot?",
     "Chatbot agent punya fallback di <code>_generate_jawaban_fallback()</code>: bukan crash, "
     "tapi compose jawaban template dari data PostgreSQL yang ada (rasio fundamental + skor "
     "scoring) plus daftar 3 berita teratas hasil retrieval. Quality lebih rendah tapi sistem "
     "tetap usable. Logging error level WARNING agar developer notice."),
    ("Kenapa SentenceSplitter karakter-based dengan _CHUNK_SIZE=512 (karakter), bukan token-based?",
     "Komentar di kode bilang &lsquo;~512 token = 2048 karakter&rsquo;, jadi asumsinya 1 token ~ "
     "4 karakter (rough untuk Bahasa Indonesia). Token-based via tiktoken akan lebih akurat tapi "
     "tambah dependency overhead. Untuk MVP, character-based cukup memberikan chunks yang konsisten."),
    ("Bagaimana cara migration schema database tanpa downtime?",
     "Project menggunakan Alembic (di requirements.txt: <code>alembic&gt;=1.14.0</code>) yang "
     "support migration script generation dan rollback. Untuk zero-downtime: (a) tambah kolom "
     "nullable terlebih dahulu, (b) deploy app yang baca + tulis kolom baru sambil tetap kompatibel "
     "dengan schema lama, (c) backfill data, (d) set kolom NOT NULL, (e) hapus path code lama. "
     "Saat ini <code>init_db.py</code> hanya CREATE TABLE IF NOT EXISTS, untuk production perlu "
     "switch ke Alembic proper."),
    ("Kenapa skor risiko inverted (tinggi = aman), tidak sama dengan komponen lain?",
     "Konvensi UX: user lebih cepat paham &lsquo;Skor Risiko 80&rsquo; = aman daripada &lsquo;Risiko 20&rsquo; "
     "= risiko rendah. Skor total = weighted sum jadi semua komponen harus berada di skala yang sama "
     "(0-100, tinggi = baik). Hanya saja interpretasi naming-nya: &lsquo;Skor Risiko Tinggi&rsquo; "
     "di domain ini berarti &lsquo;Profil Risiko Saham Rendah&rsquo;. Mungkin perlu rename ke "
     "&lsquo;Skor Keamanan&rsquo; untuk klarifikasi."),
    ("Bagaimana cara test agent secara isolasi?",
     "LangGraph StateGraph node adalah async function dengan signature standar: "
     "<code>async def node(state: ChatState) -&gt; dict</code>. Bisa di-test dengan unittest async "
     "menggunakan <code>pytest-asyncio</code>: panggil fungsi dengan state stub, assert output dict. "
     "Untuk LLM call, mock <code>llm.ainvoke()</code> dengan response fix. Database query di-mock "
     "via <code>aiomock</code> atau pakai test PostgreSQL container."),
    ("Kenapa ada double routing (with /api dan tanpa /api) di main.py?",
     "Historical reason: SwiftUI client awalnya call <code>/chat</code>, <code>/stocks/...</code> "
     "(tanpa prefix), sementara design proper API harus pakai <code>/api/chat</code>. Untuk backward "
     "compatibility tanpa break iOS client yang sudah deployed, kedua-duanya di-mount."),
    ("Kenapa pakai BackgroundTasks untuk trigger eval, bukan asyncio.create_task langsung?",
     "<code>BackgroundTasks</code> dari FastAPI menjamin task baru di-start <i>setelah</i> "
     "response dikirim ke client. Ini lebih clean daripada <code>asyncio.create_task</code> "
     "yang fire-and-forget &mdash; task bisa di-start sebelum response selesai dan saling rebut "
     "event loop. Untuk evaluasi RAG yang berat (panggil LLM), pattern ini lebih predictable."),
]
for q, a in specific_qa:
    story.extend(qa(q, a))

story.append(PageBreak())

# ============================================================
# BAB 14 — DECISIONS RECAP
# ============================================================
story.append(heading1("BAB 14 &mdash; Decisions Recap &amp; Rationale"))

story.append(heading2("14.1 Decision Matrix"))
story.append(comparison_table(
    ["Decision", "Pilihan", "Alternatif yang Ditolak", "Rationale Utama"],
    [
        ["LLM", "Qwen3 8B (Ollama)", "GPT-4 (OpenAI API)", "Local, no per-token cost, data privacy"],
        ["Embedding", "BGE-M3 (1024d)", "text-embedding-3-small", "Bilingual ID/EN, open source"],
        ["Vector DB", "ChromaDB", "Postgres+pgvector", "Simpler API, lighter for dev"],
        ["Relational", "PostgreSQL 16", "SQLite", "Production-grade, async support"],
        ["ORM Driver", "asyncpg", "psycopg2", "No GIL, true async"],
        ["Agent FW", "LangGraph", "LCEL only", "Conditional + cyclic graph"],
        ["RAG Chunking", "LlamaIndex 512/64", "Custom regex split", "Sentence-aware, mature lib"],
        ["Scheduler", "APScheduler in-process", "Celery+Redis", "Simplicity, no extra service"],
        ["Sentiment", "Lexicon-based", "Fine-tuned BERT", "Fast (<1ms), auditable"],
        ["Web FW", "FastAPI", "Flask, Django", "Async, OpenAPI, Pydantic v2"],
        ["iOS Pattern", "MVVM+EnvObj", "VIPER, Clean Arch", "SwiftUI idiomatic, less boilerplate"],
        ["API Comm", "REST + SSE", "GraphQL, gRPC", "Simple, native iOS support"],
    ]
))

story.append(heading2("14.2 Trade-offs yang Disadari"))
story.extend(bullet_list([
    "<b>Local LLM trade-off</b>: kualitas Qwen3 8B di bawah GPT-4. Acceptable untuk research, "
    "untuk production butuh upgrade ke Qwen3 32B atau switch ke Claude/GPT-4o.",
    "<b>In-process scheduler</b>: jika FastAPI crash, scheduled jobs ikut hilang. Tapi karena "
    "scheduler stateless, restart akan recover.",
    "<b>No caching layer</b>: setiap chat request fresh query DB. Latency higher tapi data selalu "
    "fresh. Untuk hot endpoints (e.g. <code>/rekomendasi/mingguan</code>) bisa ditambah Redis cache.",
    "<b>Lexicon-based sentiment</b>: lebih cepat tapi miss konteks sarkasme atau ironic phrasing. "
    "Untuk konten finansial yang umumnya straightforward, ini acceptable.",
    "<b>SHA-256 doc deduplication</b>: idempotent tapi tidak handle paraphrasing (berita yang "
    "sama tulis ulang dengan kalimat berbeda akan disimpan dua kali). Untuk near-duplicate "
    "detection butuh fingerprinting via MinHash atau locality-sensitive hashing.",
]))

story.append(heading2("14.3 Roadmap Improvement"))
story.extend(bullet_list([
    "<b>Short-term</b>: scrape laporan keuangan PDF untuk fill <code>laporan_keuangan</code> "
    "collection (saat ini 0 docs).",
    "<b>Short-term</b>: tambah unit test coverage minimum 70% untuk agent dan RAG modules.",
    "<b>Medium-term</b>: re-ranker (cross-encoder) setelah cosine retrieval untuk meningkatkan "
    "precision top-3.",
    "<b>Medium-term</b>: hybrid search (BM25 keyword + semantic) untuk handle kueri yang kaya "
    "kata kunci spesifik (kode saham, angka).",
    "<b>Long-term</b>: backtesting framework yang otomatis evaluate akurasi rekomendasi vs "
    "harga real per minggu/bulan/triwulan.",
    "<b>Long-term</b>: fine-tune Qwen3 dengan dataset Bahasa Indonesia finansial untuk "
    "domain adaptation.",
]))

story.append(Spacer(1, 1 * cm))
story.append(para(
    "<i>&mdash; AKHIR DOKUMEN &mdash;</i><br/><br/>"
    f"Disusun pada {datetime.now().strftime('%d %B %Y %H:%M WIB')}. "
    "Dokumen ini bersifat hidup &mdash; akan diupdate seiring evolusi sistem.",
    SUBTITLE,
))


# ============================================================
# Build PDF
# ============================================================

def header_footer(canvas, doc):
    canvas.saveState()
    # footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(COLOR_GRAY)
    footer_text = f"AI Saham Indonesia &mdash; Implementasi Detail | Halaman {doc.page}"
    # ReportLab canvas doesn't render &mdash; substitution; draw plain
    plain_footer = f"AI Saham Indonesia - Implementasi Detail   |   Halaman {doc.page}"
    canvas.drawString(2 * cm, 1.2 * cm, plain_footer)
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUTPUT_FILE),
    pagesize=A4,
    leftMargin=2 * cm,
    rightMargin=2 * cm,
    topMargin=1.8 * cm,
    bottomMargin=2 * cm,
    title="Laporan Implementasi Backend AI Saham Indonesia",
    author="Tim AIML Institute",
)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

# Hitung size file
size_kb = OUTPUT_FILE.stat().st_size / 1024
print(f"PDF dihasilkan: {OUTPUT_FILE}")
print(f"Ukuran file: {size_kb:.1f} KB")
print(f"Jumlah halaman: dapat dilihat saat membuka PDF.")
