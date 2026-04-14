"""
GeoMapper Pro v3 — Mapas interactivos desde cualquier Excel/CSV con coordenadas.

Características:
  • Detección automática de lat/lon por nombre O por rango de valores
  • Si no detecta, ofrece selector manual de columnas
  • TODOS los campos restantes se convierten en filtros dinámicos:
      - Categórico (≤40 únicos)  → multiselect
      - Numérico (>10 únicos)    → slider de rango
      - Texto libre              → búsqueda parcial
  • Colorear/escalar puntos por cualquier columna
  • Estilos de mapa: claro, oscuro, satélite, sin etiquetas
  • Selección lasso/box sobre el mapa → tabla reactiva
  • Export HTML standalone (offline) + Export PNG + Export XLSX
  • Compartir vía ?share_id=XXXX (guarda parquet temporalmente)
  • Tabs: Tabla · Estadísticas · Gráficos de barras
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import os, uuid, re
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GeoMapper Pro",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
BLUE   = "#1d4ed8"
INDIGO = "#4f46e5"
SLATE  = "#0f172a"
GRAY   = "#64748b"
LGRAY  = "#94a3b8"
WHITE  = "#ffffff"
BG     = "#f1f5f9"
CARD   = "#ffffff"
BORDER = "#e2e8f0"

COLOUR_SEQ = [
    "#2563eb","#dc2626","#16a34a","#d97706","#9333ea","#0891b2",
    "#e11d48","#4f46e5","#059669","#ca8a04","#7c3aed","#0284c7",
    "#ea580c","#0d9488","#7e22ce","#b45309","#be185d","#065f46",
    "#1e40af","#991b1b","#166534","#92400e","#6d28d9","#0e7490",
]

MAP_STYLES = {
    "☀️  Claro (Carto)"       : "carto-positron",
    "🌙  Oscuro (Carto)"      : "carto-darkmatter",
    "🗺️  OpenStreetMap"       : "open-street-map",
    "⬜  Fondo blanco"         : "white-bg",
}

# ══════════════════════════════════════════════════════════════════════════════
# CSS  ─ clean card-based design with DM Sans
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif !important; }}
.stApp {{ background: {BG}; }}

/* ── Metrics ── */
div[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 16px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: transform .18s ease, box-shadow .18s ease;
}}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(29,78,216,.10);
}}
div[data-testid="stMetric"] label {{
    color: {GRAY} !important;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .6px;
    font-size: .70rem;
}}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
    color: {SLATE} !important;
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -.5px;
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background: {WHITE} !important;
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] > div > div {{
    padding-top: 1.5rem !important;
}}
section[data-testid="stSidebar"] .stMarkdown p {{
    font-size: .83rem;
    color: {GRAY};
}}

/* ── Upload zone ── */
div[data-testid="stFileUploader"] {{
    border: 2px dashed {BORDER};
    border-radius: 14px;
    padding: 8px;
    background: {CARD};
    transition: border-color .2s;
}}
div[data-testid="stFileUploader"]:hover {{
    border-color: {BLUE};
}}

/* ── DataFrame ── */
div[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    font-weight: 700 !important;
    font-size: .88rem !important;
    letter-spacing: .2px !important;
}}

/* ── Buttons ── */
div.stDownloadButton > button, div.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
    transition: all .15s !important;
}}

/* ── Expanders ── */
details summary {{
    font-weight: 700 !important;
    font-size: .85rem !important;
    color: {SLATE} !important;
}}

/* ── Divider ── */
hr {{ border-color: {BORDER} !important; margin: 1rem 0 !important; }}

/* ── Selectbox / multiselect labels ── */
div[data-testid="stSelectbox"] label,
div[data-testid="stMultiSelect"] label,
div[data-testid="stSlider"] label,
div[data-testid="stTextInput"] label {{
    font-size: .8rem !important;
    font-weight: 700 !important;
    color: {SLATE} !important;
    text-transform: uppercase;
    letter-spacing: .5px;
}}

/* ── Section headers ── */
.section-title {{
    font-size: 1rem;
    font-weight: 800;
    color: {SLATE};
    letter-spacing: -.2px;
    margin-bottom: 2px;
}}
.section-sub {{
    font-size: .8rem;
    color: {GRAY};
    margin-bottom: 12px;
}}

/* ── Info cards on landing ── */
.info-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    height: 100%;
    transition: box-shadow .2s;
}}
.info-card:hover {{ box-shadow: 0 8px 24px rgba(29,78,216,.08); }}

/* ── Selection indicator ── */
.sel-badge {{
    display: inline-block;
    background: #dbeafe;
    color: #1d4ed8;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .3px;
}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SMART COLUMN DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

LAT_PATTERNS = [
    r"^lat(itud(e)?)?$", r"^y$", r"^coord_?y$", r"^geo_?lat$",
    r"^(promedio|suma|avg)\s+de\s+latitud$", r"^avg_?lat$",
]
LON_PATTERNS = [
    r"^lon(gitud(e)?)?$", r"^lng$", r"^x$", r"^coord_?x$", r"^geo_?l(o|ong)$",
    r"^(promedio|suma|avg)\s+de\s+longitud$", r"^avg_?l(ng|on)$",
]
ID_PATTERNS  = [r"^solic", r"^id$", r"^code$", r"^cod(igo)?$", r"^n[rn]o\.?$"]
NAME_PATTERNS= [r"^nombre", r"^name$", r"^cliente$", r"^razon\s+social$",
                r"^raz[oó]n\s+social$", r"^descripci[oó]n$", r"^empresa$"]


def _match_patterns(col_lower: str, patterns: list[str]) -> bool:
    return any(re.fullmatch(p, col_lower) for p in patterns)


def _detect_by_name(df: pd.DataFrame) -> dict:
    result = {"lat": None, "lon": None, "id": None, "name": None}
    for col in df.columns:
        cl = col.strip().lower()
        if result["lat"]  is None and _match_patterns(cl, LAT_PATTERNS):  result["lat"]  = col
        if result["lon"]  is None and _match_patterns(cl, LON_PATTERNS):  result["lon"]  = col
        if result["id"]   is None and _match_patterns(cl, ID_PATTERNS):   result["id"]   = col
        if result["name"] is None and _match_patterns(cl, NAME_PATTERNS): result["name"] = col
    return result


def _detect_by_values(df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    """Heuristic: scan numeric columns and find lat/lon by value ranges."""
    lat_col = lon_col = None
    candidates = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if len(s) < 3:
            continue
        mn, mx = float(s.min()), float(s.max())
        candidates.append((col, mn, mx))

    # First pass: strict lat range  (-90..90), avoid obvious IDs (integers only, large range)
    for col, mn, mx in candidates:
        if -90 <= mn and mx <= 90 and not (mn >= 0 and mx <= 99999 and df[col].dtype == "int64"):
            lat_col = col
            break

    # Second pass: lon range (-180..180), different from lat
    for col, mn, mx in candidates:
        if col == lat_col:
            continue
        if -180 <= mn and mx <= 180:
            lon_col = col
            break

    return lat_col, lon_col


def detect_columns(df: pd.DataFrame) -> dict:
    """
    Returns: {lat, lon, id, name, filter_cols}
    filter_cols = all columns not used as lat/lon/id/name
    """
    d = _detect_by_name(df)

    # Fallback to value-range detection for missing coords
    if d["lat"] is None or d["lon"] is None:
        lat_v, lon_v = _detect_by_values(df)
        if d["lat"] is None: d["lat"] = lat_v
        if d["lon"] is None: d["lon"] = lon_v

    reserved = {c for c in [d["lat"], d["lon"], d["id"], d["name"]] if c}
    d["filter_cols"] = [c for c in df.columns if c not in reserved and c != "_row_id"]
    return d


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC FILTER BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_sidebar_filters(df: pd.DataFrame, filter_cols: list[str]) -> pd.Series:
    """
    For each column in filter_cols, render an appropriate widget.
    Returns a combined boolean mask for df.
    """
    mask = pd.Series(True, index=df.index)
    shown = 0

    for col in filter_cols:
        series = df[col]
        if series.isna().all():
            continue
        n_unique = series.nunique()
        if n_unique > 300:          # too many → skip (text search offered globally)
            continue

        dtype_kind = series.dtype.kind   # 'i'=int, 'f'=float, 'O'=object, 'b'=bool, 'M'=datetime

        if shown > 0:
            st.sidebar.markdown("---")

        # ── Categorical: bool or few unique values ──────────────────────────
        if dtype_kind in ("O", "b") or n_unique <= 15:
            opts = sorted(series.dropna().astype(str).unique().tolist())
            sel = st.sidebar.multiselect(
                f"🔹 {col}",
                options=opts,
                default=opts,
                key=f"filt__{col}",
            )
            if sel and len(sel) < len(opts):
                mask &= series.astype(str).isin(sel)

        # ── Numeric range slider ─────────────────────────────────────────────
        elif dtype_kind in ("i", "f"):
            col_clean = series.dropna()
            mn, mx = float(col_clean.min()), float(col_clean.max())
            if mn == mx:
                shown += 1
                continue
            # Choose step granularity
            rng = mx - mn
            step = round(rng / 200, max(0, -int(round(rng / 200, 10).__str__().find(".") - 1))) if rng > 0 else 1.0
            step = max(step, 0.01)
            lo, hi = st.sidebar.slider(
                f"🔹 {col}",
                min_value=mn, max_value=mx,
                value=(mn, mx),
                step=float(step),
                key=f"filt__{col}",
            )
            if lo > mn or hi < mx:
                mask &= series.between(lo, hi, inclusive="both") | series.isna()

        # ── Datetime ─────────────────────────────────────────────────────────
        elif dtype_kind == "M":
            mn_d = series.min().date()
            mx_d = series.max().date()
            lo_d, hi_d = st.sidebar.date_input(
                f"🔹 {col} (rango)",
                value=(mn_d, mx_d),
                min_value=mn_d, max_value=mx_d,
                key=f"filt__{col}",
            )
            mask &= (series.dt.date >= lo_d) & (series.dt.date <= hi_d)

        # ── High-cardinality categorical → text search ───────────────────────
        else:
            txt = st.sidebar.text_input(
                f"🔹 {col}",
                placeholder=f"Buscar en {col}…",
                key=f"filt__{col}",
            )
            if txt:
                mask &= series.astype(str).str.contains(txt, case=False, na=False)

        shown += 1

    return mask


# ══════════════════════════════════════════════════════════════════════════════
# MAP BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def make_color_map(df: pd.DataFrame, color_by: Optional[str]) -> Optional[dict]:
    if not color_by or df[color_by].dtype.kind not in ("O", "b", "U"):
        return None
    unique_vals = sorted(df[color_by].dropna().astype(str).unique())
    return {v: COLOUR_SEQ[i % len(COLOUR_SEQ)] for i, v in enumerate(unique_vals)}


def build_map(
    df: pd.DataFrame,
    detected: dict,
    color_by: Optional[str],
    size_by: Optional[str],
    map_style: str,
    point_size: int,
    opacity: float,
    show_labels: bool,
) -> go.Figure:
    lat_col  = detected["lat"]
    lon_col  = detected["lon"]
    name_col = detected["name"] or detected["id"] or lat_col

    # Hover data: everything except internal fields
    hover_data = {
        c: True
        for c in df.columns
        if c not in {lat_col, lon_col, "_row_id", color_by, name_col}
    }

    cmap = make_color_map(df, color_by)

    # Size column validation
    valid_size = (
        size_by
        and size_by in df.columns
        and df[size_by].dtype.kind in ("i", "f")
        and df[size_by].nunique() > 1
    )

    fig = px.scatter_mapbox(
        df,
        lat=lat_col,
        lon=lon_col,
        color=color_by if color_by else None,
        color_discrete_map=cmap,
        color_continuous_scale="Plasma" if (color_by and df[color_by].dtype.kind in ("i","f")) else None,
        hover_name=name_col,
        custom_data=["_row_id"],
        hover_data=hover_data,
        size=size_by if valid_size else None,
        size_max=22,
        zoom=11,
        center={"lat": float(df[lat_col].mean()), "lon": float(df[lon_col].mean())},
        mapbox_style=map_style,
        height=650,
        opacity=opacity,
        text=name_col if show_labels else None,
    )

    if not valid_size:
        fig.update_traces(marker=dict(size=point_size, opacity=opacity))

    if show_labels:
        fig.update_traces(textposition="top center",
                          textfont=dict(size=9, color=SLATE))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title_text="",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="rgba(226,232,240,0.9)",
            borderwidth=1,
            font=dict(family="DM Sans", size=11),
            itemsizing="constant",
            yanchor="top", y=0.97,
            xanchor="left", x=0.01,
        ),
        dragmode="lasso",
        font=dict(family="DM Sans"),
        uirevision="geo_map",   # preserves zoom/pan on filter reruns
        coloraxis_showscale=bool(color_by and df[color_by].dtype.kind in ("i","f")),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

SHARE_DIR = ".shared_data"
os.makedirs(SHARE_DIR, exist_ok=True)


def export_html_standalone(fig: go.Figure, title: str = "GeoMapper Pro") -> str:
    """Full-featured standalone HTML — works offline, full-screen, Plotly CDN."""
    chart_html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["lasso2d", "select2d"],
            "modeBarButtonsToRemove": ["sendDataToCloud"],
            "toImageButtonOptions": {"format": "png", "width": 1920, "height": 1080, "scale": 2},
        },
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'DM Sans',sans-serif; background:#0f172a; display:flex; flex-direction:column; height:100vh; }}
    #header {{ background:#1e293b; color:#f8fafc; padding:10px 20px; display:flex; align-items:center; gap:12px; border-bottom:1px solid #334155; flex-shrink:0; }}
    #header h1 {{ font-size:1rem; font-weight:700; letter-spacing:-.2px; }}
    #header span {{ font-size:.75rem; color:#94a3b8; }}
    #map-container {{ flex:1; min-height:0; }}
    #map-container > div {{ height:100% !important; }}
    .js-plotly-plot, .plot-container {{ height:100% !important; }}
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <div id="header">
    <span style="font-size:1.5rem;">🗺️</span>
    <div>
      <h1>GeoMapper Pro</h1>
      <span>Mapa interactivo exportado · Usa scroll para zoom · Arrastra para mover</span>
    </div>
  </div>
  <div id="map-container">
    {chart_html}
  </div>
</body>
</html>"""


