"""
AI Saham Indonesia — Backfill Laporan Keuangan ke ChromaDB

Script standalone untuk mengisi ChromaDB collection `laporan_keuangan` dari data
XBRL IDX, TANPA harus menunggu scheduler `scrape_fundamental_job` berjalan.

Berguna untuk:
- One-off backfill setelah implementasi fitur indexing laporan keuangan
- Re-index ulang setelah update format teks naratif
- Mengisi data sebelum menjalankan evaluasi RAG (agar collection tidak kosong)

Cara menjalankan:
    python -m backend.scripts.backfill_laporan_keuangan
    python -m backend.scripts.backfill_laporan_keuangan --limit 5
    python -m backend.scripts.backfill_laporan_keuangan --kode BBCA,BBRI,BMRI
"""

import argparse
import asyncio
from loguru import logger
from sqlalchemy import select

from backend.db.postgres import async_session, Saham
from backend.data.collectors.xbrl_collector import collect_xbrl_fundamental
from backend.rag.indexer import index_laporan_keuangan
from backend.workers import _buat_teks_laporan_keuangan


async def backfill(kode_list: list[str] | None = None, limit: int | None = None) -> None:
    """
    Jalankan backfill laporan keuangan untuk daftar saham tertentu (atau semua).

    Args:
        kode_list: Daftar kode saham spesifik. None = ambil semua dari DB.
        limit: Batasi jumlah saham yang diproses (untuk testing).
    """
    # 1. Ambil daftar saham dari DB
    async with async_session() as session:
        stmt = select(Saham.kode, Saham.nama_perusahaan, Saham.sektor)
        if kode_list:
            stmt = stmt.where(Saham.kode.in_([k.upper() for k in kode_list]))
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        logger.error("❌ Tidak ada saham yang cocok di database.")
        return

    if limit:
        rows = rows[:limit]

    logger.info(f"📊 Memulai backfill laporan keuangan untuk {len(rows)} emiten...")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for idx, (kode, nama_perusahaan, sektor) in enumerate(rows, start=1):
        logger.info(f"[{idx}/{len(rows)}] 🔍 Memproses {kode} - {nama_perusahaan}...")

        try:
            xbrl_data = await collect_xbrl_fundamental(kode)

            if not xbrl_data:
                logger.warning(f"⚠️ {kode}: Tidak ditemukan data XBRL. Dilewati.")
                skipped_count += 1
                continue

            teks_laporan = _buat_teks_laporan_keuangan(
                kode=kode,
                nama_perusahaan=nama_perusahaan,
                sektor=sektor,
                xbrl_data=xbrl_data,
            )

            tahun_lap = xbrl_data.get("tahun", "?")
            periode_lap = xbrl_data.get("periode", "Audit")

            chunks = await index_laporan_keuangan(
                teks=teks_laporan,
                kode_saham=kode,
                periode=f"{periode_lap} {tahun_lap}",
                sumber="idx_xbrl",
            )

            if chunks > 0:
                success_count += 1
                logger.success(
                    f"✅ {kode} ({periode_lap} {tahun_lap}): "
                    f"di-index ({chunks} chunk). "
                    f"ROE={xbrl_data.get('roe')}% DER={xbrl_data.get('der')}x"
                )
            else:
                logger.warning(f"⚠️ {kode}: index mengembalikan 0 chunk.")
                fail_count += 1

        except Exception as e:
            logger.error(f"❌ {kode}: Gagal — {e}")
            fail_count += 1

        # Rate limit kecil agar sopan ke IDX API
        await asyncio.sleep(1.5)

    # Ringkasan akhir
    logger.info("=" * 60)
    logger.info(f"📚 Backfill Selesai:")
    logger.info(f"   ✅ Berhasil di-index : {success_count}")
    logger.info(f"   ⚠️  Dilewati (no data): {skipped_count}")
    logger.info(f"   ❌ Gagal             : {fail_count}")
    logger.info(f"   📊 Total diproses    : {len(rows)}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Backfill laporan keuangan ke ChromaDB")
    parser.add_argument(
        "--kode",
        type=str,
        default=None,
        help="Comma-separated kode saham, contoh: BBCA,BBRI,BMRI. Default: semua.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Batasi jumlah saham yang diproses (untuk testing).",
    )
    args = parser.parse_args()

    kode_list = [k.strip().upper() for k in args.kode.split(",")] if args.kode else None
    asyncio.run(backfill(kode_list=kode_list, limit=args.limit))


if __name__ == "__main__":
    main()
