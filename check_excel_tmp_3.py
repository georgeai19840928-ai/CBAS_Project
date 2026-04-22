import pandas as pd
import glob

files = glob.glob('d:\\私人\\CBAS_Project\\*報價表*.xlsx')
with open('d:\\私人\\CBAS_Project\\check_excel_output2.txt', 'w', encoding='utf-8') as f:
    if files:
        df = pd.read_excel(files[0], header=None)
        f.write("\nRows 0 to 10:\n")
        f.write(df.head(10).to_string())
