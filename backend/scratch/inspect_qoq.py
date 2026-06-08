import json
import os
import pandas as pd

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    raw_data_path = os.path.join(data_dir, "backtest_raw_data.json")
    
    with open(raw_data_path) as f:
        data = json.load(f)
        
    fin = data["financials"].get("BBCA", {})
    q_is = fin.get("quarterly_income_statement", {})
    
    print("Quarterly Net Income for BBCA:")
    for date_str, metrics in sorted(q_is.items()):
        net_inc = metrics.get("Net Income")
        print(f"  {date_str}: {net_inc}")
        
if __name__ == "__main__":
    main()
