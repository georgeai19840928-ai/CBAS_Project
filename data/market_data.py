import yfinance as yf
import ta
import pandas as pd
import streamlit as st
import concurrent.futures
import time
import random

def _fetch_single(stock_code, fetch_fundamentals=False, retries=3):
    suffixes = ['.TW', '.TWO']
    for suffix in suffixes:
        for attempt in range(retries):
            try:
                ticker = f"{stock_code}{suffix}"
                stock = yf.Ticker(ticker)
                df = stock.history(period="2y")
                
                if df.empty:
                    if attempt < retries - 1:
                        time.sleep(random.uniform(1.0, 3.0)) # Bypassing Yahoo rate limit
                        continue
                    continue 
                
                curr_p = float(df['Close'].iloc[-1])
                curr_v = float(df['Volume'].iloc[-1]) / 1000.0
                df['60MA'] = df['Close'].rolling(60).mean()
                df['87MA'] = df['Close'].rolling(87).mean()
                df['284MA'] = df['Close'].rolling(284).mean()
                h10 = float(df['Close'].rolling(10).max().iloc[-1])
                
                v_avg_raw = df['Volume'].rolling(5).mean().iloc[-1]
                v_avg = float(v_avg_raw) / 1000.0 if pd.notna(v_avg_raw) and v_avg_raw > 0 else 0.0

                data = {
                    "ticker": ticker, 
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
                    info = stock.info
                    data['fundamentals'] = {
                        'sector': info.get('sector', '未知'), 'industry': info.get('industry', '未知'),
                        'pe': info.get('trailingPE', 0), 'eps': info.get('trailingEps', 0),
                        'roe': info.get('returnOnEquity', 0), 'rev_growth': info.get('revenueGrowth', 0)
                    }
                    rsi = ta.momentum.RSIIndicator(close=df['Close'], window=14)
                    data['indicators']['rsi'] = float(rsi.rsi().iloc[-1]) if pd.notna(rsi.rsi().iloc[-1]) else None
                    macd = ta.trend.MACD(close=df['Close'])
                    data['indicators']['macd_hist'] = float(macd.macd_diff().iloc[-1]) if pd.notna(macd.macd_diff().iloc[-1]) else None

                return data
            except Exception as e:
                print(f"Fetch Error [{ticker}]: {e}")
                import traceback
                traceback.print_exc()
                if attempt < retries - 1:
                    time.sleep(random.uniform(1.0, 2.0))
                    continue
                break # Move to next suffix
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