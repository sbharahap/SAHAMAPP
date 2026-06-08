import json
import os
import pandas as pd
import numpy as np
import yfinance as yf

# Re-run a mini-simulation of 2025 to print out holdings
def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    news_path = os.path.join(data_dir, "backtest_news.json")
    
    with open(raw_data_path) as f:
        raw_data = json.load(f)
    with open(news_path) as f:
        news_data = json.load(f)
        
    SAHAM_LIST_20 = [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GOTO", "KLBF",
        "ANTM", "PGAS", "UNTR", "PTBA", "MEDC", "BRIS", "AMRT", "MDKA", "ICBP", "INDF"
    ]
    
    SECTOR_MAP = {
        "BBCA": "Financials", "BBRI": "Financials", "BMRI": "Financials", "BBNI": "Financials", "BRIS": "Financials",
        "TLKM": "Infrastructure", "ASII": "Consumer Discretionary",
        "UNVR": "Consumer Staples", "ICBP": "Consumer Staples", "INDF": "Consumer Staples", "AMRT": "Consumer Staples",
        "GOTO": "Technology", "KLBF": "Healthcare",
        "ANTM": "Basic Materials", "MDKA": "Basic Materials",
        "UNTR": "Industrials",
        "PGAS": "Energy", "PTBA": "Energy", "MEDC": "Energy", "ADRO": "Energy"
    }
    
    # Pre-parse
    for kode in SAHAM_LIST_20:
        if kode in news_data:
            for n in news_data[kode]:
                n["dt"] = pd.to_datetime(n["tanggal_publish"][:10])
        else:
            news_data[kode] = []
            
    # Load Exchange Rate
    usd_idr_df = yf.download("USDIDR=X", start="2021-11-01", end="2025-12-31")
    close_series = usd_idr_df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
    usd_idr = close_series.dropna().to_dict()
    usd_idr = {str(k)[:10]: float(v) for k, v in usd_idr.items()}
    
    def get_kurs(date_str):
        if date_str in usd_idr:
            return usd_idr[date_str]
        dates = sorted(usd_idr.keys())
        closest = 15500.0
        for d in dates:
            if d <= date_str:
                closest = usd_idr[d]
            else:
                break
        return closest

    price_dfs = {}
    for kode in SAHAM_LIST_20:
        if kode in raw_data["prices"]:
            df = pd.DataFrame(raw_data["prices"][kode])
            df.index = pd.to_datetime(df.index)
            price_dfs[kode] = df.sort_index()
            
    ihsg_df = pd.DataFrame(raw_data["benchmark"])
    ihsg_df.index = pd.to_datetime(ihsg_df.index)
    ihsg_df = ihsg_df.sort_index()

    for kode, df in price_dfs.items():
        df["sma50"] = df["Close"].rolling(window=50).mean()
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df["rsi14"] = 100 - (100 / (1 + rs))
        df["rsi14"] = df["rsi14"].ffill().bfill().fillna(50.0)
        df["sma50"] = df["sma50"].ffill().bfill().fillna(df["Close"])
    
    # We will trace the rebalancing during 2025
    start_date = pd.to_datetime("2022-01-03")
    end_date = pd.to_datetime("2025-12-30")
    all_trading_days = ihsg_df.loc[start_date:end_date].index
    
    weekly_rebal_dates = [d for d in all_trading_days if d.dayofweek == 0]
    monthly_rebal_dates = []
    current_month = -1
    for day in all_trading_days:
        if day.month != current_month:
            monthly_rebal_dates.append(day)
            current_month = day.month
            
    from run_backtest_optimized import (
        hitung_skor_fundamental_rel,
        hitung_skor_teknikal,
        get_sentiment_score,
        select_top_5_with_sector_cap,
        rebalance_portfolio,
        get_fundamental_variables
    )
    
    cash_t = 1_000_000_000.0
    holdings_t = {}
    fees_t = 0.0
    
    cash_i = 1_000_000_000.0
    holdings_i = {}
    fees_i = 0.0
    
    # Fees paid in 2025
    fees_t_2025 = 0.0
    fees_i_2025 = 0.0
    
    for today in all_trading_days:
        today_str = str(today.date())
        kurs = get_kurs(today_str)
        is_in_2025 = today.year == 2025
        
        # Calculate PBVs
        pbvs_today = {}
        for kode in SAHAM_LIST_20:
            if today not in price_dfs[kode].index:
                continue
            p = price_dfs[kode].loc[today, "Close"]
            _, _, pbv_val, _, _ = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
            pbvs_today[kode] = pbv_val
            
        all_pbvs_mean = np.mean(list(pbvs_today.values())) if pbvs_today else 1.2
        sector_pbvs = {}
        for kode, pbv_val in pbvs_today.items():
            sec = SECTOR_MAP.get(kode, "Other")
            if sec not in sector_pbvs:
                sector_pbvs[sec] = []
            sector_pbvs[sec].append(pbv_val)
            
        sector_means = {}
        for sec, vals in sector_pbvs.items():
            if len(vals) > 1:
                sector_means[sec] = np.mean(vals)
            else:
                sector_means[sec] = all_pbvs_mean
                
        pbvs_relative_today = {}
        for kode, pbv_val in pbvs_today.items():
            sec = SECTOR_MAP.get(kode, "Other")
            baseline = sector_means.get(sec, all_pbvs_mean)
            pbvs_relative_today[kode] = pbv_val / baseline if baseline > 0 else 1.0
            
        # Rebalance Trading Opt
        if today in weekly_rebal_dates:
            scores_t_opt = {}
            for kode in SAHAM_LIST_20:
                if today not in price_dfs[kode].index:
                    continue
                p = price_dfs[kode].loc[today, "Close"]
                roe, eps, _, der, _ = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
                pbv_rel = pbvs_relative_today.get(kode, 1.0)
                f_score_rel = hitung_skor_fundamental_rel(roe, eps, pbv_rel, der)
                
                sma50_val = price_dfs[kode].loc[today, "sma50"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["sma50"]
                rsi14_val = price_dfs[kode].loc[today, "rsi14"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["rsi14"]
                tech_score = hitung_skor_teknikal(p, sma50_val, rsi14_val)
                s_score = get_sentiment_score(news_data[kode], today)
                scores_t_opt[kode] = (f_score_rel * 0.20) + (tech_score * 0.25) + (s_score * 0.25) + (70.0 * 0.15) + (60.0 * 0.10) + (80.0 * 0.05)
                
            top_5_t_opt = select_top_5_with_sector_cap(scores_t_opt, SECTOR_MAP)
            
            # Record fee before
            fee_before = fees_t
            holdings_t, cash_t, fees_t = rebalance_portfolio(
                holdings_t, cash_t, fees_t, top_5_t_opt, today, price_dfs, 0.0020, 0.0030
            )
            if is_in_2025:
                fees_t_2025 += (fees_t - fee_before)
                
        # Rebalance Investing Opt
        if today in monthly_rebal_dates:
            scores_i_opt = {}
            for kode in SAHAM_LIST_20:
                if today not in price_dfs[kode].index:
                    continue
                p = price_dfs[kode].loc[today, "Close"]
                roe, eps, _, der, _ = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
                pbv_rel = pbvs_relative_today.get(kode, 1.0)
                f_score_rel = hitung_skor_fundamental_rel(roe, eps, pbv_rel, der)
                sma50_val = price_dfs[kode].loc[today, "sma50"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["sma50"]
                rsi14_val = price_dfs[kode].loc[today, "rsi14"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["rsi14"]
                tech_score = hitung_skor_teknikal(p, sma50_val, rsi14_val)
                scores_i_opt[kode] = (f_score_rel * 0.60) + (tech_score * 0.20) + (60.0 * 0.20)
                
            top_5_i_opt = select_top_5_with_sector_cap(scores_i_opt, SECTOR_MAP)
            
            # Record fee before
            fee_before = fees_i
            holdings_i, cash_i, fees_i = rebalance_portfolio(
                holdings_i, cash_i, fees_i, top_5_i_opt, today, price_dfs, 0.0020, 0.0030
            )
            if is_in_2025:
                fees_i_2025 += (fees_i - fee_before)
                
        # Let's print out the holdings at specific dates in 2025
        if today_str in ["2025-01-06", "2025-06-02", "2025-12-01"]:
            print(f"\n📂 PORTFOLIO HOLDINGS ON {today_str}:")
            print("  [Trading Opt]")
            total_t_val = cash_t
            for k, sh in holdings_t.items():
                p = price_dfs[k].loc[today, "Close"]
                val = sh * p
                total_t_val += val
                print(f"    - {k:<5}: Shares: {sh:>12,.2f} | Price: Rp {p:>8,.2f} | Value: Rp {val:>14,.2f} ({val/total_t_val*100:>5.1f}%)")
            print(f"    - Cash : Rp {cash_t:>14,.2f}")
            print(f"    - Total: Rp {total_t_val:>14,.2f}")
            
            print("  [Investing Opt]")
            total_i_val = cash_i
            for k, sh in holdings_i.items():
                p = price_dfs[k].loc[today, "Close"]
                val = sh * p
                total_i_val += val
                print(f"    - {k:<5}: Shares: {sh:>12,.2f} | Price: Rp {p:>8,.2f} | Value: Rp {val:>14,.2f} ({val/total_i_val*100:>5.1f}%)")
            print(f"    - Cash : Rp {cash_i:>14,.2f}")
            print(f"    - Total: Rp {total_i_val:>14,.2f}")

    print("\n" + "=" * 60)
    print("💸 TRANSACTION FEES INCURRED IN 2025:")
    print(f"  - Trading Opt  : Rp {fees_t_2025:,.2f}")
    print(f"  - Investing Opt: Rp {fees_i_2025:,.2f}")

if __name__ == "__main__":
    main()