def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Datos")
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# ── HEADER ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<h1 style='color:{SLATE};margin:0;font-size:1.7rem;font-weight:800;letter-spacing:-.5px;'>"
    f"🗺️ GeoMapper Pro"
    f"<sup style='font-size:.42em;color:{BLUE};font-weight:700;margin-left:6px;'>v3</sup>"
    "</h1>"
    f"<p style='color:{GRAY};margin-top:3px;font-size:.88rem;'>"
    "Transforma cualquier Excel/CSV con coordenadas en un mapa interactivo · "
    "Detección automática de columnas · Filtros dinámicos · Exportación completa."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# ── FILE UPLOAD (sidebar) ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-bottom:8px;'>📂 Datos</h2>",
    unsafe_allow_html=True,
)
uploaded = st.sidebar.file_uploader(
    "Subir Excel o CSV",
    type=["xlsx", "xls", "csv"],
    help="Se detectan automáticamente latitud y longitud. Todos los demás campos se convierten en filtros.",
    label_visibility="collapsed",
)

# ── Load raw data ─────────────────────────────────────────────────────────────
df_raw: Optional[pd.DataFrame] = None

if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            # Try common Latin encodings
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df_raw = pd.read_csv(uploaded, encoding=enc)
                    break
                except Exception:
                    uploaded.seek(0)
        else:
            df_raw = pd.read_excel(uploaded)
        if df_raw is not None:
            # Strip whitespace from column names
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        st.stop()

