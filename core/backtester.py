import pandas as pd
import numpy as np
import datetime
import math

class BacktestMetrics:
    @staticmethod
    def calculate_metrics(equity_curve, trades):
        """
        equity_curve: pd.DataFrame with columns ['Date', 'Equity']
        trades: list of dicts with keys ['entry_date', 'exit_date', 'pnl', 'pnl_pct', ...]
        """
        metrics = {}
        
        # 1. Return
        if len(equity_curve) > 0:
            initial_cap = equity_curve['Equity'].iloc[0]
            final_cap = equity_curve['Equity'].iloc[-1]
            total_return = (final_cap - initial_cap) / initial_cap
            metrics['Total Return'] = total_return
        else:
            return metrics
            
        # 2. Daily returns for ratios
        equity_curve['Daily Return'] = equity_curve['Equity'].pct_change().fillna(0)
        daily_returns = equity_curve['Daily Return'].values
        
        # 3. Sharpe Ratio (assuming risk-free rate = 0% for simplicity)
        mean_ret = np.mean(daily_returns)
        std_ret = np.std(daily_returns)
        if std_ret > 0:
            sharpe = (mean_ret / std_ret) * np.sqrt(252) # Annualized
            metrics['Sharpe Ratio'] = sharpe
        else:
            metrics['Sharpe Ratio'] = 0.0
            
        # 4. Sortino Ratio
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        if downside_std > 0:
            sortino = (mean_ret / downside_std) * np.sqrt(252)
            metrics['Sortino Ratio'] = sortino
        else:
            metrics['Sortino Ratio'] = float('inf') if mean_ret > 0 else 0.0
            
        # 5. Max Drawdown (MDD)
        equity_curve['Peak'] = equity_curve['Equity'].cummax()
        equity_curve['Drawdown'] = (equity_curve['Equity'] - equity_curve['Peak']) / equity_curve['Peak']
        mdd = equity_curve['Drawdown'].min()
        metrics['Max Drawdown'] = mdd
        
        # 6. Calmar Ratio
        annualized_return = (1 + total_return) ** (252 / max(1, len(equity_curve))) - 1
        if abs(mdd) > 0:
            metrics['Calmar Ratio'] = annualized_return / abs(mdd)
        else:
            metrics['Calmar Ratio'] = float('inf') if annualized_return > 0 else 0.0

        # 7. Trade Stats
        if len(trades) > 0:
            winners = [t for t in trades if t['pnl'] > 0]
            losers = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = len(winners) / len(trades)
            metrics['Win Rate'] = win_rate
            
            avg_win = np.mean([t['pnl'] for t in winners]) if winners else 0
            avg_loss = abs(np.mean([t['pnl'] for t in losers])) if losers else 0
            
            metrics['P/L Ratio'] = (avg_win / avg_loss) if avg_loss > 0 else float('inf')
            
            total_profit = sum([t['pnl'] for t in winners])
            total_loss = abs(sum([t['pnl'] for t in losers]))
            metrics['Profit Factor'] = (total_profit / total_loss) if total_loss > 0 else float('inf')
            
            metrics['Expectancy'] = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            metrics['Total Trades'] = len(trades)
        else:
            metrics['Win Rate'] = 0.0
            metrics['P/L Ratio'] = 0.0
            metrics['Profit Factor'] = 0.0
            metrics['Expectancy'] = 0.0
            metrics['Total Trades'] = 0
            
        return metrics

