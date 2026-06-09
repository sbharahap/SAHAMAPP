import json
import os
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# List 20 Saham Utama
SAHAM_LIST_20 = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GOTO", "KLBF",
    "ANTM", "PGAS", "UNTR", "PTBA", "MEDC", "BRIS", "AMRT", "MDKA", "ICBP", "INDF"
]

# Sector Map for Sector Cap & Relative PBV
SECTOR_MAP = {
    "BBCA": "Financials",
    "BBRI": "Financials",
    "BMRI": "Financials",
    "BBNI": "Financials",
    "BRIS": "Financials",
    "TLKM": "Infrastructure",
    "ASII": "Consumer Discretionary",
    "UNVR": "Consumer Staples",
    "ICBP": "Consumer Staples",
    "INDF": "Consumer Staples",
    "AMRT": "Consumer Staples",
    "GOTO": "Technology",
    "KLBF": "Healthcare",
    "ANTM": "Basic Materials",
    "MDKA": "Basic Materials",
    "UNTR": "Industrials",
    "PGAS": "Energy",
    "PTBA": "Energy",
    "MEDC": "Energy",
    "ADRO": "Energy"
}

usd_idr = {}

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

def hitung_skor_fundamental_rel(roe, eps, pbv_relative, der):
    skor = 0.0
    komponen_tersedia = 0

    if roe is not None:
        komponen_tersedia += 1
        if roe > 20: skor += 25
        elif roe > 15: skor += 20
        elif roe > 10: skor += 15
        elif roe > 5: skor += 10
        elif roe > 0: skor += 5

    if eps is not None:
        komponen_tersedia += 1
        if eps > 500: skor += 25
        elif eps > 200: skor += 20
        elif eps > 100: skor += 15
        elif eps > 0: skor += 10

    if pbv_relative is not None and pbv_relative > 0:
        komponen_tersedia += 1
        if pbv_relative < 0.8: skor += 25
        elif pbv_relative < 1.0: skor += 20
        elif pbv_relative < 1.2: skor += 15
        elif pbv_relative < 1.5: skor += 10
        else: skor += 5

    if der is not None and der >= 0:
        komponen_tersedia += 1
        if der < 0.5: skor += 25
        elif der < 1.0: skor += 20
        elif der < 1.5: skor += 15
        elif der < 2.0: skor += 10
        else: skor += 5

    if komponen_tersedia == 0:
        return 50.0

    max_skor = komponen_tersedia * 25
    return round((skor / max_skor) * 100, 2)

def hitung_skor_teknikal(price, sma50, rsi14):
    if price > sma50:
        score = 60.0
    else:
        score = 40.0
        
    if 45 <= rsi14 <= 70:
        score += 25.0
    elif 30 <= rsi14 < 45:
        score += 10.0
    elif rsi14 > 70:
        score -= 10.0
    elif rsi14 < 30:
        score -= 20.0
        
    return max(0.0, min(100.0, score))

def select_top_5_with_buffer(scores, current_holdings, sector_map, buffer_rank=8):
    if not current_holdings:
        sorted_stocks = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        selected = []
        sector_counts = {}
        for stock in sorted_stocks:
            sector = sector_map.get(stock, "Other")
            if sector_counts.get(sector, 0) < 2:
                selected.append(stock)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                if len(selected) == 5:
                    break
        if len(selected) < 5:
            for stock in sorted_stocks:
                if stock not in selected:
                    selected.append(stock)
                    if len(selected) == 5:
                        break
        return selected
        
    sorted_stocks = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    ranks = {stock: i+1 for i, stock in enumerate(sorted_stocks)}
    
    selected = []
    sector_counts = {}
    
    for stock in current_holdings:
        rank = ranks.get(stock, 99)
        sector = sector_map.get(stock, "Other")
        if rank <= buffer_rank:
            if sector_counts.get(sector, 0) < 2:
                selected.append(stock)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                
    for stock in sorted_stocks:
        if len(selected) == 5:
            break
        if stock in selected:
            continue
        sector = sector_map.get(stock, "Other")
        if sector_counts.get(sector, 0) < 2:
            selected.append(stock)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            
    if len(selected) < 5:
        for stock in sorted_stocks:
            if stock not in selected:
                selected.append(stock)
                if len(selected) == 5:
                    break
                    
    return selected

