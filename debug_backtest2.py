import os, sys, json
sys.path.append('d:/私人/CBAS_Project')
from core.backtest_loader import BacktestLoader
from core.backtester import CBASBacktester
from core.analyzer import RPAnalyzer

with open('d:/私人/CBAS_Project/strategy_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

config.update({
    'filter_price_min': 105, 'filter_price_max': 130,
    'filter_prem_min': -5, 'filter_prem_max': 15,
    'filter_ratio_min': 75,
    'filter_parity_min': 90, 'filter_parity_max': 105,
    'filter_vol_min': 2000,
    'entry_p_score': 6, 'exit_p_score': 3,
    'take_profit_pct': 1.0, 'stop_loss_pct': -0.2,
    'max_positions': 5
})

loader = BacktestLoader(data_dir='d:/私人/CBAS_Project/data/historical_data')
snapshots = loader.load_snapshots()
hist_data = loader.fetch_historical_market_data(snapshots)

engine = CBASBacktester(initial_capital=1000000, config=config)
res = engine.run(snapshots, hist_data, RPAnalyzer)
print('Total Trades:', res['metrics']['Total Trades'])

# Let us trace exactly one snapshot
snap = snapshots[0]
print(f"\nTracing Snapshot {snap['date']}:")
df = snap['df']
for _, row in df.iterrows():
    symbol = str(row['代號']).replace(' ', '')
    cb_price = row.get('CB市價', 0)
    prem = row.get('溢/折價', 0)
    ratio = row.get('餘額', 0)
    parity = row.get('轉換價值', 0)
    
    # Check hard filters
    if not (105 <= cb_price <= 130): continue
    if not (-0.05 <= prem <= 0.15): continue
    if ratio < 75: continue
    if not (0.90 <= parity <= 1.05): continue
    
    # Check volume
    stock_code = symbol[:4]
    tech = hist_data.get(stock_code, {}).get(snap['date'], {})
    vol = tech.get('vol_avg_sheets', 0)
    if vol < 2000:
        print(f'  {symbol} Failed Vol: {vol:.1f} < 2000')
        continue
        
    print(f'  {symbol} PASSED Hard Filters & Vol!')
    r_score, p_score, label, is_golden, warnings = RPAnalyzer.calculate_score(row.to_dict(), tech, row.get('上市天數', 365), config)
    print(f'  {symbol} P:{p_score} R:{r_score}')
