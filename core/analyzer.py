import pandas as pd

class RPAnalyzer:
    @staticmethod
    def calculate_score(row, tech_data, listing_days, cfg):
        """
        計算 R/P 分數 (優化版)
        回傳: (r_score, p_score, label, is_golden_timing, warning_flags)
        """
        price = row['CB市價']
        premium = row['溢/折價']
        balance = row['餘額']
        parity = row['轉換價值']
        
        warning_flags = []
        
        # --- 1. 計算 R 值 (Risk) ---
        r_score = 0
        
        # 價格評分 (0-10)
        if price < cfg['risk_price_safe']: 
            r_score += 1
        elif price <= cfg['risk_price_mid']: 
            r_score += 3
        elif price <= cfg['risk_price_high']: 
            r_score += 6
        else: 
            r_score += 10  # 懲罰分數拉高
        
        # 溢價評分 (0-8) - 修正邏輯
        if premium < 0:  # 折價 = 佔便宜
            r_score -= 2
        elif premium <= cfg['risk_prem_safe']: 
            r_score += 0
        elif premium <= cfg['risk_prem_mid']: 
            r_score += 3
        elif premium <= cfg['risk_prem_high']: 
            r_score += 5
        else: 
            r_score += 8  # 溢價過高
        
        r_score = max(0, min(r_score, 18))  # 提高上限

        # --- 2. 計算 P 值 (Potential) ---
        p_score = 2 
        is_golden_timing = False
        
        # A. 時機窗 (上市滿一年 = ~365天)
        if cfg['pot_golden_min'] <= listing_days <= cfg['pot_golden_max']: 
            p_score += 2  # 從 +3 調降至 +2
            is_golden_timing = True
        elif listing_days > 0 and listing_days < 180:
            p_score -= 2
            warning_flags.append("新股觀察期")
        
        # B. 賣回日 (剩不到一年)
        days_to_put = row.get('距離賣回日(天)', 9999)
        if 0 < days_to_put < 365: 
            p_score += 2
            is_golden_timing = True

        # C. 籌碼面 (餘額)
        if balance >= cfg['pot_balance_high']: 
            p_score += 2
        elif balance < cfg['pot_balance_low']: 
            p_score -= 2  # 從 -3 調升至 -2
            warning_flags.append("餘額過低")

        # D. 位置面 (甜蜜點)
        if cfg['pot_parity_min'] <= parity <= cfg['pot_parity_max']:
            p_score += 2  # 從 +3 調降至 +2
        elif parity < 80:
            p_score -= 1
            warning_flags.append("轉換價值過低")

        # E. 技術與成交量
        if tech_data:
            current_price = tech_data['price']
            ma87 = tech_data.get('ma87')
            ma20 = tech_data.get('ma20')
            vol_avg = tech_data.get('vol_avg_sheets')
            current_vol = tech_data.get('current_vol')
            volatility = tech_data.get('volatility')

            # 站上 87MA (權重提高)
            if pd.notna(ma87) and current_price > ma87: 
                p_score += 3  # 從 +2 提高至 +3
            
            # 站上 20MA (新增)
            if pd.notna(ma20) and current_price > ma20: 
                p_score += 1
            
            # 均線多頭排列 (新增)
            if pd.notna(ma20) and pd.notna(ma87) and ma20 > ma87:
                p_score += 2
                warning_flags.append("多頭排列")

            # 成交量評分
            if vol_avg and vol_avg < cfg['pot_vol_zombie']: 
                p_score -= 2
                warning_flags.append("殭屍量")
            elif vol_avg and vol_avg > cfg['pot_vol_active']: 
                p_score += 1
            
            # 爆量 (成交量 > 2倍均量)
            if vol_avg and vol_avg > 0 and current_vol and current_vol > (vol_avg * 2): 
                p_score += 2

            # 波動率因子 (新增)
            if volatility:
                if volatility >= cfg.get('pot_volatility_high', 30):
                    p_score += 2
                elif volatility >= cfg.get('pot_volatility_mid', 15):
                    p_score += 1

        p_score = max(0, min(p_score, 15))  # 提高上限

        # --- 3. 禁買名單機制 ---
        death_line = cfg.get('death_line_price', 140)
        days_below_death = row.get('days_below_death_line', 0)
        
        if price > death_line and days_below_death > 5:
            r_score = 20  # 直接拉滿
            warning_flags.append("☠️ 禁買")

        # --- 4. 策略定位 ---
        label = "中性觀察"
        
        if r_score >= 15:
            label = "☠️ 風險過高"
        elif r_score <= 6 and p_score >= 6: 
            label = "💎 鄭大精選"
        elif r_score <= 6: 
            label = "🛡️ 低險保守"
        elif p_score >= 8: 
            label = "🚀 強勢動能"
        elif r_score <= 10 and p_score >= 4:
            label = "⚔️ 積極布局"
        else: 
            label = "⚠️ 風險偏高"
            
        return r_score, p_score, label, is_golden_timing, warning_flags
