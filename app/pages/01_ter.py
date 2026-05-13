import streamlit as st
import pandas as pd
import plotly.express as px
from connection import run_query

st.set_page_config(page_title="SNCF Dashboard", layout="wide")
st.title("🚄 Dashboard Régularité TER")

# Chargement des données — on récupère toutes les métriques
@st.cache_data
def load_ter():
    return run_query("""
        SELECT 
            region,
            AVG(taux_regul_moyen)        as taux_regul,
            SUM(total_trains_annules)    as total_trains_annules,
            SUM(total_trains_retards)    as total_trains_retards,
            SUM(total_trains_programmes) as total_trains_programmes
        FROM transport.gold.mart_regularite_ter
        GROUP BY region
    """)

df = load_ter()

# Mapping des noms de régions
mapping = {
    "Centre Val-de-Loire": "Centre-Val de Loire",
    "Nouvelle Aquitaine": "Nouvelle-Aquitaine",
    "Pays-de-la-Loire": "Pays de la Loire",
    "Provence Alpes Côte d'Azur": "Provence-Alpes-Côte d'Azur",
    "Etoile Amiens": "Hauts-de-France",
    "Loire Océan": "Pays de la Loire",
    "Sud Azur": "Provence-Alpes-Côte d'Azur"
}
df["region"] = df["region"].replace(mapping)
df = df.groupby("region", as_index=False).agg({
    "taux_regul": "mean",
    "total_trains_annules": "sum",
    "total_trains_retards": "sum",
    "total_trains_programmes": "sum"
})

# Calcul du ratio retards
df["ratio_retards"] = (df["total_trains_retards"] / df["total_trains_programmes"] * 100).round(2)

# GeoJSON
geojson_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson"

# Boutons de sélection
col1, col2, col3 = st.columns(3)
with col1:
    btn_regul = st.button("📊 Taux de régularité", use_container_width=True)
with col2:
    btn_annules = st.button("❌ Trains annulés", use_container_width=True)
with col3:
    btn_retards = st.button("⏱️ Ratio retards", use_container_width=True)

# Gérer l'état
if "metrique" not in st.session_state:
    st.session_state.metrique = "taux_regul"
if btn_regul:
    st.session_state.metrique = "taux_regul"
if btn_annules:
    st.session_state.metrique = "total_trains_annules"
if btn_retards:
    st.session_state.metrique = "ratio_retards"

# Config par métrique
config = {
    "taux_regul": {
        "label": "Taux de régularité (%)",
        "title": "🗺️ Taux de régularité TER par région",
        "scale": "RdYlGn",
        "range": [80, 100]
    },
    "total_trains_annules": {
        "label": "Trains annulés",
        "title": "🗺️ Nombre de trains annulés par région",
        "scale": "RdYlGn_r",
        "range": [0, df["total_trains_annules"].max()]
    },
    "ratio_retards": {
        "label": "Ratio retards (%)",
        "title": "🗺️ Ratio trains en retard / trains programmés",
        "scale": "RdYlGn_r",
        "range": [0, df["ratio_retards"].max()]
    }
}

metrique = st.session_state.metrique
cfg = config[metrique]

st.subheader(cfg["title"])

fig = px.choropleth(
    df,
    geojson=geojson_url,
    locations="region",
    color=metrique,
    featureidkey="properties.nom",
    color_continuous_scale=cfg["scale"],
    range_color=cfg["range"],
    labels={metrique: cfg["label"]}
)

fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    geo_bgcolor="rgba(0,0,0,0)"
)
fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)"
)

st.plotly_chart(fig, width='stretch')
st.caption("ℹ️ Les TER ne desservent pas l'Île-de-France, couverte par le réseau Transilien.")