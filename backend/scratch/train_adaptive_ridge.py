import json
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.linear_model import Ridge

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

def _skor_sektor(sektor_saham, kinerja_sektoral, perubahan_ihsg):
    kinerja_sektor = kinerja_sektoral.get(sektor_saham.lower(), 0)
    selisih = kinerja_sektor - perubahan_ihsg
    skor = 50.0 + (selisih / 5.0) * 50.0
    return round(max(0.0, min(100.0, skor)), 2)

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
    print("=" * 100)
    print("🎓 TRAINING MARKET-ADAPTIVE RIDGE SCORING WEIGHTS")
    print("=" * 100)
    
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    
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

    print("📈 Pre-calculating daily indicators...")
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

    # IHSG daily indicators
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
    end_date = pd.to_datetime("2025-12-23") # Keep one week buffer at the end for forward return
    trading_days = ihsg_df.loc[start_date:end_date].index
    weekly_dates = [d for d in trading_days if d.dayofweek == 0]

    samples = []
    
    print("⏳ Extracting weekly factor scores and forward returns...")
    for idx_w, today in enumerate(weekly_dates[:-1]):
        next_week = weekly_dates[idx_w + 1]
        today_str = str(today.date())
        kurs = get_kurs(today_str)
        
        # 1. Market Regime
        ihsg_row = ihsg_df.loc[today]
        close_val = ihsg_row["Close"]
        sma200_val = ihsg_row["sma200"]
        rsi_val = ihsg_row["rsi14"]
        vol_20d = ihsg_row["vol20"]
        
        regime = "Normal / Sideways"
        if close_val > sma200_val and rsi_val > 45 and vol_20d < 15.0:
            regime = "Bull Market / Strong Uptrend"
        elif close_val < sma200_val and vol_20d > 18.0:
            regime = "Bear Market / Strong Downtrend"
        elif rsi_val > 70:
            regime = "Market Overbought / Correction Risk"
        elif rsi_val < 30:
            regime = "Market Oversold / Rebound Potential"

        # Calculate IHSG weekly return
        ihsg_close_today = ihsg_df.loc[today, "Close"]
        ihsg_close_next = ihsg_df.loc[next_week, "Close"]
        perubahan_ihsg = (ihsg_close_next - ihsg_close_today) / ihsg_close_today * 100

        # Calculate Sector performance for this week (average of stocks)
        stock_returns_this_week = {}
        for kode in SAHAM_LIST_20:
            if today in price_dfs[kode].index and next_week in price_dfs[kode].index:
                p_today = price_dfs[kode].loc[today, "Close"]
                p_next = price_dfs[kode].loc[next_week, "Close"]
                stock_returns_this_week[kode] = (p_next - p_today) / p_today * 100
        
        sector_returns_this_week = {}
        for sec in set(SECTOR_MAP.values()):
            sec_stocks = [k for k, s in SECTOR_MAP.items() if s == sec]
            rets = [stock_returns_this_week[k] for k in sec_stocks if k in stock_returns_this_week]
            sector_returns_this_week[sec] = np.mean(rets) if rets else 0.0

        # Relative PBV sector baselines for this week
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

        for kode in SAHAM_LIST_20:
            if today not in price_dfs[kode].index or next_week not in price_dfs[kode].index:
                continue
            
            p_today = price_dfs[kode].loc[today, "Close"]
            p_next = price_dfs[kode].loc[next_week, "Close"]
            
            # Forward return (y)
            fwd_return = (p_next - p_today) / p_today * 100
            
            # Scores
            roe, eps, _, der = get_fundamental_variables(kode, raw_data, today, today_str, p_today, kurs)
            sec = SECTOR_MAP.get(kode, "Other")
            pbv_val = pbvs_today.get(kode, 1.2)
            baseline = sector_means.get(sec, all_pbvs_mean)
            pbv_rel = pbv_val / baseline if baseline > 0 else 1.0
            
            s_fund = hitung_skor_fundamental_rel(roe, eps, pbv_rel, der)
            s_sektor = _skor_sektor(sec, sector_returns_this_week, perubahan_ihsg)
            
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
            tech_score = hitung_skor_teknikal(p_today, sma50_val, rsi14_val)
            s_risk = (80.0 * 0.6) + (tech_score * 0.4)
            
            samples.append({
                "regime": regime,
                "fundamental": s_fund,
                "sektor": s_sektor,
                "trend": s_trend,
                "risiko": s_risk,
                "y": fwd_return
            })
            
    df_samples = pd.DataFrame(samples)
    print(f"📊 Total samples extracted: {len(df_samples)}")
    
    # ----------------------------------------------------
    # TRAIN RIDGE FOR EACH REGIME
    # ----------------------------------------------------
    trained_weights = {}
    regimes = [
        "Normal / Sideways",
        "Bull Market / Strong Uptrend",
        "Bear Market / Strong Downtrend",
        "Market Overbought / Correction Risk",
        "Market Oversold / Rebound Potential"
    ]
    
    # Defaults in case of no data
    defaults = {
        "Normal / Sideways": {"fundamental": 0.30, "sektor": 0.20, "trend": 0.35, "risiko": 0.15},
        "Bull Market / Strong Uptrend": {"fundamental": 0.25, "sektor": 0.20, "trend": 0.45, "risiko": 0.10},
        "Bear Market / Strong Downtrend": {"fundamental": 0.40, "sektor": 0.20, "trend": 0.15, "risiko": 0.25},
        "Market Overbought / Correction Risk": {"fundamental": 0.30, "sektor": 0.20, "trend": 0.25, "risiko": 0.25},
        "Market Oversold / Rebound Potential": {"fundamental": 0.45, "sektor": 0.20, "trend": 0.20, "risiko": 0.15}
    }
    
    for r in regimes:
        df_r = df_samples[df_samples["regime"] == r]
        if len(df_r) < 10:
            print(f"⚠️ Regime '{r}' has too few samples ({len(df_r)}). Using baseline weights.")
            trained_weights[r] = defaults[r]
            continue
            
        X = df_r[["fundamental", "sektor", "trend", "risiko"]]
        y = df_r["y"]
        
        # Train Ridge regression with L2 penalty, fit_intercept=False so coefs directly match weights
        ridge = Ridge(alpha=100.0, fit_intercept=False)
        ridge.fit(X, y)
        
        # Enforce minimum weight of 10% per component to ensure diversification
        min_w = 0.10
        coefs = np.clip(ridge.coef_, a_min=0, a_max=None)
        
        if np.sum(coefs) > 0:
            norm_coefs = coefs / np.sum(coefs)
            w_fund = min_w + norm_coefs[0] * (1.0 - 4 * min_w)
            w_sektor = min_w + norm_coefs[1] * (1.0 - 4 * min_w)
            w_trend = min_w + norm_coefs[2] * (1.0 - 4 * min_w)
            w_risk = min_w + norm_coefs[3] * (1.0 - 4 * min_w)
            
            trained_weights[r] = {
                "fundamental": round(float(w_fund), 2),
                "sektor": round(float(w_sektor), 2),
                "trend": round(float(w_trend), 2),
                "risiko": round(float(w_risk), 2)
            }
            # Adjust rounding errors to exactly 1.00
            diff = 1.00 - sum(trained_weights[r].values())
            if diff != 0:
                trained_weights[r]["trend"] = round(trained_weights[r]["trend"] + diff, 2)
        else:
            trained_weights[r] = defaults[r]
            
        print(f"🎯 Regime '{r}' weights: {trained_weights[r]} (based on {len(df_r)} samples)")

    # Save to models path
    models_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/data/models"
    os.makedirs(models_dir, exist_ok=True)
    weights_path = os.path.join(models_dir, "ridge_weights.json")
    with open(weights_path, "w") as f:
        json.dump(trained_weights, f, indent=4)
        
    print("\n" + "=" * 100)
    print(f"✅ MARKET-ADAPTIVE RIDGE WEIGHTS TRAINED SUCCESSFULLY!")
    print(f"💾 Saved to: {weights_path}")
    print("=" * 100)
    print(f"{'Market Regime':<40} | {'Fund (%)':<8} | {'Sektor (%)':<10} | {'Trend (%)':<9} | {'Risiko (%)':<10}")
    print("-" * 90)
    for r, w in trained_weights.items():
        print(f"{r:<40} | {w['fundamental']:.0%}     | {w['sektor']:.0%}       | {w['trend']:.0%}      | {w['risiko']:.0%}")
    print("=" * 100)

if __name__ == "__main__":
    main()
