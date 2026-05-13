import streamlit as st
import pandas as pd
import pydeck as pdk
from connection import run_query

st.set_page_config(page_title="SNCF Dashboard", layout="wide")
st.title("Destinations SNCF")


# ─── Chargement des gares disponibles ────────────────────────────────────────

@st.cache_data
def load_stations():
    try:
        print("🔄 Chargement des stations...")
        result = run_query("""
            SELECT DISTINCT stop_name
            FROM transport.gold.gtfs_gold
            ORDER BY stop_name
        """)
        print(f"✅ {len(result)} stations chargées")
        return result["stop_name"].tolist()
    except Exception as e:
        print(f"❌ Erreur load_stations : {e}")
        return []


# ─── Chargement des données selon les paramètres ─────────────────────────────

@st.cache_data
def load_destinations(date, gare_depart, duree_max_h, train_types, heure_min, heure_max):
    train_filter = ""
    if train_types:
        conditions = []
        if "TGV INOUI" in train_types:
            conditions.append("trip_id LIKE '%OUI%'")
        if "TER" in train_types:
            conditions.append("trip_id LIKE '%TER%'")
        if "Autre" in train_types:
            conditions.append("(trip_id NOT LIKE '%OUI%' AND trip_id NOT LIKE '%TER%')")
        train_filter = f"AND ({' OR '.join(conditions)})"

    return run_query(f"""
        WITH depart AS (
            SELECT trip_id, departure_time
            FROM transport.gold.gtfs_gold
            WHERE date = '{date}'
            AND stop_name = '{gare_depart}'
            AND departure_time >= '{heure_min}'
            AND departure_time <= '{heure_max}'
            {train_filter}
        )
        SELECT DISTINCT
            s.stop_name,
            s.stop_lat,
            s.stop_lon,
            s.arrival_time,
            d.departure_time AS depart_time,
            ROUND(
                (
                    split(s.arrival_time, ':')[0]*3600 +
                    split(s.arrival_time, ':')[1]*60 +
                    split(s.arrival_time, ':')[2]
                ) 
                - (
                    split(d.departure_time, ':')[0]*3600 +
                    split(d.departure_time, ':')[1]*60 +
                    split(d.departure_time, ':')[2]
                )
            ) / 60.0 AS duree_min
        FROM transport.gold.gtfs_gold s
        JOIN depart d ON s.trip_id = d.trip_id
        WHERE s.date = '{date}'
        AND s.stop_name != '{gare_depart}'
        AND (
                (split(s.arrival_time, ':')[0]*3600 +
                split(s.arrival_time, ':')[1]*60 +
                split(s.arrival_time, ':')[2])
            - (split(d.departure_time, ':')[0]*3600 +
                split(d.departure_time, ':')[1]*60 +
                split(d.departure_time, ':')[2])
            ) / 3600.0 <= {duree_max_h}
        AND (
                (split(s.arrival_time, ':')[0]*3600 +
                split(s.arrival_time, ':')[1]*60 +
                split(s.arrival_time, ':')[2])
            - (split(d.departure_time, ':')[0]*3600 +
                split(d.departure_time, ':')[1]*60 +
                split(d.departure_time, ':')[2])
            ) > 0
        ORDER BY duree_min;
    """)


# ─── Formulaire sidebar ───────────────────────────────────────────────────────

stations = load_stations()

with st.sidebar:
    st.header("Paramètres")

    date = st.date_input("Date", value=pd.Timestamp("2026-05-19"))

    gare_depart = st.selectbox("Gare de départ", options=stations)

    duree_max_h = st.slider(
        "Durée maximale de trajet",
        min_value=1, max_value=8, value=3, step=1,
        format="%dh"
    )

    heure_min, heure_max = st.select_slider(
        "Heure de départ",
        options=[f"{h:02d}:00:00" for h in range(25)],
        value=("05:00:00", "23:00:00"),
    )

    train_types = st.multiselect(
        "Type de train (optionnel)",
        options=["TGV INOUI", "TER", "Autre"],
        default=["TGV INOUI", "TER", "Autre"],
    )

    lancer = st.button("Rechercher", use_container_width=True)


