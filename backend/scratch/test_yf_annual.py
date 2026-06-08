import yfinance as yf

def main():
    ticker = yf.Ticker("BBCA.JK")
    print("Annual Balance Sheet Columns:")
    try:
        bs = ticker.balance_sheet
        print(bs.columns)
    except Exception as e:
        print("Error Balance Sheet:", e)
        
    print("\nAnnual Financials Columns:")
    try:
        is_df = ticker.financials
        print(is_df.columns)
    except Exception as e:
        print("Error Financials:", e)

if __name__ == "__main__":
    main()
