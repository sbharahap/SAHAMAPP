import yfinance as yf
import pandas as pd
import numpy as np
from backend.config import settings

def get_technical_indicators_live(kode: str):
    try:
        ticker_symbol = f"{kode}{settings.yfinance_market_suffix}"
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="100d")
        if df is not None and len(df) >= 50:
            df["sma50"] = df["Close"].rolling(window=50).mean()
            delta = df["Close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df["rsi14"] = 100 - (100 / (1 + rs))
            
            latest = df.iloc[-1]
            close_price = latest["Close"]
            sma50 = latest["sma50"]
            rsi14 = latest["rsi14"]
            return close_price, sma50, rsi14
    except Exception as e:
        print(f"Error for {kode}: {e}")
    return None

if __name__ == "__main__":
    for k in ["BBCA", "BBRI"]:
        res = get_technical_indicators_live(k)
        if res:
            close, sma, rsi = res
            print(f"{k} -> Close: {close}, SMA50: {sma:.2f}, RSI14: {rsi:.2f}")
