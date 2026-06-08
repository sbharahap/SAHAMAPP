import asyncio
from sqlalchemy import select
from backend.db.postgres import async_session, ScoringMingguan

async def print_alasan():
    async with async_session() as session:
        stmt = select(ScoringMingguan).where(ScoringMingguan.alasan.is_not(None)).limit(3)
        res = await session.execute(stmt)
        rows = res.scalars().all()
        if not rows:
            print("Tidak ada data alasan di database saat ini.")
            return
        for r in rows:
            print(f"[{r.kode_saham} - {r.tanggal_scoring}]")
            print(f"Rekomendasi: {r.rekomendasi.value if r.rekomendasi else 'N/A'}")
            print(f"Alasan/AI Insight:\n{r.alasan}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(print_alasan())
