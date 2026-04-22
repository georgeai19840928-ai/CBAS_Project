import requests
import pandas as pd
from datetime import datetime, timedelta

def test_finmind(stock_id):
    print(f"Testing {stock_id}...")
    
    # 1. Price Data
    start_date = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d')
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={stock_id}&start_date={start_date}"
    res = requests.get(url)
    data = res.json()
    if data.get('msg') == 'success' and len(data.get('data', [])) > 0:
        df = pd.DataFrame(data['data'])
        print("Price Columns:", df.columns.tolist())
        print("Latest Price:", df.iloc[-1]['close'], "Volume:", df.iloc[-1]['Trading_Volume'])
    else:
        print("Price API failed:", data)

    # 2. PE, PB, Yield
    url2 = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPER&data_id={stock_id}&start_date={start_date}"
    res2 = requests.get(url2)
    data2 = res2.json()
    if data2.get('msg') == 'success' and len(data2.get('data', [])) > 0:
        df2 = pd.DataFrame(data2['data'])
        print("PER Columns:", df2.columns.tolist())
        latest_per = df2.iloc[-1].get('PER', 'N/A')
        latest_pbr = df2.iloc[-1].get('PBR', 'N/A')
        print(f"Latest PER: {latest_per}, PBR: {latest_pbr}")
    else:
        print("PER API failed:", data2)

test_finmind('1101')
test_finmind('6207')  # OTC
