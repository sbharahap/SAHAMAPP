import asyncio
from sqlalchemy import text
from backend.db.postgres import engine

async def migrate():
    async with engine.begin() as conn:
        print("1. Changing column type to VARCHAR temporarily...")
        await conn.execute(text("ALTER TABLE scoring_mingguan ALTER COLUMN rekomendasi TYPE VARCHAR(50);"))
        
        print("2. Dropping old enum type...")
        await conn.execute(text("DROP TYPE IF EXISTS rekomendasi_enum CASCADE;"))
        
        print("3. Creating new enum type...")
        await conn.execute(text("CREATE TYPE rekomendasi_enum AS ENUM ('RECOMMENDED', 'NEUTRAL', 'NEGATIVE');"))
        
        print("4. Mapping existing data...")
        await conn.execute(text("UPDATE scoring_mingguan SET rekomendasi = 'RECOMMENDED' WHERE rekomendasi = 'BUY';"))
        await conn.execute(text("UPDATE scoring_mingguan SET rekomendasi = 'NEUTRAL' WHERE rekomendasi = 'HOLD';"))
        await conn.execute(text("UPDATE scoring_mingguan SET rekomendasi = 'NEGATIVE' WHERE rekomendasi = 'SELL';"))
        # Clean up any NULL or other residues
        await conn.execute(text("UPDATE scoring_mingguan SET rekomendasi = 'NEUTRAL' WHERE rekomendasi IS NULL OR rekomendasi NOT IN ('RECOMMENDED', 'NEUTRAL', 'NEGATIVE');"))
        
        print("5. Altering column type back to rekomendasi_enum...")
        await conn.execute(text("ALTER TABLE scoring_mingguan ALTER COLUMN rekomendasi TYPE rekomendasi_enum USING rekomendasi::rekomendasi_enum;"))
        
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
