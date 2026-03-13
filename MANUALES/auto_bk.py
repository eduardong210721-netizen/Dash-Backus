import streamlit as st
import pandas as pd
import numpy as np
import math
import random
import io

# ─────────────────────── CONFIG ───────────────────────
st.set_page_config(page_title="Automatizador BK - Backus", page_icon="🚚", layout="wide")

# Capacity mapping: cajas → palets
CAPACITY_PALLETS = {
    1008: 12,
    672: 8,
    360: 6,
    200: 2.5,
    105: 1,
    0: 0,
}

MAX_TRIPS = 2

# Special clients: client name substring → forced BK
SPECIAL_CLIENTS = {
    "Mishkt": "BK3766",
    "cencosud": "BK3723",
    "dexcim": "BK3775",
}

# Priority order: prefer bigger trucks first
CAPACITY_PRIORITY = [1008, 672, 360, 200, 105]

# Expected columns for validation
TRUCK_REQUIRED_COLS = ["RUTA", "ZONAS", "Capac.", "Status"]
ORDER_REQUIRED_COLS = ["Solic#", "Nombre 1", "ST", "Prepago", "Latitud", "Longitud", "Distrito", "ZV", "Doc#venta", "Suma de Cantidad de pedido", "Suma de Palets"]


# ─────────────────────── STYLES ───────────────────────
def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0a0e17 0%, #0f1729 50%, #0a0e17 100%);
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid #f59e0b;
    }
    .main-title h1 {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .main-title p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }

    .kpi-card {
        background: linear-gradient(145deg, #1a2332, #1f2b3d);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(245, 158, 11, 0.15);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #f59e0b;
    }
    .kpi-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
    }

    .bk-card {
        background: linear-gradient(145deg, #1a2332, #1c2a3a);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .bk-card:hover {
        border-color: #f59e0b;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.1);
    }
    .bk-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid #1e293b;
    }
    .bk-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f59e0b;
    }
    .bk-badges {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    .bk-badge {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-cap {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .badge-trips {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-zone {
        background: rgba(139, 92, 246, 0.15);
        color: #8b5cf6;
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    .bk-stats {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.3rem;
    }
    .bk-stats-left {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    .progress-bar-outer {
        background: #0a0e17;
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
        margin-top: 0.5rem;
    }
    .progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }

    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f59e0b;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    .stButton > button {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        transform: scale(1.03) !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35) !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1321 0%, #111827 100%);
        border-right: 1px solid #1e293b;
    }

    .special-tag {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 700;
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.4);
        margin-left: 0.4rem;
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #1a2332, #1f2b3d) !important;
        color: #f1f5f9 !important;
        font-weight: 600 !important;
        border: 1px solid #f59e0b !important;
        border-radius: 12px !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important;
        color: #000 !important;
    }

    .upload-zone {
        background: linear-gradient(145deg, #1a2332, #1f2b3d);
        border: 2px dashed #f59e0b;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .upload-zone h3 {
        color: #f59e0b;
        margin-bottom: 0.5rem;
    }
    .upload-zone p {
        color: #94a3b8;
        font-size: 0.85rem;
    }

    .upload-success {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        padding: 0.8rem 1.2rem;
        color: #10b981;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .condition-card {
        background: linear-gradient(145deg, #1a2332, #1c2a3a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────── DATA LOADING ───────────────────────
def load_uploaded_data(uploaded_file, required_cols, file_label):
    """Load data from an uploaded Excel file, auto-detecting the correct sheet."""
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheets = xls.sheet_names

        best_sheet = None
        best_match = 0

        for sheet_name in sheets:
            try:
                df_test = pd.read_excel(uploaded_file, sheet_name=sheet_name, nrows=5)
                matches = sum(1 for c in required_cols if c in df_test.columns)
                if matches > best_match:
                    best_match = matches
                    best_sheet = sheet_name
            except Exception:
                continue

        if best_sheet is None:
            st.error(f"❌ No se encontró una hoja válida en **{file_label}**.")
            return None, None

        df = pd.read_excel(uploaded_file, sheet_name=best_sheet)

        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.warning(f"⚠️ Columnas faltantes en **{file_label}** (hoja '{best_sheet}'): {missing}")

        return df, best_sheet

    except Exception as e:
        st.error(f"❌ Error leyendo **{file_label}**: {e}")
        return None, None


def get_available_trucks(df_trucks, excluded_bks=None):
    """Return only available trucks with pallet capacity, excluding broken ones."""
    excluded_bks = excluded_bks or set()
    df = df_trucks[df_trucks["Status"] == "DISPONIBLE"].copy()
    df["Palets_Cap"] = df["Capac."].map(CAPACITY_PALLETS).fillna(0)
    df = df[df["Palets_Cap"] > 0]
    # Exclude manually disabled BKs
    if excluded_bks:
        df = df[~df["RUTA"].isin(excluded_bks)]
    return df.reset_index(drop=True)


# ─────────────────────── ASSIGNMENT ALGORITHM ───────────────────────
def assign_trucks(df_orders, df_trucks_avail, seed=42,
                  special_clients=None, priority_rules=None, custom_max_trips=None):
    """
    Assign trucks (BK) to orders based on pallet requirements.

    priority_rules: list of dicts with keys:
        - client_substr: substring to match client name
        - forced_bk: BK name to force (optional)
        - forced_trip: trip number to force (optional, 1/2/3)
        
    custom_max_trips: dict mapping bk_name -> max trips integer
    """
    rng = random.Random(seed)
    special_clients = special_clients or SPECIAL_CLIENTS
    priority_rules = priority_rules or []
    custom_max_trips = custom_max_trips or {}

    truck_pool = {}
    for _, row in df_trucks_avail.iterrows():
        bk_name = row["RUTA"]
        truck_pool[bk_name] = {
            "cap": row["Capac."],
            "pallet_cap": row["Palets_Cap"],
            "zone": str(row["ZONAS"]).strip(),
            "trips_pallets": {},
            "trips_locations": {},
            "max_trips": custom_max_trips.get(bk_name, MAX_TRIPS),
        }

    result = df_orders.copy()
    result["RUTA"] = ""
    result["VIAJE"] = 0

    # Group by client so a client's orders are processed together
    # Prioritize clients with most total pallets
    client_totals = result.groupby("Nombre 1")["Suma de Palets"].sum().to_dict()
    
    order_indices = list(result.index)
    order_indices.sort(key=lambda i: (
        -client_totals.get(result.loc[i, "Nombre 1"], 0),
        str(result.loc[i, "Nombre 1"]),
        -result.loc[i, "Suma de Palets"]
    ))

    # Disable generic shuffle if we want to preserve client grouping
    # if seed != 42:
    #     rng.shuffle(order_indices)

    client_assigned_bk = {}

    def find_and_assign(idx, forced_bk=None, forced_trip=None):
        """Find best truck for this order and assign it."""
        pallets = result.loc[idx, "Suma de Palets"]
        zone = str(result.loc[idx, "Distrito"]).strip()
        client_name = str(result.loc[idx, "Nombre 1"])
        
        # If no preferred BK yet, and client has many pallets (e.g. >= 15), try to default to BK3714 (BK14)
        is_large_client = client_totals.get(client_name, 0) >= 15
        
        preferred_bk = forced_bk or client_assigned_bk.get(client_name)
        if not preferred_bk and is_large_client:
            # Check if BK3714 exists in pool
            if any("14" in b for b in truck_pool.keys() if "BK" in b):
                bk14_name = next((b for b in truck_pool.keys() if "14" in b and "BK" in b), None)
                if bk14_name:
                    preferred_bk = bk14_name
        
        lat = pd.to_numeric(result.loc[idx, "Latitud"], errors="coerce") if "Latitud" in result.columns else float('nan')
        lon = pd.to_numeric(result.loc[idx, "Longitud"], errors="coerce") if "Longitud" in result.columns else float('nan')
        has_loc = not (pd.isna(lat) or pd.isna(lon))

        slots = []
        for bk, info in truck_pool.items():
            if forced_bk and bk != forced_bk:
                continue
                
            cap_idx = CAPACITY_PRIORITY.index(info["cap"]) if info["cap"] in CAPACITY_PRIORITY else 99
            bk_zone = info["zone"].lower()
            zone_match = -1 if (zone and (zone.lower() in bk_zone or any(z in bk_zone for z in zone.lower().split()))) else 0
            
            is_preferred = -1 if (preferred_bk and bk == preferred_bk) else 0
            
            # 1. Existing trips
            for t, rem_pallets in info["trips_pallets"].items():
                if forced_trip and t != forced_trip:
                    continue
                if rem_pallets >= pallets - 0.01:
                    dist = 0
                    if has_loc and len(info["trips_locations"][t]) > 0:
                        locs = info["trips_locations"][t]
                        c_lat = sum(p[0] for p in locs) / len(locs)
                        c_lon = sum(p[1] for p in locs) / len(locs)
                        dist = math.sqrt((lat - c_lat)**2 + (lon - c_lon)**2)
                    slots.append((is_preferred, dist, 0, cap_idx, zone_match, bk, t, False))
                    
            # 2. Potential new trip
            next_trip = max(info["trips_pallets"].keys(), default=0) + 1
            if next_trip <= info["max_trips"] and info["pallet_cap"] >= pallets - 0.01:
                if forced_trip and forced_trip != next_trip:
                    if forced_trip <= info["max_trips"]:
                        slots.append((is_preferred, 0.05 if has_loc else 0.001, 1, cap_idx, zone_match, bk, forced_trip, True))
                else:
                    dist_penalty = 0.03 if has_loc else 0.001
                    slots.append((is_preferred, dist_penalty, 1, cap_idx, zone_match, bk, next_trip, True))
                    
        slots.sort()
        
        if slots:
            best_slot = slots[0]
            _, _, _, _, _, best_bk, best_trip, is_new = best_slot
            info = truck_pool[best_bk]
            
            if is_new:
                for t in range(1, best_trip + 1):
                    if t not in info["trips_pallets"]:
                        info["trips_pallets"][t] = info["pallet_cap"]
                        info["trips_locations"][t] = []
            
            info["trips_pallets"][best_trip] -= pallets
            if has_loc:
                info["trips_locations"][best_trip].append((lat, lon))
            
            result.loc[idx, "RUTA"] = best_bk
            result.loc[idx, "VIAJE"] = best_trip
            client_assigned_bk[client_name] = best_bk
            return True
            
        # Fallback for oversized orders or when all trucks are full
        fallback_slots = []
        for bk, info in truck_pool.items():
            if forced_bk and bk != forced_bk:
                continue
            is_preferred = -1 if (preferred_bk and bk == preferred_bk) else 0
            cap_idx = CAPACITY_PRIORITY.index(info["cap"]) if info["cap"] in CAPACITY_PRIORITY else 99
            next_trip = forced_trip if forced_trip else max(info["trips_pallets"].keys(), default=0) + 1
            if next_trip <= info["max_trips"]:
                fallback_slots.append((is_preferred, cap_idx, bk, next_trip))
                
        fallback_slots.sort()
        if fallback_slots:
            _, _, best_bk, best_trip = fallback_slots[0]
            info = truck_pool[best_bk]
            for t in range(1, best_trip + 1):
                if t not in info["trips_pallets"]:
                    info["trips_pallets"][t] = 0
                    info["trips_locations"][t] = []
            info["trips_pallets"][best_trip] = 0
            if has_loc:
                info["trips_locations"][best_trip].append((lat, lon))
            result.loc[idx, "RUTA"] = best_bk
            result.loc[idx, "VIAJE"] = best_trip
            client_assigned_bk[client_name] = best_bk
            return True
            
        result.loc[idx, "RUTA"] = "SIN ASIGNAR"
        result.loc[idx, "VIAJE"] = 1
        return False

    # 1. Process priority rules first (user-defined daily conditions)
    priority_indices = set()
    for rule in priority_rules:
        substr = rule.get("client_substr", "")
        forced_bk = rule.get("forced_bk")
        forced_trip = rule.get("forced_trip")
        if not substr:
            continue
        for idx in order_indices:
            client = str(result.loc[idx, "Nombre 1"])
            if substr.lower() in client.lower():
                find_and_assign(idx, forced_bk=forced_bk, forced_trip=forced_trip)
                priority_indices.add(idx)

    # 2. Process permanent special clients
    special_indices = set()
    for substr, forced_bk in special_clients.items():
        for idx in order_indices:
            if idx in priority_indices:
                continue
            client = str(result.loc[idx, "Nombre 1"])
            if substr.lower() in client.lower():
                find_and_assign(idx, forced_bk=forced_bk)
                special_indices.add(idx)

    # 3. Process remaining orders
    for idx in order_indices:
        if idx in priority_indices or idx in special_indices:
            continue
        find_and_assign(idx)

    return result, truck_pool


# ─────────────────────── EXPORT ───────────────────────
def generate_excel_per_bk(df_result, truck_pool):
    """Generate Excel with RESUMEN_GENERAL + one sheet per BK + RESUMEN_BK."""
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Sheet 1: Full assignment table
        df_result.to_excel(writer, sheet_name="RESUMEN_GENERAL", index=False)

        # One sheet per BK
        bk_names = sorted([bk for bk in df_result["RUTA"].unique() if bk != "SIN ASIGNAR"])

        for bk_name in bk_names:
            bk_data = df_result[df_result["RUTA"] == bk_name].copy()
            bk_data = bk_data.sort_values("VIAJE").reset_index(drop=True)
            sheet_name = bk_name[:31]
            bk_data.to_excel(writer, sheet_name=sheet_name, index=False)

        # SIN ASIGNAR sheet if any
        sin_asignar = df_result[df_result["RUTA"] == "SIN ASIGNAR"]
        if len(sin_asignar) > 0:
            sin_asignar.to_excel(writer, sheet_name="SIN_ASIGNAR", index=False)

        # Summary sheet
        summary_rows = []
        for bk_name in bk_names:
            bk_data = df_result[df_result["RUTA"] == bk_name]
            info = truck_pool.get(bk_name, {})
            total_trip_count = len(info.get("trips_pallets", {}))
            total_pallets = bk_data["Suma de Palets"].sum()
            max_capacity = info.get("pallet_cap", 0) * total_trip_count
            utilization = (total_pallets / max_capacity * 100) if max_capacity > 0 else 0
            summary_rows.append({
                "BK": bk_name,
                "Capacidad (cajas)": int(info.get("cap", 0)),
                "Palets x Viaje": info.get("pallet_cap", 0),
                "Zona": info.get("zone", ""),
                "Viajes": total_trip_count,
                "Pedidos": len(bk_data),
                "Palets Totales": round(total_pallets, 2),
                "Utilización %": round(utilization, 1),
            })
        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="RESUMEN_BK", index=False)

    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_simple(df_result):
    """Generate a simple single-sheet Excel."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_result.to_excel(writer, sheet_name="Asignacion_BK", index=False)
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────── UI HELPERS ───────────────────────
def render_kpi(label, value, icon=""):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{icon} {value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def get_utilization_color(pct):
    if pct >= 80:
        return "#10b981"
    elif pct >= 50:
        return "#f59e0b"
    else:
        return "#ef4444"


def render_bk_card(bk_name, bk_data, truck_pool):
    """Render a card for a single BK truck."""
    orders = bk_data
    total_pallets = orders["Suma de Palets"].sum()
    num_trips = orders["VIAJE"].nunique()
    zones = orders["Distrito"].unique()
    zone_str = ", ".join(str(z) for z in zones[:3])

    if bk_name in truck_pool:
        info = truck_pool[bk_name]
        total_trip_count = len(info["trips_pallets"])
        max_capacity = info["pallet_cap"] * total_trip_count
        utilization = (total_pallets / max_capacity * 100) if max_capacity > 0 else 0
        cap_label = f"{int(info['cap'])} cajas / {info['pallet_cap']} palets"
    else:
        utilization = 0
        cap_label = "N/A"
        total_trip_count = num_trips

    util_color = get_utilization_color(utilization)

    is_special = False
    for substr in SPECIAL_CLIENTS:
        if any(substr.lower() in str(n).lower() for n in orders["Nombre 1"].unique()):
            is_special = True
            break

    special_html = '<span class="special-tag">⭐ ESPECIAL</span>' if is_special else ""

    card_html = f"""<div class="bk-card">
<div class="bk-header">
<span class="bk-name">🚚 {bk_name}{special_html}</span>
<div class="bk-badges">
<span class="bk-badge badge-cap">{cap_label}</span>
<span class="bk-badge badge-trips">{total_trip_count} viaje(s)</span>
<span class="bk-badge badge-zone">{zone_str}</span>
</div>
</div>
<div class="bk-stats">
<span class="bk-stats-left">{total_pallets:.1f} palets asignados · {len(orders)} pedido(s)</span>
<span style="color: {util_color}; font-weight: 700; font-size: 0.9rem;">{utilization:.0f}% util.</span>
</div>
<div class="progress-bar-outer">
<div class="progress-fill" style="width: {min(utilization, 100):.0f}%; background: linear-gradient(90deg, {util_color}, {util_color}88);"></div>
</div>
</div>"""

    st.markdown(card_html, unsafe_allow_html=True)

    with st.expander(f"📋 Detalle — {bk_name}", expanded=False):
        display_cols = ["Nombre 1", "Distrito", "Suma de Palets", "Suma de Cantidad de pedido", "VIAJE", "Doc#venta"]
        available_cols = [c for c in display_cols if c in orders.columns]
        st.dataframe(
            orders[available_cols].sort_values("VIAJE").reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )


# ─────────────────────── DAILY CONDITIONS UI ───────────────────────
def render_daily_conditions(df_trucks, df_orders):
    """Render the daily conditions panel in the sidebar."""
    st.markdown("#### 🔧 Condiciones del día")
    st.caption("Ajustes temporales para hoy")

    # ── Exclude broken BKs ──
    all_bks = sorted(df_trucks[df_trucks["Status"] == "DISPONIBLE"]["RUTA"].unique().tolist())

    if "excluded_bks" not in st.session_state:
        st.session_state.excluded_bks = []

    excluded = st.multiselect(
        "🚫 BKs no disponibles hoy",
        options=all_bks,
        default=st.session_state.excluded_bks,
        help="Selecciona camiones malogrados o no disponibles hoy",
        key="exclude_bks_select",
    )
    st.session_state.excluded_bks = excluded

    st.markdown("---")
    
    # ── Configurable Max Trips per BK ──
    st.markdown("##### 🔄 Viajes máximos por BK")
    st.caption("Ajusta cuántos viajes puede dar cada camión hoy")
    
    if "custom_max_trips" not in st.session_state:
        st.session_state.custom_max_trips = {}
        
    with st.expander("⚙️ Configurar viajes por camión", expanded=False):
        # Allow searching/filtering the list
        search_bk = st.text_input("Buscar camión", key="search_bk_trips")
        
        for bk in all_bks:
            if search_bk and search_bk.lower() not in bk.lower():
                continue
                
            col_b, col_t = st.columns([2, 1])
            with col_b:
                st.write(f"🚚 {bk}")
            with col_t:
                current_val = st.session_state.custom_max_trips.get(bk, MAX_TRIPS)
                new_val = st.number_input(
                    "Viajes", 
                    min_value=1, 
                    max_value=5, 
                    value=int(current_val), 
                    key=f"trip_limit_{bk}",
                    label_visibility="collapsed"
                )
                if new_val != current_val:
                    if new_val == MAX_TRIPS:
                        if bk in st.session_state.custom_max_trips:
                            del st.session_state.custom_max_trips[bk]
                    else:
                        st.session_state.custom_max_trips[bk] = new_val
                        
    st.markdown("---")

    # ── Priority rules ──
    st.markdown("##### ⭐ Prioridades de clientes")
    st.caption("Forzar un cliente a un BK o viaje específico")

    if "priority_rules" not in st.session_state:
        st.session_state.priority_rules = []

    # Show existing rules
    rules_to_keep = []
    for i, rule in enumerate(st.session_state.priority_rules):
        col_name, col_del = st.columns([4, 1])
        with col_name:
            label_parts = [f"**{rule['client_substr']}**"]
            if rule.get("forced_bk"):
                label_parts.append(f"→ {rule['forced_bk']}")
            if rule.get("forced_trip"):
                label_parts.append(f"viaje {rule['forced_trip']}")
            st.markdown(" · ".join(label_parts))
        with col_del:
            if st.button("❌", key=f"del_rule_{i}"):
                continue  # skip this rule (delete it)
        rules_to_keep.append(rule)

    if len(rules_to_keep) != len(st.session_state.priority_rules):
        st.session_state.priority_rules = rules_to_keep
        st.rerun()

    # Add new rule
    with st.expander("➕ Agregar regla", expanded=False):
        all_clients = sorted(df_orders["Nombre 1"].unique().tolist())
        new_client = st.selectbox(
            "Cliente",
            options=[""] + all_clients,
            key="new_rule_client",
        )
        col_bk, col_trip = st.columns(2)
        with col_bk:
            new_bk = st.selectbox(
                "Forzar BK (opcional)",
                options=["Automático"] + all_bks,
                key="new_rule_bk",
            )
        with col_trip:
            new_trip = st.selectbox(
                "Forzar viaje (opcional)",
                options=["Automático", 1, 2, 3],
                key="new_rule_trip",
            )

        if st.button("✅ Agregar regla", key="add_rule_btn"):
            if new_client:
                rule = {"client_substr": new_client}
                if new_bk != "Automático":
                    rule["forced_bk"] = new_bk
                if new_trip != "Automático":
                    rule["forced_trip"] = int(new_trip)
                st.session_state.priority_rules.append(rule)
                st.rerun()
            else:
                st.warning("Selecciona un cliente")

    return set(excluded), st.session_state.priority_rules, st.session_state.custom_max_trips


# ─────────────────────── MAIN APP ───────────────────────
def main():
    inject_styles()

    st.markdown("""
    <div class="main-title">
        <h1>🚚 Automatizador de Asignación BK</h1>
        <p>Distribución inteligente de camiones a pedidos — Backus</p>
    </div>
    """, unsafe_allow_html=True)

    # ─── FILE UPLOAD SECTION ───
    st.markdown('<div class="section-header">📂 Cargar archivos de datos</div>', unsafe_allow_html=True)

    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.markdown("""
        <div class="upload-zone">
            <h3>🚚 Disponibilidad de Camiones</h3>
            <p>Excel con columnas: RUTA, ZONAS, Capac., Status, etc.</p>
        </div>
        """, unsafe_allow_html=True)
        file_trucks = st.file_uploader(
            "Sube el archivo de DISPONIBILIDAD",
            type=["xlsx", "xls"],
            key="file_trucks",
            label_visibility="collapsed",
        )

    with col_up2:
        st.markdown("""
        <div class="upload-zone">
            <h3>📦 Cuadro de Clientes / Pedidos</h3>
            <p>Excel con columnas: Solic#, Nombre 1, ST, Prepago, Distrito, ZV, Doc#venta...</p>
        </div>
        """, unsafe_allow_html=True)
        file_orders = st.file_uploader(
            "Sube el archivo de CLIENTES / PEDIDOS",
            type=["xlsx", "xls"],
            key="file_orders",
            label_visibility="collapsed",
        )

    # Persist uploaded data in session_state to survive download reruns
    if file_trucks is not None:
        df_trucks_loaded, truck_sheet = load_uploaded_data(file_trucks, TRUCK_REQUIRED_COLS, "Disponibilidad de Camiones")
        if df_trucks_loaded is not None:
            st.session_state["df_trucks"] = df_trucks_loaded
            st.session_state["truck_sheet"] = truck_sheet

    if file_orders is not None:
        df_orders_loaded, order_sheet = load_uploaded_data(file_orders, ORDER_REQUIRED_COLS, "Clientes / Pedidos")
        if df_orders_loaded is not None:
            st.session_state["df_orders"] = df_orders_loaded
            st.session_state["order_sheet"] = order_sheet

    # Check if we have data (either freshly uploaded or from session)
    has_trucks = "df_trucks" in st.session_state
    has_orders = "df_orders" in st.session_state

    if not has_trucks or not has_orders:
        st.info("📌 **Sube ambos archivos** para comenzar la asignación automática de camiones.")
        st.markdown("---")

        with st.expander("ℹ️ Formato esperado de los archivos", expanded=False):
            st.markdown("""
            **Archivo de Disponibilidad** debe contener:
            | RUTA | ZONAS | EMPRESA | Cod. Conductor | PLACA | Capac. | MARCA | PROPIETARIO | PESO KG | Status | Comentario |
            |------|-------|---------|----------------|-------|--------|-------|-------------|---------|--------|------------|
            | BK3701 | SAN JUAN DE LURIGANCHO | CORP. BREXIMAR | 6004091 | PEBXG-761 | 1008 | MERCEDES | T77 | 10716 | DISPONIBLE | |

            **Archivo de Clientes / Pedidos** debe contener:
            | Solic# | Nombre 1 | ST | Prepago | Distrito | ZV | Doc#venta | Denominación | Suma de Cantidad de pedido | Suma de Palets |
            |--------|----------|-----|---------|----------|------|-----------|--------------|---------------------------|----------------|
            | 14324063 | Distribuidora ABC | 01 | NO PREPAGO | LIMA | PEM786 | 7655454725 | Cerveza | 1008 | 12.0 |
            """)

            st.markdown("**Capacidades configuradas:**")
            for cap in CAPACITY_PRIORITY:
                pallets = CAPACITY_PALLETS[cap]
                st.markdown(f"- **{cap} cajas** → {pallets} palets")
        return

    # ─── USE PERSISTED DATA ───
    df_trucks = st.session_state["df_trucks"]
    df_orders = st.session_state["df_orders"]
    truck_sheet = st.session_state["truck_sheet"]
    order_sheet = st.session_state["order_sheet"]

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(
            f'<div class="upload-success">✅ Disponibilidad cargada — Hoja: "{truck_sheet}" — {len(df_trucks)} registros</div>',
            unsafe_allow_html=True,
        )
    with col_c2:
        st.markdown(
            f'<div class="upload-success">✅ Clientes cargado — Hoja: "{order_sheet}" — {len(df_orders)} pedidos</div>',
            unsafe_allow_html=True,
        )

    # ─── SIDEBAR ───
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        st.markdown("---")

        if "seed" not in st.session_state:
            st.session_state.seed = 42

        st.markdown("#### 🔄 Reorganizar asignación")
        st.caption("Genera una nueva distribución de camiones")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Nueva opción", use_container_width=True, key="new_opt"):
                st.session_state.seed = random.randint(1, 100000)
                st.rerun()
        with col2:
            if st.button("↩️ Original", use_container_width=True, key="original"):
                st.session_state.seed = 42
                st.rerun()

        st.markdown("---")

        manual_seed = st.number_input(
            "Semilla manual",
            min_value=1,
            max_value=999999,
            value=st.session_state.seed,
            help="Cambia este número para obtener una distribución diferente"
        )
        if manual_seed != st.session_state.seed:
            st.session_state.seed = manual_seed
            st.rerun()

        st.markdown("---")

        # ── DAILY CONDITIONS ──
        excluded_bks, priority_rules, custom_max_trips = render_daily_conditions(df_trucks, df_orders)

        st.markdown("---")
        st.markdown("#### 📦 Capacidades")
        for cap in CAPACITY_PRIORITY:
            pallets = CAPACITY_PALLETS[cap]
            st.markdown(f"- **{cap} cajas** → {pallets} palets")

        st.markdown("---")
        st.markdown("#### 🏷️ Clientes especiales (fijos)")
        for substr, bk in SPECIAL_CLIENTS.items():
            st.markdown(f"- *{substr}* → **{bk}**")

        st.markdown("---")
        st.markdown("#### 🚚 Flota disponible")

    # ─── PREPARE AND RUN ───
    df_trucks_avail = get_available_trucks(df_trucks, excluded_bks=excluded_bks)

    if len(df_trucks_avail) == 0:
        st.error("❌ No hay camiones disponibles. Revisa el archivo o las condiciones del día.")
        return

    # Show fleet info in sidebar
    with st.sidebar:
        cap_counts = df_trucks_avail["Capac."].value_counts().sort_index(ascending=False)
        for cap, count in cap_counts.items():
            pallets = CAPACITY_PALLETS.get(cap, 0)
            st.markdown(f"- **{int(cap)}** ({pallets}p): {count} camiones")
        st.markdown(f"**Total: {len(df_trucks_avail)} camiones**")
        if excluded_bks:
            st.markdown(f"🚫 Excluidos: {len(excluded_bks)}")

    df_result, truck_pool = assign_trucks(
        df_orders, df_trucks_avail,
        seed=st.session_state.seed,
        priority_rules=priority_rules,
        custom_max_trips=custom_max_trips,
    )

    # ─── KPIs ───
    total_pallets = df_result["Suma de Palets"].sum()
    assigned_mask = df_result["RUTA"] != "SIN ASIGNAR"
    bks_used = df_result.loc[assigned_mask, "RUTA"].nunique()

    total_trips = 0
    total_capacity = 0
    for bk_name, info in truck_pool.items():
        trip_count = len(info["trips_pallets"])
        if trip_count > 0:
            total_trips += trip_count
            total_capacity += info["pallet_cap"] * trip_count

    unassigned = (~assigned_mask).sum()
    overall_util = (total_pallets / total_capacity * 100) if total_capacity > 0 else 0

    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        render_kpi("Palets totales", f"{total_pallets:.1f}", "📦")
    with cols[1]:
        render_kpi("Camiones usados", f"{bks_used}", "🚚")
    with cols[2]:
        render_kpi("Viajes totales", f"{total_trips}", "🔄")
    with cols[3]:
        render_kpi("Utilización", f"{overall_util:.0f}%", "📊")
    with cols[4]:
        render_kpi("Sin asignar", f"{unassigned}", "⚠️")

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── MAIN TABLE ───
    st.markdown('<div class="section-header">📋 Tabla de asignación completa</div>', unsafe_allow_html=True)

    st.dataframe(
        df_result,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "RUTA": st.column_config.TextColumn("🚚 RUTA", width="medium"),
            "VIAJE": st.column_config.NumberColumn("🔄 VIAJE", format="%d"),
            "Suma de Palets": st.column_config.NumberColumn("📦 Palets", format="%.2f"),
            "Suma de Cantidad de pedido": st.column_config.NumberColumn("📝 Cant. Pedido", format="%d"),
            "Nombre 1": st.column_config.TextColumn("👤 Cliente", width="large"),
            "Distrito": st.column_config.TextColumn("📍 Distrito"),
        }
    )

    # ─── EXPORT ───
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📥 Descargar resultados</div>', unsafe_allow_html=True)

    # Pre-generate Excel files
    excel_per_bk_data = generate_excel_per_bk(df_result, truck_pool)
    excel_simple_data = generate_excel_simple(df_result)

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        st.download_button(
            label="📥 Excel por BK (hojas separadas)",
            data=excel_per_bk_data,
            file_name="asignacion_por_bk.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Un Excel con una hoja por cada camión BK + resumen general",
        )

    with col_exp2:
        st.download_button(
            label="📥 Excel completo (1 hoja)",
            data=excel_simple_data,
            file_name="asignacion_bk_completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_exp3:
        csv_data = df_result.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar CSV",
            data=csv_data,
            file_name="asignacion_bk.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── BK CARDS ───
    st.markdown('<div class="section-header">🚚 Detalle por camión (BK)</div>', unsafe_allow_html=True)

    bk_names_used = [bk for bk in df_result["RUTA"].unique() if bk != "SIN ASIGNAR"]
    bk_order = []
    for bk in bk_names_used:
        cap = truck_pool[bk]["cap"] if bk in truck_pool else 0
        bk_order.append((bk, cap))
    bk_order.sort(key=lambda x: (-x[1], x[0]))

    if "SIN ASIGNAR" in df_result["RUTA"].values:
        bk_order.append(("SIN ASIGNAR", -1))

    col_left, col_right = st.columns(2)
    for i, (bk_name, _) in enumerate(bk_order):
        bk_data = df_result[df_result["RUTA"] == bk_name]
        with col_left if i % 2 == 0 else col_right:
            render_bk_card(bk_name, bk_data, truck_pool)

    # ─── SUMMARY BY ZONE ───
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📍 Resumen por zona</div>', unsafe_allow_html=True)

    zone_agg_col = "Doc#venta" if "Doc#venta" in df_result.columns else "Nombre 1"
    zone_summary = df_result.groupby("Distrito").agg(
        Pedidos=(zone_agg_col, "count"),
        Palets=("Suma de Palets", "sum"),
        Camiones=("RUTA", "nunique"),
    ).sort_values("Palets", ascending=False).reset_index()

    st.dataframe(
        zone_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Distrito": st.column_config.TextColumn("📍 Distrito"),
            "Pedidos": st.column_config.NumberColumn("📝 Pedidos", format="%d"),
            "Palets": st.column_config.NumberColumn("📦 Palets", format="%.1f"),
            "Camiones": st.column_config.NumberColumn("🚚 Camiones", format="%d"),
        }
    )

    # Footer
    st.markdown("---")
    st.caption(f"💡 Semilla actual: {st.session_state.seed} | Haz clic en '🎲 Nueva opción' para obtener una distribución diferente.")


if __name__ == "__main__":
    main()
