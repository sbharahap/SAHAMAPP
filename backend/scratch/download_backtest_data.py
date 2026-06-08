import yfinance as yf
import json
import os
import time
from datetime import datetime, date

SAHAM_LIST_20 = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GOTO", "KLBF",
    "ANTM", "PGAS", "UNTR", "PTBA", "MEDC", "BRIS", "AMRT", "MDKA", "ICBP", "INDF"
]

def serialize_df(df):
    """Converts pandas DataFrame index and columns to string keys for JSON serialization."""
    if df is None or df.empty:
        return {}
    # Convert index and columns to string
    df_clean = df.copy()
    df_clean.index = [str(x)[:10] for x in df_clean.index]
    df_clean.columns = [str(x)[:10] for x in df_clean.columns]
    return df_clean.to_dict()

def main():
    print("=" * 60)
    print("📥 DOWNLOAD DATA HISTORIS UNTUK BACKTEST (2022 - 2025)")
    print("=" * 60)
    
    start_date = "2021-11-01"  # Mulai lebih awal untuk data lag/buffer
    end_date = "2025-12-31"    # Selesai akhir 2025
    
    data_store = {
        "prices": {},
        "financials": {},
        "benchmark": {}
    }
    
    # 1. Download IHSG (Benchmark)
    print("📈 Downloading IHSG (^JKSE) price history...")
    try:
        ihsg = yf.Ticker("^JKSE")
        hist = ihsg.history(start=start_date, end=end_date)
        data_store["benchmark"] = serialize_df(hist[["Open", "High", "Low", "Close", "Volume"]])
        print(f"✅ IHSG downloaded: {len(hist)} rows.")
    except Exception as e:
        print(f"❌ Gagal download IHSG: {e}")

    # 2. Download tiap saham
    for i, kode in enumerate(SAHAM_LIST_20):
        symbol = f"{kode}.JK"
        print(f"\n({i+1}/{len(SAHAM_LIST_20)}) 📦 Downloading {symbol}...")
        
        # Download harga
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            data_store["prices"][kode] = serialize_df(hist[["Open", "High", "Low", "Close", "Volume"]])
            print(f"   - Harga: {len(hist)} baris")
        except Exception as e:
            print(f"   - ❌ Gagal download harga: {e}")
            continue
            
        # Download laporan keuangan
        try:
            # Annual
            annual_is = ticker.financials
            annual_bs = ticker.balance_sheet
            
            # Quarterly
            quarterly_is = ticker.quarterly_financials
            quarterly_bs = ticker.quarterly_balance_sheet
            
            data_store["financials"][kode] = {
                "annual_income_statement": serialize_df(annual_is),
                "annual_balance_sheet": serialize_df(annual_bs),
                "quarterly_income_statement": serialize_df(quarterly_is),
                "quarterly_balance_sheet": serialize_df(quarterly_bs),
            }
            print(f"   - Laporan Keuangan: Sukses")
        except Exception as e:
            print(f"   - ❌ Gagal download laporan keuangan: {e}")
            
        # Delay minimal agar tidak di-ban yfinance
        time.sleep(1.0)
        
    # Simpan hasil
    out_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "backtest_raw_data.json")
    
    print(f"\n💾 Menyimpan data ke {out_path}...")
    with open(out_path, "w") as f:
        json.dump(data_store, f, indent=2)
        
    print("✅ DOWNLOAD SELESAI DENGAN SUKSES!")

if __name__ == "__main__":
    main()
