import asyncio
from datetime import datetime, date
from sqlalchemy import select, func
from backend.db.postgres import async_session, Saham, Fundamental, Makro, Berita, ScoringMingguan

async def check_dates():
    async with async_session() as session:
        # Latest news publish date
        news_max = await session.scalar(select(func.max(Berita.tanggal_publish)))
        news_count_today = await session.scalar(
            select(func.count(Berita.id))
            .where(func.date(Berita.tanggal_publish) == date(2026, 6, 9))
        )
        total_news = await session.scalar(select(func.count(Berita.id)))
        
        # Latest fundamental date
        fund_max = await session.scalar(select(func.max(Fundamental.tanggal)))
        fund_count_today = await session.scalar(
            select(func.count(Fundamental.id))
            .where(Fundamental.tanggal == date(2026, 6, 9))
        )
        total_fund = await session.scalar(select(func.count(Fundamental.id)))
        
        # Latest makro date
        makro_max = await session.scalar(select(func.max(Makro.tanggal)))
        makro_count_today = await session.scalar(
            select(func.count(Makro.id))
            .where(Makro.tanggal == date(2026, 6, 9))
        )
        total_makro = await session.scalar(select(func.count(Makro.id)))
        
        print("DATABASE DIAGNOSTICS:")
        print(f"- Total Berita: {total_news}")
        print(f"- Tanggal Berita Terakhir: {news_max}")
        print(f"- Jumlah Berita Hari Ini (2026-06-09): {news_count_today}")
        print("")
        print(f"- Total Fundamental: {total_fund}")
        print(f"- Tanggal Fundamental Terakhir: {fund_max}")
        print(f"- Jumlah Fundamental Hari Ini (2026-06-09): {fund_count_today}")
        print("")
        print(f"- Total Makro: {total_makro}")
        print(f"- Tanggal Makro Terakhir: {makro_max}")
        print(f"- Jumlah Makro Hari Ini (2026-06-09): {makro_count_today}")

if __name__ == "__main__":
    asyncio.run(check_dates())
