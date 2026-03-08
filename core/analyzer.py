import pandas as pd

class RPAnalyzer:
    @staticmethod
    def calculate_score(row, tech_data, listing_days, cfg):
        """
        計算 R/P 分數
        回傳: (r_score, p_score, label, is_golden_timing)
        """
        price = row['CB市價']
        premium = row['溢/折價']
        balance = row['餘額']
        parity = row['轉換價值']
        
        # --- 1. 計算 R 值 (Risk) ---
        r_score = 0
        # 價格評分
        if price < cfg['risk_price_safe']: r_score += 1
        elif price <= cfg['risk_price_mid']: r_score += 3
        elif price <= cfg['risk_price_high']: r_score += 6
        else: r_score += 9 # 懲罰分數
        
        # 溢價評分
        if premium < 0: r_score -= 1
        elif premium <= cfg['risk_prem_safe']: r_score += 0
        elif premium <= cfg['risk_prem_high']: r_score += 2 
        else: r_score += 5
        
        r_score = max(0, min(r_score, 10)) 

        # --- 2. 計算 P 值 (Potential) ---
        p_score = 2 
        is_golden_timing = False
        
        # A. 時機窗 (上市滿一年)
        if cfg['pot_golden_min'] <= listing_days <= cfg['pot_golden_max']: 
            p_score += 3
            is_golden_timing = True
        elif listing_days > 0 and listing_days < 180:
            p_score -= 2
        
        # B. 賣回日 (剩不到一年)
        days_to_put = row.get('距離賣回日(天)', 9999)
        if 0 < days_to_put < 365: 
            p_score += 3
            is_golden_timing = True

        # C. 籌碼面
        if balance >= cfg['pot_balance_high']: p_score += 2
        elif balance < cfg['pot_balance_low']: p_score -= 3

        # D. 位置面 (甜蜜點)
        if cfg['pot_parity_min'] <= parity <= cfg['pot_parity_max']:
            p_score += 3 
        elif parity < 80:
            p_score -= 1

        # E. 技術與成交量
        if tech_data:
            current_price = tech_data['price']
            ma87 = tech_data['ma87']
            vol_avg = tech_data['vol_avg_sheets']
            current_vol = tech_data['current_vol']

            # 站上 87MA
            if pd.notna(ma87) and current_price > ma87: p_score += 2
            
            # 成交量評分
            if vol_avg < cfg['pot_vol_zombie']: p_score -= 3
            elif vol_avg > cfg['pot_vol_active']: p_score += 1
            
            # 爆量
            if vol_avg > 0 and current_vol > (vol_avg * 2): p_score += 2

        p_score = max(0, min(p_score, 10))

        # --- 3. 策略定位 ---
        label = "中性觀察"
        if r_score <= 5 and p_score >= 5: label = "💎 鄭大精選"
        elif r_score <= 5: label = "🛡️ 低險保守"
        elif p_score >= 7: label = "🚀 強勢動能"
        else: label = "⚠️ 風險偏高"
            
        return r_score, p_score, label, is_golden_timing