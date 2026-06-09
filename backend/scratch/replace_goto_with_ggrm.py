import asyncio
from loguru import logger
from sqlalchemy import select, delete
from backend.db.postgres import async_session, Saham, Berita
from backend.db.chroma import get_collection

async def migrate():
    # Hapus GOTO dari PostgreSQL
    async with async_session() as session:
        # Cek apakah GOTO ada di database
        stmt_goto = select(Saham).where(Saham.kode == "GOTO")
        res_goto = await session.execute(stmt_goto)
        goto_saham = res_goto.scalar_one_or_none()
        
        if goto_saham:
            logger.info("🗑️ Saham GOTO ditemukan. Menghapus data berita GOTO di PostgreSQL...")
            # Hapus berita terkait GOTO secara eksplisit dari Postgres agar bersih
            stmt_del_berita = delete(Berita).where(Berita.kode_saham == "GOTO")
            await session.execute(stmt_del_berita)
            
            logger.info("🗑️ Menghapus master saham GOTO (akan men-cascade fundamental, scoring, alert)...")
            await session.delete(goto_saham)
            await session.commit()
            logger.info("🗑️ Saham GOTO beserta data terkait di PostgreSQL berhasil dihapus.")
        else:
            logger.info("ℹ️ Saham GOTO tidak ditemukan di PostgreSQL.")

    # Hapus berita GOTO dari ChromaDB jika terhubung
    try:
        logger.info("🧠 Menghubungkan ke ChromaDB untuk membersihkan berita GOTO...")
        col_berita = get_collection("berita")
        count_before = col_berita.count()
        col_berita.delete(where={"kode_saham": "GOTO"})
        count_after = col_berita.count()
        logger.info(f"🗑️ ChromaDB dibersihkan. Jumlah dokumen berita: {count_before} -> {count_after}")
    except Exception as e:
        logger.error(f"⚠️ Gagal menghapus berita GOTO dari ChromaDB: {e}")

    # Tambahkan GGRM ke PostgreSQL jika belum ada
    async with async_session() as session:
        stmt_ggrm = select(Saham).where(Saham.kode == "GGRM")
        res_ggrm = await session.execute(stmt_ggrm)
        ggrm_saham = res_ggrm.scalar_one_or_none()
        
        if not ggrm_saham:
            logger.info("➕ Menambahkan saham GGRM ke database...")
            new_saham = Saham(
                kode="GGRM",
                nama_perusahaan="Gudang Garam Tbk",
                sektor="Consumer Staples",
                sub_sektor="Tobacco"
            )
            session.add(new_saham)
            await session.commit()
            logger.info("➕ Saham GGRM berhasil ditambahkan.")
        else:
            logger.info("ℹ️ Saham GGRM sudah ada di database.")

if __name__ == "__main__":
    asyncio.run(migrate())
