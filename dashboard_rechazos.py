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
    border-bottom: 2px solid #745CDB;
}
.main-title h1 {
    font-size: 1.7rem;
    font-weight: 800;
    color: #9CA5E1;
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
    box-shadow: 0 8px 25px rgba(116, 92, 219, 0.25);
    border-color: #745CDB;
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
    "#745CDB", # Color 2 (Morado principal vibrante)
    "#5C95DB", # Color 1 (Azul claro/celeste)
    "#9E5CDB", # Color 4 (Morado brillante)
    "#5C6DDB", # Color 3 (Azul rey/índigo)
    "#9CA5E1"  # Color 5 (Lila pastel/grisáceo)
]

KPI_COLORS = {
    "Negativo": "#C62828",
    "Positivo": "#2E7D32",
    "Neutro": "#9CA5E1"
}

DIVERGENT_COLORS = [
    [0.0, "#eef2fb"], # Mínimo (Azul muy claro)
    [0.5, "#9CA5E1"], # Centro (Lila)
    [1.0, "#745CDB"]  # Máximo (Morado fuerte)
]

# ─────────────────────── DATA LOADING ───────────────────────
def load_data():
    file_path = "RECHAZOS/DATA3.xlsx"
    if not os.path.exists(file_path):
        return None
    df = pd.read_excel(file_path, sheet_name="DATA")
    
    # Handle column stripping
    df.columns = df.columns.astype(str).str.strip()
    
    # Strictly numeric tracking for new columns
    for col in ['CCreado', 'CRechazado', 'CRechazadoParcial', 'CRechazadoTotal']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Override CRechazado with the real sum of Parcial + Total
    if 'CRechazadoParcial' in df.columns and 'CRechazadoTotal' in df.columns:
        df['CRechazado'] = df['CRechazadoParcial'] + df['CRechazadoTotal']
            
    # Keep legacy 'Cajas' mapping
    if 'CRechazado' in df.columns:
        df['Cajas'] = df['CRechazado']
    elif 'Cajas' in df.columns:
        df['Cajas'] = pd.to_numeric(df['Cajas'], errors='coerce').fillna(0).round(0).astype(int)
    else:
        df['Cajas'] = 0
    
    # Capacidad Camión as categorical string
    if 'Capacidad Camión' in df.columns:
        df['Capacidad Camión'] = df['Capacidad Camión'].fillna('Sin Info').astype(str).str.replace('.0', '', regex=False)
    
    # Safe float conversion for geocoordinates
    if 'Latitud' in df.columns:
        df['LATITUD'] = pd.to_numeric(df['Latitud'].astype(str).str.replace(',', '.'), errors='coerce')
    elif 'LATITUD' in df.columns:
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        
    if 'Longitud' in df.columns:
        df['LONGITUD'] = pd.to_numeric(df['Longitud'].astype(str).str.replace(',', '.'), errors='coerce')
    elif 'LONGITUD' in df.columns:
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        
    # Standardize Ruta (BK) column — column AB in the Excel
    if 'Ruta' in df.columns:
        df['Ruta'] = df['Ruta'].fillna('SIN RUTA').astype(str)
    # Responsable (AD) is a separate dimension (Sales/Customer/Logistic)
    if 'Responsable' in df.columns:
        df['Responsable'] = df['Responsable'].fillna('Sin Responsable').astype(str)
        
    # Ensure Motivo Rechazo is string
    if 'Motivo Rechazo' in df.columns:
        df['Motivo Rechazo'] = df['Motivo Rechazo'].fillna('Sin Motivo').astype(str)
        
    # Remove 'Pedido No Rechazado' contamination from dimensions
    for col in ['Ruta', 'Responsable', 'Empresario', 'Capacidad Camión', 'Distrito', 'Tipo de Rechazo']:
        if col in df.columns:
            df[col] = df[col].replace('Pedido No Rechazado', pd.NA)
            
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
        st.error("❌ No se encontró el archivo `RECHAZOS/DATA3.xlsx` en el directorio.")
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
    col_responsable = 'Responsable' if 'Responsable' in df.columns else None
    
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
            
    if col_responsable:
        responsables = st.sidebar.multiselect("👤 Responsable", options=sorted(df_filtered[col_responsable].dropna().astype(str).unique()))
        if responsables:
            df_filtered = df_filtered[df_filtered[col_responsable].astype(str).isin(responsables)]
            
    col_capacidad = 'Capacidad Camión' if 'Capacidad Camión' in df.columns else None
    col_distrito = 'Distrito' if 'Distrito' in df.columns else None
    col_tipo_rechazo = 'Tipo de Rechazo' if 'Tipo de Rechazo' in df.columns else None
    
    if 'Cliente' in df.columns:
        clientes = st.sidebar.multiselect("👤 Código Cliente", options=sorted(df_filtered['Cliente'].dropna().astype(str).unique()))
        if clientes:
            df_filtered = df_filtered[df_filtered['Cliente'].astype(str).isin(clientes)]
            
    if 'Motivo No Entregado' in df.columns:
        motivos = st.sidebar.multiselect("⚠️ Motivo de Rechazo", options=sorted(df_filtered['Motivo No Entregado'].dropna().astype(str).unique()))
        if motivos:
            df_filtered = df_filtered[df_filtered['Motivo No Entregado'].astype(str).isin(motivos)]
            
    if col_capacidad:
        capacidades = st.sidebar.multiselect("⚖️ Capacidad Camión", options=sorted(df_filtered[col_capacidad].dropna().astype(str).unique()))
        if capacidades:
            df_filtered = df_filtered[df_filtered[col_capacidad].astype(str).isin(capacidades)]
            
    if col_distrito:
        distritos = st.sidebar.multiselect("🏙️ Distrito", options=sorted(df_filtered[col_distrito].dropna().astype(str).unique()))
        if distritos:
            df_filtered = df_filtered[df_filtered[col_distrito].astype(str).isin(distritos)]
            
    if col_tipo_rechazo:
        tipos_rechazo = st.sidebar.multiselect("❌ Tipo de Rechazo", options=sorted(df_filtered[col_tipo_rechazo].dropna().astype(str).unique()))
        if tipos_rechazo:
            df_filtered = df_filtered[df_filtered[col_tipo_rechazo].astype(str).isin(tipos_rechazo)]
            
    df = df_filtered

    if df.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        return

    # ── METRIC CALCULATIONS ──
    total_c_creado = df['CCreado'].sum() if 'CCreado' in df.columns else len(df)
    total_c_rechazado = df['CRechazado'].sum() if 'CRechazado' in df.columns else 0
    pct_rechazo = (total_c_rechazado / total_c_creado * 100) if total_c_creado > 0 else 0
    
    # Peor BK
    ruta_critica = "N/A"
    ruta_critica_val = ""
    df_rechazos = df[df['CRechazado'] > 0]
    if 'Ruta' in df_rechazos.columns and not df_rechazos.empty:
        df_rutas = df_rechazos.groupby('Ruta').agg({'CRechazado': 'sum'})
        if not df_rutas.empty:
            ruta_critica = str(df_rutas['CRechazado'].idxmax())
            ruta_critica_val = f" ({df_rutas['CRechazado'].max():.0f})"
            
    # Peor Empresario
    emp_corto = "N/A"
    emp_val = ""
    if col_empresa and not df_rechazos.empty:
        df_emp = df_rechazos.groupby(col_empresa).agg({'CRechazado': 'sum'})
        if not df_emp.empty:
            emp_corto = str(df_emp['CRechazado'].idxmax())
            emp_val = f" ({df_emp['CRechazado'].max():.0f})"

    # ── KPI ROW ──
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[1]}">{total_c_creado:,.0f}</div>
            <div class="kpi-label">Total Pedidos</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col2:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {KPI_COLORS['Negativo']}">{total_c_rechazado:,.0f}</div>
            <div class="kpi-label">Pedidos Rechazados</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col3:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[0]}">{pct_rechazo:.1f}%</div>
            <div class="kpi-label">% Rechazo</div>
        </div>
        ''', unsafe_allow_html=True)

    with col4:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[2]}; font-size: 1.05rem; margin-top: 8px;">{ruta_critica}{ruta_critica_val}</div>
            <div class="kpi-label">BK Más Crítico</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with col5:
        st.markdown(f'''
        <div class="kpi-card">
            <div class="kpi-value" style="color: {THEME_COLORS[3]}; font-size: 1.05rem; margin-top: 8px;">{emp_corto}{emp_val}</div>
            <div class="kpi-label">Peor Empresa</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ──
    col_c1, col_c2 = st.columns([2, 1.5])
    
    with col_c1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Top 10 BKs (Total Rechazos)")
        # Use df_rechazos to exclude 'Pedido No Rechazado' blank rows
        df_rechazos = df_filtered[df_filtered['CRechazado'] > 0].copy()
        
        if 'Ruta' in df_rechazos.columns and 'CRechazado' in df_rechazos.columns:
            df_ruta = df_rechazos.groupby('Ruta').agg({'CRechazado': 'sum'})
            df_ruta = df_ruta[df_ruta['CRechazado'] > 0]
            df_ruta = df_ruta.reset_index().sort_values('CRechazado', ascending=False).head(10)
            
            fig_ruta = px.bar(
                df_ruta, 
                x='Ruta', y='CRechazado',
                color='CRechazado',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS],
                text_auto='.0f',
                category_orders={'Ruta': df_ruta.sort_values('CRechazado', ascending=False)['Ruta'].tolist()}
            )
            fig_ruta.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=20, r=20, t=10, b=20),
                coloraxis_showscale=False
            )
            fig_ruta.update_yaxes(title_text="Total Pedidos Rechazados")
            st.plotly_chart(fig_ruta, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Top 5 Motivos de Rechazo")
        df_rechazos = df_filtered[df_filtered['CRechazado'] > 0].copy()
        
        col_motivo = 'Motivo Rechazo' if 'Motivo Rechazo' in df_rechazos.columns else ('Responsable' if 'Responsable' in df_rechazos.columns else None)
        
        if 'Motivo Rechazo' not in df_rechazos.columns:
            st.warning("⚠️ Columna 'Motivo Rechazo' no encontrada. Mostrando por 'Responsable'.")
            
        if col_motivo and 'CRechazado' in df_rechazos.columns:
            df_motivo = df_rechazos.groupby(col_motivo)['CRechazado'].sum().reset_index()
            total_ped = total_c_creado if total_c_creado > 0 else 1
            df_motivo['% del Total'] = (df_motivo['CRechazado'] / total_ped * 100).round(2)
            df_motivo = df_motivo.sort_values('CRechazado', ascending=False)
            
            # Top 5 for pie
            df_top5 = df_motivo.head(5).copy()
            df_rest = df_motivo.iloc[5:].copy()
            
            fig_pie = px.pie(
                df_top5, 
                names=col_motivo, values='CRechazado', 
                color_discrete_sequence=THEME_COLORS,
                hole=0.45
            )
            fig_pie.update_traces(
                textinfo='label+value',
                textposition='outside',
                hovertemplate='%{label}<br>Rechazos: %{value:,.0f}<br>% del Total: %{customdata[0]:.2f}%',
                customdata=df_top5[['% del Total']].values
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0', size=10),
                margin=dict(l=5, r=5, t=5, b=5),
                showlegend=False,
                height=280
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Rest as table
            if not df_rest.empty:
                st.markdown("##### Otros Motivos")
                df_rest_disp = df_rest[[col_motivo, 'CRechazado', '% del Total']].rename(
                    columns={col_motivo: 'Motivo', 'CRechazado': 'Rechazos'}
                ).reset_index(drop=True)
                st.dataframe(df_rest_disp, use_container_width=True, hide_index=True, height=150)
        st.markdown('</div>', unsafe_allow_html=True)
        
    
    col_c3, col_c4 = st.columns([1, 1])
    
    with col_c3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Rechazo por Capacidad de Camión")
        df_rechazos = df_filtered[df_filtered['CRechazado'] > 0].copy()
        
        col_cap = 'Capacidad Camión' if 'Capacidad Camión' in df_rechazos.columns else None
        if col_cap and 'CRechazado' in df_rechazos.columns:
            df_cap = df_rechazos.groupby(col_cap).agg({'CRechazado': 'sum'})
            df_cap = df_cap[df_cap['CRechazado'] > 0]
            df_cap = df_cap.reset_index().sort_values('CRechazado', ascending=True)
                
            fig_cap = px.bar(
                df_cap, 
                y=col_cap, x='CRechazado',
                orientation='h',
                color='CRechazado',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS],
                text_auto='.0f'
            )
            fig_cap.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=20, r=20, t=10, b=20),
                coloraxis_showscale=False
            )
            fig_cap.update_xaxes(title_text="Total Pedidos Rechazados")
            fig_cap.update_yaxes(type='category')
            st.plotly_chart(fig_cap, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c4:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        df_rechazos = df_filtered[df_filtered['CRechazado'] > 0].copy()
        
        col_cap = 'Capacidad Camión' if 'Capacidad Camión' in df_rechazos.columns else None
        if col_empresa and col_cap and 'CRechazado' in df_rechazos.columns:
            st.markdown(f"#### Relación Empresario y Capacidad de Camión")
            df_resp = df_rechazos.groupby([col_empresa, col_cap])['CRechazado'].sum().reset_index()
            df_resp = df_resp[df_resp['CRechazado'] > 0]
            fig_tree = px.treemap(
                df_resp, 
                path=[px.Constant("Empresas"), col_empresa, col_cap], 
                values='CRechazado',
                color='CRechazado',
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
        st.markdown("#### Tipo de Rechazo por Empresario")
        df_rechazos = df_filtered[df_filtered['CRechazado'] > 0].copy()
        
        col_tr = 'Tipo de Rechazo' if 'Tipo de Rechazo' in df_rechazos.columns else ('Motivo Rechazo' if 'Motivo Rechazo' in df_rechazos.columns else None)
        if col_tr and 'CRechazado' in df_rechazos.columns:
            pivot_emp = pd.pivot_table(
                df_rechazos, 
                values='CRechazado', 
                index=col_empresa, 
                columns=col_tr, 
                aggfunc='sum', 
                fill_value=0,
                margins=True,
                margins_name='TOTAL GENERAL'
            )
            st.dataframe(pivot_emp.style.format("{:.0f}"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── GEOSPATIAL MAP ──
    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        st.markdown("### 🗺️ Mapa de Calor y Zonas Críticas")
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        # Filter rows with valid coordinates
        df_map = df.dropna(subset=['LATITUD', 'LONGITUD', 'CRechazado'])
        df_map = df_map[df_map['CRechazado'] > 0]
        
        if not df_map.empty:
            hover_dict = {"LATITUD": False, "LONGITUD": False, "CRechazado": True, "Cajas": False}
            if 'NombreCliente' in df_map.columns: hover_dict["NombreCliente"] = True
            elif 'Nombre' in df_map.columns: hover_dict["Nombre"] = True
            if 'Motivo No Entregado' in df_map.columns: hover_dict["Motivo No Entregado"] = True
            if 'Ruta' in df_map.columns: hover_dict["Ruta"] = True
            if 'Empresario' in df_map.columns: hover_dict["Empresario"] = True
            
            if 'Distrito' in df_map.columns: hover_dict["Distrito"] = True
            
            # Color by Distrito if available, otherwise Ruta
            color_col = 'Distrito' if 'Distrito' in df_map.columns else ('Ruta' if 'Ruta' in df_map.columns else None)
            hover_name = 'NombreCliente' if 'NombreCliente' in df_map.columns else ('CodigoCliente' if 'CodigoCliente' in df_map.columns else None)

            fig_map = px.scatter_mapbox(
                df_map, 
                lat="LATITUD", 
                lon="LONGITUD",     
                color=color_col, 
                size="CRechazado",
                hover_name=hover_name, 
                hover_data=hover_dict,
                color_discrete_sequence=THEME_COLORS * 5,
                size_max=8, 
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
        st.markdown("#### Top 10 Clientes con Mayor Impacto (% Relativo)")
        
        # Safe merge for display
        if 'Cliente' in df.columns and 'NombreCliente' in df.columns:
            df['Cliente_Disp'] = df['Cliente'].astype(str) + " - " + df['NombreCliente'].astype(str).str[:20]
        elif 'Cliente' in df.columns and 'Nombre' in df.columns:
            df['Cliente_Disp'] = df['Cliente'].astype(str) + " - " + df['Nombre'].astype(str).str[:20]
        elif 'Cliente' in df.columns:
            df['Cliente_Disp'] = df['Cliente'].astype(str)
        else:
            df['Cliente_Disp'] = None
            
        if 'Cliente_Disp' in df.columns and df['Cliente_Disp'].notnull().any() and 'CRechazado' in df.columns and 'CCreado' in df.columns:
            df_cli = df.groupby('Cliente_Disp').agg({'CCreado': 'sum', 'CRechazado': 'sum'})
            df_cli = df_cli[df_cli['CCreado'] > 0]
            df_cli['pct'] = df_cli['CRechazado'] / df_cli['CCreado'] * 100
            df_cli = df_cli.reset_index().sort_values('pct', ascending=True).tail(10)
            
            fig_cli = px.bar(
                df_cli, 
                y='Cliente_Disp', x='pct', 
                orientation='h',
                color='pct',
                color_continuous_scale=[c[1] for c in DIVERGENT_COLORS],
                text_auto='.1f'
            )
            fig_cli.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0', size=10),
                margin=dict(l=10, r=20, t=10, b=20),
                coloraxis_showscale=False
            )
            fig_cli.update_yaxes(title_text="")
            fig_cli.update_xaxes(title_text="% Rechazado")
            st.plotly_chart(fig_cli, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_t2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Tendencia de Motivos por Cliente")
        if 'Motivo No Entregado' in df.columns and 'Cliente_Disp' in df.columns and df['Cliente_Disp'].notnull().any():
            top_clientes = df_cli['Cliente_Disp'].tolist()
            df_cli_motivo = df.groupby(['Cliente_Disp', 'Motivo No Entregado'])['CRechazado'].sum().reset_index()
            df_cli_motivo = df_cli_motivo[df_cli_motivo['Cliente_Disp'].isin(top_clientes)]
            
            fig_cli_mot = px.bar(
                df_cli_motivo,
                x='CRechazado', y='Cliente_Disp',
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
            fig_cli_mot.update_xaxes(title_text="Total Rechazado")
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
