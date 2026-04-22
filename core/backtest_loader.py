import pandas as pd
import glob
import os
import time
import requests
import datetime
import concurrent.futures

class BacktestLoader:
    def __init__(self, data_dir='d:\\私人\\CBAS_Project\\data\\historical_data'):
        self.data_dir = data_dir
        
    def load_snapshots(self):
        """讀取資料夾中所有的 CBAS報價表 Excel，並轉換為 snapshot 格式"""
        files = glob.glob(os.path.join(self.data_dir, '*報價表*.xlsx'))
        # 排除暫存檔
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        snapshots = []
        for f in files:
            try:
                # 讀取沒有 Header 的 Excel 找出日期和實際欄位
                df_raw = pd.read_excel(f, header=None)
                
                # 從 row 5 (index 4) 或相似位置找出日期
                # 假設 '日期：' 在 (index 4, col 1) 或 (index 5, col 1)
                date_val = None
                for i in range(10):
                    row_str = str(df_raw.iloc[i].values).replace('nan','').replace('None','')
                    if '日期' in row_str:
                        # 找尋時間格式
                        import re
                        match = re.search(r'20\d{2}-\d{2}-\d{2}', row_str)
                        if match:
                            date_val = match.group(0)
                        break
                
                if not date_val:
                    # 如果找不到日期，嘗試從檔名提取
                    match = re.search(r'20\d{6}', os.path.basename(f))
                    if match:
                        d_str = match.group(0)
                        date_val = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                    else:
                        print(f"Warning: Cannot find date for {f}")
                        continue
                        
                # 重新讀取，找到正確的 header (通常在第5或第6行, index 5或6)
                # 根據先前的觀察，'名稱' 在 row index 6 (第7行)
                header_idx = None
                for i in range(10):
                    if '代號' in df_raw.iloc[i].values or '名稱' in df_raw.iloc[i].values:
                        header_idx = i
                        break
                        
                if header_idx is None:
                    continue
                    
                df = pd.read_excel(f, header=header_idx)
                
                # 刪除沒用的行與防呆
                df['代號'] = df['代號'].astype(str).str.replace(' ', '')
                df = df[df['代號'].notna() & (df['代號'] != 'nan') & (df['代號'] != '')]
                
                # 計算與 API 相同的衍生欄位
                df['股票代號'] = df['代號'].apply(lambda x: x[:4] if len(x) >= 4 else '')
                
                for c in ['CB市價', '溢/折價', '餘額', '轉換價值', 'TCRI']:
                    if c in df.columns: 
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                        
                # 防呆: 如果餘額小於 10，代表可能是小數比例，需要乘 100
                if '餘額' in df.columns and df['餘額'].median() < 10 and df['餘額'].median() > 0:
                    df['餘額'] *= 100
                    
                for c in ['賣回日', '上市日']:
                    if c in df.columns: 
                        df[c] = pd.to_datetime(df[c], errors='coerce')
                        snap_date = pd.to_datetime(date_val)
                        if c == '賣回日': 
                            df['距離賣回日(天)'] = (df[c] - snap_date).dt.days
                        if c == '上市日': 
                            df['上市天數'] = (snap_date - df[c]).dt.days.apply(lambda x: max(0, int(x)) if pd.notna(x) else 0)
                
                snapshots.append({
                    'date': date_val,
                    'df': df
                })
                print(f"Loaded {f} for date {date_val} with {len(df)} CBs.")
            except Exception as e:
                print(f"Error loading {f}: {e}")
                
        # 依照日期排序
        snapshots = sorted(snapshots, key=lambda x: x['date'])
        return snapshots
        
    def fetch_historical_market_data(self, snapshots):
        """抓取回測期間所有相關母股的歷史日 K 線並計算 MA 與均量"""
        if not snapshots: return {}
        
        all_stock_codes = set()
        for snap in snapshots:
            all_stock_codes.update(snap['df']['股票代號'].dropna().unique().tolist())
            
        all_stock_codes = [c for c in all_stock_codes if c.isdigit()]
        
        min_date = snapshots[0]['date']
        max_date = snapshots[-1]['date']
        
        # 為了算 87MA，提前抓 150 天前
        start_date = (pd.to_datetime(min_date) - pd.Timedelta(days=150)).strftime('%Y-%m-%d')
        end_date = (pd.to_datetime(max_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"Fetching historic tech data for {len(all_stock_codes)} stocks from {start_date} to {end_date}...")
        kline_dir = os.path.join(self.data_dir, 'k_lines_cache')
        os.makedirs(kline_dir, exist_ok=True)
        
        historical_data = {}
        
        def _fetch(stock_code):
            file_path = os.path.join(kline_dir, f"{stock_code}.csv")
            df = None
            need_fetch = True
            
            # --- 1. 嘗試讀取本地快取 ---
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path, index_col='date', parse_dates=True)
                    if not df.empty:
                        first_local = df.index.min().strftime('%Y-%m-%d')
                        last_local = df.index.max().strftime('%Y-%m-%d')
                        # 如果本地快取完全涵蓋我們需要的時間區間，就不抓取
                        if first_local <= start_date and last_local >= max_date:
                            need_fetch = False
                except Exception as e:
                    print(f"Cache read error for {stock_code}: {e}")
                    need_fetch = True
                    
            # --- 2. 缺少資料，從 FinMind 抓取並儲存快取 ---
            if need_fetch:
                url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={stock_code}&start_date={start_date}&end_date={end_date}"
                try:
                    res = requests.get(url, timeout=10)
                    json_data = res.json()
                    if json_data.get('msg') == 'success' and json_data.get('data'):
                        df_new = pd.DataFrame(json_data['data'])
                        if not df_new.empty:
                            df_new['close'] = pd.to_numeric(df_new['close'], errors='coerce')
                            df_new['Trading_Volume'] = pd.to_numeric(df_new['Trading_Volume'], errors='coerce')
                            df_new['date'] = pd.to_datetime(df_new['date'])
                            df_new = df_new.set_index('date')
                            
                            # 儲存快取 (只留需要的欄位，節省空間)
                            df_new[['close', 'Trading_Volume']].to_csv(file_path)
                            df = df_new
                except Exception as e:
                    print(f"FinMind fetch error for {stock_code}: {e}")
                    
            # --- 3. 計算技術指標 ---
            if df is not None and not df.empty:
                df = df.sort_index()
                df_calc = df.copy()
                df_calc['87MA'] = df_calc['close'].rolling(87).mean()
                df_calc['60MA'] = df_calc['close'].rolling(60).mean()
                df_calc['20MA'] = df_calc['close'].rolling(20).mean()
                df_calc['vol_avg'] = df_calc['Trading_Volume'].rolling(5).mean() / 1000.0 # 換算張數
                
                df_calc.index = df_calc.index.strftime('%Y-%m-%d')
                
                stock_history = {}
                for snap_date in [s['date'] for s in snapshots]:
                    past_data = df_calc[df_calc.index <= snap_date]
                    if not past_data.empty:
                        latest = past_data.iloc[-1]
                        stock_history[snap_date] = {
                            'price': float(latest['close']),
                            'ma87': float(latest['87MA']) if pd.notna(latest['87MA']) else None,
                            'ma60': float(latest['60MA']) if pd.notna(latest['60MA']) else None,
                            'ma20': float(latest['20MA']) if pd.notna(latest['20MA']) else None,
                            'vol_avg_sheets': float(latest['vol_avg']) if pd.notna(latest['vol_avg']) else 0,
                            'current_vol': float(latest['Trading_Volume']) / 1000.0 if pd.notna(latest['Trading_Volume']) else 0
                        }
                return stock_code, stock_history
            return stock_code, {}

        # 使用多執行緒抓取
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_code = {executor.submit(_fetch, code): code for code in all_stock_codes}
            for future in concurrent.futures.as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    data = future.result()[1]
                    historical_data[code] = data
                except Exception as e:
                    print(f"Error fetching {code}: {e}")
                    
        return historical_data
