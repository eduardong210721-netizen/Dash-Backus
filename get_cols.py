import pandas as pd
df = pd.read_excel('RECHAZOS/DATA3.xlsx', sheet_name='DATA', nrows=1)
print(list(df.columns))
