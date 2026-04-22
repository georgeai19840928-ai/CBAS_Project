import itertools
import pandas as pd
from core.backtester import CBASBacktester
from core.analyzer import RPAnalyzer
import copy

class StrategyOptimizer:
    def __init__(self, base_config, snapshots, hist_data, initial_capital=1000000):
        self.base_config = base_config
        self.snapshots = snapshots
        self.hist_data = hist_data
        self.initial_capital = initial_capital
        
    def optimize(self, param_grid):
        """
        param_grid: dict where keys are config keys and values are lists of options to test
        Example: {'pot_parity_min': [85, 90, 95], 'risk_price_safe': [110, 120]}
        """
        keys, values = zip(*param_grid.items())
        permutations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        results = []
        
        total_runs = len(permutations)
        print(f"Starting optimization over {total_runs} combinations...")
        
        for i, perm in enumerate(permutations):
            test_config = copy.deepcopy(self.base_config)
            test_config.update(perm)
            
            engine = CBASBacktester(initial_capital=self.initial_capital, config=test_config)
            try:
                bt_result = engine.run(self.snapshots, self.hist_data, RPAnalyzer)
                metrics = bt_result['metrics']
                
                res = copy.deepcopy(perm)
                res['Total Return'] = metrics.get('Total Return', 0)
                res['Sharpe Ratio'] = metrics.get('Sharpe Ratio', 0)
                res['Sortino Ratio'] = metrics.get('Sortino Ratio', 0)
                res['Max Drawdown'] = metrics.get('Max Drawdown', 0)
                res['Win Rate'] = metrics.get('Win Rate', 0)
                res['Profit Factor'] = metrics.get('Profit Factor', 0)
                res['Total Trades'] = metrics.get('Total Trades', 0)
                
                results.append(res)
            except Exception as e:
                print(f"Error evaluating config {perm}: {e}")
                
        # Convert to DataFrame and sort by a default composite score (e.g. Sharpe)
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values(by='Sharpe Ratio', ascending=False)
            
        return df_results
