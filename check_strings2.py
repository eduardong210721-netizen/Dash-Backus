import pandas as pd
df = pd.read_excel('RECHAZOS/DATA3.xlsx', sheet_name='DATA', nrows=5000)
with open('ascii_out.txt', 'w', encoding='utf-8') as f:
    for c in df.select_dtypes(include=['object']).columns:
        vals = [str(x) for x in df[c].dropna().unique() if str(x).strip()]
        f.write(f"{c}: {vals[:5]}\n")
