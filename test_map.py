import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import random

def main():
    st.title("Test Map")

    df_valid = pd.DataFrame([
        {"Nombre 1": "Cliente A", "RUTA": "BK30", "VIAJE": 1, "Suma de Palets": 5, "Latitud": -12.0464, "Longitud": -77.0428, "Prioridad_Num": 1},
        {"Nombre 1": "Cliente B", "RUTA": "BK30", "VIAJE": 1, "Suma de Palets": 10, "Latitud": -12.0500, "Longitud": -77.0500, "Prioridad_Num": 0},
    ])

    center_lat, center_lon = df_valid["Latitud"].mean(), df_valid["Longitud"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 'black']
    bks = ["BK30"]
    bk_color = {"BK30": "blue"}

    for idx, row in df_valid.iterrows():
        color = "gray" if row["RUTA"] == "SIN ASIGNAR" else bk_color.get(row["RUTA"], "blue")
        r_lat = row["Latitud"] + random.uniform(-0.0001, 0.0001)
        r_lon = row["Longitud"] + random.uniform(-0.0001, 0.0001)
        
        popup_html = f"<b>{row['Nombre 1']}</b><br>BK: {row['RUTA']}<br>Viaje: {row['VIAJE']}<br>Palets: {row['Suma de Palets']}"
        folium.Marker(
            [r_lat, r_lon],
            popup=popup_html,
            tooltip=str(row["Nombre 1"]),
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    warehouse_lat, warehouse_lon = -12.0435, -76.9537
    for bk in bks:
        df_bk = df_valid[df_valid["RUTA"] == bk]
        color = bk_color.get(bk, "blue")
        for viaje in df_bk["VIAJE"].unique():
            df_viaje = df_bk[df_bk["VIAJE"] == viaje].sort_values("Prioridad_Num", ascending=False)
            route_coords = [[warehouse_lat, warehouse_lon]] + [[row["Latitud"], row["Longitud"]] for _, row in df_viaje.iterrows()]
            if len(route_coords) > 1:
                folium.PolyLine(
                    route_coords,
                    color=color,
                    weight=3,
                    opacity=0.7,
                    dash_array="10",
                    tooltip=f"Ruta {bk} - Viaje {viaje}"
                ).add_to(m)

    st_folium(m, height=500, use_container_width=True, key="route_map")

if __name__ == "__main__":
    main()
