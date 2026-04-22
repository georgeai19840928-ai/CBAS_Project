import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from main import get_cbas_live_data, config
from data.market_data import get_bulk_technical_data
from core.analyzer import RPAnalyzer

# Pretend we are running main.py logic
df = get_cbas_live_data()
if df.empty:
    print("API Failed")
    sys.exit()

# Set relaxed filters
price_range = (80, 200)
prem_range = (-10, 50)
ratio_min = 0
parity_range = (50, 150)
min_vol_avg = 100 # Low volume requirement

mask = (df['CB市價'].between(price_range[0], price_range[1])) & \
       (df['溢/折價'].between(prem_range[0], prem_range[1])) & \
       (df['餘額'] >= ratio_min) & \
       (df['轉換價值'].between(parity_range[0], parity_range[1]))
       
candidates_pre = df[mask].copy()
print(f"Candidates Pre: {len(candidates_pre)}")

# Test just 2 candidates
target_codes = ['1101', '1256']
candidates_pre = candidates_pre[candidates_pre['股票代號'].isin(target_codes)]
print(f"Testing 2 candidates: {candidates_pre['代號'].tolist()}")

unique_codes = candidates_pre['股票代號'].unique().tolist()
bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)

for i, (idx, row) in enumerate(candidates_pre.iterrows()):
    tech = bulk_tech_data.get(row['股票代號'])
    print(f"\n--- {row['股票代號']} Tech Data ---")
    print(tech)
    
    if tech and tech['vol_avg_sheets'] < min_vol_avg: 
        print(f"** Skipped {row['股票代號']} due to volume < {min_vol_avg}")
        continue
        
    print(f"++ Kept {row['股票代號']}")
