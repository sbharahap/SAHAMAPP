"""
AI Saham Indonesia — SQLAlchemy Models (Async)

Modul ini mendefinisikan semua tabel database menggunakan SQLAlchemy 2.0
declarative style dengan Mapped type annotations. Semua operasi database
menggunakan async engine (asyncpg) untuk performa optimal.

Tabel:
    - Saham           : Master data emiten IDX
    - Fundamental     : Data fundamental harian (ROE, EPS, PBV, dll)
    - Makro           : Data makroekonomi (BI rate, inflasi, kurs)
    - Berita          : Metadata berita (teks lengkap di ChromaDB)
    - ScoringMingguan : Hasil scoring rekomendasi mingguan

Penggunaan:
    from backend.db.postgres import async_session, Saham, Fundamental

    async with async_session() as session:
        result = await session.execute(select(Saham))
        semua_saham = result.scalars().all()
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from backend.config import settings

# ============================================================
# Async Engine & Session Factory
# ============================================================

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,  # Log SQL queries di development
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Cek koneksi sebelum dipakai (hindari stale connection)
    pool_recycle=3600,    # Recycle koneksi setiap 1 jam
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Objek tetap bisa diakses setelah commit
)


# ============================================================
# Base Model
# ============================================================

class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class untuk semua SQLAlchemy model.

    AsyncAttrs memungkinkan akses lazy-loaded relationship secara async.
    Semua model mewarisi kolom created_at dan updated_at secara otomatis.
    """
    pass


# ============================================================
# Enum Types
# ============================================================

class Rekomendasi(str, enum.Enum):
    """Tipe rekomendasi saham dari scoring engine."""
    RECOMMENDED = "RECOMMENDED"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


# ============================================================
# Tabel 1: Saham — Master Data Emiten
# ============================================================

class Saham(Base):
    """
    Master data emiten yang terdaftar di IDX.

    Kolom `kode` adalah kode saham 4 huruf (contoh: BBCA, TLKM).
    Digunakan sebagai primary key karena kode saham bersifat unik
    dan jarang berubah.
    """

    __tablename__ = "saham"

    # Primary key: kode saham 4 huruf (BBCA, TLKM, ASII, dll)
    kode: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="Kode saham IDX (contoh: BBCA)",
    )
    nama_perusahaan: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nama lengkap perusahaan",
    )
    sektor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Sektor industri (contoh: Financials)",
    )
    sub_sektor: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Sub-sektor industri (contoh: Banks)",
    )
    tanggal_listing: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Tanggal pertama kali listing di IDX",
    )

    # Metadata timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Waktu record dibuat",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Waktu record terakhir diupdate",
    )

    # Relationships — satu saham punya banyak data fundamental, berita, dan skor
    fundamentals: Mapped[list["Fundamental"]] = relationship(
        back_populates="saham",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    beritas: Mapped[list["Berita"]] = relationship(
        back_populates="saham",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scorings: Mapped[list["ScoringMingguan"]] = relationship(
        back_populates="saham",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="saham",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Saham(kode='{self.kode}', nama='{self.nama_perusahaan}')>"


# ============================================================
# Tabel 2: Fundamental — Data Fundamental Harian
# ============================================================

class Fundamental(Base):
    """
    Data fundamental saham yang dikumpulkan secara harian.

    Setiap baris merepresentasikan snapshot fundamental satu saham
    pada satu tanggal tertentu. Data bersumber dari Yahoo Finance
    dan IDX API.

    Constraint: kombinasi (kode_saham, tanggal) harus unik
    untuk mencegah duplikasi data.
    """

    __tablename__ = "fundamental"
    __table_args__ = (
        UniqueConstraint("kode_saham", "tanggal", name="uq_fundamental_kode_tanggal"),
        Index("ix_fundamental_tanggal", "tanggal"),
        Index("ix_fundamental_kode_tanggal", "kode_saham", "tanggal"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    kode_saham: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("saham.kode", ondelete="CASCADE"),
        nullable=False,
        comment="Kode saham (FK ke tabel saham)",
    )
    tanggal: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Tanggal data fundamental",
    )

    # Data harga & volume
    harga_terakhir: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Harga penutupan terakhir (IDR)",
    )
    volume: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Volume transaksi harian (lot)",
    )

    # Rasio fundamental
    roe: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Return on Equity (%)",
    )
    eps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Earnings Per Share (IDR)",
    )
    pbv: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Price to Book Value (x)",
    )
    der: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Debt to Equity Ratio (x)",
    )
    market_cap: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Kapitalisasi pasar (IDR, dalam miliar)",
    )
    pe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Price to Earnings Ratio (x)",
    )
    dividend_yield: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Dividend Yield (%)",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationship
    saham: Mapped["Saham"] = relationship(back_populates="fundamentals")

    def __repr__(self) -> str:
        return (
            f"<Fundamental(kode='{self.kode_saham}', tanggal='{self.tanggal}', "
            f"harga={self.harga_terakhir})>"
        )


