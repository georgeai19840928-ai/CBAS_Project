import pandas as pd
import glob

files = glob.glob('d:\\私人\\CBAS_Project\\*報價表*.xlsx')
print(f'Found {len(files)} files: {files}')

if files:
    df = pd.read_excel(files[0])
    print('\nColumns:', df.columns.tolist())
    print('\nHead:')
    print(df.head(3))
