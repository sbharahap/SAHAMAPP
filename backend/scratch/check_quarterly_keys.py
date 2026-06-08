import json
import os

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    
    with open(raw_data_path) as f:
        data = json.load(f)
        
    # Check BBCA quarterly financials
    fin = data["financials"].get("BBCA", {})
    print("KEYS in financials for BBCA:")
    print(list(fin.keys()))
    
    q_is = fin.get("quarterly_income_statement", {})
    print("\nDates in quarterly income statement:")
    dates = list(q_is.keys())
    print(dates[:5])
    
    if dates:
        print(f"\nKeys in quarterly IS for date {dates[0]}:")
        print(list(q_is[dates[0]].keys())[:15])

if __name__ == "__main__":
    main()
