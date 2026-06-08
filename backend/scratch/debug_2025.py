import json
import os
import pandas as pd
import numpy as np

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    
    with open(raw_data_path) as f:
        raw_data = json.load(f)
        
    prices = raw_data["prices"]
    
    # Let's see the performance of all 20 stocks in 2025
    print("📈 STOCK PERFORMANCE IN 2025 (Jan 2, 2025 to Dec 30, 2025):")
    print("-" * 60)
    stock_perf = {}
    for kode in prices.keys():
        df = pd.DataFrame(prices[kode])
        df.index = pd.to_datetime(df.index)
        df_2025 = df.loc["2025-01-02":"2025-12-30"]
        if not df_2025.empty:
            start_p = df_2025.iloc[0]["Close"]
            end_p = df_2025.iloc[-1]["Close"]
            ret = (end_p - start_p) / start_p * 100
            stock_perf[kode] = {"start": start_p, "end": end_p, "return": ret}
            
    sorted_perf = sorted(stock_perf.items(), key=lambda x: x[1]["return"], reverse=True)
    for kode, info in sorted_perf:
        print(f"{kode:<6}: Start: Rp {info['start']:>8,.2f} | End: Rp {info['end']:>8,.2f} | Return: {info['return']:>+8.2f}%")
        
    print("\n" + "=" * 60)
    
    # Read the portfolio values at key dates in 2024 and 2025
    csv_path = os.path.join(data_dir, "backtest_opt_results.csv")
    if os.path.exists(csv_path):
        df_res = pd.read_csv(csv_path)
        df_res["tanggal"] = pd.to_datetime(df_res["tanggal"])
        df_res.set_index("tanggal", inplace=True)
        
        # Key dates
        d_end_2023 = "2023-12-29"
        d_end_2024 = "2024-12-30"
        d_end_2025 = "2025-12-30"
        
        print("📊 PORTFOLIO VALUES AT KEY YEAR-ENDS:")
        for date in [d_end_2023, d_end_2024, d_end_2025]:
            dt = pd.to_datetime(date)
            if dt in df_res.index:
                row = df_res.loc[dt]
                print(f"\nTanggal: {date}")
                print(f"  - Trading Opt  : Rp {row['Trading_Opt']*1e9:,.2f}")
                print(f"  - Investing Opt: Rp {row['Investing_Opt']*1e9:,.2f}")
                print(f"  - IHSG         : Rp {row['IHSG']*1e9:,.2f}")
                
        # Let's look at the return of portfolios during 2025 itself
        val_2024_end_t = df_res.loc[pd.to_datetime(d_end_2024), "Trading_Opt"]
        val_2025_end_t = df_res.loc[pd.to_datetime(d_end_2025), "Trading_Opt"]
        ret_t_2025 = (val_2025_end_t - val_2024_end_t) / val_2024_end_t * 100
        
        val_2024_end_i = df_res.loc[pd.to_datetime(d_end_2024), "Investing_Opt"]
        val_2025_end_i = df_res.loc[pd.to_datetime(d_end_2025), "Investing_Opt"]
        ret_i_2025 = (val_2025_end_i - val_2024_end_i) / val_2024_end_i * 100
        
        print("\n" + "-" * 60)
        print(f"⚡ Performance in 2025 alone:")
        print(f"  - Trading Opt return in 2025: {ret_t_2025:+.2f}%")
        print(f"  - Investing Opt return in 2025: {ret_i_2025:+.2f}%")
        
if __name__ == "__main__":
    main()