def rebalance_portfolio(holdings, cash, fee_paid, top_5, today, price_dfs, fee_buy, fee_sell):
    for k in list(holdings.keys()):
        if k not in top_5:
            exec_price = price_dfs[k].loc[today, "Open"] if today in price_dfs[k].index else price_dfs[k].asof(today)["Open"]
            revenue = holdings.pop(k) * exec_price
            fee = revenue * fee_sell
            fee_paid += fee
            cash += (revenue - fee)
            
    total_val = cash + sum(holdings[k] * (price_dfs[k].loc[today, "Open"] if today in price_dfs[k].index else price_dfs[k].asof(today)["Open"]) for k in holdings)
    alloc = total_val / 5.0
    
    for k in top_5:
        exec_price = price_dfs[k].loc[today, "Open"] if today in price_dfs[k].index else price_dfs[k].asof(today)["Open"]
        curr_val = holdings.get(k, 0) * exec_price
        diff = alloc - curr_val
        
        if diff > 0:
            cost = diff / (1.0 + fee_buy)
            holdings[k] = holdings.get(k, 0) + (cost / exec_price)
            cash -= cost * (1.0 + fee_buy)
            fee_paid += cost * fee_buy
        elif diff < 0:
            shares_to_sell = abs(diff) / exec_price
            holdings[k] = holdings.get(k, 0) - shares_to_sell
            if holdings[k] < 1e-5:
                holdings.pop(k, None)
            revenue = shares_to_sell * exec_price
            fee = revenue * fee_sell
            fee_paid += fee
            cash += (revenue - fee)
            
    return holdings, cash, fee_paid

def get_fundamental_variables(kode, raw_data, today, today_str, price, kurs):
    year = today.year
    if today_str < f"{year}-03-01":
        rep_year = f"{year - 2}-12-31"
    else:
        rep_year = f"{year - 1}-12-31"
        
    fin = raw_data["financials"].get(kode, {})
    bs = fin.get("annual_balance_sheet", {}).get(rep_year, {})
    is_statement = fin.get("annual_income_statement", {}).get(rep_year, {})
    
    equity = bs.get("Stockholde")
    debt = bs.get("Total Debt")
    net_income = is_statement.get("Net Income")
    shares_outstanding = bs.get("Ordinary S") or bs.get("Share Issu")
    
    if not equity or not net_income or not shares_outstanding:
        return 12.0, 100.0, 1.2, 0.8
    else:
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
        pbv = price / bvps if bvps > 0 else 1.2
        return roe, eps, pbv, der

