import yfinance as yf
import ta
import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600)
def get_technical_data(stock_code, fetch_fundamentals=False):
    suffixes = ['.TW', '.TWO']
    for suffix in suffixes:
        try:
            ticker = f"{stock_code}{suffix}"
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y")
            if df.empty: continue 
            
            curr_p = df['Close'].iloc[-1]
            curr_v = df['Volume'].iloc[-1] / 1000
            df['60MA'] = df['Close'].rolling(60).mean()
            df['87MA'] = df['Close'].rolling(87).mean()
            df['284MA'] = df['Close'].rolling(284).mean()
            h10 = df['Close'].rolling(10).max().iloc[-1]
            v_avg = df['Volume'].rolling(5).mean().iloc[-1] / 1000 if df['Volume'].rolling(5).mean().iloc[-1] > 0 else 0

            data = {
                "ticker": ticker, "price": curr_p, "ma60": df['60MA'].iloc[-1],
                "ma87": df['87MA'].iloc[-1], "ma284": df['284MA'].iloc[-1],
                "is_10d_high": curr_p >= h10, "vol_avg_sheets": v_avg, "current_vol": curr_v,
                "fundamentals": {}, "indicators": {}
            }

            if fetch_fundamentals:
                info = stock.info
                data['fundamentals'] = {
                    'sector': info.get('sector', '未知'), 'industry': info.get('industry', '未知'),
                    'pe': info.get('trailingPE', 0), 'eps': info.get('trailingEps', 0),
                    'roe': info.get('returnOnEquity', 0), 'rev_growth': info.get('revenueGrowth', 0)
                }
                rsi = ta.momentum.RSIIndicator(close=df['Close'], window=14)
                data['indicators']['rsi'] = rsi.rsi().iloc[-1]
                macd = ta.trend.MACD(close=df['Close'])
                data['indicators']['macd_hist'] = macd.macd_diff().iloc[-1]

            return data
        except: continue
    return None