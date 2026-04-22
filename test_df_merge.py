import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from main import get_cbas_live_data, config
from data.market_data import get_bulk_technical_data
from core.analyzer import RPAnalyzer

df = get_cbas_live_data()
candidates_pre = df.head(3).copy()

unique_codes = candidates_pre['股票代號'].unique().tolist()
bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)

final_results = []
for i, (idx, row) in enumerate(candidates_pre.iterrows()):
    tech = bulk_tech_data.get(row['股票代號'])
    print(f"Tech for {row['股票代號']}:", "Exists" if tech else "None!")
    
    r, p, lbl, gold = RPAnalyzer.calculate_score(row, tech, row['上市天數'], config)
    
    res = row.to_dict()
    res.update({
        'R值': r, 'P值': p, '策略標籤': lbl,
        '母股價': float(tech['price']) if tech and tech.get('price') is not None else None,
        '均量': int(tech['vol_avg_sheets']) if tech and tech.get('vol_avg_sheets') is not None else None,
        '60MA': round(float(tech['ma60']), 2) if tech and tech.get('ma60') is not None else None,
        '87MA': round(float(tech['ma87']), 2) if tech and tech.get('ma87') is not None else None,
        'EPS': float(tech['fundamentals'].get('eps')) if tech and 'fundamentals' in tech and tech['fundamentals'].get('eps') is not None else None,
        'PE': round(float(tech['fundamentals'].get('pe', 0)), 1) if tech and 'fundamentals' in tech and tech['fundamentals'].get('pe') is not None else None
    })
    final_results.append(res)

final_df = pd.DataFrame(final_results)
print("\n--- FINAL DF COLUMNS ---")
print(final_df[['代號', '母股價', '均量', 'PE']])
