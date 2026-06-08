import asyncio
from sqlalchemy import text
from backend.db.postgres import engine

async def check_columns():
    async with engine.connect() as conn:
        res = await conn.execute(text(
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = 'scoring_mingguan'"
        ))
        rows = res.all()
        print("KOLOM DI DATABASE POSTGRESQL (scoring_mingguan):")
        for r in rows:
            print(f"- {r.column_name} ({r.data_type})")

if __name__ == "__main__":
    asyncio.run(check_columns())
