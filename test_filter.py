import pandas as pd
import requests
from io import BytesIO

url = 'https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB'
requests.packages.urllib3.disable_warnings()
res = requests.get(url, verify=False, timeout=15)
df = pd.read_excel(BytesIO(res.content))

col_map = {
    '可轉債市價': 'CB市價',
    '溢(折)價率': '溢/折價',
    '餘額比例': '餘額',
    '轉換價值': '轉換價值'
}
df = df.rename(columns=col_map)
for c in ['CB市價', '溢/折價', '餘額', '轉換價值']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

m1 = df['CB市價'].between(80, 200)
m2 = df['溢/折價'].between(-10, 50)
m3 = df['餘額'] >= 0
m4 = df['轉換價值'].between(50, 150)

print(f'Total: {len(df)}')
print(f'm1 (price 80-200): {m1.sum()}')
print(f'm2 (prem -10-50): {m2.sum()}')
print(f'm3 (bal >= 0): {m3.sum()}')
print(f'm4 (parity 50-150): {m4.sum()}')
all_mask = m1 & m2 & m3 & m4
print(f'All mask: {all_mask.sum()}')
