import yfinance as yf
import json

def main():
    ticker = yf.Ticker("BBCA.JK")
    print("Quarterly Balance Sheet:")
    try:
        bs = ticker.quarterly_balance_sheet
        print(list(bs.index))
        print(bs.columns)
    except Exception as e:
        print("Error Balance Sheet:", e)
        
    print("\nQuarterly Financials / Income Statement:")
    try:
        is_df = ticker.quarterly_financials
        print(list(is_df.index))
        print(is_df.columns)
    except Exception as e:
        print("Error Financials:", e)

if __name__ == "__main__":
    main()