# ============================================================
# Tabel 3: Makro — Data Makroekonomi
# ============================================================

class Makro(Base):
    """
    Data makroekonomi Indonesia dari Bank Indonesia dan BPS.

    Menyimpan indikator seperti BI rate, inflasi, kurs USD/IDR,
    pertumbuhan GDP, dll. Setiap baris adalah satu observasi
    indikator pada tanggal tertentu.

    Contoh:
        indikator="bi_rate", nilai=6.25, satuan="persen"
        indikator="inflasi_yoy", nilai=3.05, satuan="persen"
        indikator="kurs_usd_idr", nilai=15850, satuan="IDR"
    """

    __tablename__ = "makro"
    __table_args__ = (
        UniqueConstraint("indikator", "tanggal", name="uq_makro_indikator_tanggal"),
        Index("ix_makro_tanggal", "tanggal"),
        Index("ix_makro_indikator", "indikator"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tanggal: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Tanggal data makro",
    )
    indikator: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Nama indikator (contoh: bi_rate, inflasi_yoy, kurs_usd_idr)",
    )
    nilai: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Nilai indikator",
    )
    satuan: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="persen",
        comment="Satuan nilai (contoh: persen, IDR, miliar_idr)",
    )
    sumber: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="bank_indonesia",
        comment="Sumber data (contoh: bank_indonesia, bps)",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Makro(indikator='{self.indikator}', tanggal='{self.tanggal}', "
            f"nilai={self.nilai} {self.satuan})>"
        )


# ============================================================
# Tabel 4: Berita — Metadata Berita (Teks di ChromaDB)
# ============================================================

class Berita(Base):
    """
    Metadata berita terkait saham Indonesia.

    Teks lengkap berita disimpan di ChromaDB sebagai embedding vector.
    Tabel ini hanya menyimpan metadata (judul, URL, sumber, sentimen)
    untuk query cepat dan tracking status embedding.

    Kolom skor_sentimen:
        -1.0 = sangat negatif
         0.0 = netral
        +1.0 = sangat positif
    """

    __tablename__ = "berita"
    __table_args__ = (
        # Cegah duplikasi berita berdasarkan URL
        UniqueConstraint("url", name="uq_berita_url"),
        Index("ix_berita_kode_saham", "kode_saham"),
        Index("ix_berita_tanggal_publish", "tanggal_publish"),
        Index("ix_berita_sumber", "sumber"),
        # Index untuk cari berita yang belum di-embedding
        Index("ix_berita_belum_embedding", "sudah_diembedding"),
        # Validasi skor sentimen dalam range -1 sampai 1
        CheckConstraint(
            "skor_sentimen IS NULL OR (skor_sentimen >= -1.0 AND skor_sentimen <= 1.0)",
            name="ck_berita_skor_sentimen_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    kode_saham: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("saham.kode", ondelete="SET NULL"),
        nullable=True,
        comment="Kode saham terkait (nullable karena berita bisa tentang pasar umum)",
    )
    judul: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Judul berita",
    )
    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
        comment="URL sumber berita (unik, mencegah duplikasi)",
    )
    sumber: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Sumber berita (contoh: kontan, idx_news, stockbit, google_news)",
    )
    tanggal_publish: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Tanggal dan waktu berita dipublikasikan",
    )

    # Analisis sentimen: -1.0 (sangat negatif) sampai +1.0 (sangat positif)
    skor_sentimen: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Skor sentimen berita (-1.0 s/d 1.0), NULL jika belum dianalisis",
    )

    # Isi berita lengkap
    isi_berita: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Isi berita lengkap (teks)",
    )

    # Status embedding: apakah teks berita sudah di-embed ke ChromaDB
    sudah_diembedding: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Apakah teks sudah di-embed ke ChromaDB",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationship
    saham: Mapped["Saham | None"] = relationship(back_populates="beritas")

    def __repr__(self) -> str:
        sentimen = f"{self.skor_sentimen:+.2f}" if self.skor_sentimen is not None else "N/A"
        return (
            f"<Berita(id={self.id}, kode='{self.kode_saham}', "
            f"sentimen={sentimen}, sumber='{self.sumber}')>"
        )


