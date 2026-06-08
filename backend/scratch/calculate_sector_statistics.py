import asyncio
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select
from backend.db.postgres import async_session, Saham

async def main():
    print("🔋 Menghubungkan ke database untuk mengambil sektor emiten...")
    sector_map = {}
    async with async_session() as session:
        stmt = select(Saham)
        res = await session.execute(stmt)
        for s in res.scalars().all():
            sector_map[s.kode] = s.sektor
            
    print(f"✅ Pemetaan sektor berhasil: {sector_map}")
    
    # Load raw backtest data
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    
    if not os.path.exists(raw_data_path):
        print(f"❌ File data {raw_data_path} tidak ditemukan!")
        return
        
    with open(raw_data_path) as f:
        raw_data = json.load(f)
        
    print("📈 Mengunduh data nilai tukar USD/IDR historis...")
    import yfinance as yf
    usdidr = yf.download("USDIDR=X", start="2021-11-01", end="2025-12-31")
    usdidr_close = usdidr['Close'] if not usdidr.empty else pd.Series(dtype=float)
    
    # helper to get kurs
    def get_kurs_on_date(d_str):
        if usdidr_close.empty:
            return 15500.0
        try:
            d_dt = pd.to_datetime(d_str)
            idx = usdidr_close.index.get_indexer([d_dt], method='pad')[0]
            if idx != -1:
                val = usdidr_close.iloc[idx]
                if isinstance(val, pd.Series):
                    val = float(val.iloc[0])
                else:
                    val = float(val)
                return val
            return 15500.0
        except:
            return 15500.0

    print("📊 Memulai rekonstruksi data mingguan (2022 - 2025)...")
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    # Generate weekly dates (every Friday)
    current_date = start_date
    weekly_dates = []
    while current_date <= end_date:
        if current_date.weekday() == 4: # Friday
            weekly_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
        
    print(f"📅 Jumlah minggu analisis: {len(weekly_dates)}")
    
    records = []
    
    # Helper to find latest statement before a given date
    def get_latest_financials(fin_data, today_str):
        annual_bs_dict = fin_data.get("annual_balance_sheet", {})
        annual_is_dict = fin_data.get("annual_income_statement", {})
        
        # Sort available report dates that exist in both BS and IS
        common_dates = set(annual_bs_dict.keys()).intersection(set(annual_is_dict.keys()))
        available_dates = sorted([d for d in common_dates if d <= today_str])
        if not available_dates:
            return None, None
            
        latest_date = available_dates[-1]
        return annual_bs_dict[latest_date], annual_is_dict[latest_date]

    # Helper to calculate QoQ Growth from quarterly reports
    def get_qoq_growth(fin_data, today_str):
        q_is = fin_data.get("quarterly_income_statement", {})
        if not q_is:
            return 0.0
            
        # Get dates before today
        q_dates = sorted([d for d in q_is.keys() if d <= today_str], reverse=True)
        if len(q_dates) < 2:
            return 0.0
            
        try:
            latest_q = q_dates[0]
            prev_q = q_dates[1]
            
            # Find Net Income in the nested columns
            # The structure of q_is is {date: {metric: value}}
            latest_is = q_is[latest_q]
            prev_is = q_is[prev_q]
            
            latest_net = latest_is.get("Net Income") or latest_is.get("NetIncome") or latest_is.get("Net Income Common Stockholders")
            prev_net = prev_is.get("Net Income") or prev_is.get("NetIncome") or prev_is.get("Net Income Common Stockholders")
            
            if latest_net is not None and prev_net is not None and prev_net != 0:
                return float((latest_net - prev_net) / abs(prev_net) * 100.0)
        except Exception as e:
            pass
        return 0.0

    # Pre-parse price dataframes
    price_dfs = {}
    for kode, p_dict in raw_data["prices"].items():
        if p_dict:
            df = pd.DataFrame(p_dict)
            df.index = pd.to_datetime(df.index)
            price_dfs[kode] = df
            
    for today_str in weekly_dates:
        kurs = get_kurs_on_date(today_str)
        today_dt = pd.to_datetime(today_str)
        
        for kode in raw_data["prices"].keys():
            sector = sector_map.get(kode, "Other")
            
            # 1. Get price on this date
            p_df = price_dfs.get(kode)
            if p_df is None or p_df.empty:
                continue
                
            idx = p_df.index.get_indexer([today_dt], method='pad')[0]
            if idx == -1:
                continue
            price = float(p_df.iloc[idx]["Close"])
            
            # 2. Get financials
            fin_data = raw_data["financials"].get(kode, {})
            bs, is_statement = get_latest_financials(fin_data, today_str)
            if not bs or not is_statement:
                continue
                
            # Extract keys
            equity = bs.get("Stockholders Equity") or bs.get("StockholdersEquity") or bs.get("Stockholde")
            debt = bs.get("Total Debt") or bs.get("TotalDebt") or bs.get("Total Liab")
            net_income = is_statement.get("Net Income") or is_statement.get("NetIncome") or is_statement.get("Net Income Common Stockholders")
            shares_outstanding = bs.get("Ordinary Shares Number") or bs.get("Share Issued") or bs.get("Ordinary S") or bs.get("Share Issu")
            
            if not equity or not net_income or not shares_outstanding:
                continue
                
            # Handle USD currency normalization (like BYAN, ADRO)
            is_usd = equity < 1e11
            if is_usd:
                equity_idr = equity * kurs
                debt_idr = (debt or 0) * kurs
                net_income_idr = net_income * kurs
            else:
                equity_idr = equity
                debt_idr = debt or 0
                net_income_idr = net_income
                
            roe = (net_income_idr / equity_idr) * 100
            der = debt_idr / equity_idr
            eps = net_income_idr / shares_outstanding
            bvps = equity_idr / shares_outstanding
            
            if eps <= 0 or bvps <= 0:
                continue
                
            pbv = price / bvps
            pe = price / eps
            
            # Calculate QoQ growth
            qoq_growth = get_qoq_growth(fin_data, today_str)
            
            records.append({
                "tanggal": today_str,
                "kode_saham": kode,
                "sektor": sector,
                "price": price,
                "roe": roe,
                "der": der,
                "pbv": pbv,
                "pe": pe,
                "qoq_growth": qoq_growth
            })
            
    df_results = pd.DataFrame(records)
    print(f"\n📊 Rekonstruksi selesai. Total data poin: {len(df_results)}")
    
    # Analyze distributions by sector
    sectors = df_results["sektor"].unique()
    sector_statistics = {}
    
    print("\n" + "=" * 60)
    print("📈 HASIL STATISTIK SEKTORAL HISTORIS LENGKAP (2022 - 2025)")
    print("=" * 60)
    
    for sector in sectors:
        sec_df = df_results[df_results["sektor"] == sector]
        
        # Clean infinite/outliers
        pbvs = sec_df["pbv"].replace([np.inf, -np.inf], np.nan).dropna()
        pes = sec_df["pe"].replace([np.inf, -np.inf], np.nan).dropna()
        pes_clean = pes[pes.between(0.5, 150)]
        ders = sec_df["der"].replace([np.inf, -np.inf], np.nan).dropna()
        roes = sec_df["roe"].replace([np.inf, -np.inf], np.nan).dropna()
        qoqs = sec_df["qoq_growth"].replace([np.inf, -np.inf], np.nan).dropna()
        # Clean QoQ extreme outliers
        qoqs_clean = qoqs[qoqs.between(-100, 300)]
        
        pbv_median, pbv_25, pbv_75 = pbvs.median(), pbvs.quantile(0.25), pbvs.quantile(0.75)
        pe_median, pe_25, pe_75 = pes_clean.median(), pes_clean.quantile(0.25), pes_clean.quantile(0.75)
        der_median, der_25, der_75 = ders.median(), ders.quantile(0.25), ders.quantile(0.75)
        roe_median, roe_25, roe_75 = roes.median(), roes.quantile(0.25), roes.quantile(0.75)
        qoq_median, qoq_25, qoq_75 = qoqs_clean.median(), qoqs_clean.quantile(0.25), qoqs_clean.quantile(0.75)
        
        print(f"\n📁 SEKTOR: {sector} ({len(sec_df)} data poin)")
        print(f"  * PBV: Median={pbv_median:.2f}x | Rentang=[{pbv_25:.2f}x - {pbv_75:.2f}x]")
        print(f"  * PE:  Median={pe_median:.2f}x  | Rentang=[{pe_25:.2f}x - {pe_75:.2f}x]")
        print(f"  * DER: Median={der_median:.2f}x | Rentang=[{der_25:.2f}x - {der_75:.2f}x]")
        print(f"  * ROE: Median={roe_median:.2f}% | Rentang=[{roe_25:.2f}% - {roe_75:.2f}%]")
        print(f"  * QoQ: Median={qoq_median:.2f}% | Rentang=[{qoq_25:.2f}% - {qoq_75:.2f}%]")
        
        sector_statistics[sector] = {
            "pbv": {
                "mean": round(pbvs.mean(), 2) if pd.notna(pbvs.mean()) else 1.2,
                "median": round(pbv_median, 2),
                "q25": round(pbv_25, 2),
                "q75": round(pbv_75, 2)
            },
            "pe": {
                "mean": round(pes_clean.mean(), 2) if pd.notna(pes_clean.mean()) else 15.0,
                "median": round(pe_median, 2),
                "q25": round(pe_25, 2),
                "q75": round(pe_75, 2)
            },
            "der": {
                "mean": round(ders.mean(), 2) if pd.notna(ders.mean()) else 1.0,
                "median": round(der_median, 2),
                "q25": round(der_25, 2),
                "q75": round(der_75, 2)
            },
            "roe": {
                "mean": round(roes.mean(), 2) if pd.notna(roes.mean()) else 12.0,
                "median": round(roe_median, 2),
                "q25": round(roe_25, 2),
                "q75": round(roe_75, 2)
            },
            "qoq_growth": {
                "mean": round(qoqs_clean.mean(), 2) if pd.notna(qoqs_clean.mean()) else 5.0,
                "median": round(qoq_median, 2),
                "q25": round(qoq_25, 2),
                "q75": round(qoq_75, 2)
            }
        }
        
    # Save sector stats to JSON for code use
    stats_out_path = os.path.join(data_dir, "sector_historical_stats.json")
    with open(stats_out_path, "w") as f:
        json.dump(sector_statistics, f, indent=2)
    print(f"\n💾 Statistik sektoral lengkap disimpan ke: {stats_out_path}")

if __name__ == "__main__":
    asyncio.run(main())
