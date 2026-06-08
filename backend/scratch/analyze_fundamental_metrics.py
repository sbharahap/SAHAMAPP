import asyncio
import numpy as np
import pandas as pd
from sqlalchemy import select
from backend.db.postgres import async_session, Fundamental, Saham

async def main():
    print("🔋 Menghubungkan ke database untuk menganalisis data fundamental 3 tahun...")
    async with async_session() as session:
        # Join Fundamental and Saham to get sector information
        stmt = (
            select(
                Fundamental.kode_saham,
                Saham.sektor,
                Fundamental.tanggal,
                Fundamental.pbv,
                Fundamental.pe_ratio,
                Fundamental.der
            )
            .join(Saham, Fundamental.kode_saham == Saham.kode)
            .order_by(Fundamental.tanggal.asc())
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            print("⚠️ Tidak ada data fundamental di database.")
            return
            
        print(f"📊 Ditemukan {len(rows)} data fundamental historis.")
        
        # Convert to pandas DataFrame for easy analysis
        data = []
        for r in rows:
            data.append({
                "kode_saham": r[0],
                "sektor": r[1],
                "tanggal": r[2],
                "pbv": r[3],
                "pe_ratio": r[4],
                "der": r[5]
            })
            
        df = pd.DataFrame(data)
        
        # Clean data (replace None/NaN)
        df['pbv'] = pd.to_numeric(df['pbv'], errors='coerce')
        df['pe_ratio'] = pd.to_numeric(df['pe_ratio'], errors='coerce')
        df['der'] = pd.to_numeric(df['der'], errors='coerce')
        
        print("\n=== STATISTIK KESELURUHAN (ALL SECTORS) ===")
        print(df[['pbv', 'pe_ratio', 'der']].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]))
        
        print("\n=== RATA-RATA & PERSENTIL METRIK PER SEKTOR ===")
        sectors = df['sektor'].unique()
        
        results_by_sector = {}
        for sector in sectors:
            sector_df = df[df['sektor'] == sector]
            print(f"\n📁 Sektor: {sector} ({len(sector_df)} baris data)")
            
            pbv_stats = sector_df['pbv'].dropna()
            pe_stats = sector_df['pe_ratio'].dropna()
            der_stats = sector_df['der'].dropna()
            
            print("  --- PBV ---")
            if not pbv_stats.empty:
                print(f"    Rata-rata: {pbv_stats.mean():.2f} | Median: {pbv_stats.median():.2f}")
                print(f"    P25: {pbv_stats.quantile(0.25):.2f} | P75: {pbv_stats.quantile(0.75):.2f}")
            else:
                print("    Tidak ada data PBV")
                
            print("  --- PE Ratio ---")
            if not pe_stats.empty:
                # Filter out extreme outliers for mean/median calculations if any
                clean_pe = pe_stats[pe_stats.between(-100, 300)]
                print(f"    Rata-rata: {clean_pe.mean():.2f} | Median: {clean_pe.median():.2f}")
                print(f"    P25: {clean_pe.quantile(0.25):.2f} | P75: {clean_pe.quantile(0.75):.2f}")
            else:
                print("    Tidak ada data PE Ratio")
                
            print("  --- DER ---")
            if not der_stats.empty:
                print(f"    Rata-rata: {der_stats.mean():.2f} | Median: {der_stats.median():.2f}")
                print(f"    P25: {der_stats.quantile(0.25):.2f} | P75: {der_stats.quantile(0.75):.2f}")
            else:
                print("    Tidak ada data DER")
                
            # Store stats for review
            results_by_sector[sector] = {
                "pbv_mean": pbv_stats.mean() if not pbv_stats.empty else 1.2,
                "pbv_median": pbv_stats.median() if not pbv_stats.empty else 1.2,
                "pe_mean": clean_pe.mean() if not pe_stats.empty else 15.0,
                "pe_median": clean_pe.median() if not pe_stats.empty else 12.0,
                "der_mean": der_stats.mean() if not der_stats.empty else 1.0,
                "der_median": der_stats.median() if not der_stats.empty else 1.0,
            }

if __name__ == "__main__":
    asyncio.run(main())
