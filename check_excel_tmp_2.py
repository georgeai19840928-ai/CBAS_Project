import pandas as pd
import glob

files = glob.glob('d:\\私人\\CBAS_Project\\*報價表*.xlsx')
with open('d:\\私人\\CBAS_Project\\check_excel_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Found {len(files)} files: {files}\n")
    if files:
        df = pd.read_excel(files[0])
        f.write(f"\nColumns: {df.columns.tolist()}\n")
        f.write("\nHead:\n")
        f.write(str(df.head(3)))