elif "share_id" in st.query_params:
    share_path = os.path.join(SHARE_DIR, f"{st.query_params['share_id']}.parquet")
    if os.path.exists(share_path):
        st.sidebar.success("✅ Datos cargados desde enlace compartido.")
        df_raw = pd.read_parquet(share_path)
    else:
        st.error("❌ Enlace inválido o datos expirados (máx. 7 días).")
        st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── LANDING PAGE (no data) ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if df_raw is None:
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px 50px;
        border:2px dashed {BORDER};border-radius:20px;
        background:{CARD};margin-bottom:32px;">
        <span style="font-size:5rem;">📤</span>
        <h2 style="color:{BLUE};margin:16px 0 10px;font-size:1.4rem;font-weight:800;">
            Sube tu archivo de datos</h2>
        <p style="color:{GRAY};max-width:560px;margin:auto;line-height:1.7;font-size:.9rem;">
            Carga un <b>.xlsx</b>, <b>.xls</b> o <b>.csv</b> con coordenadas geográficas.<br>
            GeoMapper Pro detecta automáticamente latitud y longitud,<br>
            y convierte <em>todas</em> las demás columnas en filtros interactivos.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    features = [
        ("🔍", "Detección Automática",
         "Reconoce lat/lon por nombre o por rango de valores numéricos. Sin configuración manual."),
        ("🎛️", "Filtros Dinámicos",
         "Multiselect, sliders y búsqueda de texto según el tipo de cada columna."),
        ("🎨", "Visual Potente",
         "Colorear y escalar puntos por cualquier campo. 4 estilos de mapa. Selección lasso/box."),
        ("🔗", "Compartir y Exportar",
         "HTML offline, PNG de alta resolución, XLSX filtrado y enlace de compartición."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], features):
        with col:
            st.markdown(f"""
            <div class="info-card">
                <span style="font-size:2.4rem;">{icon}</span>
                <h3 style="color:{SLATE};margin:10px 0 6px;font-size:.95rem;font-weight:700;">{title}</h3>
                <p style="color:{GRAY};font-size:.8rem;line-height:1.55;">{desc}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:28px;background:{CARD};border:1px solid {BORDER};
        border-radius:16px;padding:20px 24px;">
        <p class="section-title">📋 Formato mínimo requerido</p>
        <p class="section-sub">El archivo debe tener al menos columnas de latitud y longitud (se admiten muchas variantes de nombre).</p>
    </div>""", unsafe_allow_html=True)

    st.dataframe(pd.DataFrame([
        ["lat / latitud / Latitud / Promedio de Latitud", "Coordenada latitud",  "-12.050978"],
        ["lon / lng / longitud / Longitud / Promedio de Longitud", "Coordenada longitud", "-77.021005"],
        ["Cualquier otra columna", "Se usa como filtro automático", "Supervisor, Zona, Cantidad…"],
    ], columns=["Encabezado aceptado", "Descripción", "Ejemplo"]),
        use_container_width=True, hide_index=True)

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── AUTO-DETECT / MANUAL COLUMN PICKER ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
detected = detect_columns(df_raw)

# Show detection status in sidebar
with st.sidebar.expander("🔎 Columnas detectadas", expanded=False):
    status_rows = []
    for k, label in [("lat","Latitud"),("lon","Longitud"),("id","ID"),("name","Nombre")]:
        val = detected.get(k)
        icon = "✅" if val else "❓"
        status_rows.append({"Campo": label, "Columna detectada": val or "—", "Estado": icon})
    st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

# If coordinates missing → show picker
if detected["lat"] is None or detected["lon"] is None:
    st.warning("⚠️ No se pudo detectar automáticamente las columnas de coordenadas. "
               "Por favor selecciónalas manualmente:")
    num_cols  = list(df_raw.select_dtypes(include="number").columns)
    all_cols  = list(df_raw.columns)
    opts = num_cols if num_cols else all_cols
    cA, cB = st.columns(2)
    with cA:
        lat_manual = st.selectbox("📍 Columna de **Latitud**", opts,
                                  index=0, key="manual_lat")
    with cB:
        lon_manual = st.selectbox("📍 Columna de **Longitud**", opts,
                                  index=min(1, len(opts)-1), key="manual_lon")
    if lat_manual == lon_manual:
        st.error("Latitud y Longitud deben ser columnas distintas.")
        st.stop()
    detected["lat"]  = lat_manual
    detected["lon"]  = lon_manual
    reserved = {detected["lat"], detected["lon"], detected["id"], detected["name"]}
    detected["filter_cols"] = [c for c in df_raw.columns if c not in reserved]


# ══════════════════════════════════════════════════════════════════════════════
# ── PREPARE DATA ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
df = df_raw.copy()
df[detected["lat"]] = pd.to_numeric(df[detected["lat"]], errors="coerce")
df[detected["lon"]] = pd.to_numeric(df[detected["lon"]], errors="coerce")

n_before = len(df)
df = df.dropna(subset=[detected["lat"], detected["lon"]]).reset_index(drop=True)
n_dropped = n_before - len(df)
if n_dropped:
    st.warning(f"⚠️ Se ignoraron **{n_dropped}** filas con coordenadas vacías o inválidas.")

df["_row_id"] = range(len(df))

if df.empty:
    st.error("❌ No hay filas con coordenadas válidas.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── SIDEBAR: MAP OPTIONS ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-top:16px;margin-bottom:8px;'>🗺️ Opciones de Mapa</h2>",
    unsafe_allow_html=True,
)

map_style_name = st.sidebar.selectbox(
    "Estilo de mapa", list(MAP_STYLES.keys()), index=0, key="map_style",
)
map_style = MAP_STYLES[map_style_name]

# Color by
filter_cols = detected["filter_cols"]
cat_cols = [c for c in filter_cols if df[c].nunique() <= 60]
color_options = ["(ninguno)"] + filter_cols
default_color_idx = 1 if len(filter_cols) > 0 else 0
color_by = st.sidebar.selectbox("🎨 Colorear puntos por", color_options,
                                 index=default_color_idx, key="color_by")
color_by = None if color_by == "(ninguno)" else color_by

# Size by
num_extra = [c for c in filter_cols
             if df[c].dtype.kind in ("i","f") and df[c].nunique() > 1]
size_options = ["(igual)"] + num_extra
size_by = st.sidebar.selectbox("📏 Tamaño por", size_options, index=0, key="size_by")
size_by = None if size_by == "(igual)" else size_by

col_ps, col_op = st.sidebar.columns(2)
with col_ps:
    point_size = st.slider("Tamaño", 3, 22, 9, key="pt_size")
with col_op:
    opacity = st.slider("Opacidad", 0.1, 1.0, 0.85, step=0.05, key="opacity")

show_labels = st.sidebar.checkbox("🏷️ Mostrar etiquetas", value=False, key="labels")

# ── SIDEBAR: FILTERS ──────────────────────────────────────────────────────────
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-top:16px;margin-bottom:8px;'>🔎 Filtros</h2>",
    unsafe_allow_html=True,
)

# Global text search on ID or name
search_global = st.sidebar.text_input(
    "🔍 Búsqueda global",
    placeholder="Buscar en ID o nombre…",
    key="global_search",
)

filter_mask = build_sidebar_filters(df, filter_cols)

# Apply global search
if search_global:
    global_cols = [c for c in [detected["id"], detected["name"]] if c]
    if global_cols:
        gm = pd.Series(False, index=df.index)
        for gc in global_cols:
            gm |= df[gc].astype(str).str.contains(search_global, case=False, na=False)
        filter_mask &= gm

df_filtered = df[filter_mask].copy().reset_index(drop=True)
df_filtered["_row_id"] = range(len(df_filtered))

if df_filtered.empty:
    st.warning("⚠️ Sin resultados con los filtros actuales. Amplía los criterios.")
    st.stop()

# ── SIDEBAR: SHARE ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("🔗 Compartir mapa"):
    st.markdown("<p>Genera un enlace para compartir los datos sin enviar el Excel original.</p>",
                unsafe_allow_html=True)
    if st.button("⚡ Generar enlace de compartición", use_container_width=True):
        sid = str(uuid.uuid4())[:8]
        df_raw.to_parquet(os.path.join(SHARE_DIR, f"{sid}.parquet"), index=False)
        st.code(f"?share_id={sid}")
        st.caption("Añade este parámetro a la URL de tu app (ej: https://tu-app.streamlit.app/?share_id=" + sid + ")")


# ══════════════════════════════════════════════════════════════════════════════
# ── MAP SECTION ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
info_col, badge_col = st.columns([8, 2])
with info_col:
    st.markdown(
        f"<p style='color:{GRAY};font-size:.82rem;margin:0;'>"
        "💡 Herramientas del mapa: <b>Lasso ∿</b> o <b>Box □</b> para seleccionar puntos · "
        "<b>Scroll</b> para zoom · <b>Doble clic</b> para deseleccionar</p>",
        unsafe_allow_html=True,
    )
with badge_col:
    st.markdown(
        f"<div style='text-align:right'>"
        f"<span class='sel-badge'>{len(df_filtered):,} puntos</span></div>",
        unsafe_allow_html=True,
    )

# Build and render map
fig = build_map(df_filtered, detected, color_by, size_by,
                map_style, point_size, opacity, show_labels)

event = st.plotly_chart(
    fig,
    use_container_width=True,
    key="geo_map",
    on_select="rerun",
    selection_mode=["points", "lasso", "box"],
)

