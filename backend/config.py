"""
AI Saham Indonesia — Konfigurasi Aplikasi

Modul ini menggunakan pydantic-settings untuk membaca semua environment
variables dari file .env. Semua konfigurasi terpusat di sini sehingga
modul lain cukup import `settings` tanpa perlu membaca env vars sendiri.

Penggunaan:
    from backend.config import settings

    print(settings.database_url)
    print(settings.ollama_model)
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory proyek (satu level di atas backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Konfigurasi utama aplikasi AI Saham Indonesia.

    Semua nilai dibaca dari environment variables atau file .env.
    Nilai default disediakan untuk development, tapi WAJIB di-override
    untuk production (terutama password dan API keys).
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Abaikan env vars yang tidak terdefinisi
    )

    # ================================================================
    # Aplikasi
    # ================================================================
    app_name: str = Field(
        default="AI Saham Indonesia",
        description="Nama aplikasi",
    )
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment aplikasi saat ini",
    )
    app_debug: bool = Field(
        default=True,
        description="Mode debug (auto-reload, verbose logging)",
    )
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Level logging minimum",
    )
    app_host: str = Field(
        default="0.0.0.0",
        description="Host untuk menjalankan FastAPI server",
    )
    app_port: int = Field(
        default=8080,
        description="Port untuk menjalankan FastAPI server",
    )

    # ================================================================
    # PostgreSQL
    # ================================================================
    postgres_host: str = Field(
        default="localhost",
        description="Hostname PostgreSQL",
    )
    postgres_port: int = Field(
        default=5432,
        description="Port PostgreSQL",
    )
    postgres_db: str = Field(
        default="saham_db",
        description="Nama database PostgreSQL",
    )
    postgres_user: str = Field(
        default="saham_user",
        description="Username PostgreSQL",
    )
    postgres_password: str = Field(
        default="saham_secret_2024",
        description="Password PostgreSQL — WAJIB diganti di production!",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """URL koneksi PostgreSQL async (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """URL koneksi PostgreSQL sync (untuk Alembic migration)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ================================================================
    # ChromaDB
    # ================================================================
    chroma_host: str = Field(
        default="localhost",
        description="Hostname ChromaDB",
    )
    chroma_port: int = Field(
        default=8000,
        description="Port ChromaDB",
    )
    chroma_server_authn_credentials: str = Field(
        default="",
        description="Credential autentikasi ChromaDB (opsional)",
    )
    chroma_server_authn_provider: str = Field(
        default="",
        description="Provider autentikasi ChromaDB (opsional)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chroma_url(self) -> str:
        """URL lengkap untuk koneksi ke ChromaDB server."""
        return f"http://{self.chroma_host}:{self.chroma_port}"

    # ================================================================
    # Ollama — LLM Lokal (Qwen3 8B)
    # ================================================================
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL Ollama API",
    )
    ollama_model: str = Field(
        default="qwen3:8b",
        description="Nama model Ollama yang digunakan",
    )
    ollama_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature untuk generasi teks (0.0 = deterministik)",
    )
    ollama_num_ctx: int = Field(
        default=8192,
        ge=512,
        description="Ukuran context window",
    )
    ollama_timeout: int = Field(
        default=120,
        ge=10,
        description="Timeout request ke Ollama dalam detik",
    )

    # ================================================================
    # Embedding — BGE-M3 (bilingual ID/EN)
    # ================================================================
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Nama model embedding dari HuggingFace",
    )
    embedding_device: Literal["mps", "cpu", "cuda"] = Field(
        default="mps",
        description="Device untuk inference embedding (mps untuk Apple Silicon)",
    )
    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size saat membuat embedding",
    )

    # ================================================================
    # Scheduler — APScheduler
    # ================================================================
    scoring_cron_day_of_week: str = Field(
        default="mon",
        description="Hari scoring dijalankan (format cron: mon, tue, dst)",
    )
    scoring_cron_hour: int = Field(
        default=6,
        ge=0,
        le=23,
        description="Jam scoring dijalankan (0-23)",
    )
    scoring_cron_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Menit scoring dijalankan (0-59)",
    )
    news_scrape_interval_minutes: int = Field(
        default=30,
        ge=5,
        description="Interval scraping berita dalam menit",
    )
    alert_check_interval_minutes: int = Field(
        default=30,
        ge=5,
        description="Interval pengecekan alert dalam menit",
    )

    # ================================================================
    # Scoring Engine — Bobot Default
    # ================================================================
    score_weight_fundamental: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Bobot skor fundamental (default 30%)",
    )
    score_weight_sentimen: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Bobot skor sentimen (default 25%)",
    )
    score_weight_sektor: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Bobot skor sektor (default 20%)",
    )
    score_weight_makro: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Bobot skor makroekonomi (default 15%)",
    )
    score_weight_risiko: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Bobot skor risiko (default 10%)",
    )
    top_k_saham: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Jumlah saham dalam rekomendasi mingguan",
    )

    @field_validator("score_weight_risiko")
    @classmethod
    def validate_total_bobot(cls, v: float, info) -> float:
        """Validasi bahwa total semua bobot scoring = 1.0 (toleransi 0.01)."""
        # Ambil semua bobot yang sudah di-parse
        data = info.data
        total = (
            data.get("score_weight_fundamental", 0.30)
            + data.get("score_weight_sentimen", 0.25)
            + data.get("score_weight_sektor", 0.20)
            + data.get("score_weight_makro", 0.15)
            + v  # score_weight_risiko
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Total bobot scoring harus = 1.0, saat ini = {total:.4f}. "
                f"Periksa kembali nilai SCORE_WEIGHT_* di .env"
            )
        return v

    # ================================================================
    # Data Sources — URL & Konfigurasi
    # ================================================================
    yfinance_market_suffix: str = Field(
        default=".JK",
        description="Suffix ticker untuk saham IDX di Yahoo Finance",
    )
    kontan_rss_url: str = Field(
        default="https://www.kontan.co.id/rss",
        description="URL RSS feed Kontan",
    )
    idx_api_base_url: str = Field(
        default="https://www.idx.co.id/primary/ListedCompany",
        description="Base URL IDX API",
    )
    google_news_rss_url: str = Field(
        default=(
            "https://news.google.com/rss/search"
            "?q=saham+indonesia&hl=id&gl=ID&ceid=ID:id"
        ),
        description="URL Google News RSS untuk berita saham Indonesia",
    )
    bi_api_base_url: str = Field(
        default="https://www.bi.go.id/api",
        description="Base URL Bank Indonesia API",
    )
    bps_api_base_url: str = Field(
        default="https://webapi.bps.go.id/v1",
        description="Base URL BPS API",
    )

    # ================================================================
    # Tailscale VPN
    # ================================================================
    tailscale_hostname: str = Field(
        default="",
        description="Hostname Tailscale untuk akses dari iPhone",
    )

    # ================================================================
    # Helper Properties
    # ================================================================
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """Cek apakah aplikasi berjalan di mode development."""
        return self.app_env == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Cek apakah aplikasi berjalan di mode production."""
        return self.app_env == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def default_scoring_weights(self) -> dict[str, float]:
        """
        Dictionary bobot scoring default.
        Digunakan sebagai fallback jika LangGraph agent tidak mengubah bobot.
        """
        return {
            "fundamental": self.score_weight_fundamental,
            "sentimen": self.score_weight_sentimen,
            "sektor": self.score_weight_sektor,
            "makro": self.score_weight_makro,
            "risiko": self.score_weight_risiko,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Singleton factory untuk Settings.

    Menggunakan lru_cache agar Settings hanya di-instantiate sekali.
    Ini penting karena setiap instantiation membaca file .env dari disk.

    Penggunaan:
        from backend.config import get_settings

        settings = get_settings()
    """
    return Settings()


# Shortcut: langsung import `settings` tanpa perlu panggil fungsi
settings = get_settings()
