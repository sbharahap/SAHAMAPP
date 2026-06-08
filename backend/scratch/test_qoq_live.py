import asyncio
import yfinance as yf
import pandas as pd
from backend.config import settings

def get_qoq_growth_live(kode: str) -> float:
    try:
        ticker_symbol = f"{kode}{settings.yfinance_market_suffix}"
        ticker = yf.Ticker(ticker_symbol)
        is_df = ticker.quarterly_financials
        if is_df is None or is_df.empty or "Net Income" not in is_df.index:
            is_df = ticker.quarterly_income_stmt
            
        if is_df is not None and not is_df.empty and "Net Income" in is_df.index:
            net_inc_row = is_df.loc["Net Income"]
            if isinstance(net_inc_row, pd.DataFrame):
                # Sometimes yfinance returns a DataFrame instead of a Series if there are duplicate rows
                net_inc_row = net_inc_row.iloc[0]
            if len(net_inc_row) >= 2:
                latest_val = net_inc_row.iloc[0]
                prev_val = net_inc_row.iloc[1]
                if pd.notna(latest_val) and pd.notna(prev_val) and prev_val != 0:
                    growth = (latest_val - prev_val) / abs(prev_val) * 100
                    return round(growth, 2)
    except Exception as e:
        print(f"Error fetching for {kode}: {e}")
    return 0.0

if __name__ == "__main__":
    for k in ["BBCA", "BBRI"]:
        growth = get_qoq_growth_live(k)
        print(f"QoQ Net Income Growth for {k}: {growth}%")
