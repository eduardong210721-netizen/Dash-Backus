import pandas as pd
df = pd.read_excel(r"RECHAZOS/DATA3.xlsx", sheet_name="DATA", nrows=100)
for c in df.select_dtypes(include=['object']).columns:
    vals = [str(x) for x in df[c].dropna().unique() if str(x).strip()]
    print(f"{c}: {vals[:5]}")
