import asyncio
from sqlalchemy import select
from backend.db.postgres import async_session, Saham, Fundamental, Makro, Berita, ScoringMingguan, Alert

async def query_samples():
    async with async_session() as session:
        print("=== SAHAM ===")
        stmt = select(Saham).limit(3)
        res = await session.execute(stmt)
        saham_list = res.scalars().all()
        for s in saham_list:
            print(f"Kode: {s.kode}, Nama: {s.nama_perusahaan}, Sektor: {s.sektor}, Subsektor: {s.sub_sektor}, Listing: {s.tanggal_listing}")
            
        print("\n=== FUNDAMENTAL ===")
        stmt = select(Fundamental).limit(3)
        res = await session.execute(stmt)
        fund_list = res.scalars().all()
        for f in fund_list:
            print(f"Kode: {f.kode_saham}, Tanggal: {f.tanggal}, Harga: {f.harga_terakhir}, ROE: {f.roe}, EPS: {f.eps}, PBV: {f.pbv}, DER: {f.der}, Cap: {f.market_cap}")
            
        print("\n=== MAKRO ===")
        stmt = select(Makro).limit(3)
        res = await session.execute(stmt)
        makro_list = res.scalars().all()
        for m in makro_list:
            print(f"Tanggal: {m.tanggal}, Indikator: {m.indikator}, Nilai: {m.nilai}, Satuan: {m.satuan}, Sumber: {m.sumber}")
            
        print("\n=== BERITA ===")
        stmt = select(Berita).limit(3)
        res = await session.execute(stmt)
        berita_list = res.scalars().all()
        for b in berita_list:
            print(f"Kode: {b.kode_saham}, Judul: {b.judul[:50]}..., URL: {b.url[:50]}..., Sumber: {b.sumber}, Sentimen: {b.skor_sentimen}")
            
        print("\n=== SCORING ===")
        stmt = select(ScoringMingguan).limit(3)
        res = await session.execute(stmt)
        scoring_list = res.scalars().all()
        for sc in scoring_list:
            print(f"Kode: {sc.kode_saham}, Tanggal: {sc.tanggal_scoring}, Total: {sc.skor_total}, Rek: {sc.rekomendasi.value if sc.rekomendasi else None}, Conf: {sc.confidence}")
            
        print("\n=== ALERT ===")
        stmt = select(Alert).limit(3)
        res = await session.execute(stmt)
        alert_list = res.scalars().all()
        for al in alert_list:
            print(f"Kode: {al.kode_saham}, Tanggal: {al.tanggal}, Pesan: {al.pesan[:50]}..., Delta: {al.delta}")

if __name__ == "__main__":
    asyncio.run(query_samples())