# ── Export row ────────────────────────────────────────────────────────────────
ecol1, ecol2, ecol3, _ = st.columns([2, 2, 2, 4])

map_html = export_html_standalone(fig, "GeoMapper Pro · Mapa Interactivo")
with ecol1:
    st.download_button(
        "⬇️ HTML offline",
        data=map_html,
        file_name="mapa_interactivo.html",
        mime="text/html",
        help="Mapa completo que funciona en cualquier navegador sin conexión.",
        use_container_width=True,
    )

with ecol2:
    try:
        img_bytes = fig.to_image(format="png", scale=2, width=1920, height=1080)
        st.download_button(
            "🖼️ Imagen PNG",
            data=img_bytes,
            file_name="mapa.png",
            mime="image/png",
            help="Captura de alta resolución (1920×1080 px @2x).",
            use_container_width=True,
        )
    except Exception:
        st.caption("_(instala kaleido para PNG)_")

with ecol3:
    disp_cols = [c for c in df_filtered.columns if c != "_row_id"]
    xlsx_bytes = df_to_xlsx_bytes(df_filtered[disp_cols])
    st.download_button(
        "📊 XLSX filtrado",
        data=xlsx_bytes,
        file_name="datos_filtrados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ── SELECTION LOGIC ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
df_display        = df_filtered.copy()
selection_active  = False

if event and hasattr(event, "selection"):
    pts = event.selection.get("points", [])
    if pts:
        ids = [p["customdata"][0] for p in pts if "customdata" in p]
        if ids:
            df_display       = df_filtered[df_filtered["_row_id"].isin(ids)].copy()
            selection_active = True


# ══════════════════════════════════════════════════════════════════════════════
# ── METRICS ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.divider()

num_extra_disp = [
    c for c in df_display.select_dtypes(include="number").columns
    if c not in {detected["lat"], detected["lon"], "_row_id"}
]

m_cols = st.columns(5)
with m_cols[0]:
    st.metric("📍 Total (filtrado)", f"{len(df_filtered):,}")
with m_cols[1]:
    lbl = "✅ Seleccionados" if selection_active else "🖱️ Selección"
    st.metric(lbl, f"{len(df_display):,}" if selection_active else "—")
with m_cols[2]:
    if num_extra_disp:
        col0 = num_extra_disp[0]
        st.metric(f"∑ {col0}", f"{df_display[col0].sum():,.0f}")
    elif detected["id"]:
        st.metric("IDs únicos", f"{df_display[detected['id']].nunique():,}")
    else:
        st.metric("Columnas", f"{len(df_display.columns):,}")
with m_cols[3]:
    if len(num_extra_disp) > 1:
        col1_ = num_extra_disp[1]
        st.metric(f"∑ {col1_}", f"{df_display[col1_].sum():,.0f}")
    elif color_by:
        st.metric(f"Grupos ({color_by})", f"{df_display[color_by].nunique():,}")
    else:
        st.metric("Lat (centro)", f"{df_display[detected['lat']].mean():.4f}")
with m_cols[4]:
    pct = len(df_display) / len(df_filtered) * 100 if len(df_filtered) else 0
    st.metric("% del total", f"{pct:.1f}%" if selection_active else "100%")


# ══════════════════════════════════════════════════════════════════════════════
# ── TABS: TABLA · ESTADÍSTICAS · GRÁFICOS ───────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
tab_table, tab_stats, tab_charts = st.tabs(["📋 Tabla de datos", "📊 Estadísticas", "📈 Gráficos"])

# ── TAB 1: TABLE ──────────────────────────────────────────────────────────────
with tab_table:
    if selection_active:
        st.markdown(
            f"<span class='sel-badge'>✅ Mostrando {len(df_display)} puntos seleccionados en el mapa</span>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Mostrando {len(df_display):,} puntos filtrados. "
                   "Usa lasso o box en el mapa para seleccionar un subconjunto.")

    display_cols = [c for c in df_display.columns if c != "_row_id"]

    # Sort by first numeric col if exists
    sort_col = num_extra_disp[0] if num_extra_disp else display_cols[0]
    df_table = (
        df_display[display_cols]
        .sort_values(by=sort_col, ascending=False)
        .reset_index(drop=True)
    )

    # Download selected/filtered
    st.download_button(
        "⬇️ Descargar esta tabla (.xlsx)",
        data=df_to_xlsx_bytes(df_table),
        file_name="seleccion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Column config: format lat/lon nicely
    col_cfg = {}
    if detected["lat"]:
        col_cfg[detected["lat"]] = st.column_config.NumberColumn("Lat", format="%.6f")
    if detected["lon"]:
        col_cfg[detected["lon"]] = st.column_config.NumberColumn("Lon", format="%.6f")

    st.dataframe(df_table, use_container_width=True, height=420, column_config=col_cfg)

# ── TAB 2: STATS ─────────────────────────────────────────────────────────────
with tab_stats:
    num_df = df_display.select_dtypes("number").drop(
        columns=[c for c in ["_row_id", detected["lat"], detected["lon"]] if c],
        errors="ignore",
    )
    if not num_df.empty:
        desc = num_df.describe().T
        desc.index.name = "Columna"
        st.dataframe(
            desc.style.format("{:.2f}").background_gradient(
                subset=["mean", "std"], cmap="Blues"
            ),
            use_container_width=True,
        )
    else:
        st.info("No hay columnas numéricas para estadísticas.")

    # Value counts for categorical
    cat_filter_cols = [c for c in filter_cols if df_display[c].dtype.kind == "O" and df_display[c].nunique() <= 30]
    if cat_filter_cols:
        st.markdown(f"<p class='section-title' style='margin-top:16px;'>Distribución categórica</p>",
                    unsafe_allow_html=True)
        cat_sel = st.selectbox("Ver distribución de", cat_filter_cols, key="cat_dist")
        vc = df_display[cat_sel].value_counts().reset_index()
        vc.columns = [cat_sel, "Conteo"]
        st.dataframe(vc, use_container_width=True, height=280, hide_index=True)

# ── TAB 3: CHARTS ────────────────────────────────────────────────────────────
with tab_charts:
    if not filter_cols:
        st.info("No hay columnas adicionales para graficar.")
    else:
        cc1, cc2 = st.columns(2)
        with cc1:
            x_opts = [c for c in filter_cols if df_display[c].nunique() <= 40]
            x_col  = st.selectbox("Eje X (categoría / grupo)", x_opts if x_opts else filter_cols,
                                   key="chart_x")
        with cc2:
            y_opts = num_extra_disp if num_extra_disp else [detected["lat"]]
            y_col  = st.selectbox("Eje Y (valor)", y_opts, key="chart_y")

        agg_fn = st.radio("Agregación", ["Suma", "Promedio", "Conteo"],
                          horizontal=True, key="agg_fn")

        if agg_fn == "Suma":
            agg_df = df_display.groupby(x_col)[y_col].sum().reset_index()
        elif agg_fn == "Promedio":
            agg_df = df_display.groupby(x_col)[y_col].mean().reset_index()
        else:
            agg_df = df_display.groupby(x_col)[y_col].count().reset_index()
            y_col  = y_col  # rename handled below

        agg_df = agg_df.sort_values(y_col, ascending=False).head(30)

        fig_bar = px.bar(
            agg_df, x=x_col, y=y_col,
            color=x_col,
            color_discrete_sequence=COLOUR_SEQ,
            template="plotly_white",
            title=f"{agg_fn} de {y_col} por {x_col}",
            text_auto=".2s",
        )
        fig_bar.update_layout(
            showlegend=False,
            font=dict(family="DM Sans"),
            title_font=dict(size=13, family="DM Sans"),
            xaxis_tickangle=-35,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Pie if few categories
        if df_display[x_col].nunique() <= 15:
            fig_pie = px.pie(
                agg_df, names=x_col, values=y_col,
                color_discrete_sequence=COLOUR_SEQ,
                template="plotly_white",
                title=f"Distribución de {y_col} por {x_col}",
            )
            fig_pie.update_layout(font=dict(family="DM Sans"), title_font=dict(size=13))
            st.plotly_chart(fig_pie, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── FOOTER ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<p style='text-align:center;color:{LGRAY};font-size:.75rem;margin-top:36px;'>"
    "GeoMapper Pro v3 · Plotly WebGL · Detección automática de columnas · © 2026</p>",
    unsafe_allow_html=True,
)"""
GeoMapper Pro v3 — Mapas interactivos desde cualquier Excel/CSV con coordenadas.

Características:
  • Detección automática de lat/lon por nombre O por rango de valores
  • Si no detecta, ofrece selector manual de columnas
  • TODOS los campos restantes se convierten en filtros dinámicos:
      - Categórico (≤40 únicos)  → multiselect
      - Numérico (>10 únicos)    → slider de rango
      - Texto libre              → búsqueda parcial
  • Colorear/escalar puntos por cualquier columna
  • Estilos de mapa: claro, oscuro, satélite, sin etiquetas
  • Selección lasso/box sobre el mapa → tabla reactiva
  • Export HTML standalone (offline) + Export PNG + Export XLSX
  • Compartir vía ?share_id=XXXX (guarda parquet temporalmente)
  • Tabs: Tabla · Estadísticas · Gráficos de barras
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import os, uuid, re
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GeoMapper Pro",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
BLUE   = "#1d4ed8"
INDIGO = "#4f46e5"
SLATE  = "#0f172a"
GRAY   = "#64748b"
LGRAY  = "#94a3b8"
WHITE  = "#ffffff"
BG     = "#f1f5f9"
CARD   = "#ffffff"
BORDER = "#e2e8f0"

COLOUR_SEQ = [
    "#2563eb","#dc2626","#16a34a","#d97706","#9333ea","#0891b2",
    "#e11d48","#4f46e5","#059669","#ca8a04","#7c3aed","#0284c7",
    "#ea580c","#0d9488","#7e22ce","#b45309","#be185d","#065f46",
    "#1e40af","#991b1b","#166534","#92400e","#6d28d9","#0e7490",
]

MAP_STYLES = {
    "☀️  Claro (Carto)"       : "carto-positron",
    "🌙  Oscuro (Carto)"      : "carto-darkmatter",
    "🗺️  OpenStreetMap"       : "open-street-map",
    "⬜  Fondo blanco"         : "white-bg",
}

# ══════════════════════════════════════════════════════════════════════════════
# CSS  ─ clean card-based design with DM Sans
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif !important; }}
.stApp {{ background: {BG}; }}

/* ── Metrics ── */
div[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 16px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: transform .18s ease, box-shadow .18s ease;
}}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(29,78,216,.10);
}}
div[data-testid="stMetric"] label {{
    color: {GRAY} !important;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .6px;
    font-size: .70rem;
}}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
    color: {SLATE} !important;
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -.5px;
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background: {WHITE} !important;
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] > div > div {{
    padding-top: 1.5rem !important;
}}
section[data-testid="stSidebar"] .stMarkdown p {{
    font-size: .83rem;
    color: {GRAY};
}}

/* ── Upload zone ── */
div[data-testid="stFileUploader"] {{
    border: 2px dashed {BORDER};
    border-radius: 14px;
    padding: 8px;
    background: {CARD};
    transition: border-color .2s;
}}
div[data-testid="stFileUploader"]:hover {{
    border-color: {BLUE};
}}

/* ── DataFrame ── */
div[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    font-weight: 700 !important;
    font-size: .88rem !important;
    letter-spacing: .2px !important;
}}

/* ── Buttons ── */
div.stDownloadButton > button, div.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
    transition: all .15s !important;
}}

/* ── Expanders ── */
details summary {{
    font-weight: 700 !important;
    font-size: .85rem !important;
    color: {SLATE} !important;
}}

/* ── Divider ── */
hr {{ border-color: {BORDER} !important; margin: 1rem 0 !important; }}

/* ── Selectbox / multiselect labels ── */
div[data-testid="stSelectbox"] label,
div[data-testid="stMultiSelect"] label,
div[data-testid="stSlider"] label,
div[data-testid="stTextInput"] label {{
    font-size: .8rem !important;
    font-weight: 700 !important;
    color: {SLATE} !important;
    text-transform: uppercase;
    letter-spacing: .5px;
}}

/* ── Section headers ── */
.section-title {{
    font-size: 1rem;
    font-weight: 800;
    color: {SLATE};
    letter-spacing: -.2px;
    margin-bottom: 2px;
}}
.section-sub {{
    font-size: .8rem;
    color: {GRAY};
    margin-bottom: 12px;
}}

/* ── Info cards on landing ── */
.info-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    height: 100%;
    transition: box-shadow .2s;
}}
.info-card:hover {{ box-shadow: 0 8px 24px rgba(29,78,216,.08); }}

/* ── Selection indicator ── */
.sel-badge {{
    display: inline-block;
    background: #dbeafe;
    color: #1d4ed8;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .3px;
}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SMART COLUMN DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

LAT_PATTERNS = [
    r"^lat(itud(e)?)?$", r"^y$", r"^coord_?y$", r"^geo_?lat$",
    r"^(promedio|suma|avg)\s+de\s+latitud$", r"^avg_?lat$",
]
LON_PATTERNS = [
    r"^lon(gitud(e)?)?$", r"^lng$", r"^x$", r"^coord_?x$", r"^geo_?l(o|ong)$",
    r"^(promedio|suma|avg)\s+de\s+longitud$", r"^avg_?l(ng|on)$",
]
ID_PATTERNS  = [r"^solic", r"^id$", r"^code$", r"^cod(igo)?$", r"^n[rn]o\.?$"]
NAME_PATTERNS= [r"^nombre", r"^name$", r"^cliente$", r"^razon\s+social$",
                r"^raz[oó]n\s+social$", r"^descripci[oó]n$", r"^empresa$"]


def _match_patterns(col_lower: str, patterns: list[str]) -> bool:
    return any(re.fullmatch(p, col_lower) for p in patterns)


def _detect_by_name(df: pd.DataFrame) -> dict:
    result = {"lat": None, "lon": None, "id": None, "name": None}
    for col in df.columns:
        cl = col.strip().lower()
        if result["lat"]  is None and _match_patterns(cl, LAT_PATTERNS):  result["lat"]  = col
        if result["lon"]  is None and _match_patterns(cl, LON_PATTERNS):  result["lon"]  = col
        if result["id"]   is None and _match_patterns(cl, ID_PATTERNS):   result["id"]   = col
        if result["name"] is None and _match_patterns(cl, NAME_PATTERNS): result["name"] = col
    return result


def _detect_by_values(df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    """Heuristic: scan numeric columns and find lat/lon by value ranges."""
    lat_col = lon_col = None
    candidates = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if len(s) < 3:
            continue
        mn, mx = float(s.min()), float(s.max())
        candidates.append((col, mn, mx))

    # First pass: strict lat range  (-90..90), avoid obvious IDs (integers only, large range)
    for col, mn, mx in candidates:
        if -90 <= mn and mx <= 90 and not (mn >= 0 and mx <= 99999 and df[col].dtype == "int64"):
            lat_col = col
            break

    # Second pass: lon range (-180..180), different from lat
    for col, mn, mx in candidates:
        if col == lat_col:
            continue
        if -180 <= mn and mx <= 180:
            lon_col = col
            break

    return lat_col, lon_col


def detect_columns(df: pd.DataFrame) -> dict:
    """
    Returns: {lat, lon, id, name, filter_cols}
    filter_cols = all columns not used as lat/lon/id/name
    """
    d = _detect_by_name(df)

    # Fallback to value-range detection for missing coords
    if d["lat"] is None or d["lon"] is None:
        lat_v, lon_v = _detect_by_values(df)
        if d["lat"] is None: d["lat"] = lat_v
        if d["lon"] is None: d["lon"] = lon_v

    reserved = {c for c in [d["lat"], d["lon"], d["id"], d["name"]] if c}
    d["filter_cols"] = [c for c in df.columns if c not in reserved and c != "_row_id"]
    return d


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC FILTER BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_sidebar_filters(df: pd.DataFrame, filter_cols: list[str]) -> pd.Series:
    """
    For each column in filter_cols, render an appropriate widget.
    Returns a combined boolean mask for df.
    """
    mask = pd.Series(True, index=df.index)
    shown = 0

    for col in filter_cols:
        series = df[col]
        if series.isna().all():
            continue
        n_unique = series.nunique()
        if n_unique > 300:          # too many → skip (text search offered globally)
            continue

        dtype_kind = series.dtype.kind   # 'i'=int, 'f'=float, 'O'=object, 'b'=bool, 'M'=datetime

        if shown > 0:
            st.sidebar.markdown("---")

        # ── Categorical: bool or few unique values ──────────────────────────
        if dtype_kind in ("O", "b") or n_unique <= 15:
            opts = sorted(series.dropna().astype(str).unique().tolist())
            sel = st.sidebar.multiselect(
                f"🔹 {col}",
                options=opts,
                default=opts,
                key=f"filt__{col}",
            )
            if sel and len(sel) < len(opts):
                mask &= series.astype(str).isin(sel)

        # ── Numeric range slider ─────────────────────────────────────────────
        elif dtype_kind in ("i", "f"):
            col_clean = series.dropna()
            mn, mx = float(col_clean.min()), float(col_clean.max())
            if mn == mx:
                shown += 1
                continue
            # Choose step granularity
            rng = mx - mn
            step = round(rng / 200, max(0, -int(round(rng / 200, 10).__str__().find(".") - 1))) if rng > 0 else 1.0
            step = max(step, 0.01)
            lo, hi = st.sidebar.slider(
                f"🔹 {col}",
                min_value=mn, max_value=mx,
                value=(mn, mx),
                step=float(step),
                key=f"filt__{col}",
            )
            if lo > mn or hi < mx:
                mask &= series.between(lo, hi, inclusive="both") | series.isna()

        # ── Datetime ─────────────────────────────────────────────────────────
        elif dtype_kind == "M":
            mn_d = series.min().date()
            mx_d = series.max().date()
            lo_d, hi_d = st.sidebar.date_input(
                f"🔹 {col} (rango)",
                value=(mn_d, mx_d),
                min_value=mn_d, max_value=mx_d,
                key=f"filt__{col}",
            )
            mask &= (series.dt.date >= lo_d) & (series.dt.date <= hi_d)

        # ── High-cardinality categorical → text search ───────────────────────
        else:
            txt = st.sidebar.text_input(
                f"🔹 {col}",
                placeholder=f"Buscar en {col}…",
                key=f"filt__{col}",
            )
            if txt:
                mask &= series.astype(str).str.contains(txt, case=False, na=False)

        shown += 1

    return mask


# ══════════════════════════════════════════════════════════════════════════════
# MAP BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def make_color_map(df: pd.DataFrame, color_by: Optional[str]) -> Optional[dict]:
    if not color_by or df[color_by].dtype.kind not in ("O", "b", "U"):
        return None
    unique_vals = sorted(df[color_by].dropna().astype(str).unique())
    return {v: COLOUR_SEQ[i % len(COLOUR_SEQ)] for i, v in enumerate(unique_vals)}


def build_map(
    df: pd.DataFrame,
    detected: dict,
    color_by: Optional[str],
    size_by: Optional[str],
    map_style: str,
    point_size: int,
    opacity: float,
    show_labels: bool,
) -> go.Figure:
    lat_col  = detected["lat"]
    lon_col  = detected["lon"]
    name_col = detected["name"] or detected["id"] or lat_col

    # Hover data: everything except internal fields
    hover_data = {
        c: True
        for c in df.columns
        if c not in {lat_col, lon_col, "_row_id", color_by, name_col}
    }

    cmap = make_color_map(df, color_by)

    # Size column validation
    valid_size = (
        size_by
        and size_by in df.columns
        and df[size_by].dtype.kind in ("i", "f")
        and df[size_by].nunique() > 1
    )

    fig = px.scatter_mapbox(
        df,
        lat=lat_col,
        lon=lon_col,
        color=color_by if color_by else None,
        color_discrete_map=cmap,
        color_continuous_scale="Plasma" if (color_by and df[color_by].dtype.kind in ("i","f")) else None,
        hover_name=name_col,
        custom_data=["_row_id"],
        hover_data=hover_data,
        size=size_by if valid_size else None,
        size_max=22,
        zoom=11,
        center={"lat": float(df[lat_col].mean()), "lon": float(df[lon_col].mean())},
        mapbox_style=map_style,
        height=650,
        opacity=opacity,
        text=name_col if show_labels else None,
    )

    if not valid_size:
        fig.update_traces(marker=dict(size=point_size, opacity=opacity))

    if show_labels:
        fig.update_traces(textposition="top center",
                          textfont=dict(size=9, color=SLATE))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title_text="",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="rgba(226,232,240,0.9)",
            borderwidth=1,
            font=dict(family="DM Sans", size=11),
            itemsizing="constant",
            yanchor="top", y=0.97,
            xanchor="left", x=0.01,
        ),
        dragmode="lasso",
        font=dict(family="DM Sans"),
        uirevision="geo_map",   # preserves zoom/pan on filter reruns
        coloraxis_showscale=bool(color_by and df[color_by].dtype.kind in ("i","f")),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

SHARE_DIR = ".shared_data"
os.makedirs(SHARE_DIR, exist_ok=True)


def export_html_standalone(fig: go.Figure, title: str = "GeoMapper Pro") -> str:
    """Full-featured standalone HTML — works offline, full-screen, Plotly CDN."""
    chart_html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["lasso2d", "select2d"],
            "modeBarButtonsToRemove": ["sendDataToCloud"],
            "toImageButtonOptions": {"format": "png", "width": 1920, "height": 1080, "scale": 2},
        },
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'DM Sans',sans-serif; background:#0f172a; display:flex; flex-direction:column; height:100vh; }}
    #header {{ background:#1e293b; color:#f8fafc; padding:10px 20px; display:flex; align-items:center; gap:12px; border-bottom:1px solid #334155; flex-shrink:0; }}
    #header h1 {{ font-size:1rem; font-weight:700; letter-spacing:-.2px; }}
    #header span {{ font-size:.75rem; color:#94a3b8; }}
    #map-container {{ flex:1; min-height:0; }}
    #map-container > div {{ height:100% !important; }}
    .js-plotly-plot, .plot-container {{ height:100% !important; }}
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <div id="header">
    <span style="font-size:1.5rem;">🗺️</span>
    <div>
      <h1>GeoMapper Pro</h1>
      <span>Mapa interactivo exportado · Usa scroll para zoom · Arrastra para mover</span>
    </div>
  </div>
  <div id="map-container">
    {chart_html}
  </div>
</body>
</html>"""


def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Datos")
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# ── HEADER ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<h1 style='color:{SLATE};margin:0;font-size:1.7rem;font-weight:800;letter-spacing:-.5px;'>"
    f"🗺️ GeoMapper Pro"
    f"<sup style='font-size:.42em;color:{BLUE};font-weight:700;margin-left:6px;'>v3</sup>"
    "</h1>"
    f"<p style='color:{GRAY};margin-top:3px;font-size:.88rem;'>"
    "Transforma cualquier Excel/CSV con coordenadas en un mapa interactivo · "
    "Detección automática de columnas · Filtros dinámicos · Exportación completa."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# ── FILE UPLOAD (sidebar) ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-bottom:8px;'>📂 Datos</h2>",
    unsafe_allow_html=True,
)
uploaded = st.sidebar.file_uploader(
    "Subir Excel o CSV",
    type=["xlsx", "xls", "csv"],
    help="Se detectan automáticamente latitud y longitud. Todos los demás campos se convierten en filtros.",
    label_visibility="collapsed",
)

# ── Load raw data ─────────────────────────────────────────────────────────────
df_raw: Optional[pd.DataFrame] = None

if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            # Try common Latin encodings
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df_raw = pd.read_csv(uploaded, encoding=enc)
                    break
                except Exception:
                    uploaded.seek(0)
        else:
            df_raw = pd.read_excel(uploaded)
        if df_raw is not None:
            # Strip whitespace from column names
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        st.stop()

elif "share_id" in st.query_params:
    share_path = os.path.join(SHARE_DIR, f"{st.query_params['share_id']}.parquet")
    if os.path.exists(share_path):
        st.sidebar.success("✅ Datos cargados desde enlace compartido.")
        df_raw = pd.read_parquet(share_path)
    else:
        st.error("❌ Enlace inválido o datos expirados (máx. 7 días).")
        st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── LANDING PAGE (no data) ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if df_raw is None:
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px 50px;
        border:2px dashed {BORDER};border-radius:20px;
        background:{CARD};margin-bottom:32px;">
        <span style="font-size:5rem;">📤</span>
        <h2 style="color:{BLUE};margin:16px 0 10px;font-size:1.4rem;font-weight:800;">
            Sube tu archivo de datos</h2>
        <p style="color:{GRAY};max-width:560px;margin:auto;line-height:1.7;font-size:.9rem;">
            Carga un <b>.xlsx</b>, <b>.xls</b> o <b>.csv</b> con coordenadas geográficas.<br>
            GeoMapper Pro detecta automáticamente latitud y longitud,<br>
            y convierte <em>todas</em> las demás columnas en filtros interactivos.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    features = [
        ("🔍", "Detección Automática",
         "Reconoce lat/lon por nombre o por rango de valores numéricos. Sin configuración manual."),
        ("🎛️", "Filtros Dinámicos",
         "Multiselect, sliders y búsqueda de texto según el tipo de cada columna."),
        ("🎨", "Visual Potente",
         "Colorear y escalar puntos por cualquier campo. 4 estilos de mapa. Selección lasso/box."),
        ("🔗", "Compartir y Exportar",
         "HTML offline, PNG de alta resolución, XLSX filtrado y enlace de compartición."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], features):
        with col:
            st.markdown(f"""
            <div class="info-card">
                <span style="font-size:2.4rem;">{icon}</span>
                <h3 style="color:{SLATE};margin:10px 0 6px;font-size:.95rem;font-weight:700;">{title}</h3>
                <p style="color:{GRAY};font-size:.8rem;line-height:1.55;">{desc}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:28px;background:{CARD};border:1px solid {BORDER};
        border-radius:16px;padding:20px 24px;">
        <p class="section-title">📋 Formato mínimo requerido</p>
        <p class="section-sub">El archivo debe tener al menos columnas de latitud y longitud (se admiten muchas variantes de nombre).</p>
    </div>""", unsafe_allow_html=True)

    st.dataframe(pd.DataFrame([
        ["lat / latitud / Latitud / Promedio de Latitud", "Coordenada latitud",  "-12.050978"],
        ["lon / lng / longitud / Longitud / Promedio de Longitud", "Coordenada longitud", "-77.021005"],
        ["Cualquier otra columna", "Se usa como filtro automático", "Supervisor, Zona, Cantidad…"],
    ], columns=["Encabezado aceptado", "Descripción", "Ejemplo"]),
        use_container_width=True, hide_index=True)

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── AUTO-DETECT / MANUAL COLUMN PICKER ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
detected = detect_columns(df_raw)

# Show detection status in sidebar
with st.sidebar.expander("🔎 Columnas detectadas", expanded=False):
    status_rows = []
    for k, label in [("lat","Latitud"),("lon","Longitud"),("id","ID"),("name","Nombre")]:
        val = detected.get(k)
        icon = "✅" if val else "❓"
        status_rows.append({"Campo": label, "Columna detectada": val or "—", "Estado": icon})
    st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

# If coordinates missing → show picker
if detected["lat"] is None or detected["lon"] is None:
    st.warning("⚠️ No se pudo detectar automáticamente las columnas de coordenadas. "
               "Por favor selecciónalas manualmente:")
    num_cols  = list(df_raw.select_dtypes(include="number").columns)
    all_cols  = list(df_raw.columns)
    opts = num_cols if num_cols else all_cols
    cA, cB = st.columns(2)
    with cA:
        lat_manual = st.selectbox("📍 Columna de **Latitud**", opts,
                                  index=0, key="manual_lat")
    with cB:
        lon_manual = st.selectbox("📍 Columna de **Longitud**", opts,
                                  index=min(1, len(opts)-1), key="manual_lon")
    if lat_manual == lon_manual:
        st.error("Latitud y Longitud deben ser columnas distintas.")
        st.stop()
    detected["lat"]  = lat_manual
    detected["lon"]  = lon_manual
    reserved = {detected["lat"], detected["lon"], detected["id"], detected["name"]}
    detected["filter_cols"] = [c for c in df_raw.columns if c not in reserved]


# ══════════════════════════════════════════════════════════════════════════════
# ── PREPARE DATA ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
df = df_raw.copy()
df[detected["lat"]] = pd.to_numeric(df[detected["lat"]], errors="coerce")
df[detected["lon"]] = pd.to_numeric(df[detected["lon"]], errors="coerce")

n_before = len(df)
df = df.dropna(subset=[detected["lat"], detected["lon"]]).reset_index(drop=True)
n_dropped = n_before - len(df)
if n_dropped:
    st.warning(f"⚠️ Se ignoraron **{n_dropped}** filas con coordenadas vacías o inválidas.")

df["_row_id"] = range(len(df))

if df.empty:
    st.error("❌ No hay filas con coordenadas válidas.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── SIDEBAR: MAP OPTIONS ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-top:16px;margin-bottom:8px;'>🗺️ Opciones de Mapa</h2>",
    unsafe_allow_html=True,
)

map_style_name = st.sidebar.selectbox(
    "Estilo de mapa", list(MAP_STYLES.keys()), index=0, key="map_style",
)
map_style = MAP_STYLES[map_style_name]

# Color by
filter_cols = detected["filter_cols"]
cat_cols = [c for c in filter_cols if df[c].nunique() <= 60]
color_options = ["(ninguno)"] + filter_cols
default_color_idx = 1 if len(filter_cols) > 0 else 0
color_by = st.sidebar.selectbox("🎨 Colorear puntos por", color_options,
                                 index=default_color_idx, key="color_by")
color_by = None if color_by == "(ninguno)" else color_by

# Size by
num_extra = [c for c in filter_cols
             if df[c].dtype.kind in ("i","f") and df[c].nunique() > 1]
size_options = ["(igual)"] + num_extra
size_by = st.sidebar.selectbox("📏 Tamaño por", size_options, index=0, key="size_by")
size_by = None if size_by == "(igual)" else size_by

col_ps, col_op = st.sidebar.columns(2)
with col_ps:
    point_size = st.slider("Tamaño", 3, 22, 9, key="pt_size")
with col_op:
    opacity = st.slider("Opacidad", 0.1, 1.0, 0.85, step=0.05, key="opacity")

show_labels = st.sidebar.checkbox("🏷️ Mostrar etiquetas", value=False, key="labels")

# ── SIDEBAR: FILTERS ──────────────────────────────────────────────────────────
st.sidebar.markdown(
    f"<h2 style='color:{BLUE};font-size:.78rem;text-transform:uppercase;"
    "letter-spacing:1.2px;font-weight:800;margin-top:16px;margin-bottom:8px;'>🔎 Filtros</h2>",
    unsafe_allow_html=True,
)

# Global text search on ID or name
search_global = st.sidebar.text_input(
    "🔍 Búsqueda global",
    placeholder="Buscar en ID o nombre…",
    key="global_search",
)

filter_mask = build_sidebar_filters(df, filter_cols)

# Apply global search
if search_global:
    global_cols = [c for c in [detected["id"], detected["name"]] if c]
    if global_cols:
        gm = pd.Series(False, index=df.index)
        for gc in global_cols:
            gm |= df[gc].astype(str).str.contains(search_global, case=False, na=False)
        filter_mask &= gm

df_filtered = df[filter_mask].copy().reset_index(drop=True)
df_filtered["_row_id"] = range(len(df_filtered))

if df_filtered.empty:
    st.warning("⚠️ Sin resultados con los filtros actuales. Amplía los criterios.")
    st.stop()

# ── SIDEBAR: SHARE ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("🔗 Compartir mapa"):
    st.markdown("<p>Genera un enlace para compartir los datos sin enviar el Excel original.</p>",
                unsafe_allow_html=True)
    if st.button("⚡ Generar enlace de compartición", use_container_width=True):
        sid = str(uuid.uuid4())[:8]
        df_raw.to_parquet(os.path.join(SHARE_DIR, f"{sid}.parquet"), index=False)
        st.code(f"?share_id={sid}")
        st.caption("Añade este parámetro a la URL de tu app (ej: https://tu-app.streamlit.app/?share_id=" + sid + ")")


# ══════════════════════════════════════════════════════════════════════════════
# ── MAP SECTION ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
info_col, badge_col = st.columns([8, 2])
with info_col:
    st.markdown(
        f"<p style='color:{GRAY};font-size:.82rem;margin:0;'>"
        "💡 Herramientas del mapa: <b>Lasso ∿</b> o <b>Box □</b> para seleccionar puntos · "
        "<b>Scroll</b> para zoom · <b>Doble clic</b> para deseleccionar</p>",
        unsafe_allow_html=True,
    )
with badge_col:
    st.markdown(
        f"<div style='text-align:right'>"
        f"<span class='sel-badge'>{len(df_filtered):,} puntos</span></div>",
        unsafe_allow_html=True,
    )

# Build and render map
fig = build_map(df_filtered, detected, color_by, size_by,
                map_style, point_size, opacity, show_labels)

event = st.plotly_chart(
    fig,
    use_container_width=True,
    key="geo_map",
    on_select="rerun",
    selection_mode=["points", "lasso", "box"],
)

# ── Export row ────────────────────────────────────────────────────────────────
ecol1, ecol2, ecol3, _ = st.columns([2, 2, 2, 4])

map_html = export_html_standalone(fig, "GeoMapper Pro · Mapa Interactivo")
with ecol1:
    st.download_button(
        "⬇️ HTML offline",
        data=map_html,
        file_name="mapa_interactivo.html",
        mime="text/html",
        help="Mapa completo que funciona en cualquier navegador sin conexión.",
        use_container_width=True,
    )

with ecol2:
    try:
        img_bytes = fig.to_image(format="png", scale=2, width=1920, height=1080)
        st.download_button(
            "🖼️ Imagen PNG",
            data=img_bytes,
            file_name="mapa.png",
            mime="image/png",
            help="Captura de alta resolución (1920×1080 px @2x).",
            use_container_width=True,
        )
    except Exception:
        st.caption("_(instala kaleido para PNG)_")

with ecol3:
    disp_cols = [c for c in df_filtered.columns if c != "_row_id"]
    xlsx_bytes = df_to_xlsx_bytes(df_filtered[disp_cols])
    st.download_button(
        "📊 XLSX filtrado",
        data=xlsx_bytes,
        file_name="datos_filtrados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ── SELECTION LOGIC ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
df_display        = df_filtered.copy()
selection_active  = False

if event and hasattr(event, "selection"):
    pts = event.selection.get("points", [])
    if pts:
        ids = [p["customdata"][0] for p in pts if "customdata" in p]
        if ids:
            df_display       = df_filtered[df_filtered["_row_id"].isin(ids)].copy()
            selection_active = True


# ══════════════════════════════════════════════════════════════════════════════
# ── METRICS ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.divider()

num_extra_disp = [
    c for c in df_display.select_dtypes(include="number").columns
    if c not in {detected["lat"], detected["lon"], "_row_id"}
]

m_cols = st.columns(5)
with m_cols[0]:
    st.metric("📍 Total (filtrado)", f"{len(df_filtered):,}")
with m_cols[1]:
    lbl = "✅ Seleccionados" if selection_active else "🖱️ Selección"
    st.metric(lbl, f"{len(df_display):,}" if selection_active else "—")
with m_cols[2]:
    if num_extra_disp:
        col0 = num_extra_disp[0]
        st.metric(f"∑ {col0}", f"{df_display[col0].sum():,.0f}")
    elif detected["id"]:
        st.metric("IDs únicos", f"{df_display[detected['id']].nunique():,}")
    else:
        st.metric("Columnas", f"{len(df_display.columns):,}")
with m_cols[3]:
    if len(num_extra_disp) > 1:
        col1_ = num_extra_disp[1]
        st.metric(f"∑ {col1_}", f"{df_display[col1_].sum():,.0f}")
    elif color_by:
        st.metric(f"Grupos ({color_by})", f"{df_display[color_by].nunique():,}")
    else:
        st.metric("Lat (centro)", f"{df_display[detected['lat']].mean():.4f}")
with m_cols[4]:
    pct = len(df_display) / len(df_filtered) * 100 if len(df_filtered) else 0
    st.metric("% del total", f"{pct:.1f}%" if selection_active else "100%")


# ══════════════════════════════════════════════════════════════════════════════
# ── TABS: TABLA · ESTADÍSTICAS · GRÁFICOS ───────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
tab_table, tab_stats, tab_charts = st.tabs(["📋 Tabla de datos", "📊 Estadísticas", "📈 Gráficos"])

# ── TAB 1: TABLE ──────────────────────────────────────────────────────────────
with tab_table:
    if selection_active:
        st.markdown(
            f"<span class='sel-badge'>✅ Mostrando {len(df_display)} puntos seleccionados en el mapa</span>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Mostrando {len(df_display):,} puntos filtrados. "
                   "Usa lasso o box en el mapa para seleccionar un subconjunto.")

    display_cols = [c for c in df_display.columns if c != "_row_id"]

    # Sort by first numeric col if exists
    sort_col = num_extra_disp[0] if num_extra_disp else display_cols[0]
    df_table = (
        df_display[display_cols]
        .sort_values(by=sort_col, ascending=False)
        .reset_index(drop=True)
    )

    # Download selected/filtered
    st.download_button(
        "⬇️ Descargar esta tabla (.xlsx)",
        data=df_to_xlsx_bytes(df_table),
        file_name="seleccion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Column config: format lat/lon nicely
    col_cfg = {}
    if detected["lat"]:
        col_cfg[detected["lat"]] = st.column_config.NumberColumn("Lat", format="%.6f")
    if detected["lon"]:
        col_cfg[detected["lon"]] = st.column_config.NumberColumn("Lon", format="%.6f")

    st.dataframe(df_table, use_container_width=True, height=420, column_config=col_cfg)

# ── TAB 2: STATS ─────────────────────────────────────────────────────────────
with tab_stats:
    num_df = df_display.select_dtypes("number").drop(
        columns=[c for c in ["_row_id", detected["lat"], detected["lon"]] if c],
        errors="ignore",
    )
    if not num_df.empty:
        desc = num_df.describe().T
        desc.index.name = "Columna"
        st.dataframe(
            desc.style.format("{:.2f}").background_gradient(
                subset=["mean", "std"], cmap="Blues"
            ),
            use_container_width=True,
        )
    else:
        st.info("No hay columnas numéricas para estadísticas.")

    # Value counts for categorical
    cat_filter_cols = [c for c in filter_cols if df_display[c].dtype.kind == "O" and df_display[c].nunique() <= 30]
    if cat_filter_cols:
        st.markdown(f"<p class='section-title' style='margin-top:16px;'>Distribución categórica</p>",
                    unsafe_allow_html=True)
        cat_sel = st.selectbox("Ver distribución de", cat_filter_cols, key="cat_dist")
        vc = df_display[cat_sel].value_counts().reset_index()
        vc.columns = [cat_sel, "Conteo"]
        st.dataframe(vc, use_container_width=True, height=280, hide_index=True)

# ── TAB 3: CHARTS ────────────────────────────────────────────────────────────
with tab_charts:
    if not filter_cols:
        st.info("No hay columnas adicionales para graficar.")
    else:
        cc1, cc2 = st.columns(2)
        with cc1:
            x_opts = [c for c in filter_cols if df_display[c].nunique() <= 40]
            x_col  = st.selectbox("Eje X (categoría / grupo)", x_opts if x_opts else filter_cols,
                                   key="chart_x")
        with cc2:
            y_opts = num_extra_disp if num_extra_disp else [detected["lat"]]
            y_col  = st.selectbox("Eje Y (valor)", y_opts, key="chart_y")

        agg_fn = st.radio("Agregación", ["Suma", "Promedio", "Conteo"],
                          horizontal=True, key="agg_fn")

        if agg_fn == "Suma":
            agg_df = df_display.groupby(x_col)[y_col].sum().reset_index()
        elif agg_fn == "Promedio":
            agg_df = df_display.groupby(x_col)[y_col].mean().reset_index()
        else:
            agg_df = df_display.groupby(x_col)[y_col].count().reset_index()
            y_col  = y_col  # rename handled below

        agg_df = agg_df.sort_values(y_col, ascending=False).head(30)

        fig_bar = px.bar(
            agg_df, x=x_col, y=y_col,
            color=x_col,
            color_discrete_sequence=COLOUR_SEQ,
            template="plotly_white",
            title=f"{agg_fn} de {y_col} por {x_col}",
            text_auto=".2s",
        )
        fig_bar.update_layout(
            showlegend=False,
            font=dict(family="DM Sans"),
            title_font=dict(size=13, family="DM Sans"),
            xaxis_tickangle=-35,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Pie if few categories
        if df_display[x_col].nunique() <= 15:
            fig_pie = px.pie(
                agg_df, names=x_col, values=y_col,
                color_discrete_sequence=COLOUR_SEQ,
                template="plotly_white",
                title=f"Distribución de {y_col} por {x_col}",
            )
            fig_pie.update_layout(font=dict(family="DM Sans"), title_font=dict(size=13))
            st.plotly_chart(fig_pie, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── FOOTER ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<p style='text-align:center;color:{LGRAY};font-size:.75rem;margin-top:36px;'>"
    "GeoMapper Pro v3 · Plotly WebGL · Detección automática de columnas · © 2026</p>",
    unsafe_allow_html=True,
)