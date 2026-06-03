"""
AI Saham Indonesia — Inisialisasi Database

Modul ini menangani pembuatan semua tabel di PostgreSQL saat pertama
kali dijalankan. Menggunakan async engine dari postgres.py.

Cara menjalankan:
    # Dari root proyek
    python -m backend.db.init_db

    # Atau dari kode Python
    import asyncio
    from backend.db.init_db import init_database
    asyncio.run(init_database())

Catatan:
    - Untuk migration di production, gunakan Alembic
    - Script ini hanya untuk inisialisasi awal (development)
    - Tabel yang sudah ada TIDAK akan di-drop/recreate
"""

import asyncio
import sys
from pathlib import Path

from loguru import logger

# Konfigurasi loguru — format yang readable untuk output init
logger.remove()  # Hapus handler default
logger.add(
    sys.stderr,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{message}</cyan>"
    ),
    level="INFO",
    colorize=True,
)


async def init_database() -> None:
    """
    Membuat semua tabel yang didefinisikan di postgres.py.

    Fungsi ini:
    1. Mengimpor semua model agar terdaftar di metadata Base
    2. Membuat koneksi ke PostgreSQL
    3. Menjalankan CREATE TABLE IF NOT EXISTS untuk setiap model
    4. Menutup koneksi

    Tabel yang sudah ada tidak akan di-drop atau dimodifikasi.
    Untuk perubahan skema, gunakan Alembic migration.
    """
    # Import di dalam fungsi untuk menghindari circular import
    # dan memastikan semua model sudah terdaftar di Base.metadata
    from backend.db.postgres import Base, engine

    logger.info("🚀 Memulai inisialisasi database AI Saham Indonesia...")
    logger.info(f"📦 Database engine: {engine.url.render_as_string(hide_password=True)}")

    try:
        async with engine.begin() as conn:
            # Daftarkan semua tabel yang ada di metadata
            tabel_terdaftar = list(Base.metadata.tables.keys())
            logger.info(
                f"📋 Tabel yang akan dibuat: {', '.join(tabel_terdaftar)} "
                f"({len(tabel_terdaftar)} tabel)"
            )

            # CREATE TABLE IF NOT EXISTS — aman dijalankan berulang kali
            await conn.run_sync(Base.metadata.create_all)
            
            # Tambahkan kolom isi_berita jika belum ada
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE berita ADD COLUMN IF NOT EXISTS isi_berita TEXT;"))

        logger.info("✅ Semua tabel berhasil dibuat!")
        logger.info("")
        logger.info("📊 Ringkasan tabel:")
        for nama_tabel in tabel_terdaftar:
            tabel = Base.metadata.tables[nama_tabel]
            kolom = [col.name for col in tabel.columns]
            logger.info(f"   • {nama_tabel} ({len(kolom)} kolom): {', '.join(kolom)}")

    except Exception as e:
        logger.error(f"❌ Gagal membuat tabel: {e}")
        logger.error(
            "💡 Pastikan PostgreSQL sudah berjalan: docker compose up -d postgres"
        )
        raise

    finally:
        # Tutup engine dan semua koneksi di pool
        await engine.dispose()
        logger.info("🔌 Koneksi database ditutup.")


async def drop_all_tables() -> None:
    """
    ⚠️ BERBAHAYA: Menghapus SEMUA tabel dari database.

    Hanya gunakan untuk development/testing. JANGAN jalankan di production.
    Semua data akan hilang secara permanen.
    """
    from backend.db.postgres import Base, engine

    logger.warning("⚠️  MENGHAPUS SEMUA TABEL — hanya untuk development!")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    logger.info("🗑️  Semua tabel berhasil dihapus.")


# ============================================================
# Entry point: python -m backend.db.init_db
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  AI Saham Indonesia — Database Initialization")
    logger.info("=" * 60)
    logger.info("")

    asyncio.run(init_database())
