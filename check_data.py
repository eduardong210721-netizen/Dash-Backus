import pandas as pd

df = pd.read_excel('RECHAZOS/DATA3.xlsx', sheet_name='DATA')
for c in ['CCreado','CRechazado','CRechazadoParcial','CRechazadoTotal']:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

# Override like load_data does
df['CRechazado'] = df['CRechazadoParcial'] + df['CRechazadoTotal']

g = df.groupby('Ruta').agg({'CCreado':'sum', 'CRechazado':'sum'})
g = g[g['CCreado'] > 0]
g['pct'] = round(g['CRechazado'] / g['CCreado'] * 100, 1)
g = g.sort_values('pct', ascending=False)

print("=== Top 10 BKs by pct rejection ===")
print(g.head(10).to_string())
print()
print("=== Bottom 5 BKs ===")
print(g.tail(5).to_string())
print()

# Check motivos
if 'Motivos Rechazos' in df.columns:
    df['Motivo'] = df['Motivos Rechazos'].fillna('Sin Motivo').astype(str)
    m = df.groupby('Motivo')['CRechazado'].sum().sort_values(ascending=False)
    print("=== Motivos top 5 ===")
    print(m.head(7).to_string())
