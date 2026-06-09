"""
AI Saham Indonesia — Seed & Initial Data Seeder Script

Script ini menginisialisasi database PostgreSQL, memasukkan 20 emiten saham IDX
paling likuid (watchlist utama), melakukan scraping data fundamental harian,
mengambil indikator makroekonomi, mengambil berita 7 hari terakhir, meng-index
berita ke ChromaDB untuk RAG, serta memicu scoring pertama kali.

Cara menjalankan:
    python -m backend.scripts.seed_data
"""

import asyncio
import sys
from datetime import date
from loguru import logger
from sqlalchemy import select

from backend.db.init_db import init_database
from backend.db.postgres import async_session, Saham
from backend.workers import (
    seed_saham_if_empty,
    scrape_fundamental_job,
    scrape_makro_job,
    scrape_news_job,
    run_scoring_job,
)

# 20 Saham paling likuid di bursa efek Indonesia
SAHAM_LIST_20 = [
    {"kode": "BBCA", "nama_perusahaan": "Bank Central Asia Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BBRI", "nama_perusahaan": "Bank Rakyat Indonesia (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BMRI", "nama_perusahaan": "Bank Mandiri (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BBNI", "nama_perusahaan": "Bank Negara Indonesia (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "TLKM", "nama_perusahaan": "Telkom Indonesia (Persero) Tbk", "sektor": "Infrastructure", "sub_sektor": "Telecommunication"},
    {"kode": "ASII", "nama_perusahaan": "Astra International Tbk", "sektor": "Consumer Discretionary", "sub_sektor": "Automotive"},
    {"kode": "UNVR", "nama_perusahaan": "Unilever Indonesia Tbk", "sektor": "Consumer Staples", "sub_sektor": "Personal Care Product"},
    {"kode": "ICBP", "nama_perusahaan": "Indofood CBP Sukses Makmur Tbk", "sektor": "Consumer Staples", "sub_sektor": "Processed Foods"},
    {"kode": "INDF", "nama_perusahaan": "Indofood Sukses Makmur Tbk", "sektor": "Consumer Staples", "sub_sektor": "Processed Foods"},
    {"kode": "AMRT", "nama_perusahaan": "Sumber Alfaria Trijaya Tbk", "sektor": "Consumer Staples", "sub_sektor": "Supermarkets & Convenience Stores"},
    {"kode": "GGRM", "nama_perusahaan": "Gudang Garam Tbk", "sektor": "Consumer Staples", "sub_sektor": "Tobacco"},
    {"kode": "BYAN", "nama_perusahaan": "Bayan Resources Tbk", "sektor": "Energy", "sub_sektor": "Coal"},
    {"kode": "KLBF", "nama_perusahaan": "Kalbe Farma Tbk", "sektor": "Healthcare", "sub_sektor": "Pharmaceuticals"},
    {"kode": "ANTM", "nama_perusahaan": "Aneka Tambang Tbk", "sektor": "Basic Materials", "sub_sektor": "Metals & Mining"},
    {"kode": "PGAS", "nama_perusahaan": "Perusahaan Gas Negara Tbk", "sektor": "Energy", "sub_sektor": "Utilities"},
    {"kode": "UNTR", "nama_perusahaan": "United Tractors Tbk", "sektor": "Industrials", "sub_sektor": "Heavy Equipment"},
    {"kode": "PTBA", "nama_perusahaan": "Bukit Asam Tbk", "sektor": "Energy", "sub_sektor": "Coal"},
    {"kode": "MEDC", "nama_perusahaan": "Medco Energi Internasional Tbk", "sektor": "Energy", "sub_sektor": "Oil & Gas"},
    {"kode": "BRIS", "nama_perusahaan": "Bank Syariah Indonesia Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "MDKA", "nama_perusahaan": "Merdeka Copper Gold Tbk", "sektor": "Basic Materials", "sub_sektor": "Metals & Mining"},
]


async def run_seeder() -> None:
    """
    Menjalankan proses seeding data awal secara berurutan.
    """
    logger.info("=" * 60)
    logger.info("🌱 MEMULAI PROSES SEEDING DATA AWAL")
    logger.info("=" * 60)

    # 1. Inisialisasi Database
    logger.info("Step 1: Menginisialisasi skema database relasional...")
    try:
        await init_database()
    except Exception as e:
        logger.critical(f"❌ Inisialisasi DB gagal: {e}. Harap pastikan Docker Compose sudah berjalan.")
        sys.exit(1)

    # 1b. Inisialisasi Vektor Database (ChromaDB Collections)
    logger.info("Step 1b: Menginisialisasi skema database vektor (ChromaDB)...")
    try:
        from backend.db.chroma import init_all_collections
        init_all_collections()
    except Exception as e:
        logger.error(f"❌ Inisialisasi ChromaDB collections gagal: {e}")

    # 2. Seeding Master Data Saham
    logger.info("Step 2: Memasukkan 20 emiten paling likuid...")
    async with async_session() as session:
        for item in SAHAM_LIST_20:
            # Cek apakah kode emiten sudah terdaftar
            stmt = select(Saham).where(Saham.kode == item["kode"])
            res = await session.execute(stmt)
            exists = res.scalar_one_or_none()

            if not exists:
                new_saham = Saham(
                    kode=item["kode"],
                    nama_perusahaan=item["nama_perusahaan"],
                    sektor=item["sektor"],
                    sub_sektor=item["sub_sektor"]
                )
                session.add(new_saham)
                logger.info(f"   ➕ Terdaftar: {item['kode']} - {item['nama_perusahaan']}")
        await session.commit()
    logger.info("✅ 20 Emiten Saham berhasil dipastikan terdaftar.")

    # 3. Scraping Indikator Makroekonomi
    logger.info("Step 3: Mengambil data indikator makroekonomi (BI rate, inflasi, kurs, IHSG)...")
    try:
        await scrape_makro_job()
    except Exception as e:
        logger.error(f"❌ Scraping data makro gagal: {e}")

    # 4. Scraping Fundamental Keuangan
    logger.info("Step 4: Mengambil data fundamental keuangan (Yahoo Finance) untuk seluruh saham...")
    try:
        await scrape_fundamental_job()
    except Exception as e:
        logger.error(f"❌ Scraping fundamental gagal: {e}")

    # 5. Scraping Berita & RAG Indexing ke ChromaDB
    logger.info("Step 5: Mengambil berita 7 hari terakhir dan membuat vektor embedding ChromaDB...")
    try:
        # Modifikasi scraping berita awal agar mengambil data lebih banyak
        await scrape_news_job()
    except Exception as e:
        logger.error(f"❌ Scraping & Indexing berita gagal: {e}")

    # 6. Jalankan Scoring Rekomendasi Pertama Kali
    logger.info("Step 6: Memicu scoring mingguan perdana untuk menghasilkan rekomendasi top 10...")
    try:
        await run_scoring_job()
    except Exception as e:
        logger.error(f"❌ Scoring awal gagal: {e}")

    logger.info("=" * 60)
    logger.info("🎉 SEEDING DATA AWAL SELESAI DENGAN SUKSES!")
    logger.info("💡 Jalankan `uvicorn backend.main:app --port 8080 --reload` untuk menyalakan server.")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Windows event loop policy override jika dijalankan di Windows, untuk Mac tidak masalah
    asyncio.run(run_seeder())
