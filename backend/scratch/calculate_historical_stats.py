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
    
    current_date = start_date
    weekly_dates = []
    while current_date <= end_date:
        if current_date.weekday() == 4: # Friday
            weekly_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
        
    print(f"📅 Jumlah minggu analisis: {len(weekly_dates)}")
    
    records = []
    
    def get_latest_financials(fin_data, today_str):
        annual_bs_dict = fin_data.get("annual_balance_sheet", {})
        annual_is_dict = fin_data.get("annual_income_statement", {})
        
        common_dates = set(annual_bs_dict.keys()).intersection(set(annual_is_dict.keys()))
        available_dates = sorted([d for d in common_dates if d <= today_str])
        if not available_dates:
            return None, None
            
        latest_date = available_dates[-1]
        return annual_bs_dict[latest_date], annual_is_dict[latest_date]

    def get_qoq_growth(fin_data, today_str):
        q_is = fin_data.get("quarterly_income_statement", {})
        if not q_is:
            return 0.0
            
        q_dates = sorted([d for d in q_is.keys() if d <= today_str], reverse=True)
        if len(q_dates) < 2:
            return 0.0
            
        try:
            latest_q = q_dates[0]
            prev_q = q_dates[1]
            
            latest_is = q_is[latest_q]
            prev_is = q_is[prev_q]
            
            latest_net = latest_is.get("Net Income") or latest_is.get("NetIncome") or latest_is.get("Net Income Common Stockholders")
            prev_net = prev_is.get("Net Income") or prev_is.get("NetIncome") or prev_is.get("Net Income Common Stockholders")
            
            if latest_net is not None and prev_net is not None and prev_net != 0:
                return float((latest_net - prev_net) / abs(prev_net) * 100.0)
        except Exception:
            pass
        return 0.0

    # Pre-parse price dataframes & volumes
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
            
            p_df = price_dfs.get(kode)
            if p_df is None or p_df.empty:
                continue
                
            idx = p_df.index.get_indexer([today_dt], method='pad')[0]
            if idx == -1:
                continue
            row = p_df.iloc[idx]
            price = float(row["Close"])
            volume = float(row["Volume"]) if "Volume" in row else 0.0
            
            fin_data = raw_data["financials"].get(kode, {})
            bs, is_statement = get_latest_financials(fin_data, today_str)
            if not bs or not is_statement:
                continue
                
            equity = bs.get("Stockholders Equity") or bs.get("StockholdersEquity") or bs.get("Stockholde")
            debt = bs.get("Total Debt") or bs.get("TotalDebt") or bs.get("Total Liab")
            net_income = is_statement.get("Net Income") or is_statement.get("NetIncome") or is_statement.get("Net Income Common Stockholders")
            shares_outstanding = bs.get("Ordinary Shares Number") or bs.get("Share Issued") or bs.get("Ordinary S") or bs.get("Share Issu")
            
            if not equity or not net_income or not shares_outstanding:
                continue
                
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
            qoq_growth = get_qoq_growth(fin_data, today_str)
            
            records.append({
                "tanggal": today_str,
                "kode_saham": kode,
                "sektor": sector,
                "price": price,
                "volume": volume,
                "roe": roe,
                "der": der,
                "pbv": pbv,
                "pe": pe,
                "eps": eps,
                "qoq_growth": qoq_growth
            })
            
    df_results = pd.DataFrame(records)
    print(f"\n📊 Rekonstruksi selesai. Total data poin: {len(df_results)}")
    
    # ─── Calculate Sector Stats ───
    sectors = df_results["sektor"].unique()
    sector_statistics = {}
    for sector in sectors:
        sec_df = df_results[df_results["sektor"] == sector]
        
        pbvs = sec_df["pbv"].replace([np.inf, -np.inf], np.nan).dropna()
        pes = sec_df["pe"].replace([np.inf, -np.inf], np.nan).dropna()
        pes_clean = pes[pes.between(0.5, 150)]
        ders = sec_df["der"].replace([np.inf, -np.inf], np.nan).dropna()
        roes = sec_df["roe"].replace([np.inf, -np.inf], np.nan).dropna()
        
        # Calculate QoQ growth excluding 0.0
        qoqs = sec_df["qoq_growth"].replace([np.inf, -np.inf], np.nan).dropna()
        qoqs_active = qoqs[qoqs != 0.0]
        qoqs_clean = qoqs_active[qoqs_active.between(-100, 300)]
        
        pbv_median, pbv_25, pbv_75 = pbvs.median(), pbvs.quantile(0.25), pbvs.quantile(0.75)
        pe_median, pe_25, pe_75 = pes_clean.median(), pes_clean.quantile(0.25), pes_clean.quantile(0.75)
        der_median, der_25, der_75 = ders.median(), ders.quantile(0.25), ders.quantile(0.75)
        roe_median, roe_25, roe_75 = roes.median(), roes.quantile(0.25), roes.quantile(0.75)
        
        # Fallback to defaults if no active qoq growth reports
        if not qoqs_clean.empty:
            qoq_median, qoq_25, qoq_75 = qoqs_clean.median(), qoqs_clean.quantile(0.25), qoqs_clean.quantile(0.75)
        else:
            qoq_median, qoq_25, qoq_75 = 0.0, -15.0, 25.0
            
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
                "mean": round(qoqs_clean.mean(), 2) if not qoqs_clean.empty else 5.0,
                "median": round(qoq_median, 2),
                "q25": round(qoq_25, 2),
                "q75": round(qoq_75, 2)
            }
        }
        
    # Save sector stats
    stats_out_path = os.path.join(data_dir, "sector_historical_stats.json")
    with open(stats_out_path, "w") as f:
        json.dump(sector_statistics, f, indent=2)
    print(f"💾 Statistik sektoral disimpan ke: {stats_out_path}")
    
    # ─── Calculate Emiten Stats ───
    emiten_codes = df_results["kode_saham"].unique()
    emiten_statistics = {}
    for code in emiten_codes:
        em_df = df_results[df_results["kode_saham"] == code]
        
        pbvs = em_df["pbv"].replace([np.inf, -np.inf], np.nan).dropna()
        pes = em_df["pe"].replace([np.inf, -np.inf], np.nan).dropna()
        pes_clean = pes[pes.between(0.5, 150)]
        ders = em_df["der"].replace([np.inf, -np.inf], np.nan).dropna()
        roes = em_df["roe"].replace([np.inf, -np.inf], np.nan).dropna()
        eps_vals = em_df["eps"].replace([np.inf, -np.inf], np.nan).dropna()
        vols = em_df["volume"].replace([np.inf, -np.inf], np.nan).dropna()
        
        # Calculate QoQ growth excluding 0.0
        qoqs = em_df["qoq_growth"].replace([np.inf, -np.inf], np.nan).dropna()
        qoqs_active = qoqs[qoqs != 0.0]
        qoqs_clean = qoqs_active[qoqs_active.between(-100, 300)]
        
        pbv_median, pbv_25, pbv_75 = pbvs.median(), pbvs.quantile(0.25), pbvs.quantile(0.75)
        pe_median, pe_25, pe_75 = pes_clean.median(), pes_clean.quantile(0.25), pes_clean.quantile(0.75)
        der_median, der_25, der_75 = ders.median(), ders.quantile(0.25), ders.quantile(0.75)
        roe_median, roe_25, roe_75 = roes.median(), roes.quantile(0.25), roes.quantile(0.75)
        eps_median, eps_25, eps_75 = eps_vals.median(), eps_vals.quantile(0.25), eps_vals.quantile(0.75)
        vol_median, vol_25, vol_75 = vols.median(), vols.quantile(0.25), vols.quantile(0.75)
        
        if not qoqs_clean.empty:
            qoq_median, qoq_25, qoq_75 = qoqs_clean.median(), qoqs_clean.quantile(0.25), qoqs_clean.quantile(0.75)
        else:
            qoq_median, qoq_25, qoq_75 = 0.0, -15.0, 25.0
            
        emiten_statistics[code] = {
            "pbv": {
                "median": round(pbv_median, 2) if pd.notna(pbv_median) else 1.2,
                "q25": round(pbv_25, 2) if pd.notna(pbv_25) else 0.8,
                "q75": round(pbv_75, 2) if pd.notna(pbv_75) else 2.0
            },
            "pe": {
                "median": round(pe_median, 2) if pd.notna(pe_median) else 12.0,
                "q25": round(pe_25, 2) if pd.notna(pe_25) else 8.0,
                "q75": round(pe_75, 2) if pd.notna(pe_75) else 18.0
            },
            "der": {
                "median": round(der_median, 2) if pd.notna(der_median) else 0.8,
                "q25": round(der_25, 2) if pd.notna(der_25) else 0.4,
                "q75": round(der_75, 2) if pd.notna(der_75) else 1.5
            },
            "roe": {
                "median": round(roe_median, 2) if pd.notna(roe_median) else 12.0,
                "q25": round(roe_25, 2) if pd.notna(roe_25) else 8.0,
                "q75": round(roe_75, 2) if pd.notna(roe_75) else 18.0
            },
            "eps": {
                "median": round(eps_median, 2) if pd.notna(eps_median) else 100.0,
                "q25": round(eps_25, 2) if pd.notna(eps_25) else 50.0,
                "q75": round(eps_75, 2) if pd.notna(eps_75) else 200.0
            },
            "volume": {
                "median": round(vol_median, 2) if pd.notna(vol_median) else 1000000.0,
                "q25": round(vol_25, 2) if pd.notna(vol_25) else 500000.0,
                "q75": round(vol_75, 2) if pd.notna(vol_75) else 2000000.0
            },
            "qoq_growth": {
                "median": round(qoq_median, 2),
                "q25": round(qoq_25, 2),
                "q75": round(qoq_75, 2)
            }
        }
        
    # Save emiten stats
    em_out_path = os.path.join(data_dir, "emiten_historical_stats.json")
    with open(em_out_path, "w") as f:
        json.dump(emiten_statistics, f, indent=2)
    print(f"💾 Statistik emiten disimpan ke: {em_out_path}")

if __name__ == "__main__":
    asyncio.run(main())
