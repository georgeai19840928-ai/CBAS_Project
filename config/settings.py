import json
import os

CONFIG_FILE = "strategy_config.json"

DEFAULT_CONFIG = {
    # --- R 值 (Risk) 參數 ---
    "risk_price_safe": 110,    # 極低險 (<110)
    "risk_price_mid": 120,     # 舒適區 (<120)
    "risk_price_high": 130,    # 警戒區 (超過此處+9分)
    "risk_prem_safe": 10,      # 安全溢價 (<10%)
    "risk_prem_mid": 15,       # 中等溢價 (<15%)
    "risk_prem_high": 20,      # 危險溢價 (>20%)
    
    # --- P 值 (Potential) 參數 ---
    "pot_balance_high": 90,    # 籌碼安定 (>90%)
    "pot_balance_low": 30,     # 殘券風險 (<30%)
    "pot_parity_min": 90,      # 甜蜜點下限
    "pot_parity_max": 110,     # 甜蜜點上限
    "pot_vol_zombie": 500,     # 殭屍量扣分 (<500)
    "pot_vol_active": 2000,    # 活絡量加分 (>2000)
    "pot_golden_min": 330,     # 黃金期下限 (天)
    "pot_golden_max": 450,     # 黃金期上限 (天)

    # --- 濾網預設值 (Filter) ---
    "filter_price_min": 110,
    "filter_price_max": 120,
    "filter_prem_min": 5,
    "filter_prem_max": 15,
    "filter_ratio_min": 90,
    "filter_parity_min": 90,
    "filter_parity_max": 110,
    "filter_vol_min": 1000
}

class ConfigManager:
    @staticmethod
    def load():
        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    cfg.update(loaded)
            except: pass
        return cfg

    @staticmethod
    def save(new_config):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)