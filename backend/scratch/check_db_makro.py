import asyncio
from backend.db.postgres import async_session, Makro, Berita
from sqlalchemy import select, func

async def check_db():
    async with async_session() as session:
        # Check macro
        res_makro = await session.execute(select(Makro.indikator, Makro.nilai, Makro.tanggal))
        rows_makro = res_makro.all()
        print("--- MAKRO TABLE ---")
        for r in rows_makro:
            print(f"Indikator: {r[0]}, Nilai: {r[1]}, Tanggal: {r[2]}")

        # Check latest alert
        from backend.db.postgres import Alert
        res_alert = await session.execute(select(Alert.kode_saham, Alert.pesan, Alert.tanggal).order_by(Alert.tanggal.desc()).limit(3))
        print("--- LATEST ALERTS ---")
        for r in res_alert.all():
            print(f"Stock: {r[0]}, Msg: {r[1]}, Tanggal: {r[2]}")

if __name__ == "__main__":
    asyncio.run(check_db())