# ============================================================
# Tabel 5: ScoringMingguan — Hasil Scoring Rekomendasi
# ============================================================

class ScoringMingguan(Base):
    """
    Hasil scoring rekomendasi saham mingguan.

    Setiap Senin pagi, LangGraph agent menjalankan scoring terhadap
    semua saham aktif. Tabel ini menyimpan skor per komponen,
    bobot yang digunakan (bisa berbeda tiap minggu karena adaptif),
    skor total, rekomendasi, dan alasan dari LLM.

    Alur:
        1. LangGraph agent menentukan bobot adaptif berdasarkan kondisi pasar
        2. Scoring engine menghitung skor per komponen
        3. Skor total = weighted sum dari semua komponen
        4. LLM menghasilkan alasan dan rekomendasi (BUY/HOLD/SELL)
        5. Hasil disimpan di tabel ini
    """

    __tablename__ = "scoring_mingguan"
    __table_args__ = (
        UniqueConstraint(
            "kode_saham", "tanggal_scoring",
            name="uq_scoring_kode_tanggal",
        ),
        Index("ix_scoring_tanggal", "tanggal_scoring"),
        Index("ix_scoring_kode_tanggal", "kode_saham", "tanggal_scoring"),
        Index("ix_scoring_rekomendasi", "rekomendasi"),
        # Skor total harus antara 0 dan 100
        CheckConstraint(
            "skor_total >= 0 AND skor_total <= 100",
            name="ck_scoring_skor_total_range",
        ),
        # Confidence harus antara 0 dan 1
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_scoring_confidence_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    kode_saham: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("saham.kode", ondelete="CASCADE"),
        nullable=False,
        comment="Kode saham (FK ke tabel saham)",
    )
    tanggal_scoring: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Tanggal scoring dijalankan",
    )

    # Skor per komponen (skala 0–100)
    skor_total: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor total weighted (0-100)",
    )
    skor_fundamental: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor komponen fundamental (0-100)",
    )
    skor_sentimen: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor komponen sentimen (0-100)",
    )
    skor_sektor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor komponen sektor (0-100)",
    )
    skor_makro: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor komponen makroekonomi (0-100)",
    )
    skor_risiko: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor komponen risiko (0-100)",
    )

    # Bobot yang digunakan (bisa berbeda tiap minggu — adaptif oleh LangGraph)
    bobot_fundamental: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Bobot fundamental yang digunakan saat scoring",
    )
    bobot_sentimen: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Bobot sentimen yang digunakan saat scoring",
    )
    bobot_sektor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Bobot sektor yang digunakan saat scoring",
    )
    bobot_makro: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Bobot makroekonomi yang digunakan saat scoring",
    )
    bobot_risiko: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Bobot risiko yang digunakan saat scoring",
    )

    # Output LLM
    alasan: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Penjelasan dari LLM mengapa saham ini direkomendasikan",
    )
    rekomendasi: Mapped[Rekomendasi] = mapped_column(
        Enum(Rekomendasi, name="rekomendasi_enum"),
        nullable=False,
        comment="Rekomendasi: BUY, HOLD, atau SELL",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Tingkat kepercayaan model (0.0–1.0)",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationship
    saham: Mapped["Saham"] = relationship(back_populates="scorings")

    def __repr__(self) -> str:
        return (
            f"<ScoringMingguan(kode='{self.kode_saham}', "
            f"tanggal='{self.tanggal_scoring}', skor={self.skor_total:.1f}, "
            f"rekomendasi={self.rekomendasi.value})>"
        )



# ============================================================
# Tabel 6: Alert — Monitoring & Notifikasi Fluktuasi Sentimen
# ============================================================

class Alert(Base):
    """
    Data alert/notifikasi fluktuasi sentimen saham.
    
    Digunakan oleh alert_agent untuk mencatat alert yang dipicu
    akibat adanya perubahan sentimen signifikan (> 10 poin)
    berdasarkan berita baru yang masuk.
    """

    __tablename__ = "alert"
    __table_args__ = (
        Index("ix_alert_kode_saham", "kode_saham"),
        Index("ix_alert_tanggal", "tanggal"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    kode_saham: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("saham.kode", ondelete="CASCADE"),
        nullable=False,
        comment="Kode saham terkait (FK ke tabel saham)",
    )
    tanggal: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Waktu alert dipicu",
    )
    pesan: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Isi pesan alert",
    )
    delta: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Perubahan skor sentimen (delta)",
    )
    dikirim: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Apakah alert sudah dikirim ke external notification service",
    )

    # Relationship
    saham: Mapped["Saham"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return (
            f"<Alert(kode='{self.kode_saham}', tanggal='{self.tanggal}', "
            f"delta={self.delta:+.1f}, dikirim={self.dikirim})>"
        )


# ============================================================
# Tabel 7: RAGEvaluation — Hasil Evaluasi RAG Triad
# ============================================================

class RAGEvaluation(Base):
    """
    Hasil evaluasi RAG Triad (Context Relevance, Groundedness, Answer Relevance).

    Setiap baris merepresentasikan satu evaluasi terhadap interaksi chatbot RAG.
    Digunakan untuk mengukur kualitas pipeline RAG secara sistematis.
    """

    __tablename__ = "rag_evaluation"
    __table_args__ = (
        Index("ix_rag_eval_batch_id", "batch_id"),
        Index("ix_rag_eval_created_at", "created_at"),
        CheckConstraint(
            "context_relevance >= 1.0 AND context_relevance <= 5.0",
            name="ck_rag_eval_cr_range",
        ),
        CheckConstraint(
            "groundedness >= 1.0 AND groundedness <= 5.0",
            name="ck_rag_eval_g_range",
        ),
        CheckConstraint(
            "answer_relevance >= 1.0 AND answer_relevance <= 5.0",
            name="ck_rag_eval_ar_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    batch_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ID batch evaluasi (untuk mengelompokkan satu run evaluasi)",
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Pertanyaan user yang dievaluasi",
    )
    response_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Jawaban chatbot yang dievaluasi",
    )
    num_contexts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Jumlah dokumen konteks yang digunakan",
    )

    context_relevance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor Context Relevance (1-5)",
    )
    context_relevance_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Alasan skor Context Relevance",
    )
    groundedness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor Groundedness (1-5)",
    )
    groundedness_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Alasan skor Groundedness",
    )
    answer_relevance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Skor Answer Relevance (1-5)",
    )
    answer_relevance_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Alasan skor Answer Relevance",
    )
    avg_triad_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Rata-rata ketiga skor triad",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<RAGEvaluation(id={self.id}, batch='{self.batch_id}', "
            f"avg={self.avg_triad_score:.2f})>"
        )


# ============================================================
# Dependency Injection Helper
# ============================================================


async def get_db_session() -> AsyncSession:
    """
    Dependency untuk FastAPI yang menyediakan database session.

    Digunakan di route handler sebagai:
        @router.get("/saham")
        async def list_saham(db: AsyncSession = Depends(get_db_session)):
            ...

    Session otomatis di-close setelah request selesai.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
