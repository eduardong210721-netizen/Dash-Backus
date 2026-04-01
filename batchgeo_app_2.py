import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ──────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BatchGeo Clone v2 – Backus",
    page_icon="🗺️",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────
# Colour palette / tokens
# ──────────────────────────────────────────────────────────────
BLUE   = "#2563eb"
SLATE  = "#1e293b"
GRAY   = "#64748b"
WHITE  = "#ffffff"
BG     = "#f8fafc"

# Supervisor palette (vibrant, high-contrast)
COLOUR_SEQ = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706",
    "#9333ea", "#0891b2", "#e11d48", "#4f46e5",
    "#059669", "#ca8a04", "#7c3aed", "#0284c7",
]

# ──────────────────────────────────────────────────────────────
# CSS – clean light design
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {BG}; }}

    div[data-testid="stMetric"] {{
        background: {WHITE};
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37,99,235,0.10);
    }}
    div[data-testid="stMetric"] label {{
        color: {GRAY} !important;
        font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.5px; font-size: 0.75rem;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: {SLATE} !important; font-size: 1.9rem; font-weight: 700;
    }}

    section[data-testid="stSidebar"] {{
        background: {WHITE} !important;
        border-right: 1px solid #e2e8f0;
    }}
    section[data-testid="stSidebar"] .stMarkdown h2 {{
        color: {BLUE} !important;
        font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;
    }}

    div[data-testid="stFileUploader"] {{
        border: 2px dashed #cbd5e1; border-radius: 12px; padding: 8px;
    }}
    div[data-testid="stDataFrame"] {{
        border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .legend-box {{
        background: {WHITE}; border: 1px solid #e2e8f0; border-radius: 8px;
        padding: 12px; margin-top: 10px; max-height: 300px; overflow-y: auto;
    }}
    .legend-item {{
        display: flex; align-items: center; margin-bottom: 6px;
        font-size: 0.8rem; color: {SLATE};
    }}
    .legend-dot {{
        width: 12px; height: 12px; border-radius: 50%;
        margin-right: 8px; flex-shrink: 0;
    }}
    hr {{ border-color: #e2e8f0 !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{SLATE}; margin-bottom:0;'>🗺️ BatchGeo Clone <sup style='font-size:.5em; color:{BLUE};'>v2 · Plotly</sup></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:{GRAY}; margin-top:2px;'>"
    "Mapa de alto rendimiento con WebGL. Usa <b>lasso</b> o <b>box select</b> para seleccionar clientes directo en el mapa."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ──────────────────────────────────────────────────────────────
# Column mapping — fuzzy, case-insensitive, multi-alias
# ──────────────────────────────────────────────────────────────
REQUIRED_COLS = {
    "Solic": {
        "canonical": "Solic",
        "mandatory": True,
        "aliases": ["solic#", "solic.", "solic", "solicitud", "nro solicitud", "nro solic", "código", "codigo"],
    },
    "Nombre": {
        "canonical": "Nombre",
        "mandatory": True,
        "aliases": ["nombre 1", "nombre1", "nombre", "cliente", "razón social", "razon social"],
    },
    "Latitud": {
        "canonical": "Latitud",
        "mandatory": True,
        "aliases": [
            "promedio de latitud", "suma de latitud",
            "latitud", "lat", "latitude",
        ],
    },
    "Longitud": {
        "canonical": "Longitud",
        "mandatory": True,
        "aliases": [
            "promedio de longitud", "suma de longitud",
            "longitud", "lng", "lon", "longitude",
        ],
    },
    "Supervisor": {
        "canonical": "Supervisor",
        "mandatory": False,
        "aliases": ["supervisor", "sup", "supervisores"],
    },
    "ZV": {
        "canonical": "ZV",
        "mandatory": False,
        "aliases": ["zv", "zona venta", "zona de venta", "zona"],
    },
    "Cantidad": {
        "canonical": "Cantidad",
        "mandatory": False,
        "aliases": [
            "suma de cantidad de pedido", "cantidad de pedido",
            "cantidad", "pedidos", "qty", "quantity",
        ],
    },
}

_HEADER_EXAMPLES = [
    ("Solic. / Solic#", "Número de solicitud", "10165221"),
    ("Nombre 1 / Nombre", "Nombre del cliente", "Mendoza Toribio, Teodomiro"),
    ("Supervisor", "Nombre del supervisor", "Heiger Cespedes"),
    ("ZV", "Zona de venta", "PEX525"),
    ("Promedio de Latitud / Latitud", "Coordenada latitud", "-12.050978"),
    ("Promedio de Longitud / Longitud", "Coordenada longitud", "-77.021005"),
    ("Suma de Cantidad de pedido", "Cantidad de pedidos", "7"),
]


def _normalise(df: pd.DataFrame) -> pd.DataFrame | None:
    """Fuzzy-match real column names to canonical names."""
    real_cols = {col.strip().lower(): col for col in df.columns}
    rename = {}
    missing_mandatory = []
    
    for key, info in REQUIRED_COLS.items():
        found = False
        for alias in info["aliases"]:
            if alias.strip().lower() in real_cols:
                rename[real_cols[alias.strip().lower()]] = info["canonical"]
                found = True
                break
        
        # Handle missing columns
        if not found:
            if info.get("mandatory", False):
                missing_mandatory.append(key)
            else:
                # Add optional with default value
                if key == "Cantidad":
                    df[key] = 1  # default to 1 instance
                else:
                    df[key] = "Sin asignar"

    if missing_mandatory:
        st.error(
            "❌ Faltan columnas indispensables: "
            + ", ".join(f"**{m}**" for m in missing_mandatory)
        )
        st.info("💡 Solo el **Código (Solic)**, **Nombre**, **Latitud** y **Longitud** son estrictamente obligatorios. Los demás son opcionales.")
        with st.expander("📄 Columnas encontradas en tu archivo"):
            st.write(list(df.columns))
        return None
        
    return df.rename(columns=rename)


# ──────────────────────────────────────────────────────────────
# File uploader
# ──────────────────────────────────────────────────────────────
uploaded = st.sidebar.file_uploader(
    "📂 Subir archivo Excel (.xlsx)",
    type=["xlsx"],
    help="Acepta variaciones: Solic. / Solic#, Nombre 1, Promedio de Latitud, etc.",
)

if uploaded is None:
    st.markdown(
        f"""
        <div style="
            text-align:center; padding:50px 20px 30px;
            border:2px dashed #cbd5e1; border-radius:16px;
            margin-top:30px; background:{WHITE};
        ">
            <span style="font-size:4rem;">📤</span>
            <h2 style="color:{BLUE}; margin-top:16px;">Sube tu Excel de Ventas</h2>
            <p style="color:{GRAY}; max-width:540px; margin:auto;">
                Utiliza la barra lateral para cargar un archivo <b>.xlsx</b>
                con los datos de pedidos. Renderizado con <b>Plotly WebGL</b>
                para máximo rendimiento.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h3 style='color:{SLATE}; margin-top:28px;'>📋 Formato requerido del Excel</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:{GRAY}; font-size:0.9rem;'>"
        "Tu archivo debe contener <b>al menos</b> las siguientes columnas. "
        "Se aceptan variaciones en el nombre."
        "</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        pd.DataFrame(_HEADER_EXAMPLES, columns=["Encabezado aceptado", "Descripción", "Ejemplo"]),
        use_container_width=True, hide_index=True,
    )
    st.stop()

# ──────────────────────────────────────────────────────────────
# Read & normalise
# ──────────────────────────────────────────────────────────────
df_raw = pd.read_excel(uploaded)
df = _normalise(df_raw)
if df is None:
    st.stop()

# Clean coordinates
df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
rows_before = len(df)
df = df.dropna(subset=["Latitud", "Longitud"]).reset_index(drop=True)
dropped = rows_before - len(df)
if dropped:
    st.warning(f"⚠️ Se omitieron **{dropped}** filas con coordenadas vacías o inválidas.")

# ──────────────────────────────────────────────────────────────
# Sidebar filters
# ──────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🔎 Filtros")

# 1. Text filter for code (Solic)
search_solic = st.sidebar.text_input(
    "Buscar por Código (Solic)",
    placeholder="Ej. 10165221",
    help="Busca un código específico o coincidencia parcial (puedes escribir directamente)."
)

# 2. Supervisor & ZV
supervisors = sorted(df["Supervisor"].astype(str).dropna().unique())
selected_sup = st.sidebar.multiselect(
    "Supervisor", options=supervisors, default=supervisors,
)

zvs = sorted(df["ZV"].astype(str).dropna().unique())
selected_zv = st.sidebar.multiselect(
    "Zona de Venta (ZV)", options=zvs, default=zvs,
)

# Apply filters
mask_solic = df["Solic"].astype(str).str.contains(search_solic, case=False, na=False) if search_solic else True
mask = df["Supervisor"].astype(str).isin(selected_sup) & df["ZV"].astype(str).isin(selected_zv) & mask_solic
df_filtered = df.loc[mask].copy()

if df_filtered.empty:
    st.warning("⚠️ No hay datos para los filtros seleccionados.")
    st.stop()

# Assign a unique row ID for map selection mapping
df_filtered = df_filtered.copy()
df_filtered["_row_id"] = range(len(df_filtered))

# Build colour map (ensure stability across filters)
unique_sups_all = sorted(df["Supervisor"].dropna().unique())
color_map = {s: COLOUR_SEQ[i % len(COLOUR_SEQ)] for i, s in enumerate(unique_sups_all)}
# Map – Plotly scatter_mapbox (WebGL, fast)
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='color:{GRAY}; font-size:0.85rem; margin-bottom:4px;'>"
    "💡 Usa las herramientas de <b>Lasso</b> ∿ o <b>Box select</b> □ en la barra "
    "superior del mapa para seleccionar clientes. Haz doble clic para deseleccionar."
    "</p>",
    unsafe_allow_html=True,
)

# (Colour map is now defined above for the sidebar legend)

fig = px.scatter_mapbox(
    df_filtered,
    lat="Latitud",
    lon="Longitud",
    color="Supervisor",
    color_discrete_map=color_map,
    hover_name="Nombre",
    custom_data=["_row_id"],
    hover_data={
        "Cantidad": True,
        "ZV": True,
        "Solic": True,
        "Latitud": ":.6f",
        "Longitud": ":.6f",
        "Supervisor": False,   # already in legend
    },
    labels={
        "Cantidad": "📦 Pedidos",
        "ZV": "Zona Venta",
        "Solic": "Solicitud",
    },
    size_max=12,
    zoom=11,
    center={
        "lat": df_filtered["Latitud"].mean(),
        "lon": df_filtered["Longitud"].mean(),
    },
    mapbox_style="carto-positron",
    height=600,
)

fig.update_traces(marker=dict(size=9, opacity=0.85))
fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(
        title="",  # Hide title to save space
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="rgba(226,232,240,0.8)",
        borderwidth=1,
        font=dict(family="Inter", size=9),
        itemsizing="constant",
        yanchor="bottom",
        y=0.03,
        xanchor="left",
        x=0.01
    ),
    dragmode="lasso",  # default tool is lasso select
    font=dict(family="Inter"),
)

# Render with selection support
event = st.plotly_chart(
    fig,
    use_container_width=True,
    key="map_chart",
    on_select="rerun",
    selection_mode=["points", "lasso", "box"],
)

# ──────────────────────────────────────────────────────────────
# Process selection
# ──────────────────────────────────────────────────────────────
df_display = df_filtered.copy()
selection_active = False

if event and hasattr(event, "selection"):
    # Extract points from the selection
    points = event.selection.get("points", [])
    if points:
        # custom_data=["_row_id"] places _row_id at index 0 of customdata
        selected_row_ids = [pt["customdata"][0] for pt in points if "customdata" in pt]
        if selected_row_ids:
            df_display = df_filtered[df_filtered["_row_id"].isin(selected_row_ids)]
            selection_active = True

# ──────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📦 Total de Pedidos", f"{df_display['Cantidad'].sum():,.0f}")
with col2:
    st.metric("👥 Clientes", f"{df_display.shape[0]:,}")
with col3:
    avg_q = df_display["Cantidad"].mean() if len(df_display) else 0
    st.metric("📊 Promedio / Cliente", f"{avg_q:,.1f}")
with col4:
    lbl = "🔵 Selección activa" if selection_active else "⚪ Sin selección"
    st.metric(lbl, f"{df_display.shape[0]:,}" if selection_active else "—")

# ──────────────────────────────────────────────────────────────
# Data table
# ──────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<h3 style='color:{SLATE}; margin-bottom:4px;'>📋 Detalle de Clientes</h3>",
    unsafe_allow_html=True,
)
if selection_active:
    st.caption(f"Mostrando {len(df_display)} clientes seleccionados en el mapa.")
else:
    st.caption(f"Mostrando {len(df_display)} clientes (usa lasso/box en el mapa para seleccionar).")

# Download button
df_export = (
    df_display[["Solic", "Nombre", "Supervisor", "ZV", "Cantidad", "Latitud", "Longitud"]]
    .sort_values("Cantidad", ascending=False)
    .reset_index(drop=True)
)
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_export.to_excel(writer, index=False, sheet_name="Clientes")
buffer.seek(0)

st.download_button(
    label="⬇️ Descargar tabla en Excel",
    data=buffer,
    file_name="clientes_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.dataframe(
    df_export,
    use_container_width=True,
    height=400,
    column_config={
        "Solic": st.column_config.NumberColumn("Solic", format="%d"),
        "Nombre": st.column_config.TextColumn("Cliente"),
        "Supervisor": st.column_config.TextColumn("Supervisor"),
        "ZV": st.column_config.TextColumn("Zona Venta"),
        "Cantidad": st.column_config.NumberColumn("Pedidos", format="%d"),
        "Latitud": st.column_config.NumberColumn("Lat", format="%.6f"),
        "Longitud": st.column_config.NumberColumn("Lng", format="%.6f"),
    },
)

# ──────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:30px;'>"
    "BatchGeo Clone v2 • Plotly WebGL • Backus © 2026"
    "</p>",
    unsafe_allow_html=True,
)
