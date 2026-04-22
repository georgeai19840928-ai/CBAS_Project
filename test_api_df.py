import pandas as pd
import requests
from io import BytesIO

url = 'https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB'
requests.packages.urllib3.disable_warnings()
res = requests.get(url, verify=False, timeout=15)
df = pd.read_excel(BytesIO(res.content))

col_map = {
    '債券代號': '代號',
    '標的債券': '名稱',
    '可轉債市價': 'CB市價',
    '溢(折)價率': '溢/折價',
    '流通餘額(張數)': '餘額_raw',
    '轉換價值': '轉換價值',
    'TCRI': 'TCRI',
    '最新賣回日': '賣回日',
    '發行日期': '上市日'
}
df = df.rename(columns=col_map)
print("Columns:", df.columns.tolist())

# Check how many have missing CB市價 or 溢/折價
print("\n--- Missing Value Report ---")
for c in ['名稱', 'CB市價', '溢/折價', '餘額_raw', '轉換價值', '上市日']:
    if c in df.columns:
        print(f"{c}: {df[c].isna().sum()} nulls out of {len(df)}")
    else:
        print(f"{c}: Column NOT FOUND")

# Check values for 11011
if '代號' in df.columns:
    df['代號'] = df['代號'].astype(str).str.strip()
    target = df[df['代號'] == '11011']
    print("\n--- 11011 (台泥一) Data ---")
    if not target.empty:
        for c in ['名稱', 'CB市價', '溢/折價', '餘額_raw', '轉換價值', '上市日']:
            if c in target.columns:
                print(f"{c}: {target.iloc[0][c]}")
    else:
        print("11011 not found!")
