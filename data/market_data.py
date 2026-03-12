import requests
import ta
import pandas as pd
import streamlit as st
import concurrent.futures
import time
import random
from datetime import datetime, timedelta

def _fetch_single(stock_code, fetch_fundamentals=False, retries=3):
    """
    從 FinMind API 抓取台股資料，替代被 Yahoo Finance 封鎖的 yfinance。
    """
    for attempt in range(retries):
        try:
            # 1. 抓取股價歷史 (為了計算均線與技術指摽)
            # 抓取過去 180 天的資料應足以計算 60, 87 MA
            start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
            price_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={stock_code}&start_date={start_date}"
            
            res = requests.get(price_url, timeout=10)
            price_json = res.json()
            
            if price_json.get('msg') != 'success' or not price_json.get('data'):
                if attempt < retries -1:
                    time.sleep(1)
                    continue
                return None
            
            df = pd.DataFrame(price_json['data'])
            # FinMind 欄位: date, stock_id, Trading_Volume, Trading_money, open, max, min, close, spread, Trading_turnover
            # 轉換為 float 確保計算正確
            for col in ['close', 'open', 'max', 'min', 'Trading_Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if len(df) < 2: return None
            
            curr_p = float(df['close'].iloc[-1])
            curr_v = float(df['Trading_Volume'].iloc[-1]) / 1000.0 # 單位換算為張 (FinMind 原始單位是股)
            
            df['60MA'] = df['close'].rolling(60).mean()
            df['87MA'] = df['close'].rolling(87).mean()
            df['284MA'] = df['close'].rolling(284).mean()
            h10 = float(df['close'].rolling(10).max().iloc[-1])
            
            v_avg_raw = df['Trading_Volume'].rolling(5).mean().iloc[-1]
            v_avg = float(v_avg_raw) / 1000.0 if pd.notna(v_avg_raw) and v_avg_raw > 0 else 0.0

            data = {
                "ticker": f"{stock_code}.TW", 
                "price": curr_p, 
                "ma60": float(df['60MA'].iloc[-1]) if pd.notna(df['60MA'].iloc[-1]) else None,
                "ma87": float(df['87MA'].iloc[-1]) if pd.notna(df['87MA'].iloc[-1]) else None,
                "ma284": float(df['284MA'].iloc[-1]) if pd.notna(df['284MA'].iloc[-1]) else None,
                "is_10d_high": curr_p >= h10, 
                "vol_avg_sheets": v_avg, 
                "current_vol": curr_v,
                "fundamentals": {}, 
                "indicators": {}
            }

            if fetch_fundamentals:
                # 2. 抓取基本面 (PE, PBR, Yield) - TaiwanStockPER
                per_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPER&data_id={stock_code}&start_date={start_date}"
                res_per = requests.get(per_url, timeout=10)
                per_json = res_per.json()
                
                pe = 0
                if per_json.get('msg') == 'success' and per_json.get('data'):
                    pe = float(per_json['data'][-1].get('PER', 0))

                data['fundamentals'] = {
                    'sector': '台股', # FinMind 需另外爬產業，暫時設為台股
                    'industry': '台股',
                    'pe': pe,
                    'eps': 0, # FinMind EPS 需從 FinancialStatements 抓，稍後優化
                    'roe': 0,
                    'rev_growth': 0
                }
                
                # 計算 RSI 與 MACD
                rsi = ta.momentum.RSIIndicator(close=df['close'], window=14)
                data['indicators']['rsi'] = float(rsi.rsi().iloc[-1]) if pd.notna(rsi.rsi().iloc[-1]) else None
                macd = ta.trend.MACD(close=df['close'])
                data['indicators']['macd_hist'] = float(macd.macd_diff().iloc[-1]) if pd.notna(macd.macd_diff().iloc[-1]) else None

            return data
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
    return None
    return None

@st.cache_data(ttl=3600)
def get_bulk_technical_data(stock_codes, fetch_fundamentals=False):
    results = {}
    # 降低線程數量，避免被 Yahoo Finance 的防機器人機制 (Rate Limit) 封鎖
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_code = {
            executor.submit(_fetch_single, code, fetch_fundamentals): code 
            for code in set(stock_codes)
        }
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                data = future.result()
                results[code] = data
            except Exception:
                results[code] = None
    return results

@st.cache_data(ttl=3600)
def get_technical_data(stock_code, fetch_fundamentals=False):
    return _fetch_single(stock_code, fetch_fundamentals)