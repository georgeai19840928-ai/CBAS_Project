import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from main import get_cbas_live_data, config
from data.market_data import get_bulk_technical_data

df = get_cbas_live_data()
candidates_pre = df.head(5).copy() # Just test first 5

unique_codes = candidates_pre['股票代號'].unique().tolist()
print(f"Fetching data for: {unique_codes}")
bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)

for i, (idx, row) in enumerate(candidates_pre.iterrows()):
    tech = bulk_tech_data.get(row['股票代號'])
    print(f"\n--- Code: {row['股票代號']} ---")
    if not tech:
        print("Tech is None!")
        continue
    
    try:
        price = float(tech['price']) if tech.get('price') is not None else None
        print(f"Price parsed: {price}")
    except Exception as e:
        print(f"Price Error: {e}")
        
    try:
        pe = round(float(tech['fundamentals'].get('pe', 0)), 1) if 'fundamentals' in tech and tech['fundamentals'].get('pe') is not None else None
        print(f"PE parsed: {pe}")
    except Exception as e:
        print(f"PE Error: {e}")
