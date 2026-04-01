import streamlit as st
import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import shape, Point

# ──────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BatchGeo Clone – Backus",
    page_icon="🗺️",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────
# Colour palette / tokens
# ──────────────────────────────────────────────────────────────
BLUE   = "#2563eb"
BLUE_L = "#dbeafe"
SLATE  = "#1e293b"
GRAY   = "#64748b"
WHITE  = "#ffffff"
BG     = "#f8fafc"

# Supervisor → colour map for circle markers
COLOURS = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706",
    "#9333ea", "#0891b2", "#e11d48", "#4f46e5",
    "#059669", "#ca8a04", "#7c3aed", "#0284c7",
]

# ──────────────────────────────────────────────────────────────
# Custom CSS – clean light design
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    .stApp {{ background: {BG}; }}

    /* ── Metric cards ── */
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
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.75rem;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: {SLATE} !important;
        font-size: 1.9rem;
        font-weight: 700;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background: {WHITE} !important;
        border-right: 1px solid #e2e8f0;
    }}
    section[data-testid="stSidebar"] .stMarkdown h2 {{
        color: {BLUE} !important;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── File uploader ── */
    div[data-testid="stFileUploader"] {{
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 8px;
    }}

    /* ── Map container ── */
    iframe {{ border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }}

    /* ── Data table ── */
    div[data-testid="stDataFrame"] {{
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
    }}

    /* ── Divider ── */
    hr {{ border-color: #e2e8f0 !important; }}

    /* ── Legend box ── */
    .legend-box {{
        background: {WHITE};
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .legend-item {{
        display: flex; align-items: center; gap: 8px;
        font-size: 0.82rem; color: {SLATE};
        margin-bottom: 4px;
    }}
    .legend-dot {{
        width: 12px; height: 12px; border-radius: 50%;
        display: inline-block; flex-shrink: 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{SLATE}; margin-bottom:0;'>🗺️ BatchGeo Clone</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:{GRAY}; margin-top:2px;'>"
    "Sube tu Excel de ventas, visualiza clientes en el mapa y selecciona zonas dibujando figuras."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ──────────────────────────────────────────────────────────────
# Column mapping — fuzzy, case-insensitive, multi-alias
# ──────────────────────────────────────────────────────────────
# Each canonical name has a list of accepted aliases (checked
# case-insensitively with stripped whitespace).  The FIRST match
# found wins.
REQUIRED_COLS = {
    "Solic": {
        "canonical": "Solic",
        "aliases": ["solic#", "solic.", "solic", "solicitud", "nro solicitud", "nro solic"],
    },
    "Nombre": {
        "canonical": "Nombre",
        "aliases": ["nombre 1", "nombre1", "nombre", "cliente", "razón social", "razon social"],
    },
    "Supervisor": {
        "canonical": "Supervisor",
        "aliases": ["supervisor", "sup", "supervisores"],
    },
    "ZV": {
        "canonical": "ZV",
        "aliases": ["zv", "zona venta", "zona de venta", "zona"],
    },
    "Latitud": {
        "canonical": "Latitud",
        "aliases": [
            "promedio de latitud", "suma de latitud",
            "latitud", "lat", "latitude",
        ],
    },
    "Longitud": {
        "canonical": "Longitud",
        "aliases": [
            "promedio de longitud", "suma de longitud",
            "longitud", "lng", "lon", "longitude",
        ],
    },
    "Cantidad": {
        "canonical": "Cantidad",
        "aliases": [
            "suma de cantidad de pedido", "cantidad de pedido",
            "cantidad", "pedidos", "qty", "quantity",
        ],
    },
}

# Nice display names for the required-format table
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
    # Build a lookup: lowered-stripped real col → original col name
    real_cols = {col.strip().lower(): col for col in df.columns}

    rename = {}
    missing = []
    for key, info in REQUIRED_COLS.items():
        found = False
        for alias in info["aliases"]:
            alias_clean = alias.strip().lower()
            if alias_clean in real_cols:
                rename[real_cols[alias_clean]] = info["canonical"]
                found = True
                break
        if not found:
            missing.append(key)

    if missing:
        st.error(
            "❌ No se encontraron las siguientes columnas obligatorias: "
            + ", ".join(f"**{m}**" for m in missing)
        )
        st.info(
            "💡 Revisa que tu archivo contenga los encabezados esperados. "
            "Se aceptan variaciones como *Solic.*, *Solic#*, *Nombre 1*, "
            "*Promedio de Latitud*, *Suma de Latitud*, etc."
        )
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
    help="Acepta variaciones de encabezados: Solic. / Solic#, Nombre 1 / Nombre, Promedio de Latitud / Latitud, etc.",
)

if uploaded is None:
    # ── Empty state: explain required format ──
    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding: 50px 20px 30px;
            border: 2px dashed #cbd5e1;
            border-radius: 16px;
            margin-top: 30px;
            background: {WHITE};
        ">
            <span style="font-size:4rem;">📤</span>
            <h2 style="color:{BLUE}; margin-top:16px;">
                Sube tu Excel de Ventas
            </h2>
            <p style="color:{GRAY}; max-width:540px; margin:auto;">
                Utiliza la barra lateral para cargar un archivo <b>.xlsx</b>
                con los datos de pedidos. Los clientes aparecerán automáticamente
                en el mapa interactivo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show required format table
    st.markdown(
        f"<h3 style='color:{SLATE}; margin-top:28px;'>📋 Formato requerido del Excel</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:{GRAY}; font-size:0.9rem;'>"
        "Tu archivo debe contener <b>al menos</b> las siguientes columnas. "
        "Se aceptan variaciones en el nombre (ver columna <i>Encabezado</i>)."
        "</p>",
        unsafe_allow_html=True,
    )
    fmt_df = pd.DataFrame(
        _HEADER_EXAMPLES,
        columns=["Encabezado aceptado", "Descripción", "Ejemplo"],
    )
    st.dataframe(
        fmt_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Encabezado aceptado": st.column_config.TextColumn(width="large"),
            "Descripción": st.column_config.TextColumn(width="large"),
            "Ejemplo": st.column_config.TextColumn(width="medium"),
        },
    )
    st.stop()

# ──────────────────────────────────────────────────────────────
# Read & normalise
# ──────────────────────────────────────────────────────────────
df_raw = pd.read_excel(uploaded)
df = _normalise(df_raw)
if df is None:
    st.stop()

# Clean coordinates: coerce text to numeric & drop rows with missing lat/lng
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

supervisors = sorted(df["Supervisor"].dropna().unique())
selected_sup = st.sidebar.multiselect(
    "Supervisor",
    options=supervisors,
    default=supervisors,
    help="Filtra por supervisor",
)

zvs = sorted(df["ZV"].dropna().unique())
selected_zv = st.sidebar.multiselect(
    "Zona de Venta (ZV)",
    options=zvs,
    default=zvs,
    help="Filtra por zona de venta",
)

# Apply sidebar filters
mask = df["Supervisor"].isin(selected_sup) & df["ZV"].isin(selected_zv)
df_sidebar = df.loc[mask].copy()

# ──────────────────────────────────────────────────────────────
# Build supervisor → colour mapping
# ──────────────────────────────────────────────────────────────
unique_sups = sorted(df_sidebar["Supervisor"].dropna().unique())
sup_color = {s: COLOURS[i % len(COLOURS)] for i, s in enumerate(unique_sups)}

# ──────────────────────────────────────────────────────────────
# Build map
# ──────────────────────────────────────────────────────────────
if df_sidebar.empty:
    st.warning("⚠️ No hay datos para los filtros seleccionados.")
    st.stop()

center_lat = df_sidebar["Latitud"].mean()
center_lon = df_sidebar["Longitud"].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="CartoDB Positron",
)

# Individual CircleMarkers (no clusters)
for _, row in df_sidebar.iterrows():
    popup_html = (
        f"<div style='font-family:Inter,sans-serif; min-width:200px;'>"
        f"<b style='color:{BLUE}; font-size:13px;'>{row['Nombre']}</b><br>"
        f"<hr style='margin:5px 0; border-color:#e2e8f0;'>"
        f"<span style='font-size:12px;'>📦 Pedidos: <b>{int(row['Cantidad'])}</b></span><br>"
        f"<span style='font-size:11px; color:#64748b;'>ZV: {row['ZV']}</span><br>"
        f"<span style='font-size:11px; color:#64748b;'>Solic: {row['Solic']}</span>"
        f"</div>"
    )
    color = sup_color.get(row["Supervisor"], BLUE)
    folium.CircleMarker(
        location=[row["Latitud"], row["Longitud"]],
        radius=7,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
        weight=1.5,
        popup=folium.Popup(popup_html, max_width=280),
    ).add_to(m)

# Draw plugin – rectangle, polygon, circle
draw = Draw(
    draw_options={
        "polyline": False,
        "marker": False,
        "circlemarker": False,
        "polygon": True,
        "rectangle": True,
        "circle": True,
    },
    edit_options={"edit": True, "remove": True},
)
draw.add_to(m)

# ──────────────────────────────────────────────────────────────
# Render map & capture drawn shapes
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='color:{GRAY}; font-size:0.85rem; margin-bottom:6px;'>"
    "💡 Usa las herramientas de dibujo (▭ ⬠ ○) en el lado izquierdo del mapa para seleccionar clientes por zona."
    "</p>",
    unsafe_allow_html=True,
)

map_data = st_folium(m, use_container_width=True, height=560)

# ──────────────────────────────────────────────────────────────
# Filter by drawn shape
# ──────────────────────────────────────────────────────────────
df_display = df_sidebar.copy()
shape_active = False

if map_data and map_data.get("all_drawings"):
    drawings = map_data["all_drawings"]
    if drawings:
        # Combine all drawn shapes into a single filter
        selected_indices = set()
        for drawing in drawings:
            geom = drawing.get("geometry")
            if geom:
                try:
                    drawn_shape = shape(geom)
                    for idx, row in df_sidebar.iterrows():
                        pt = Point(row["Longitud"], row["Latitud"])
                        if drawn_shape.contains(pt):
                            selected_indices.add(idx)
                except Exception:
                    pass
        if selected_indices:
            df_display = df_sidebar.loc[list(selected_indices)]
            shape_active = True

# ──────────────────────────────────────────────────────────────
# Legend (supervisor colours)
# ──────────────────────────────────────────────────────────────
legend_html = "".join(
    f'<div class="legend-item">'
    f'<span class="legend-dot" style="background:{c};"></span>'
    f'{s}</div>'
    for s, c in sup_color.items()
)
st.sidebar.markdown("## 🎨 Leyenda")
st.sidebar.markdown(f'<div class="legend-box">{legend_html}</div>', unsafe_allow_html=True)

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
    label = "🔵 Selección activa" if shape_active else "⚪ Sin selección"
    st.metric(label, f"{df_display.shape[0]:,}" if shape_active else "—")

# ──────────────────────────────────────────────────────────────
# Data table
# ──────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<h3 style='color:{SLATE}; margin-bottom:4px;'>📋 Detalle de Clientes</h3>",
    unsafe_allow_html=True,
)
if shape_active:
    st.caption(f"Mostrando {len(df_display)} clientes dentro de la figura dibujada.")
else:
    st.caption(f"Mostrando {len(df_display)} clientes (dibuja una figura en el mapa para filtrar).")

# ── Download button ──
from io import BytesIO

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
    df_display[["Solic", "Nombre", "Supervisor", "ZV", "Cantidad", "Latitud", "Longitud"]]
    .sort_values("Cantidad", ascending=False)
    .reset_index(drop=True),
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
    "BatchGeo Clone • Backus © 2026"
    "</p>",
    unsafe_allow_html=True,
)
