import pandas as pd
df = pd.read_excel('RECHAZOS/DATA3.xlsx', sheet_name='DATA', nrows=1)
cols = list(df.columns)
print("TOTAL COLUMNS:", len(cols))
for c in cols:
    print(f"'{c}'")
