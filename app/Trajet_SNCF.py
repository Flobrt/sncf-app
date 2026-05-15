import streamlit as st
import pandas as pd
import pydeck as pdk
from connection import run_query
from datetime import datetime

st.set_page_config(page_title="SNCF Dashboard", layout="wide")
st.title("Destinations SNCF")

# ─── Session state ────────────────────────────────────────────────────────────

if "df_resultats" not in st.session_state:
    st.session_state.df_resultats = None
if "depart_df" not in st.session_state:
    st.session_state.depart_df = None
if "destination_selectionnee" not in st.session_state:
    st.session_state.destination_selectionnee = None
if "params" not in st.session_state:
    st.session_state.params = None
if "train_selectionne" not in st.session_state:
    st.session_state.train_selectionne = None

# ─── Chargement des gares disponibles ────────────────────────────────────────

@st.cache_data
def load_stations():
    return run_query("""
        SELECT DISTINCT stop_name
        FROM transport.gold.gtfs_gold
        ORDER BY stop_name
    """)["stop_name"].tolist()

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
            AND date_format(departure_time, 'HH:mm:ss') >= '{heure_min}'
            AND date_format(departure_time, 'HH:mm:ss') <= '{heure_max}'
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

# ─── Chargement des trains pour une destination ───────────────────────────────

@st.cache_data
def load_trains(date, gare_depart, gare_arrivee, heure_min, heure_max):
    return run_query(f"""
        WITH depart AS (
            SELECT trip_id, departure_time
            FROM transport.gold.gtfs_gold
            WHERE date = '{date}'
            AND stop_name = '{gare_depart}'
            AND date_format(departure_time, 'HH:mm:ss') >= '{heure_min}'
            AND date_format(departure_time, 'HH:mm:ss') <= '{heure_max}'
        )
        SELECT
            d.departure_time AS heure_depart,
            s.arrival_time AS heure_arrivee,
            s.trip_id,
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
        AND s.stop_name = '{gare_arrivee}'
        ORDER BY d.departure_time;
    """)

# ─── Chargement du numéro de séquence d'un arrêt dans un trip ────────────────

@st.cache_data
def load_seq(date, trip_id, stop_name):
    result = run_query(f"""
        SELECT stop_sequence
        FROM transport.gold.gtfs_gold
        WHERE date = '{date}'
        AND trip_id = '{trip_id}'
        AND stop_name = '{stop_name}'
        LIMIT 1
    """)
    if result.empty:
        return None
    return result["stop_sequence"].iloc[0]

# ─── Chargement des arrêts entre départ et arrivée pour un trip ──────────────

@st.cache_data
def load_train_stops(date, trip_id, seq_dep, seq_arr):
    return run_query(f"""
        SELECT stop_name, stop_lat, stop_lon, departure_time, stop_sequence
        FROM transport.gold.gtfs_gold
        WHERE date = '{date}'
        AND trip_id = '{trip_id}'
        AND stop_sequence >= {seq_dep}
        AND stop_sequence <= {seq_arr}
        ORDER BY stop_sequence
    """)

# ─── Formulaire sidebar ───────────────────────────────────────────────────────

stations = load_stations()

with st.sidebar:
    st.header("Paramètres")
    today = datetime.today().strftime("%Y-%m-%d")
    date = st.date_input("Date", value=pd.Timestamp(today))
    gare_depart = st.selectbox(
        "Gare de départ", 
        options=stations,
        index=stations.index("Lyon Part Dieu") if "Lyon Part Dieu" in stations else 0)
    duree_max_h = st.slider("Durée maximale de trajet", min_value=1, max_value=8, value=3, step=1, format="%dh")
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

    st.markdown("---")
    st.markdown("**Florian Berthelot**")
    st.markdown("""
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)](https://www.linkedin.com/in/florian-berthelot-ba2252173/)
    [![GitHub](https://img.shields.io/badge/GitHub-black?logo=github)](https://github.com/Flobrt)
    """)

