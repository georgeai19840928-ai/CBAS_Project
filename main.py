import sys
import os
# 強制將目前目錄加入 Python 搜尋路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv

# 模組匯入
from config.settings import ConfigManager, STRATEGY_PRESETS
from core.analyzer import RPAnalyzer
from data.crawler import fetch_tpex_with_selenium
from data.market_data import get_technical_data, get_bulk_technical_data
from services.ai_agent import AIAgent
from services.notification import send_line_broadcast
from ui.system_guide import render_guide

# ==========================================
# 🚀 初始化與設定
# ==========================================
st.set_page_config(
    page_title="CBAS 鄭大戰情室 (V1.6)", 
    layout="wide", 
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

load_dotenv()
config = ConfigManager.load()

if 'ai_agent' not in st.session_state:
    st.session_state.ai_agent = AIAgent(os.getenv("GEMINI_API_KEY"))

st.title("💎 CBAS 鄭大戰情室 (V1.6 狀態優化版)")

# ==========================================
# 📊 優先顯示系統說明書
# ==========================================
render_guide(config)
st.divider()

# ==========================================
# ⚙️ 側邊欄設定
# ==========================================
st.sidebar.header("📂 資料來源")
uploaded = st.sidebar.file_uploader("上傳 Excel", type=['xlsx'])
path = uploaded 

# 強制重抓按鈕
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ 系統維護")
if st.sidebar.button("🔄 強制重跑爬蟲 (清除快取)", type="primary"):
    st.cache_data.clear()
    if 'tpex_data_cache' in st.session_state:
        del st.session_state['tpex_data_cache']
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🎯 策略快速套用 (Presets)")
col1, col2, col3 = st.sidebar.columns(3)
if col1.button("🛡️ 保守"):
    config.update(STRATEGY_PRESETS["保守 (Conservative)"])
    ConfigManager.save(config)
    st.rerun()
if col2.button("⚖️ 標準"):
    config.update(STRATEGY_PRESETS["標準 (Standard)"])
    ConfigManager.save(config)
    st.rerun()
if col3.button("🔥 激進"):
    config.update(STRATEGY_PRESETS["激進 (Aggressive)"])
    ConfigManager.save(config)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🔍 手動篩選濾網 (可儲存)")
price_range = st.sidebar.slider("1. CB 市價", 80, 200, 
                                (config.get('filter_price_min', 110), config.get('filter_price_max', 120)))
prem_range = st.sidebar.slider("2. 溢價率", -10, 50, 
                               (config.get('filter_prem_min', 5), config.get('filter_prem_max', 15)))
ratio_min = st.sidebar.slider("3. 未轉換餘額 > (%)", 0, 100, config.get('filter_ratio_min', 90))
parity_range = st.sidebar.slider("4. 股價靠近轉換價 (%)", 50, 150, 
                                 (config.get('filter_parity_min', 90), config.get('filter_parity_max', 110)))
min_vol_avg = st.sidebar.number_input("5. 五日均量 > (張)", value=config.get('filter_vol_min', 1000), step=100)

if st.sidebar.button("💾 儲存濾網設定"):
    config.update({
        'filter_price_min': price_range[0], 'filter_price_max': price_range[1],
        'filter_prem_min': prem_range[0], 'filter_prem_max': prem_range[1],
        'filter_ratio_min': ratio_min,
        'filter_parity_min': parity_range[0], 'filter_parity_max': parity_range[1],
        'filter_vol_min': min_vol_avg
    })
    ConfigManager.save(config)
    st.sidebar.success("已儲存！")

with st.sidebar.expander("⚙️ 專家評分參數", expanded=False):
    st.write("調整 R/P 評分門檻，設定自動儲存。")
    new_cfg = config.copy()
    
    st.caption("🛡️ Risk (R值) 參數")
    c1, c2 = st.columns(2)
    new_cfg['risk_price_safe'] = c1.number_input("R+1分 價格 <", value=config['risk_price_safe'])
    new_cfg['risk_price_mid'] = c2.number_input("R+3分 價格 <", value=config['risk_price_mid'])
    new_cfg['risk_price_high'] = st.number_input("R+9分 警戒價 >", value=config['risk_price_high'])
    
    c3, c4 = st.columns(2)
    new_cfg['risk_prem_safe'] = c3.number_input("安全溢價 <", value=config['risk_prem_safe'])
    new_cfg['risk_prem_high'] = c4.number_input("危險溢價 >", value=config['risk_prem_high'])

    st.caption("🚀 Potential (P值) 參數")
    new_cfg['pot_balance_high'] = st.number_input("籌碼安定 (餘額>%)", value=config['pot_balance_high'])
    
    c5, c6 = st.columns(2)
    new_cfg['pot_vol_zombie'] = c5.number_input("殭屍量扣分 (張<)", value=config['pot_vol_zombie'])
    new_cfg['pot_vol_active'] = c6.number_input("活絡量加分 (張>)", value=config['pot_vol_active'])
    
    c7, c8 = st.columns(2)
    new_cfg['pot_parity_min'] = c7.number_input("甜蜜點下限", value=config['pot_parity_min'])
    new_cfg['pot_parity_max'] = c8.number_input("甜蜜點上限", value=config['pot_parity_max'])
    
    if st.button("💾 儲存評分參數"):
        ConfigManager.save(new_cfg)
        config = new_cfg
        st.sidebar.success("參數已更新！")

# ==========================================
# 🔢 背景資料處理
# ==========================================
if 'tpex_data_cache' not in st.session_state:
    with st.spinner("🚀 系統啟動中：正在同步櫃買中心(TPEX)與市場數據..."):
        data = fetch_tpex_with_selenium()
        st.session_state.tpex_data_cache = data
        if not data:
            st.error("⚠️ 警告：櫃買中心爬蟲未抓到資料，上市日期將顯示為未知。請按側邊欄的「強制重跑」重試。")
        else:
            st.toast(f"✅ 成功更新 {len(data)} 筆上市日資料", icon="🎉")

tpex_data = st.session_state.tpex_data_cache

candidates = pd.DataFrame()

if not path:
    st.info("👋 請於左上方「資料來源」區塊，手動上傳 CBAS 報價表 Excel 檔案以開始分析。")
    st.stop()
else:
    try:
        df = pd.read_excel(path, header=6, engine='openpyxl')
        if '代號' in df.columns:
            df['代號'] = df['代號'].astype(str).str.replace(' ', '')
            df = df[df['代號'].notna()]
            df['股票代號'] = df['代號'].apply(lambda x: x[:4])
        
        for c in ['CB市價', '溢/折價', '餘額', '轉換價值', 'TCRI']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        for c in ['轉換價值', '溢/折價', '餘額']:
            if c in df.columns and df[c].median() < 10: df[c] *= 100
            
        today = datetime.now()
        
        def patch_days(row):
            if '上市天數' in row and row['上市天數'] > 0: return row['上市天數']
            c4 = str(row['代號'])[:4]
            if tpex_data and c4 in tpex_data: 
                return (today - pd.to_datetime(tpex_data[c4][0]['date'])).days
            return 0
        
        def get_listing_date_str(row):
            if '上市日' in row and pd.notna(row['上市日']): return row['上市日'].strftime('%Y-%m-%d')
            c4 = str(row['代號'])[:4]
            if tpex_data and c4 in tpex_data: return tpex_data[c4][0]['date']
            return "未知"
        
        # 嘗試讀取賣回日 (處理不同命名可能)
        if '賣回日' in df.columns:
            df['賣回日'] = pd.to_datetime(df['賣回日'], errors='coerce')
            df['距離賣回日(天)'] = (df['賣回日'] - today).dt.days
        else:
            df['距離賣回日(天)'] = 9999

        df['上市天數'] = df.apply(patch_days, axis=1)
        df['上市日_顯示'] = df.apply(get_listing_date_str, axis=1)

        mask = (df['CB市價'].between(price_range[0], price_range[1])) & \
               (df['溢/折價'].between(prem_range[0], prem_range[1])) & \
               (df['餘額'] >= ratio_min) & \
               (df['轉換價值'].between(parity_range[0], parity_range[1]))
        candidates_pre = df[mask].copy()

        final_results = []
        if not candidates_pre.empty:
            with st.spinner("📊 正在聯網批次抓取技術面、基本面數據..."):
                unique_codes = candidates_pre['股票代號'].unique().tolist()
                bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)
                
                progress_bar = st.progress(0)
                for i, (idx, row) in enumerate(candidates_pre.iterrows()):
                    progress_bar.progress((i + 1) / len(candidates_pre))
                    
                    tech = bulk_tech_data.get(row['股票代號'])
                    if tech and tech['vol_avg_sheets'] < min_vol_avg: continue
                    
                    r, p, lbl, gold = RPAnalyzer.calculate_score(row, tech, row['上市天數'], config)
                    
                    # 🔥 [V1.6] 更細緻的黃金期狀態顯示
                    listing_days = row['上市天數']
                    days_put = row.get('距離賣回日(天)', 9999)
                    
                    if config['pot_golden_min'] <= listing_days <= config['pot_golden_max']:
                        gp_status = "✨上市滿一年"
                    elif 0 < days_put < 365:
                        gp_status = "💰賣回前一年"
                    elif listing_days > 0 and listing_days < 100:
                        gp_status = "👶新債蜜月期"
                    elif listing_days > config['pot_golden_max']:
                        gp_status = "🐢上市逾一年"
                    else:
                        gp_status = "👀觀察期"

                    res = row.to_dict()
                    res.update({
                        'R值': r, 'P值': p, '策略標籤': lbl,
                        '黃金期': gp_status, 
                        '上市日期': row['上市日_顯示'],
                        '母股價': tech['price'] if tech else 0,
                        '均量': int(tech['vol_avg_sheets']) if tech else 0,
                        '60MA': round(tech['ma60'], 2) if tech else 0,
                        '87MA': round(tech['ma87'], 2) if tech else 0,
                        'MA狀態': '站上' if tech and tech['price'] > tech['ma87'] else '跌破',
                        'EPS': tech['fundamentals'].get('eps', 0) if tech else 0,
                        'PE': round(tech['fundamentals'].get('pe', 0), 1) if tech else 0
                    })
                    final_results.append(res)
                progress_bar.empty()
                
        candidates = pd.DataFrame(final_results)

    except Exception as e:
        st.error(f"資料處理錯誤: {e}")

