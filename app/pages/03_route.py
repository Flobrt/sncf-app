import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import pydeck as pdk


st.set_page_config(layout="wide")
st.set_page_config(page_title="SNCF Dashboard - Tracés", layout="wide")
st.title("Tracés SNCF")

def load_data():
    df = pd.read_parquet("/home/flobert/code/sncf_pipeline/data/gold/gtfs_static/total_test")
    # Filtrer les données du 19/05/2026
    # df = df[(df['date'] == '2026-05-19') & (df['trip_id'].str.contains('12176'))]
    return df

# Extraire le type de train depuis trip_id
def get_train_type(trip_id):
    if "OUI" in trip_id:
        return "TGV INOUI"
    elif "TER" in trip_id:
        return "TER"
    else:
        return "Autre"


df = load_data()

df["train_type"] = df["trip_id"].apply(get_train_type)

# Filtre dans la sidebar
types_disponibles = sorted(df["train_type"].unique().tolist())
selection = st.sidebar.multiselect(
    "Type de train",
    options=types_disponibles,
    default=types_disponibles,
)

# Appliquer le filtre
df_filtered = df[df["train_type"].isin(selection)]

# Coordonnées dans l'ordre du DataFrame (déjà trié par stop_sequence)
path_coords = df_filtered[["stop_lon", "stop_lat"]].values.tolist()

# Tracé de la ligne
path_layer = pdk.Layer(
    "PathLayer",
    data=[{"path": path_coords, "name": df_filtered["route_long_name"].iloc[0]}],
    get_path="path",
    get_color="[30, 158, 117, 220]",
    get_width=4,
    width_min_pixels=3,
)

# Points aux arrêts
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_filtered,
    get_position=["stop_lon", "stop_lat"],
    get_radius=800,
    get_fill_color="[255, 255, 255, 240]",
    get_line_color="[30, 158, 117, 255]",
    stroked=True,
    filled=True,
    line_width_min_pixels=2,
    pickable=True,
)

# Affichage
st.pydeck_chart(
    pdk.Deck(
        layers=[path_layer, scatter_layer],
        initial_view_state=pdk.ViewState(
            latitude=df_filtered["stop_lat"].mean(),
            longitude=df_filtered["stop_lon"].mean(),
            zoom=8,
            pitch=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"html": "<b>{stop_name}</b><br/>{arrival_time} → {departure_time}"},
    ),
    height=800,
    width='stretch',
)