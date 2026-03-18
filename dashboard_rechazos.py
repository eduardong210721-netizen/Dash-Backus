import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ─────────────────────── STYLES & PALETTE ───────────────────────
st.set_page_config(page_title="Control de Rechazos - Backus", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background: linear-gradient(135deg, #0a0e17 0%, #0f1729 50%, #0a0e17 100%);
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
    font-size: 0.85rem;
}

.main-title {
    text-align: center;
    padding: 1rem 0;
    margin-bottom: 1rem;
    border-bottom: 2px solid #FDB913;
}
.main-title h1 {
    font-size: 1.7rem;
    font-weight: 800;
    color: #FDB913;
    margin: 0;
}
.main-title p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-top: 0.3rem;
}

.kpi-card {
    background: linear-gradient(145deg, #1a2332, #1f2b3d);
    border: 1px solid #333333;
    border-radius: 16px;
    padding: 1.2rem;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(253, 185, 19, 0.15);
    border-color: #FDB913;
}
.kpi-value {
    font-size: 1.7rem;
    font-weight: 800;
}
.kpi-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.3rem;
}

.chart-container {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1rem;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# Colors specified by the user
THEME_COLORS = [
    "#FDB913", # Color 1 (Principal)
    "#E5B611", # Color 7 (Mostaza corporativo)
    "#FFD700", # Color 3 (Dorado brillante)
    "#FBC02D", # Color 5 (Amarillo ámbar)
    "#D4AF37", # Color 8 (Dorado metálico)
    "#B8860B", # Color 4 (Dorado oscuro/ocre)
    "#333333", # Color 6 (Gris carbón)
    "#000000"  # Color 2 (Negro puro)
]

KPI_COLORS = {
    "Negativo": "#C62828",
    "Positivo": "#2E7D32",
    "Neutro": "#FBC02D"
}

DIVERGENT_COLORS = [
    [0.0, "#FFFDE7"], # Mínimo
    [0.5, "#FFEB3B"], # Centro
    [1.0, "#F57F17"]  # Máximo
]

# ─────────────────────── DATA LOADING ───────────────────────
@st.cache_data
def load_data():
    file_path = "RECHAZOS/DATA2.xlsx"
    if not os.path.exists(file_path):
        return None
    df = pd.read_excel(file_path)
    
    # Handle column stripping
    df.columns = df.columns.astype(str).str.strip()
    
    # Ensure 'Ruta' and 'Motivo No Entregado', 'Cajas' exist
    if 'Cajas' not in df.columns:
        df['Cajas'] = 1 # Fallback if missing
        
    # Strictly round Cajas to whole integers
    df['Cajas'] = pd.to_numeric(df['Cajas'], errors='coerce').fillna(0).round(0).astype(int)
    
    # Safe float conversion for geocoordinates
    if 'LATITUD' in df.columns:
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    if 'LONGITUD' in df.columns:
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        
    # Standardize empty strings
    if 'Ruta' in df.columns:
        df['Ruta'] = df['Ruta'].fillna('SIN RUTA').astype(str)
        
    return df

# ─────────────────────── MAIN APP ───────────────────────
def main():
    st.markdown('''
    <div class="main-title">
        <h1>Dashboard de Rechazos y No Entregas</h1>
        <p>Análisis de Impacto y Causas por Camión (BK)</p>
    </div>
    ''', unsafe_allow_html=True)

    df = load_data()
    
    if df is None:
        st.error("❌ No se encontró el archivo `RECHAZOS/DATA2.xlsx` en el directorio.")
        return
        
    if df.empty:
        st.warning("⚠️ El archivo de datos está vacío.")
        return

    # ── FILTERS ──
    st.sidebar.markdown("### 🎛️ Segmentadores")
    
    col_fecha = next((c for c in df.columns if 'FECHA' in c.upper()), None)
    col_unidad = next((c for c in df.columns if 'UNIDAD' in c.upper()), None)
    col_empresa = next((c for c in df.columns if 'EMPRESA' in c.upper()), None)
    col_ruta = 'Ruta' if 'Ruta' in df.columns else None
    
    df_filtered = df.copy()
    
    if col_fecha:
        fechas = st.sidebar.multiselect("📅 Fecha", options=sorted(df_filtered[col_fecha].dropna().astype(str).unique()))
        if fechas:
            df_filtered = df_filtered[df_filtered[col_fecha].astype(str).isin(fechas)]
            
    if col_unidad:
        unidades = st.sidebar.multiselect("🏢 Unidad de Negocio", options=sorted(df_filtered[col_unidad].dropna().astype(str).unique()))
        if unidades:
            df_filtered = df_filtered[df_filtered[col_unidad].astype(str).isin(unidades)]
            
    if col_empresa:
        empresas = st.sidebar.multiselect("🚛 Empresario", options=sorted(df_filtered[col_empresa].dropna().astype(str).unique()))
        if empresas:
            df_filtered = df_filtered[df_filtered[col_empresa].astype(str).isin(empresas)]
            
    if col_ruta:
        rutas = st.sidebar.multiselect("🚚 BK (Ruta)", options=sorted(df_filtered[col_ruta].dropna().astype(str).unique()))
        if rutas:
            df_filtered = df_filtered[df_filtered[col_ruta].astype(str).isin(rutas)]
            
    if 'Cliente' in df.columns:
        clientes = st.sidebar.multiselect("👤 Código Cliente", options=sorted(df_filtered['Cliente'].dropna().astype(str).unique()))
        if clientes:
            df_filtered = df_filtered[df_filtered['Cliente'].astype(str).isin(clientes)]
            
    if 'Motivo No Entregado' in df.columns:
        motivos = st.sidebar.multiselect("⚠️ Motivo de Rechazo", options=sorted(df_filtered['Motivo No Entregado'].dropna().astype(str).unique()))
        if motivos:
            df_filtered = df_filtered[df_filtered['Motivo No Entregado'].astype(str).isin(motivos)]
            
    df = df_filtered

    if df.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        return

    # Basic metrics
    total_rechazos = len(df)
    total_cajas = df['Cajas'].sum()
    
    ruta_critica = "N/A"
    motivo_principal = "N/A"
    
    if 'Ruta' in df.columns and not df.empty:
        top_ruta = df.groupby('Ruta')['Cajas'].sum().idxmax()
        ruta_critica = str(top_ruta)
        
    if 'Motivo No Entregado' in df.columns and not df.empty:
        top_motivo = df.groupby('Motivo No Entregado')['Cajas'].sum().idxmax()
        motivo_principal = str(top_motivo)
        
    peor_empresario = "N/A"
    if col_empresa and not df.empty:
        top_emp = df.groupby(col_empresa)['Cajas'].sum().idxmax()
        peor_empresario = str(top_emp)

    # ── KPI ROW ──
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {KPI_COLORS['Negativo']}">{total_rechazos:,}</div>
            <div class="kpi-label">Total Órdenes Fallidas</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col2:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {KPI_COLORS['Neutro']}">{total_cajas:,.0f}</div>
            <div class="kpi-label">Total Cajas Impactadas</div>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[0]}">{ruta_critica}</div>
            <div class="kpi-label">BK Más Crítico</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col4:
        emp_corto = peor_empresario
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[4]}; font-size: 0.95rem;">{emp_corto}</div>
            <div class="kpi-label">Empresa con Más Rechazos</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col5:
        motivo_corto = motivo_principal[:20] + "..." if len(motivo_principal) > 20 else motivo_principal
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[1]}; font-size: 1.3rem; margin-top: 10px;">{motivo_corto}</div>
            <div class="kpi-label">Motivo Principal</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ──
    col_c1, col_c2 = st.columns([2, 1.5])
    
    with col_c1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Top 15 BKs con Mayor Impacto (Cajas)")
        if 'Ruta' in df.columns:
            df_ruta = df.groupby('Ruta')['Cajas'].sum().reset_index().sort_values('Cajas', ascending=False).head(15)
            fig_ruta = px.bar(
                df_ruta, 
                x='Ruta', y='Cajas', 
                color='Cajas',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS],
                text_auto='.0f'
            )
            fig_ruta.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=20, r=20, t=10, b=20),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_ruta, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Distribución de Motivos (%)")
        if 'Motivo No Entregado' in df.columns:
            df_motivo = df.groupby('Motivo No Entregado')['Cajas'].sum().reset_index()
            fig_pie = px.pie(
                df_motivo, 
                names='Motivo No Entregado', values='Cajas', 
                color_discrete_sequence=THEME_COLORS,
                hole=0.4
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    
    col_c3, col_c4 = st.columns([1, 1])
    
    with col_c3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Top 10 BKs con Más Eventos (Rechazos)")
        if 'Ruta' in df.columns:
            df_eventos = df.groupby('Ruta').size().reset_index(name='Eventos').sort_values('Eventos', ascending=True).tail(10)
            fig_eventos = px.bar(
                df_eventos, 
                y='Ruta', x='Eventos', 
                orientation='h',
                color_discrete_sequence=[THEME_COLORS[2]],
                text_auto=True
            )
            fig_eventos.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=20, r=20, t=10, b=20)
            )
            st.plotly_chart(fig_eventos, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c4:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        col_to_graph = col_empresa if col_empresa else ('Responsable' if 'Responsable' in df.columns else None)
        if col_to_graph and 'Ruta' in df.columns:
            st.markdown(f"#### Relación {col_to_graph} y BK")
            df_resp = df.groupby([col_to_graph, 'Ruta'])['Cajas'].sum().reset_index()
            fig_tree = px.treemap(
                df_resp, 
                path=[px.Constant("Empresas"), col_to_graph, 'Ruta'], 
                values='Cajas',
                color='Cajas',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS]
            )
            fig_tree.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_tree, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # ── EMPRESARIO DEEP DIVE ──
    if col_empresa:
        st.markdown("### 🏢 Análisis Resumen de Empresa de Transporte")
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Matriz de Motivos por Empresario (Cajas Impactadas)")
        if 'Motivo No Entregado' in df.columns:
            pivot_emp = pd.pivot_table(
                df, 
                values='Cajas', 
                index=col_empresa, 
                columns='Motivo No Entregado', 
                aggfunc='sum', 
                fill_value=0,
                margins=True,
                margins_name='TOTAL GENERAL'
            )
            # Apply corporate yellow/gold background gradient highlighting where impact is highest
            styled_table = pivot_emp.style.format("{:.0f}").background_gradient(cmap="YlOrBr", axis=None, vmin=0)
            st.dataframe(styled_table, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── GEOSPATIAL MAP ──
    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        st.markdown("### 🗺️ Mapa de Calor y Zonas Críticas")
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        # Filter rows with valid coordinates
        df_map = df.dropna(subset=['LATITUD', 'LONGITUD', 'Ruta', 'Cajas'])
        df_map = df_map[df_map['Cajas'] > 0]
        
        if not df_map.empty:
            hover_dict = {"LATITUD": False, "LONGITUD": False, "Cajas": True}
            if 'Nombre' in df_map.columns: hover_dict["Nombre"] = True
            if 'Motivo No Entregado' in df_map.columns: hover_dict["Motivo No Entregado"] = True
            if 'UNIDAD DE NEGOCIO FINAL' in df_map.columns: hover_dict["UNIDAD DE NEGOCIO FINAL"] = True
            
            if 'Cliente' in df_map.columns:
                hover_name = 'Cliente'
            else:
                hover_name = 'Ruta'

            fig_map = px.scatter_mapbox(
                df_map, 
                lat="LATITUD", 
                lon="LONGITUD",     
                color="Ruta", 
                size="Cajas",
                hover_name=hover_name, 
                hover_data=hover_dict,
                color_discrete_sequence=THEME_COLORS * 5, # repeating to avoid running out of colors
                size_max=20, 
                zoom=10,
                mapbox_style="carto-darkmatter"
            )
            fig_map.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("No hay coordenadas válidas para graficar en el mapa con los filtros actuales.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── CLIENT TRENDS ──
    st.markdown("### 🎯 Análisis de Tendencias por Cliente")
    col_t1, col_t2 = st.columns([1, 1.5])
    
    with col_t1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Top 10 Clientes más Críticos (Cajas)")
        
        # Safe merge for display
        if 'Cliente' in df.columns and 'Nombre' in df.columns:
            df['Cliente_Disp'] = df['Cliente'].astype(str) + " - " + df['Nombre'].astype(str).str[:20]
        elif 'Cliente' in df.columns:
            df['Cliente_Disp'] = df['Cliente'].astype(str)
        else:
            df['Cliente_Disp'] = None
            
        if 'Cliente_Disp' in df.columns and df['Cliente_Disp'].notnull().any():
            df_cli = df.groupby('Cliente_Disp')['Cajas'].sum().reset_index().sort_values('Cajas', ascending=True).tail(10)
            fig_cli = px.bar(
                df_cli, 
                y='Cliente_Disp', x='Cajas', 
                orientation='h',
                color='Cajas',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS],
                text_auto='.0f'
            )
            fig_cli.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0', size=10),
                margin=dict(l=10, r=20, t=10, b=20),
                coloraxis_showscale=False
            )
            fig_cli.update_yaxes(title_text="")
            st.plotly_chart(fig_cli, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_t2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Tendencia de Motivos por Cliente")
        if 'Motivo No Entregado' in df.columns and 'Cliente_Disp' in df.columns and df['Cliente_Disp'].notnull().any():
            top_clientes = df_cli['Cliente_Disp'].tolist()
            df_cli_motivo = df.groupby(['Cliente_Disp', 'Motivo No Entregado'])['Cajas'].sum().reset_index()
            df_cli_motivo = df_cli_motivo[df_cli_motivo['Cliente_Disp'].isin(top_clientes)]
            
            fig_cli_mot = px.bar(
                df_cli_motivo,
                x='Cajas', y='Cliente_Disp',
                orientation='h',
                color='Motivo No Entregado',
                color_discrete_sequence=THEME_COLORS,
                category_orders={'Cliente_Disp': top_clientes}
            )
            fig_cli_mot.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0', size=10),
                margin=dict(l=10, r=10, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
            )
            fig_cli_mot.update_yaxes(title_text="")
            st.plotly_chart(fig_cli_mot, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── DATA TABLE ──
    st.markdown("### 📋 Detalle de Rechazos")
    st.dataframe(
        df.head(200), 
        use_container_width=True,
        hide_index=True
    )

if __name__ == "__main__":
    main()