# ==========================================
# 🔄 結果顯示 Tabs
# ==========================================
if candidates.empty:
    if os.path.exists(path) or uploaded:
        st.warning("⚠️ 篩選無結果，請嘗試放寬側邊欄的篩選條件。")
else:
    tab1, tab2 = st.tabs(["🏆 戰情總覽 (擴充版)", "🚀 單檔深度戰情"])

    with tab1:
        st.write(f"篩選出 **{len(candidates)}** 檔標的。")
        
        display_cols = [
            '代號', '名稱', '策略標籤', 'R值', 'P值', '黃金期',
            'CB市價', '溢/折價', '轉換價值', '餘額', 
            '母股價', '60MA', '87MA', '均量', 'EPS', 'PE', '上市日期'
        ]
        
        st.dataframe(
            candidates[display_cols],
            column_config={
                "R值": st.column_config.ProgressColumn("Risk", min_value=0, max_value=10, format="%d"),
                "P值": st.column_config.ProgressColumn("Potential", min_value=0, max_value=10, format="%d"),
                "溢/折價": st.column_config.NumberColumn(format="%.1f%%"),
                "轉換價值": st.column_config.NumberColumn(format="%.1f%%"),
                "餘額": st.column_config.NumberColumn(format="%.1f%%"),
                "均量": st.column_config.NumberColumn(format="%d 張"),
                "母股價": st.column_config.NumberColumn(format="%.2f"),
                "EPS": st.column_config.NumberColumn(format="%.2f"),
            },
            hide_index=True
        )
        
        elite = candidates[(candidates['R值'] <= 5) & (candidates['P值'] >= 5)]
        st.markdown(f"### 🤖 AI 批量掃描 (精選 {len(elite)} 檔)")
        
        if st.button("🚀 啟動 AI 批量簡評"):
            if elite.empty:
                st.warning("無符合 R≤5 & P≥5 的標的。")
            else:
                with st.spinner("🚀 AI 批量分析進行中 (預計 5-10 秒)..."):
                    # 組合所有標的資訊
                    targets_info = ""
                    for i, (idx, row) in enumerate(elite.iterrows()):
                        days_lbl = row['黃金期']
                        targets_info += f"[{i+1}] 標的: {row['名稱']}({row['代號']}) | Risk: {row['R值']} | Potential: {row['P值']} | 市價: {row['CB市價']} | 溢價: {row['溢/折價']:.1f}% | 狀態: {days_lbl}\n"
                    
                    prompt = f"""
                    # Role: 鄭大 CB 策略操盤手 (風格: 果斷、犀利)
                    
                    # Input Data (多檔標的):
                    {targets_info}
                    
                    # Rules:
                    1. **買進訊號**: 若 Risk<=5 且 溢價<20%，視為「優質買點」，請給出【強力佈局】或【分批買進】。
                    2. **理由**: 強調低溢價的優勢，禁止因溢價未達 20% 而觀望。
                    3. **風險**: 僅在 Risk>5 或 溢價>20% 時才建議【觀望】。
                    
                    # Output Format:
                    請為每一檔標的輸出大約 50 字的建議，格式如下：
                    ⭐ [名稱] (R[Risk值]/P[Potential值])
                    【指令】操作建議。(理由...)
                    """
                    
                    long_comment = st.session_state.ai_agent.ask(prompt)
                    clean_comment = long_comment.replace("**", "")
                    
                full_msg = "🏆 鄭大精選掃描報告 (深度指令版) 🏆\n\n" + clean_comment
                st.text_area("AI 報告預覽", full_msg, height=400)
                send_line_broadcast(os.getenv("LINE_ACCESS_TOKEN"), full_msg)
                st.success("深度指令報告已發送至 LINE！")

    with tab2:
        col1, col2 = st.columns([2,1])
        target_str = col1.selectbox("選擇標的", candidates['代號'] + " " + candidates['名稱'])
        manual_date = col2.date_input("校正上市日", value=None)
        
        if st.button("啟動全方位戰情分析"):
            row = candidates[candidates['代號'] == target_str.split()[0]].iloc[0]
            with st.spinner("正在聯網抓取產業與財報數據..."):
                tech_detail = get_technical_data(row['股票代號'], fetch_fundamentals=True)
            
            fund = tech_detail['fundamentals']
            ind = tech_detail['indicators']
            days = row['上市天數']
            if manual_date: days = (today.date() - manual_date).days
            
            prompt = f"""
# Role: 鄭大 CB 策略首席分析師
# Task: 綜合量化分數、基本面與技術面，給出深度投資建議。

# 1. 核心量化數據:
- 標的: {row['名稱']} ({row['代號']})
- R值(險): {row['R值']}, P值(潛): {row['P值']}
- 狀態: {row['黃金期']} (上市 {int(days)} 天)

# 2. 關鍵數據:
- 轉換價值: {row['轉換價值']:.2f}%, 溢價率: {row['溢/折價']:.2f}%
- 餘額: {row['餘額']:.2f}%

# 3. 基本面:
- 產業: {fund.get('sector')}
- EPS: {fund.get('eps', 0):.2f}, PE: {fund.get('pe', 0):.1f}

# 4. 技術面:
- 母股價: {row['母股價']:.2f} vs 87MA: {row['87MA']:.2f}
- RSI: {ind.get('rsi', 0):.1f}

# 5. 操作指引:
請給出明確買賣建議與理由。
"""
            with st.spinner("AI 撰寫中..."):
                reply = st.session_state.ai_agent.ask(prompt)
                st.markdown(reply)
                send_line_broadcast(os.getenv("LINE_ACCESS_TOKEN"), f"🔥 {row['名稱']} 全方位報告\n\n{reply}")