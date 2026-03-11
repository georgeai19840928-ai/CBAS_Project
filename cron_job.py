import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# 強制將目前目錄加入 Python 搜尋路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import ConfigManager
from core.analyzer import RPAnalyzer
from data.market_data import get_bulk_technical_data
from services.ai_agent import AIAgent
from services.notification import send_line_broadcast

import requests
from io import BytesIO

def run_daily_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 開始執行 CBAS 全自動每日結算腳本...")
    
    # 1. 載入環境變數與設定
    load_dotenv()
    config = ConfigManager.load()
    ai_agent = AIAgent(os.getenv("GEMINI_API_KEY"))
    
    # 2. 自動擷取官方 API 發行明細表 (免 Excel)
    print(f"📊 正在從官方金庫同步最新可轉債即時報價...")
    url = 'https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        df_api = pd.read_excel(BytesIO(res.content))
        
        col_map = {
            '債券代號': '代號',
            '標的債券': '名稱',
            '可轉債市價': 'CB市價',
            '溢(折)價率': '溢/折價',
            '流通餘額(張數)': '餘額',
            '轉換價值': '轉換價值',
            'TCRI': 'TCRI',
            '最新賣回日': '賣回日',
            '發行日期': '上市日'
        }
        df = df_api.rename(columns=col_map)
        
        if '代號' in df.columns:
            df['代號'] = df['代號'].astype(str).str.replace(' ', '')
            df = df[df['代號'].notna() & (df['代號'] != 'nan') & (df['代號'] != '')]
            df['股票代號'] = df['代號'].apply(lambda x: x[:4])
        
        for c in ['CB市價', '溢/折價', '餘額', '轉換價值', 'TCRI']:
            if c in df.columns: 
                df[c] = pd.to_numeric(df[c], errors='coerce')
        
        for c in ['轉換價值', '溢/折價', '餘額']:
            if c in df.columns and df[c].median() < 10: 
                df[c] *= 100
        
        today = datetime.now()
        for c in ['賣回日', '上市日']:
            if c in df.columns: 
                df[c] = pd.to_datetime(df[c], errors='coerce')
                if c == '賣回日': 
                    df['距離賣回日(天)'] = (df[c] - today).dt.days
                if c == '上市日': 
                    df['上市天數'] = (today - df[c]).dt.days.apply(lambda x: max(0, int(x)) if pd.notna(x) else 0)
                    
        # 補上 default 名稱對應，因為 analyzer 預期有名稱欄位
        if '名稱' not in df.columns and '簡稱' in df.columns:
            df['名稱'] = df['簡稱']
            
    except Exception as e:
        print(f"❌ API 擷取失敗: {e}")
        return


    # 4. 初步篩選 (使用設定檔參數)
    print("🔍 進行條件篩選...")
    mask = (df['CB市價'].between(config.get('filter_price_min', 110), config.get('filter_price_max', 120))) & \
           (df['溢/折價'].between(config.get('filter_prem_min', 5), config.get('filter_prem_max', 15))) & \
           (df['餘額'] >= config.get('filter_ratio_min', 90)) & \
           (df['轉換價值'].between(config.get('filter_parity_min', 90), config.get('filter_parity_max', 110)))
    candidates_pre = df[mask].copy()

    if candidates_pre.empty:
        print("ℹ️ 根據當前濾網設定，無符合篩選條件之標的。")
        return
        
    print(f"🎯 初篩出 {len(candidates_pre)} 檔標的，開始聯網抓取行情並計算RP...")
    
    # 5. 聯網批次抓取與 RP 評分
    unique_codes = candidates_pre['股票代號'].unique().tolist()
    bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)
    
    final_results = []
    for _, row in candidates_pre.iterrows():
        tech = bulk_tech_data.get(row['股票代號'])
        if tech and tech['vol_avg_sheets'] < config.get('filter_vol_min', 1000): continue
        
        r, p, lbl, gold = RPAnalyzer.calculate_score(row, tech, row['上市天數'], config)
        
        res = row.to_dict()
        res.update({
            'R值': r, 'P值': p, '策略標籤': lbl,
            'EPS': tech['fundamentals'].get('eps', 0) if tech else 0,
            'PE': round(tech['fundamentals'].get('pe', 0), 1) if tech else 0
        })
        final_results.append(res)
        
    candidates = pd.DataFrame(final_results)
    if candidates.empty:
        print("ℹ️ RP 分析後，無標的符合要求(如均量不足)。")
        return
        
    # 6. 選出菁英名單 (R低P高) 給 AI 分析
    elite = candidates[(candidates['R值'] <= 5) & (candidates['P值'] >= 5)]
    if elite.empty:
        print("ℹ️ 雖有篩選標的，但無符合 AI 戰情室條件(R<=5, P>=5)之菁英目標。")
        return
        
    print(f"🤖 發現 {len(elite)} 檔菁英標的，啟動 AI 批量掃描...")
    summary_report = ai_agent.analyze_batch_summary(elite)
    
    # 7. 組織訊息並推播至 LINE
    report_title = f"📢 CBAS 戰情室每日結算 ({today.strftime('%m/%d')})"
    print(f"📱 準備推播至 LINE...")
    
    line_token = os.getenv("LINE_ACCESS_TOKEN")
    send_line_broadcast(line_token, f"{report_title}\n\n{summary_report}")
    print("✅ 每日結算腳本執行完畢！")

if __name__ == "__main__":
    run_daily_job()
