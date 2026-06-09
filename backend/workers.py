"""
AI Saham Indonesia — Background Workers & Jobs

Modul ini mendefinisikan pekerjaan background (cron jobs) yang dijalankan oleh
APScheduler, serta fungsi pembantu untuk inisialisasi awal database (seeding).
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.config import settings
from backend.db.postgres import (
    async_session,
    Saham,
    Fundamental,
    Makro,
    Berita,
    ScoringMingguan,
)
from backend.data.collectors.berita_collector import collect_berita_batch, collect_berita_pasar
from backend.data.collectors.fundamental_collector import collect_fundamental_batch, collect_last_prices
from backend.data.collectors.xbrl_collector import collect_xbrl_fundamental
from backend.data.collectors.makro_collector import collect_makro
from backend.data.preprocessors.data_cleaner import clean_berita, normalize_fundamental, hitung_sentimen_sederhana, hitung_sentimen_qwen
from backend.rag.indexer import index_batch_berita
from backend.agents.scoring_agent import jalankan_scoring
import backend.system_notifier as notifier

_WIB = timezone(timedelta(hours=7))

# Daftar default saham Bluechip Indonesia (LQ45 / Kompas100 teratas)
SAHAM_DEFAULT = [
    {"kode": "BBCA", "nama_perusahaan": "Bank Central Asia Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BBRI", "nama_perusahaan": "Bank Rakyat Indonesia (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BMRI", "nama_perusahaan": "Bank Mandiri (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "BBNI", "nama_perusahaan": "Bank Negara Indonesia (Persero) Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "TLKM", "nama_perusahaan": "Telkom Indonesia (Persero) Tbk", "sektor": "Infrastructure", "sub_sektor": "Telecommunication"},
    {"kode": "ASII", "nama_perusahaan": "Astra International Tbk", "sektor": "Consumer Discretionary", "sub_sektor": "Automotive"},
    {"kode": "UNVR", "nama_perusahaan": "Unilever Indonesia Tbk", "sektor": "Consumer Staples", "sub_sektor": "Personal Care Product"},
    {"kode": "ADRO", "nama_perusahaan": "Adaro Energy Indonesia Tbk", "sektor": "Energy", "sub_sektor": "Coal"},
    {"kode": "GGRM", "nama_perusahaan": "Gudang Garam Tbk", "sektor": "Consumer Staples", "sub_sektor": "Tobacco"},
    {"kode": "KLBF", "nama_perusahaan": "Kalbe Farma Tbk", "sektor": "Healthcare", "sub_sektor": "Pharmaceuticals"},
    {"kode": "ANTM", "nama_perusahaan": "Aneka Tambang Tbk", "sektor": "Basic Materials", "sub_sektor": "Metals & Mining"},
    {"kode": "PGAS", "nama_perusahaan": "Perusahaan Gas Negara Tbk", "sektor": "Energy", "sub_sektor": "Utilities"},
    {"kode": "ICBP", "nama_perusahaan": "Indofood CBP Sukses Makmur Tbk", "sektor": "Consumer Staples", "sub_sektor": "Processed Foods"},
    {"kode": "INDF", "nama_perusahaan": "Indofood Sukses Makmur Tbk", "sektor": "Consumer Staples", "sub_sektor": "Processed Foods"},
    {"kode": "UNTR", "nama_perusahaan": "United Tractors Tbk", "sektor": "Industrials", "sub_sektor": "Heavy Equipment"},
    {"kode": "PTBA", "nama_perusahaan": "Bukit Asam Tbk", "sektor": "Energy", "sub_sektor": "Coal"},
    {"kode": "MEDC", "nama_perusahaan": "Medco Energi Internasional Tbk", "sektor": "Energy", "sub_sektor": "Oil & Gas"},
    {"kode": "BRIS", "nama_perusahaan": "Bank Syariah Indonesia Tbk", "sektor": "Financials", "sub_sektor": "Banks"},
    {"kode": "AMRT", "nama_perusahaan": "Sumber Alfaria Trijaya Tbk", "sektor": "Consumer Staples", "sub_sektor": "Supermarkets & Convenience Stores"},
    {"kode": "MDKA", "nama_perusahaan": "Merdeka Copper Gold Tbk", "sektor": "Basic Materials", "sub_sektor": "Metals & Mining"},
]


async def seed_saham_if_empty() -> None:
    """
    Mengisi data master saham jika tabel saham masih kosong.
    """
    logger.info("🌱 Mengecek master data saham...")
    async with async_session() as session:
        result = await session.execute(select(Saham).limit(1))
        existing = result.scalars().first()

        if not existing:
            logger.info(f"🌱 Tabel saham kosong, mengisi dengan {len(SAHAM_DEFAULT)} saham default...")
            for item in SAHAM_DEFAULT:
                new_saham = Saham(
                    kode=item["kode"],
                    nama_perusahaan=item["nama_perusahaan"],
                    sektor=item["sektor"],
                    sub_sektor=item["sub_sektor"],
                    tanggal_listing=None,
                )
                session.add(new_saham)
            await session.commit()
            logger.info("🌱 Seeding saham selesai.")
        else:
            logger.info("🌱 Master data saham sudah terisi.")


async def scrape_news_job() -> None:
    """
    Background job untuk melakukan scraping berita saham dan berita pasar umum.
    Berita disimpan ke PostgreSQL, dianalisis sentimennya, dan dimasukkan ke ChromaDB (RAG).
    Dijalankan tiap 30 menit.
    """
    from backend.progress_tracker import set_progress
    logger.info("⏰ Memulai background job: Scraping Berita...")
    set_progress("scrape_news", 5, "running", "Mengambil daftar emiten...")
    try:
        # 1. Ambil daftar semua kode saham dari PostgreSQL
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            kode_saham_list = [row for row in result.scalars().all()]

        if not kode_saham_list:
            logger.warning("⚠️ Tidak ada kode saham terdaftar di DB. Skip scraping berita.")
            set_progress("scrape_news", 100, "idle", "Selesai (tidak ada emiten)")
            return

        # 2. Collect berita untuk semua saham (batch)
        logger.info(f"📰 Scraping berita untuk {len(kode_saham_list)} saham...")
        set_progress("scrape_news", 15, "running", f"Scraping berita untuk {len(kode_saham_list)} emiten...")
        
        async def news_progress_callback(current, total, kode):
            percent = int(15 + (current / total) * 15)  # Maps 15% to 30% progress
            set_progress("scrape_news", percent, "running", f"Scraping berita emiten {kode} ({current}/{total})...")
            
        raw_berita = await collect_berita_batch(kode_saham_list, hari_terakhir=3, progress_callback=news_progress_callback)

        # 3. Collect berita pasar umum
        logger.info("🌐 Scraping berita pasar umum...")
        set_progress("scrape_news", 30, "running", "Scraping berita pasar umum...")
        raw_berita_pasar = await collect_berita_pasar(hari_terakhir=2)
        raw_berita.extend(raw_berita_pasar)

        # 4. Clean data, analisis sentimen, dan simpan ke PostgreSQL
        saved_count = 0
        total_berita = len(raw_berita)
        async with async_session() as session:
            for index, item in enumerate(raw_berita):
                try:
                    percent = int(35 + (index / max(total_berita, 1)) * 45)
                    set_progress("scrape_news", percent, "running", f"Menganalisis sentimen berita {index+1}/{total_berita}...")
                    # Clean data
                    cleaned = clean_berita(item)
                    # Hitung sentimen menggunakan isi_berita jika ada, fallback ke judul (Kasus 5)
                    sentimen_text = cleaned.get("isi_berita") or cleaned["judul"]
                    cleaned["skor_sentimen"] = await hitung_sentimen_qwen(sentimen_text)
 
                    # Gunakan PostgreSQL insert ON CONFLICT DO NOTHING
                    stmt = pg_insert(Berita).values(
                        kode_saham=cleaned["kode_saham"],
                        judul=cleaned["judul"],
                        url=cleaned["url"],
                        sumber=cleaned["sumber"],
                        tanggal_publish=cleaned["tanggal_publish"],
                        skor_sentimen=cleaned["skor_sentimen"],
                        isi_berita=cleaned.get("isi_berita"),
                        sudah_diembedding=False
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
                    res = await session.execute(stmt)
                    if res.rowcount > 0:
                        saved_count += 1
                except Exception as e:
                    logger.error(f"❌ Gagal memproses single berita '{item.get('judul', '')[:30]}': {e}")
            await session.commit()
 
        logger.info(f"💾 {saved_count} berita baru berhasil disimpan ke PostgreSQL.")
 
        # 5. Ambil berita yang belum di-embed dari PostgreSQL, kirim ke ChromaDB
        async with async_session() as session:
            stmt = select(Berita).where(Berita.sudah_diembedding == False)
            result = await session.execute(stmt)
            unembedded_news = result.scalars().all()
 
            if unembedded_news:
                logger.info(f"🧠 Melakukan embedding untuk {len(unembedded_news)} berita baru ke ChromaDB...")
                set_progress("scrape_news", 85, "running", f"Melakukan embedding {len(unembedded_news)} berita ke ChromaDB...")
                
                # Ubah model SQLAlchemy ke format list of dict untuk indexer
                berita_dict_list = []
                for n in unembedded_news:
                    berita_dict_list.append({
                        "id": n.id,
                        "kode_saham": n.kode_saham,
                        "judul": n.judul,
                        "url": n.url,
                        "sumber": n.sumber,
                        "tanggal_publish": n.tanggal_publish,
                        "isi_berita": n.isi_berita,
                    })
 
                # Jalankan indexing
                stats = await index_batch_berita(berita_dict_list)
                
                if stats["berhasil"] > 0:
                    # Update status sudah_diembedding di Postgres
                    success_urls = [n["url"] for n in berita_dict_list]
                    # Kita lakukan chunk update status
                    for n in unembedded_news:
                        if n.url in success_urls:
                            n.sudah_diembedding = True
                    await session.commit()
                    logger.info(f"✅ Embedding selesai: {stats['berhasil']} berita ter-index ke ChromaDB.")
            else:
                logger.info("🧠 Tidak ada berita baru untuk di-embed.")
        
        set_progress("scrape_news", 100, "idle", f"Selesai (Berhasil menyimpan {saved_count} berita)")

    except Exception as e:
        logger.error(f"❌ Gagal menjalankan scraping berita: {e}")
        set_progress("scrape_news", 0, "failed", f"Gagal: {e}")
    logger.info("⏰ Background job: Scraping Berita selesai.")


async def scrape_fundamental_job() -> None:
    """
    Background job untuk memperbarui data fundamental dan harga harian emiten.
    Dijalankan tiap hari.
    """
    from backend.progress_tracker import set_progress
    logger.info("⏰ Memulai background job: Scraping Fundamental...")
    set_progress("scrape_fundamental", 5, "running", "Mengambil daftar emiten...")
    try:
        # 1. Ambil daftar semua kode saham
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            kode_saham_list = [row for row in result.scalars().all()]

        if not kode_saham_list:
            logger.warning("⚠️ Tidak ada kode saham terdaftar di DB.")
            set_progress("scrape_fundamental", 100, "idle", "Selesai (tidak ada emiten)")
            return

        # 2. Collect fundamental dari Yahoo Finance
        logger.info(f"📊 Mengambil fundamental untuk {len(kode_saham_list)} saham...")
        set_progress("scrape_fundamental", 15, "running", f"Mengambil data fundamental dari Yahoo Finance...")
        raw_fund = await collect_fundamental_batch(kode_saham_list, batch_size=10)

        # 3. Bersihkan dan simpan ke PostgreSQL
        saved_count = 0
        total_stocks = len(raw_fund)
        async with async_session() as session:
            for index, item in enumerate(raw_fund):
                try:
                    kode = item.get("kode_saham")
                    percent = int(20 + (index / max(total_stocks, 1)) * 80)
                    set_progress("scrape_fundamental", percent, "running", f"Memproses fundamental & XBRL {kode} ({index+1}/{total_stocks})...")
                    
                    if kode:
                        logger.info(f"🔍 Mengambil data XBRL IDX untuk {kode}...")
                        xbrl_data = await collect_xbrl_fundamental(kode)
                        if xbrl_data:
                            item["roe"] = xbrl_data.get("roe")
                            item["eps"] = xbrl_data.get("eps")
                            item["der"] = xbrl_data.get("der")
                            
                            # Rekalkulasi PE & PBV menggunakan harga penutupan terupdate
                            harga = item.get("harga_terakhir")
                            if harga is not None:
                                if item["eps"] and item["eps"] != 0:
                                    item["pe_ratio"] = round(harga / item["eps"], 2)
                                    if item["roe"] is not None:
                                        item["pbv"] = round(item["pe_ratio"] * (item["roe"] / 100.0), 2)
                        
                        # Delay kecil agar sopan ke IDX API
                        await asyncio.sleep(1.0)

                    cleaned = normalize_fundamental(item)

                    # Simpan/Upsert ke fundamental harian
                    # Kombinasi (kode_saham, tanggal) unik
                    stmt = pg_insert(Fundamental).values(
                        kode_saham=cleaned["kode_saham"],
                        tanggal=cleaned["tanggal"],
                        harga_terakhir=cleaned["harga_terakhir"],
                        volume=cleaned["volume"],
                        roe=cleaned["roe"],
                        eps=cleaned["eps"],
                        pbv=cleaned["pbv"],
                        der=cleaned["der"],
                        market_cap=cleaned["market_cap"],
                        pe_ratio=cleaned["pe_ratio"],
                        dividend_yield=cleaned["dividend_yield"]
                    )
                    
                    # Update jika duplikat di hari yang sama
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_fundamental_kode_tanggal",
                        set_={
                            "harga_terakhir": cleaned["harga_terakhir"],
                            "volume": cleaned["volume"],
                            "roe": cleaned["roe"],
                            "eps": cleaned["eps"],
                            "pbv": cleaned["pbv"],
                            "der": cleaned["der"],
                            "market_cap": cleaned["market_cap"],
                            "pe_ratio": cleaned["pe_ratio"],
                            "dividend_yield": cleaned["dividend_yield"]
                        }
                    )
                    await session.execute(stmt)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"❌ Gagal memproses fundamental {item.get('kode_saham', '')}: {e}")
            await session.commit()
        logger.info(f"💾 {saved_count} data fundamental berhasil disimpan/diperbarui di PostgreSQL.")
        set_progress("scrape_fundamental", 100, "idle", "Selesai")

    except Exception as e:
        logger.error(f"❌ Gagal menjalankan scraping fundamental: {e}")
        set_progress("scrape_fundamental", 0, "failed", f"Gagal: {e}")
    logger.info("⏰ Background job: Scraping Fundamental selesai.")


async def scrape_makro_job() -> None:
    """
    Background job untuk memperbarui data makroekonomi (BI rate, Inflasi, kurs USD/IDR, IHSG).
    Dijalankan tiap hari.
    """
    from backend.progress_tracker import set_progress
    logger.info("⏰ Memulai background job: Scraping Makroekonomi...")
    set_progress("scrape_makro", 10, "running", "Menghubungkan ke API Bank Indonesia & BPS...")
    try:
        raw_makro = await collect_makro()

        set_progress("scrape_makro", 50, "running", "Menyimpan indikator makroekonomi ke database...")
        saved_count = 0
        async with async_session() as session:
            for item in raw_makro:
                try:
                    stmt = pg_insert(Makro).values(
                        tanggal=item["tanggal"],
                        indikator=item["indikator"],
                        nilai=item["nilai"],
                        satuan=item["satuan"],
                        sumber=item["sumber"]
                    )
                    # Update jika tanggal & indikator duplikat
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_makro_indikator_tanggal",
                        set_={
                            "nilai": item["nilai"],
                            "satuan": item["satuan"],
                            "sumber": item["sumber"]
                        }
                    )
                    await session.execute(stmt)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"❌ Gagal memproses data makro {item.get('indikator', '')}: {e}")
            await session.commit()
        logger.info(f"💾 {saved_count} data makroekonomi berhasil disimpan/diperbarui.")

        # Index data makro ke ChromaDB (Kasus 1)
        if raw_makro:
            try:
                from backend.rag.indexer import index_data_makro
                
                summary_parts = []
                for item in raw_makro:
                    summary_parts.append(
                        f"- {item['indikator'].replace('_', ' ').upper()}: {item['nilai']} {item['satuan']} (Sumber: {item['sumber']})"
                    )
                
                summary_text = f"Kondisi Makroekonomi Indonesia per {date.today().isoformat()}:\n" + "\n".join(summary_parts)
                
                logger.info("📥 Meng-index ringkasan data makro ke ChromaDB...")
                set_progress("scrape_makro", 80, "running", "Meng-index ringkasan makro ke ChromaDB...")
                await index_data_makro(summary_text, indikator="ringkasan_makro", sumber="system_generated")
            except Exception as ex_index:
                logger.error(f"❌ Gagal meng-index data makro ke ChromaDB: {ex_index}")
        
        set_progress("scrape_makro", 100, "idle", "Selesai")

    except Exception as e:
        logger.error(f"❌ Gagal menjalankan scraping makroekonomi: {e}")
        set_progress("scrape_makro", 0, "failed", f"Gagal: {e}")
    logger.info("⏰ Background job: Scraping Makroekonomi selesai.")


async def run_scoring_job() -> None:
    """
    Background job untuk melakukan scoring mingguan (top 10 rekomendasi).
    Dijalankan setiap hari Senin jam 06:00 pagi.
    """
    from backend.progress_tracker import set_progress
    logger.info("⏰ Memulai background job: Scoring Rekomendasi Mingguan...")
    set_progress("run_scoring", 5, "running", "Memuat daftar emiten...")
    try:
        # 1. Ambil daftar semua kode saham
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            kode_saham_list = [row for row in result.scalars().all()]

        if not kode_saham_list:
            msg = "Tidak ada kode saham terdaftar untuk di-scoring."
            logger.warning(f"⚠️ {msg}")
            notifier.report_error("scoring_job", msg, level="ERROR", auto_open_browser=True)
            set_progress("run_scoring", 0, "failed", msg)
            return

        # 2. Jalankan pipeline scoring
        logger.info(f"🚀 Menjalankan scoring untuk {len(kode_saham_list)} saham...")
        set_progress("run_scoring", 15, "running", f"Menjalankan scoring untuk {len(kode_saham_list)} emiten...")
        await jalankan_scoring(kode_saham_list, simpan_ke_db=True)
        logger.info("✅ Scoring rekomendasi mingguan selesai.")
        notifier.report_info("scoring_job", f"Scoring mingguan selesai untuk {len(kode_saham_list)} emiten. Lihat hasil di tab Rekomendasi.")
        set_progress("run_scoring", 100, "idle", "Selesai")

    except RuntimeError as e:
        # RuntimeError dilempar oleh scoring_agent jika ada emiten yang gagal atau DB offline
        msg = f"Scoring DIHENTIKAN karena error kritis: {e}"
        logger.critical(f"🚨 {msg}")
        notifier.report_error("scoring_job", msg, level="CRITICAL", auto_open_browser=True)
        set_progress("run_scoring", 0, "failed", msg)
    except Exception as e:
        msg = f"Gagal menjalankan scoring mingguan: {type(e).__name__}: {e}"
        logger.error(f"❌ {msg}")
        notifier.report_error("scoring_job", msg, level="ERROR", auto_open_browser=True)
        set_progress("run_scoring", 0, "failed", msg)
    logger.info("⏰ Background job: Scoring selesai.")


async def update_last_prices_job() -> None:
    """
    Background job untuk memperbarui hanya harga_terakhir dan volume saham.
    Dijalankan setiap 30 menit sekali.
    """
    logger.info("⏰ Memulai background job: Update Last Price (30 Menit Sekali)...")
    try:
        # 1. Ambil daftar semua kode saham
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            kode_saham_list = [row for row in result.scalars().all()]

        if not kode_saham_list:
            logger.warning("⚠️ Tidak ada kode saham terdaftar di DB.")
            return

        # 2. Ambil update harga tercepat dari Yahoo Finance
        logger.info(f"📊 Mengambil update harga cepat untuk {len(kode_saham_list)} saham...")
        raw_prices = await collect_last_prices(kode_saham_list)

        # 3. Simpan/Update ke PostgreSQL
        updated_count = 0
        async with async_session() as session:
            for data in raw_prices:
                try:
                    if data["harga_terakhir"] is not None:
                        # Update / Upsert ke fundamental harian (uq_fundamental_kode_tanggal)
                        # Kita gunakan ON CONFLICT DO UPDATE untuk update harga_terakhir & volume saja
                        stmt = pg_insert(Fundamental).values(
                            kode_saham=data["kode_saham"],
                            tanggal=data["tanggal"],
                            harga_terakhir=data["harga_terakhir"],
                            volume=data["volume"]
                        )
                        stmt = stmt.on_conflict_do_update(
                            constraint="uq_fundamental_kode_tanggal",
                            set_={
                                "harga_terakhir": data["harga_terakhir"],
                                "volume": data["volume"]
                            }
                        )
                        await session.execute(stmt)
                        updated_count += 1
                except Exception as e:
                    logger.error(f"❌ Gagal memproses update harga untuk {data.get('kode_saham', '')}: {e}")
            await session.commit()
            
        logger.info(f"💾 {updated_count} harga saham berhasil diperbarui di PostgreSQL.")
    except Exception as e:
        logger.error(f"❌ Gagal menjalankan job update last price: {e}")
    logger.info("⏰ Background job: Update Last Price selesai.")