# ─── Lancement de la recherche ────────────────────────────────────────────────

if lancer:
    st.session_state.destination_selectionnee = None
    st.session_state.train_selectionne = None
    with st.spinner("Chargement des données..."):
        df = load_destinations(str(date), gare_depart, duree_max_h, train_types, heure_min, heure_max)

    if df.empty:
        st.warning("Aucune destination trouvée pour ces paramètres.")
        st.stop()

    depart_df = pd.DataFrame([{"stop_name": gare_depart, "stop_lat": 0.0, "stop_lon": 0.0}])
    depart_info = run_query(f"""
        SELECT stop_lat, stop_lon FROM transport.gold.gtfs_gold
        WHERE stop_name = '{gare_depart}' LIMIT 1
    """)
    if not depart_info.empty:
        depart_df["stop_lat"] = depart_info["stop_lat"].iloc[0]
        depart_df["stop_lon"] = depart_info["stop_lon"].iloc[0]

    st.session_state.df_resultats = df
    st.session_state.depart_df = depart_df
    st.session_state.params = {
        "gare_depart": gare_depart,
        "date": str(date),
        "heure_min": heure_min,
        "heure_max": heure_max,
    }

# ─── Affichage des résultats ──────────────────────────────────────────────────

if st.session_state.df_resultats is not None:
    df = st.session_state.df_resultats
    depart_df = st.session_state.depart_df
    params = st.session_state.params

    distinct_destinations = df["stop_name"].nunique()
    st.success(f"{distinct_destinations} destinations trouvées depuis **{params['gare_depart']}**")

    lines_data = [{
        "start": [depart_df["stop_lon"].iloc[0], depart_df["stop_lat"].iloc[0]],
        "end": [row["stop_lon"], row["stop_lat"]],
        "duree_min": row["duree_min"],
        "stop_name": row["stop_name"],
    } for _, row in df.iterrows()]

    def duree_to_color(d, max_d):
        ratio = min(d / max_d, 1.0)
        r = int(255 * ratio)
        g = int(200 * (1 - ratio))
        return [r, g, 80, 180]

    max_duree = df["duree_min"].max()
    for line in lines_data:
        line["color"] = duree_to_color(line["duree_min"], max_duree)

    line_layer = pdk.Layer(
        "LineLayer", data=lines_data,
        get_source_position="start", get_target_position="end",
        get_color="color", get_width=2, width_min_pixels=1, pickable=True,
    )
    dest_layer = pdk.Layer(
        "ScatterplotLayer", data=df,
        get_position=["stop_lon", "stop_lat"],
        get_radius=600, get_fill_color="[30, 158, 117, 200]",
        get_line_color="[255, 255, 255, 255]",
        stroked=True, filled=True, line_width_min_pixels=2, pickable=True,
    )
    depart_layer = pdk.Layer(
        "ScatterplotLayer", data=depart_df,
        get_position=["stop_lon", "stop_lat"],
        get_radius=900, get_fill_color="[220, 53, 69, 255]",
        get_line_color="[255, 255, 255, 255]",
        stroked=True, filled=True, line_width_min_pixels=2, pickable=True,
    )

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
                    zoom=6, pitch=0,
                ),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"html": "<b>{stop_name}</b><br/>Durée : {duree_min} min"},
            ),
            height=600,
            use_container_width=True,
        )

    with col_table:
        df_display = (
            df[["stop_name", "duree_min"]]
            .rename(columns={"stop_name": "Destination", "duree_min": "Durée (min)"})
            .drop_duplicates("Destination")
            .reset_index(drop=True)
        )
        df_display["Durée (min)"] = df_display["Durée (min)"].apply(
                lambda x: f"{int(x//60)}h {int(x%60)}m" if x >= 60 else f"{int(x)} min"
            )
        selection = st.dataframe(
            df_display,
            use_container_width=True,
            height=600,
            on_select="rerun",
            selection_mode="single-row",
        )

        if selection["selection"]["rows"]:
            idx = selection["selection"]["rows"][0]
            nouvelle_dest = df_display.iloc[idx]["Destination"]
            if nouvelle_dest != st.session_state.destination_selectionnee:
                st.session_state.destination_selectionnee = nouvelle_dest
                st.session_state.train_selectionne = None

    # ─── Détail des trains ────────────────────────────────────────────────────

    if st.session_state.destination_selectionnee:
        dest = st.session_state.destination_selectionnee
        st.divider()
        st.markdown(f"### 🚉 Trains disponibles : **{params['gare_depart']}** → **{dest}** ({params['date']})")

        with st.spinner("Chargement des trains..."):
            df_trains = load_trains(
                params["date"], params["gare_depart"], dest,
                params["heure_min"], params["heure_max"]
            )
            df_trains = df_trains[df_trains["duree_min"] > 0].reset_index(drop=True)
            df_trains["duree_str"] = df_trains["duree_min"].apply(
                lambda x: f"{int(x//60)}h {int(x%60)}m" if x >= 60 else f"{int(x)} min"
            )

        if df_trains.empty:
            st.warning("Aucun train direct trouvé pour cette destination.")
        else:
            col_trains, col_carte_trajet = st.columns([1, 2])

            with col_trains:
                sel_train = st.dataframe(
                    df_trains[["heure_depart", "heure_arrivee", "duree_str"]].rename(columns={
                        "heure_depart": "Départ",
                        "heure_arrivee": "Arrivée",
                        "duree_str": "Durée",
                    }),
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=400,
                )

                if sel_train["selection"]["rows"]:
                    st.session_state.train_selectionne = df_trains.iloc[sel_train["selection"]["rows"][0]]["trip_id"]

            with col_carte_trajet:
                trip_id = st.session_state.train_selectionne or df_trains.iloc[0]["trip_id"]

                seq_dep = load_seq(params["date"], trip_id, params["gare_depart"])
                seq_arr = load_seq(params["date"], trip_id, dest)

                if seq_dep is not None and seq_arr is not None:
                    df_stops = load_train_stops(params["date"], trip_id, seq_dep, seq_arr)

                    if not df_stops.empty:
                        lines_trajet = [
                            {
                                "start": [df_stops.iloc[i]["stop_lon"], df_stops.iloc[i]["stop_lat"]],
                                "end":   [df_stops.iloc[i+1]["stop_lon"], df_stops.iloc[i+1]["stop_lat"]],
                            }
                            for i in range(len(df_stops) - 1)
                        ]

                        df_stops["color"] = df_stops["stop_name"].apply(
                            lambda x: [220, 53, 69, 255] if x in [params["gare_depart"], dest] else [255, 255, 255, 220]
                        )
                        df_stops["radius"] = df_stops["stop_name"].apply(
                            lambda x: 800 if x in [params["gare_depart"], dest] else 400
                        )

                        st.pydeck_chart(pdk.Deck(
                            layers=[
                                pdk.Layer("LineLayer", data=lines_trajet,
                                    get_source_position="start", get_target_position="end",
                                    get_color=[50, 130, 220, 200], get_width=4, width_min_pixels=2),
                                pdk.Layer("ScatterplotLayer", data=df_stops,
                                    get_position=["stop_lon", "stop_lat"],
                                    get_radius="radius", get_fill_color="color",
                                    get_line_color=[255, 255, 255, 255],
                                    stroked=True, filled=True, line_width_min_pixels=2, pickable=True),
                            ],
                            initial_view_state=pdk.ViewState(
                                latitude=df_stops["stop_lat"].mean(),
                                longitude=df_stops["stop_lon"].mean(),
                                zoom=7, pitch=0,
                            ),
                            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                            tooltip={"html": "<b>{stop_name}</b><br/>🕐 {departure_time}"},
                        ), height=400, use_container_width=True)
                else:
                    st.warning("Impossible de charger le tracé pour ce train.")
