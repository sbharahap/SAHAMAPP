import asyncio
from sqlalchemy import select, func
from backend.db.postgres import async_session, Fundamental

async def main():
    async with async_session() as session:
        res = await session.execute(select(func.count(Fundamental.id)).where(Fundamental.kode_saham == 'BBCA'))
        print(f"Jumlah baris BBCA di tabel fundamental: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(main())
