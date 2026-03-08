import re
import pandas as pd

def parse_pasted_text(raw_text):
    parsed = {}
    if raw_text:
        for line in raw_text.split('\n'):
            match = re.search(r'(\d{4}).*?(\d{3}/\d{2}/\d{2})', line)
            if match:
                c, d = match.group(1), match.group(2)
                p = d.split('/')
                parsed[c] = f"{int(p[0])+1911}-{p[1]}-{p[2]}"
    return parsed