def main():
    global usd_idr
    print("🔬 RUNNING SIMULATION TO COLLECT 3 STRATEGIES FOR PLOTTING...")
    
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    weights_path = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/data/models/ridge_weights.json"
    artifact_dir = "/Users/satriabaladewaharahap/.gemini/antigravity-ide/brain/85414e74-7f32-4a34-98f1-6bf79908bc9d"
    
    if not os.path.exists(raw_data_path):
        print("❌ Data file tidak ditemukan!")
        return
        
    with open(raw_data_path) as f:
        raw_data = json.load(f)
        
    print("💱 Downloading USD/IDR exchange rate...")
    usd_idr_df = yf.download("USDIDR=X", start="2021-11-01", end="2025-12-31")
    close_series = usd_idr_df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
    usd_idr = close_series.dropna().to_dict()
    usd_idr = {str(k)[:10]: float(v) for k, v in usd_idr.items()}
        
    price_dfs = {}
    for kode in SAHAM_LIST_20:
        if kode in raw_data["prices"]:
            df = pd.DataFrame(raw_data["prices"][kode])
            df.index = pd.to_datetime(df.index)
            price_dfs[kode] = df.sort_index()
            
    ihsg_df = pd.DataFrame(raw_data["benchmark"])
    ihsg_df.index = pd.to_datetime(ihsg_df.index)
    ihsg_df = ihsg_df.sort_index()

    print("📈 Pre-calculating indicators...")
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

    ihsg_df["sma50"] = ihsg_df["Close"].rolling(window=50).mean()
    ihsg_df["sma200"] = ihsg_df["Close"].rolling(window=200).mean()
    delta_i = ihsg_df["Close"].diff()
    gain_i = delta_i.clip(lower=0)
    loss_i = -delta_i.clip(upper=0)
    avg_gain_i = gain_i.rolling(window=14).mean()
    avg_loss_i = loss_i.rolling(window=14).mean()
    rs_i = avg_gain_i / avg_loss_i
    ihsg_df["rsi14"] = 100 - (100 / (1 + rs_i))
    ihsg_df["log_return"] = np.log(ihsg_df["Close"] / ihsg_df["Close"].shift(1))
    ihsg_df["vol20"] = ihsg_df["log_return"].rolling(window=20).std() * np.sqrt(252) * 100
    
    ihsg_df["sma50"] = ihsg_df["sma50"].ffill().bfill().fillna(ihsg_df["Close"])
    ihsg_df["sma200"] = ihsg_df["sma200"].ffill().bfill().fillna(ihsg_df["Close"])
    ihsg_df["rsi14"] = ihsg_df["rsi14"].ffill().bfill().fillna(50.0)
    ihsg_df["vol20"] = ihsg_df["vol20"].ffill().bfill().fillna(12.0)

    start_date = pd.to_datetime("2022-01-03")
    end_date = pd.to_datetime("2025-12-30")
    trading_days = ihsg_df.loc[start_date:end_date].index
    
    weekly_rebal_dates = [d for d in trading_days if d.dayofweek == 0]
    monthly_rebal_dates = []
    current_month = -1
    for day in trading_days:
        if day.month != current_month:
            monthly_rebal_dates.append(day)
            current_month = day.month
            
    starting_cash = 1_000_000_000.0
    fee_buy = 0.0020
    fee_sell = 0.0030
    
    # Portfolios to simulate
    portfolios = {
        "trading_heuristic": {"cash": starting_cash, "holdings": {}, "fees": 0.0, "vals": {}},
        "hybrid_heuristic": {"cash": starting_cash, "holdings": {}, "fees": 0.0, "vals": {}}
    }
    
    ihsg_val = {}
    ihsg_shares = starting_cash / ihsg_df.loc[trading_days[0], "Open"]
    
    print("⏳ Running simulation loop...")
    for today in trading_days:
        today_str = str(today.date())
        kurs = get_kurs(today_str)
        
        # A. UPDATE VALUES
        for name, port in portfolios.items():
            val = port["cash"]
            for k, shares in port["holdings"].items():
                p = price_dfs[k].loc[today, "Close"] if today in price_dfs[k].index else price_dfs[k].asof(today)["Close"]
                val += shares * p
            port["vals"][today] = val
        ihsg_val[today] = ihsg_shares * ihsg_df.loc[today, "Close"]
        
        # B. DYNAMIC SECTORAL PBV FOR RELATIVE PBV
        pbvs_today = {}
        for kode in SAHAM_LIST_20:
            if today not in price_dfs[kode].index:
                continue
            p = price_dfs[kode].loc[today, "Close"]
            _, _, pbv_val, _ = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
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
            sector_means[sec] = np.mean(vals) if len(vals) > 0 else all_pbvs_mean
                
        pbvs_relative_today = {}
        for kode, pbv_val in pbvs_today.items():
            sec = SECTOR_MAP.get(kode, "Other")
            baseline = sector_means.get(sec, all_pbvs_mean)
            pbvs_relative_today[kode] = pbv_val / baseline if baseline > 0 else 1.0

        # C. GET REGIME WEIGHTS (HEURISTIC ONLY AS RIDGE IS NOT USED BY USER)
        ihsg_row = ihsg_df.loc[today]
        close_val = ihsg_row["Close"]
        sma200_val = ihsg_row["sma200"]
        rsi_val = ihsg_row["rsi14"]
        vol_20d = ihsg_row["vol20"]
        
        h_f = 0.30; h_t = 0.35; h_s = 0.20; h_r = 0.15
        
        if close_val > sma200_val and rsi_val > 45 and vol_20d < 15.0:
            h_f = 0.25; h_t = 0.45; h_s = 0.20; h_r = 0.10
        elif close_val < sma200_val and vol_20d > 18.0:
            h_f = 0.40; h_t = 0.15; h_s = 0.20; h_r = 0.25
        elif rsi_val > 70:
            h_f = 0.30; h_t = 0.25; h_s = 0.20; h_r = 0.25
        elif rsi_val < 30:
            h_f = 0.45; h_t = 0.20; h_s = 0.20; h_r = 0.15

        # D. WEEKLY REBALANCING (TRADING HEURISTIC)
        if today in weekly_rebal_dates:
            scores_h = {}
            for kode in SAHAM_LIST_20:
                if today not in price_dfs[kode].index:
                    continue
                p = price_dfs[kode].loc[today, "Close"]
                roe, eps, _, der = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
                pbv_rel = pbvs_relative_today.get(kode, 1.0)
                
                s_fundamental = hitung_skor_fundamental_rel(roe, eps, pbv_rel, der)
                s_sektor = 70.0
                
                # Multi-Timeframe Trend
                df_hist_stock = price_dfs[kode].loc[:today]
                df_weekly = df_hist_stock.resample("W").agg({"Close": "last", "Volume": "sum"})
                if len(df_weekly) >= 5:
                    df_weekly["ma5"] = df_weekly["Close"].rolling(window=5).mean()
                    df_weekly["ma20"] = df_weekly["Close"].rolling(window=min(20, len(df_weekly))).mean()
                    df_weekly["ma52"] = df_weekly["Close"].rolling(window=min(52, len(df_weekly))).mean()
                    df_weekly["vol_ma20"] = df_weekly["Volume"].rolling(window=min(20, len(df_weekly))).mean()
                    
                    latest_w = df_weekly.iloc[-1]
                    w_close = float(latest_w["Close"])
                    w_vol = float(latest_w["Volume"])
                    w_ma5 = float(latest_w["ma5"]) if pd.notna(latest_w["ma5"]) else w_close
                    w_ma20 = float(latest_w["ma20"]) if pd.notna(latest_w["ma20"]) else w_close
                    w_ma52 = float(latest_w["ma52"]) if pd.notna(latest_w["ma52"]) else w_close
                    w_vol_ma20 = float(latest_w["vol_ma20"]) if pd.notna(latest_w["vol_ma20"]) else w_vol
                    
                    s_trend = 0.0
                    if w_close > w_ma5: s_trend += 20.0
                    if w_close > w_ma20: s_trend += 30.0
                    if w_close > w_ma52: s_trend += 30.0
                    if w_vol > w_vol_ma20: s_trend += 20.0
                else:
                    s_trend = 50.0
                
                # Tech risk
                sma50_val = price_dfs[kode].loc[today, "sma50"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["sma50"]
                rsi14_val = price_dfs[kode].loc[today, "rsi14"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["rsi14"]
                tech_score = hitung_skor_teknikal(p, sma50_val, rsi14_val)
                s_risiko = (80.0 * 0.6) + (tech_score * 0.4)
                
                scores_h[kode] = (s_fundamental * h_f) + (s_sektor * h_s) + (s_trend * h_t) + (s_risiko * h_r)
                
            curr_h = list(portfolios["trading_heuristic"]["holdings"].keys())
            top_5_h = select_top_5_with_buffer(scores_h, curr_h, SECTOR_MAP, buffer_rank=10)
            portfolios["trading_heuristic"]["holdings"], portfolios["trading_heuristic"]["cash"], portfolios["trading_heuristic"]["fees"] = rebalance_portfolio(
                portfolios["trading_heuristic"]["holdings"], portfolios["trading_heuristic"]["cash"], portfolios["trading_heuristic"]["fees"],
                top_5_h, today, price_dfs, fee_buy, fee_sell
            )

        # E. MONTHLY REBALANCING (HYBRID HEURISTIC / VALUE INVESTING)
        if today in monthly_rebal_dates:
            scores_h = {}
            for kode in SAHAM_LIST_20:
                if today not in price_dfs[kode].index:
                    continue
                p = price_dfs[kode].loc[today, "Close"]
                roe, eps, _, der = get_fundamental_variables(kode, raw_data, today, today_str, p, kurs)
                pbv_rel = pbvs_relative_today.get(kode, 1.0)
                
                s_fundamental = hitung_skor_fundamental_rel(roe, eps, pbv_rel, der)
                s_sektor = 70.0
                
                # Multi-Timeframe Trend
                df_hist_stock = price_dfs[kode].loc[:today]
                df_weekly = df_hist_stock.resample("W").agg({"Close": "last", "Volume": "sum"})
                if len(df_weekly) >= 5:
                    df_weekly["ma5"] = df_weekly["Close"].rolling(window=5).mean()
                    df_weekly["ma20"] = df_weekly["Close"].rolling(window=min(20, len(df_weekly))).mean()
                    df_weekly["ma52"] = df_weekly["Close"].rolling(window=min(52, len(df_weekly))).mean()
                    df_weekly["vol_ma20"] = df_weekly["Volume"].rolling(window=min(20, len(df_weekly))).mean()
                    
                    latest_w = df_weekly.iloc[-1]
                    w_close = float(latest_w["Close"])
                    w_vol = float(latest_w["Volume"])
                    w_ma5 = float(latest_w["ma5"]) if pd.notna(latest_w["ma5"]) else w_close
                    w_ma20 = float(latest_w["ma20"]) if pd.notna(latest_w["ma20"]) else w_close
                    w_ma52 = float(latest_w["ma52"]) if pd.notna(latest_w["ma52"]) else w_close
                    w_vol_ma20 = float(latest_w["vol_ma20"]) if pd.notna(latest_w["vol_ma20"]) else w_vol
                    
                    s_trend = 0.0
                    if w_close > w_ma5: s_trend += 20.0
                    if w_close > w_ma20: s_trend += 30.0
                    if w_close > w_ma52: s_trend += 30.0
                    if w_vol > w_vol_ma20: s_trend += 20.0
                else:
                    s_trend = 50.0
                    
                # Tech risk
                sma50_val = price_dfs[kode].loc[today, "sma50"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["sma50"]
                rsi14_val = price_dfs[kode].loc[today, "rsi14"] if today in price_dfs[kode].index else price_dfs[kode].asof(today)["rsi14"]
                tech_score = hitung_skor_teknikal(p, sma50_val, rsi14_val)
                s_risiko = (80.0 * 0.6) + (tech_score * 0.4)
                
                scores_h[kode] = (s_fundamental * h_f) + (s_sektor * h_s) + (s_trend * h_t) + (s_risiko * h_r)
                
            curr_h = list(portfolios["hybrid_heuristic"]["holdings"].keys())
            top_5_h = select_top_5_with_buffer(scores_h, curr_h, SECTOR_MAP, buffer_rank=8)
            portfolios["hybrid_heuristic"]["holdings"], portfolios["hybrid_heuristic"]["cash"], portfolios["hybrid_heuristic"]["fees"] = rebalance_portfolio(
                portfolios["hybrid_heuristic"]["holdings"], portfolios["hybrid_heuristic"]["cash"], portfolios["hybrid_heuristic"]["fees"],
                top_5_h, today, price_dfs, fee_buy, fee_sell
            )

    # Liquidate final day for final pricing check
    last_day = trading_days[-1]
    for name, port in portfolios.items():
        final_val = port["cash"]
        for k, shares in port["holdings"].items():
            p = price_dfs[k].loc[last_day, "Close"]
            revenue = shares * p
            fee = revenue * fee_sell
            port["fees"] += fee
            final_val += (revenue - fee)
        port["vals"][last_day] = final_val

    # Convert to Dataframe for plotting
    df_plot = pd.DataFrame({
        "Trading": pd.Series(portfolios["trading_heuristic"]["vals"]),
        "Investing": pd.Series(portfolios["hybrid_heuristic"]["vals"]),
        "IHSG": pd.Series(ihsg_val)
    })
    
    # Save CSV
    csv_out_path = os.path.join(data_dir, "backtest_new_system_3lines.csv")
    df_plot.to_csv(csv_out_path, index_label="tanggal")
    print(f"✅ Daily values saved to {csv_out_path}")
    
    # Convert values to Billion Rupiah
    df_plot_b = df_plot / 1e9
    
    # Matplotlib Premium Plotting (Dark Mode)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    fig.patch.set_facecolor('#0f172a')  # Slate 900
    ax.set_facecolor('#0f172a')
    
    # Colors
    color_trading = '#fb923c'   # Premium Orange 400
    color_investing = '#2dd4bf' # Premium Teal 400
    color_ihsg = '#94a3b8'      # Slate 400
    
    # Plot lines
    ax.plot(df_plot_b.index, df_plot_b["Trading"], color=color_trading, label='Swing Trading (Weekly - Heuristic)', linewidth=3.0)
    ax.plot(df_plot_b.index, df_plot_b["Investing"], color=color_investing, label='Value Investing (Monthly - Heuristic)', linewidth=2.5)
    ax.plot(df_plot_b.index, df_plot_b["IHSG"], color=color_ihsg, label='IHSG (Benchmark)', linewidth=1.8, linestyle='--')
    
    # Customize labels and title
    ax.set_title("Grafik Perbandingan Backtesting Sistem Terbaru (2022 - 2025)\nPerforma Model dengan Sector Cap & Holding Buffer", 
                 fontsize=15, fontweight='bold', color='#f8fafc', pad=20)
    ax.set_xlabel("Tanggal", fontsize=11, color='#cbd5e1', labelpad=10)
    ax.set_ylabel("Nilai Portofolio (Miliar Rupiah)", fontsize=11, color='#cbd5e1', labelpad=10)
    
    # Grid styling
    ax.grid(True, which='both', color='#1e293b', linestyle=':', linewidth=0.8)
    
    # X/Y Axis ticks formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=25, color='#cbd5e1')
    plt.yticks(color='#cbd5e1')
    
    # Remove outer borders
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    # Legend
    legend = ax.legend(loc='upper left', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=10)
    for text in legend.get_texts():
        text.set_color('#f8fafc')
        
    # Annotations for final values
    last_date = df_plot_b.index[-1]
    val_trading = df_plot_b['Trading'].iloc[-1]
    val_investing = df_plot_b['Investing'].iloc[-1]
    val_ihsg = df_plot_b['IHSG'].iloc[-1]
    
    ax.annotate(f"Rp {val_trading:.3f} B\n(+147.68%)", 
                xy=(last_date, val_trading), 
                xytext=(8, -5), textcoords='offset points', 
                color=color_trading, fontweight='bold', fontsize=9.5)
                
    ax.annotate(f"Rp {val_investing:.3f} B\n(+95.04%)", 
                xy=(last_date, val_investing), 
                xytext=(8, -5), textcoords='offset points', 
                color=color_investing, fontweight='bold', fontsize=9.5)
                
    ax.annotate(f"Rp {val_ihsg:.3f} B\n(+31.29%)", 
                xy=(last_date, val_ihsg), 
                xytext=(8, -5), textcoords='offset points', 
                color=color_ihsg, fontweight='bold', fontsize=9.5)
                
    plt.tight_layout()
    
    # Save to outputs
    out_scratch = os.path.join(data_dir, "backtest_new_system.png")
    out_artifact = os.path.join(artifact_dir, "backtest_new_system.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chart successfully plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