# ─── Résultats ────────────────────────────────────────────────────────────────

if lancer:
    with st.spinner("Chargement des données..."):
        df = load_destinations(
            str(date), gare_depart, duree_max_h,
            train_types, heure_min, heure_max
        )

    if df.empty:
        st.warning("Aucune destination trouvée pour ces paramètres.")
        st.stop()

    st.success(f"{len(df)} destinations trouvées depuis **{gare_depart}**")

    # Gare de départ (point rouge)
    depart_df = pd.DataFrame([{
        "stop_name": gare_depart,
        "stop_lat": df["stop_lat"].mean(),  # approximation visuelle
        "stop_lon": df["stop_lon"].mean(),
    }])

    # Récupérer les coords réelles de la gare de départ
    depart_info = run_query(f"""
        SELECT stop_lat, stop_lon FROM transport.gold.gtfs_gold
        WHERE stop_name = '{gare_depart}' LIMIT 1
    """)
    if not depart_info.empty:
        depart_df["stop_lat"] = depart_info["stop_lat"].iloc[0]
        depart_df["stop_lon"] = depart_info["stop_lon"].iloc[0]

    # Lignes depuis le départ vers chaque destination
    lines_data = [{
        "start": [depart_df["stop_lon"].iloc[0], depart_df["stop_lat"].iloc[0]],
        "end": [row["stop_lon"], row["stop_lat"]],
        "duree_min": row["duree_min"],
        "stop_name": row["stop_name"],
    } for _, row in df.iterrows()]

    # Couleur selon durée (vert → orange → rouge)
    def duree_to_color(d, max_d):
        ratio = min(d / max_d, 1.0)
        r = int(255 * ratio)
        g = int(200 * (1 - ratio))
        return [r, g, 80, 180]

    max_duree = df["duree_min"].max()
    for line in lines_data:
        line["color"] = duree_to_color(line["duree_min"], max_duree)

    # Layers
    line_layer = pdk.Layer(
        "LineLayer",
        data=lines_data,
        get_source_position="start",
        get_target_position="end",
        get_color="color",
        get_width=2,
        width_min_pixels=1,
        pickable=True,
    )

    dest_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["stop_lon", "stop_lat"],
        get_radius=600,
        get_fill_color="[30, 158, 117, 200]",
        get_line_color="[255, 255, 255, 255]",
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
        pickable=True,
    )

    depart_layer = pdk.Layer(
        "ScatterplotLayer",
        data=depart_df,
        get_position=["stop_lon", "stop_lat"],
        get_radius=900,
        get_fill_color="[220, 53, 69, 255]",
        get_line_color="[255, 255, 255, 255]",
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
        pickable=True,
    )

    # Carte + tableau côte à côte
    col_map, col_table = st.columns([2, 1])

    with col_map:
        all_lats = list(df["stop_lat"]) + [depart_df["stop_lat"].iloc[0]]
        all_lons = list(df["stop_lon"]) + [depart_df["stop_lon"].iloc[0]]

        st.pydeck_chart(
            pdk.Deck(
                layers=[line_layer, dest_layer, depart_layer],
                initial_view_state=pdk.ViewState(
                    latitude=sum(all_lats) / len(all_lats),
                    longitude=sum(all_lons) / len(all_lons),
                    zoom=6,
                    pitch=0,
                ),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"html": "<b>{stop_name}</b><br/>Durée : {duree_min} min"},
            ),
            height=700,
            use_container_width=True,
        )

    with col_table:
        st.subheader("Destinations")
        st.dataframe(
            # df[["stop_name", "depart_time", "arrival_time", "duree_min"]]
            df[["stop_name", "duree_min"]]
            .rename(columns={
                "stop_name": "Destination",
                "duree_min": "Durée (min)",
            })
            .drop_duplicates(["Destination"])
            .reset_index(drop=True),
            use_container_width=True,
            height=700,
        )