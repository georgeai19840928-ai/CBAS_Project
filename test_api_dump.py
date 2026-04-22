import pandas as pd
import requests
from io import BytesIO

url = 'https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB'
requests.packages.urllib3.disable_warnings()
res = requests.get(url, verify=False, timeout=15)
df = pd.read_excel(BytesIO(res.content))

with open('api_cols.txt', 'w', encoding='utf-8') as f:
    for c in df.columns:
        f.write(f"{c}\n")

# Dump first row to see what values look like
with open('api_row1.txt', 'w', encoding='utf-8') as f:
    for c in df.columns:
        f.write(f"{c}: {df.iloc[0][c]}\n")
