import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# 強制將目前目錄加入 Python 搜尋路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import ConfigManager
from core.analyzer import RPAnalyzer
from data.crawler import fetch_tpex_with_selenium
from data.market_data import get_bulk_technical_data
from services.ai_agent import AIAgent
from services.notification import send_line_broadcast

def run_daily_job(excel_path):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 開始執行 CBAS 每日自動結算腳本...")
    
    # 1. 載入環境變數與設定
    load_dotenv()
    config = ConfigManager.load()
    ai_agent = AIAgent(os.getenv("GEMINI_API_KEY"))
    
    # 2. 爬取 TPEX 上市資料
    print("⏳ 正在抓取櫃買中心(TPEX)上市資料...")
    tpex_data = fetch_tpex_with_selenium()
    if not tpex_data:
        print("⚠️ 警告：TPEX 爬蟲未能取得資料。")
        
    # 3. 讀取 Excel 報價表
    print(f"📊 正在讀取報價表: {excel_path}...")
    try:
        df = pd.read_excel(excel_path, header=6, engine='openpyxl')
    except Exception as e:
        print(f"❌ 讀取 Excel 失敗: {e}")
        return

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
    
    # 嘗試讀取賣回日
    if '賣回日' in df.columns:
        df['賣回日'] = pd.to_datetime(df['賣回日'], errors='coerce')
        df['距離賣回日(天)'] = (df['賣回日'] - today).dt.days
    else:
        df['距離賣回日(天)'] = 9999

    df['上市天數'] = df.apply(patch_days, axis=1)

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
    if len(sys.argv) < 2:
        print("用法: python cron_job.py <報價表Excel路徑>")
        # 提供測試備份路徑 (若不輸入參數則嘗試抓取同一目錄下的 demo)
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CBAS_0310.xlsx")
        if os.path.exists(default_path):
            print(f"未指定檔案，預設使用: {default_path}")
            run_daily_job(default_path)
        else:
            sys.exit(1)
    else:
        run_daily_job(sys.argv[1])