class CBASBacktester:
    def __init__(self, initial_capital=1000000, config=None):
        self.initial_capital = initial_capital
        self.config = config
        self.capital = initial_capital
        self.positions = {} # symbol -> {entry_date, entry_price, shares}
        self.trade_log = []
        self.equity_history = []
        
    def run(self, weekly_snapshots, historical_market_data, analyzer_class):
        """
        weekly_snapshots: list of dict {'date': 'YYYY-MM-DD', 'df': pd.DataFrame} sorted by date
        historical_market_data: dict of dicts structure caching the needed historical tech data
                                e.g. historical_market_data[symbol][date] = tech_data_dict
        """
        from datetime import datetime
        
        for snapshot in weekly_snapshots:
            current_date = snapshot['date']
            df_cb = snapshot['df']
            
            # --- 1. Evaluate open positions and sell if condition triggered ---
            symbols_to_sell = []
            for symbol, pos in list(self.positions.items()):
                row_list = df_cb[df_cb['代號'] == symbol]
                trade_mode = self.config.get('trade_mode', 'CBAS')
                
                if row_list.empty:
                    # CB not in snapshot anymore (matured/delisted)
                    last_px = pos.get('last_price', pos['entry_price'])
                    last_rate = pos.get('last_fixed_rate', pos.get('entry_fixed_rate', 0.05))
                    symbols_to_sell.append((symbol, last_px, last_rate, "下市/轉換/賣回")) # Force sell
                    continue
                
                row = row_list.iloc[0]
                current_price = row.get('CB市價', pos.get('last_price', pos['entry_price']))
                
                raw_rate = row.get('百元報價', pos.get('last_fixed_rate', pos.get('entry_fixed_rate', 0.05)))
                if pd.isna(raw_rate) or type(raw_rate) == str and raw_rate.strip() in ['-', '']: raw_rate = 0.05
                elif type(raw_rate) == str and '%' in raw_rate: raw_rate = float(raw_rate.replace('%', '')) / 100.0
                current_rate = float(raw_rate)
                
                pos['last_price'] = current_price
                pos['last_fixed_rate'] = current_rate
                
                # Check stop loss / take profit
                # Dynamic rules can be placed here or we just evaluate R/P score
                stock_code = symbol[:4]
                tech_data = historical_market_data.get(stock_code, {}).get(current_date, None)
                r_score, p_score, label, _, w_flags, _ = analyzer_class.calculate_score(row, tech_data, row.get('上市天數', 365), self.config)
                
                # --- 新增出場條件：硬性停損與停利 ---
                if trade_mode == 'CBAS':
                    current_premium = (current_rate * 100) + max(0, current_price - 100)
                    p_base = pos.get('entry_premium', 1)
                    pnl_pct = (current_premium - p_base) / p_base if p_base > 0 else 0
                else:
                    pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
                
                tp_pct = self.config.get('take_profit_pct', 0.20) # default 20%
                sl_pct = self.config.get('stop_loss_pct', -0.05) # default -5%
                exit_p = self.config.get('exit_p_score', 4)     # default P < 4
                exit_r = self.config.get('exit_r_score', 10)    # default R >= 10
                
                # Sell conditions:
                if pnl_pct >= tp_pct:
                    symbols_to_sell.append((symbol, current_price, current_rate, f"停利 (+{pnl_pct*100:.1f}%)"))
                elif pnl_pct <= sl_pct:
                    symbols_to_sell.append((symbol, current_price, current_rate, f"停損 ({pnl_pct*100:.1f}%)"))
                elif r_score >= exit_r or '☠️ 禁買' in w_flags:
                    symbols_to_sell.append((symbol, current_price, current_rate, f"觸發風險上限 (R={r_score})"))
                elif p_score < exit_p:
                    symbols_to_sell.append((symbol, current_price, current_rate, f"動能衰退 (P={p_score})"))
                    
            # Execute sells
            for sell_info in symbols_to_sell:
                symbol = sell_info[0]
                sell_price = sell_info[1]
                sell_rate = sell_info[2]
                reason = sell_info[3] if len(sell_info) > 3 else "下市/轉換/賣回"
                
                pos = self.positions.pop(symbol)
                trade_mode = self.config.get('trade_mode', 'CBAS')
                
                if trade_mode == 'CBAS':
                    sell_premium = (sell_rate * 100) + max(0, sell_price - 100)
                    revenue = sell_premium * 1000 * pos['shares']
                    entry_cost = pos.get('entry_premium', pos['entry_price']) * 1000 * pos['shares']
                    pnl = revenue - entry_cost
                    p_base = pos.get('entry_premium', 1)
                    pnl_pct_final = (sell_premium - p_base) / p_base if p_base > 0 else 0
                else:
                    revenue = sell_price * 1000 * pos['shares']
                    entry_cost = pos['entry_price'] * 1000 * pos['shares']
                    pnl = revenue - entry_cost
                    pnl_pct_final = (sell_price - pos['entry_price']) / pos['entry_price']
                
                self.capital += revenue
                
                self.trade_log.append({
                    'code': symbol,
                    'entry_date': pos['entry_date'],
                    'exit_date': current_date,
                    'entry_price': pos.get('entry_premium', pos['entry_price']) if trade_mode == 'CBAS' else pos['entry_price'],
                    'exit_price': sell_premium if trade_mode == 'CBAS' else sell_price,
                    'shares': pos['shares'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct_final,
                    'reason': reason
                })
            
            # --- 2. Evaluate buy candidates ---
            buy_candidates = []
            for _, row in df_cb.iterrows():
                symbol = str(row['代號']).replace(' ', '')
                if symbol in self.positions:
                    continue # Already holding
                    
                # 【新增】嚴格套用四大核心濾網 (如果沒過，連R/P都不算直接淘汰)
                f_price_min = self.config.get('filter_price_min', 80)
                f_price_max = self.config.get('filter_price_max', 200)
                f_prem_min = self.config.get('filter_prem_min', -20) * 0.01
                f_prem_max = self.config.get('filter_prem_max', 50) * 0.01
                f_ratio_min = self.config.get('filter_ratio_min', 0)
                f_parity_min = self.config.get('filter_parity_min', 50) * 0.01
                f_parity_max = self.config.get('filter_parity_max', 150) * 0.01
                
                cb_price = row.get('CB市價', 0)
                prem = row.get('溢/折價', 0)
                ratio = row.get('餘額', 0)
                parity = row.get('轉換價值', 0)
                
                if pd.isna(cb_price) or not (f_price_min <= cb_price <= f_price_max): continue
                if pd.isna(prem) or not (f_prem_min <= prem <= f_prem_max): continue
                if pd.isna(ratio) or ratio < f_ratio_min: continue
                if pd.isna(parity) or not (f_parity_min <= parity <= f_parity_max): continue
                    
                stock_code = symbol[:4]
                tech_data = historical_market_data.get(stock_code, {}).get(current_date, {})
                
                f_vol_min = self.config.get('filter_vol_min', 0)
                vol = tech_data.get('vol_avg_sheets', 0) if tech_data else 0
                if f_vol_min > 0 and (pd.isna(vol) or vol < f_vol_min):
                    continue
                
                r_score, p_score, label, is_golden, warnings, _ = analyzer_class.calculate_score(row, tech_data, row.get('上市天數', 365), self.config)
                
                entry_p = self.config.get('entry_p_score', 6)
                entry_r = self.config.get('entry_r_score', 6)
                
                if r_score <= entry_r and p_score >= entry_p: 
                    buy_candidates.append({
                        'symbol': symbol,
                        'price': row['CB市價'],
                        'r_score': r_score,
                        'p_score': p_score
                    })
            
            # Sort candidates by P score descending, R score ascending
            buy_candidates = sorted(buy_candidates, key=lambda x: (-x['p_score'], x['r_score']))
            
            # --- 3. Execute Buys ---
            # Max 5 positions
            MAX_POSITIONS = 5
            available_slots = MAX_POSITIONS - len(self.positions)
            buy_amount_per_trade = self.capital / max(1, available_slots)
            
            for bc in buy_candidates:
                if available_slots <= 0 or self.capital <= 0:
                    break
                
                if pd.isna(bc['price']) or bc['price'] <= 0: continue
                
                row_raw = df_cb[df_cb['代號'].astype(str).str.contains(bc['symbol'])].iloc[0]
                raw_rate = row_raw.get('百元報價', 0.05)
                if pd.isna(raw_rate) or type(raw_rate) == str and raw_rate.strip() in ['-', '']: raw_rate = 0.05
                elif type(raw_rate) == str and '%' in raw_rate: raw_rate = float(raw_rate.replace('%', '')) / 100.0
                cbas_fixed_rate = float(raw_rate)
                
                trade_mode = self.config.get('trade_mode', 'CBAS')
                if trade_mode == 'CBAS':
                    premium_per_100 = (cbas_fixed_rate * 100) + max(0, bc['price'] - 100)
                    cost_per_lot = premium_per_100 * 1000
                else:
                    cost_per_lot = bc['price'] * 1000
                    premium_per_100 = 0
                    
                max_lots = int(buy_amount_per_trade // cost_per_lot)
                
                # 若因均分資金導致單筆預算不足買 1 張，但帳上總資金夠買 1 張，則特例允許買 1 張
                if max_lots == 0 and self.capital >= cost_per_lot:
                    max_lots = 1
                    
                if max_lots > 0:
                    cost = max_lots * cost_per_lot
                    self.capital -= cost
                    self.positions[bc['symbol']] = {
                        'entry_date': current_date,
                        'entry_price': bc['price'],
                        'last_price': bc['price'],
                        'entry_fixed_rate': cbas_fixed_rate,
                        'last_fixed_rate': cbas_fixed_rate,
                        'entry_premium': premium_per_100,
                        'shares': max_lots
                    }
                    available_slots -= 1
            
            # --- 4. Record Equity ---
            total_equity = self.capital
            for sym, pos in self.positions.items():
                row_list = df_cb[df_cb['代號'] == sym]
                curr_price = row_list.iloc[0]['CB市價'] if not row_list.empty else pos['entry_price']
                
                trade_mode = self.config.get('trade_mode', 'CBAS')
                if trade_mode == 'CBAS':
                    raw_rate = row_list.iloc[0].get('百元報價', pos.get('last_fixed_rate', 0.05)) if not row_list.empty else pos.get('last_fixed_rate', 0.05)
                    if pd.isna(raw_rate) or type(raw_rate) == str and raw_rate.strip() in ['-', '']: raw_rate = 0.05
                    elif type(raw_rate) == str and '%' in raw_rate: raw_rate = float(raw_rate.replace('%', '')) / 100.0
                    curr_rate = float(raw_rate)
                    
                    curr_premium = (curr_rate * 100) + max(0, curr_price - 100)
                    total_equity += curr_premium * 1000 * pos['shares']
                else:
                    total_equity += curr_price * 1000 * pos['shares']
                
            self.equity_history.append({'Date': current_date, 'Equity': total_equity})
            
        # Compile final results
        eq_df = pd.DataFrame(self.equity_history)
        metrics = BacktestMetrics.calculate_metrics(eq_df, self.trade_log)
        
        return {
            'equity_curve': eq_df,
            'metrics': metrics,
            'trades': pd.DataFrame(self.trade_log)
        }
