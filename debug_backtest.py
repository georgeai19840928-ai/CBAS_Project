import os, sys, json
sys.path.append('d:/私人/CBAS_Project')
from core.backtest_loader import BacktestLoader
from core.backtester import CBASBacktester
from core.analyzer import RPAnalyzer

with open('d:/私人/CBAS_Project/strategy_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Override with user settings
config.update({
    'filter_price_min': 105, 'filter_price_max': 130,
    'filter_prem_min': -5, 'filter_prem_max': 15,
    'filter_ratio_min': 75,
    'filter_parity_min': 90, 'filter_parity_max': 110,
    'entry_p_score': 6, 'exit_p_score': 3,
    'take_profit_pct': 1.0, 'stop_loss_pct': -0.2
})

loader = BacktestLoader(data_dir='d:/私人/CBAS_Project/data/historical_data')
snapshots = loader.load_snapshots()
hist_data = loader.fetch_historical_market_data(snapshots)

engine = CBASBacktester(initial_capital=1000000, config=config)
res = engine.run(snapshots, hist_data, RPAnalyzer)
print('Total Trades:', res['metrics']['Total Trades'])

print('Testing filters manually on the first snapshot')
passed = 0
for idx, row in snapshots[0]['df'].iterrows():
    cb_price = row.get('CB市價', 0)
    prem = row.get('溢/折價', 0)
    ratio = row.get('餘額', 0)
    parity = row.get('轉換價值', 0)
    if 105 <= cb_price <= 130 and -0.05 <= prem <= 0.15 and ratio >= 75 and 0.90 <= parity <= 1.10:
        code = row['股票代號']
        if code in hist_data and snapshots[0]['date'] in hist_data[code]:
            tech = hist_data[code][snapshots[0]['date']]
            res_dict = RPAnalyzer.calculate_score(row.to_dict(), tech, config)
            print(f"Passed Hard Filters: {row['代號']} | P Score: {res_dict.get('P_Score')} | R Score: {res_dict.get('R_Score')}")
            passed += 1
print('Total passed hard filters in snap 1:', passed)
