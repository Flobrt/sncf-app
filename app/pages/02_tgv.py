import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from connection import run_query

st.set_page_config(page_title="SNCF Dashboard - TGV", layout="wide")
st.title("🚄 Dashboard Régularité TGV")

@st.cache_data
def load_tgv():
    return run_query("""
        SELECT 
            t.gare_depart,
            t.gare_arrivee,
            AVG(t.retard_moyen_arrivee)  as retard_moyen,
            SUM(t.total_annules)         as total_annules,
            g1.latitude                  as lat_depart,
            g1.longitude                 as lon_depart,
            g2.latitude                  as lat_arrivee,
            g2.longitude                 as lon_arrivee
        FROM transport.gold.mart_retards_tgv t
        LEFT JOIN transport.gold.gare_tgv g1 ON LOWER(t.gare_depart)  = g1.gare_depart
        LEFT JOIN transport.gold.gare_tgv g2 ON LOWER(t.gare_arrivee) = g2.gare_depart
        GROUP BY t.gare_depart, t.gare_arrivee,
                 g1.latitude, g1.longitude,
                 g2.latitude, g2.longitude
    """)

df = load_tgv()

# Boutons de sélection
col1, col2 = st.columns(2)
with col1:
    btn_retard = st.button("⏱️ Retard moyen", use_container_width=True)
with col2:
    btn_annules = st.button("❌ Trains annulés", use_container_width=True)

if "metrique_tgv" not in st.session_state:
    st.session_state.metrique_tgv = "retard_moyen"
if btn_retard:
    st.session_state.metrique_tgv = "retard_moyen"
if btn_annules:
    st.session_state.metrique_tgv = "total_annules"

metrique = st.session_state.metrique_tgv

config = {
    "retard_moyen": {
        "title": "🗺️ Retard moyen par liaison TGV",
        "label": "Retard moyen (min)"
    },
    "total_annules": {
        "title": "🗺️ Trains annulés par liaison TGV",
        "label": "Trains annulés"
    }
}

st.subheader(config[metrique]["title"])

# Transformation en format long
df_clean = df.dropna(subset=["lat_depart", "lon_depart", "lat_arrivee", "lon_arrivee"])

rows = []
for _, row in df_clean.iterrows():
    liaison = f"{row['gare_depart']} → {row['gare_arrivee']}"
    valeur = row[metrique]
    rows.append({"liaison": liaison, "lat": row["lat_depart"],  "lon": row["lon_depart"],  "valeur": valeur})
    rows.append({"liaison": liaison, "lat": row["lat_arrivee"], "lon": row["lon_arrivee"], "valeur": valeur})

df_plot = pd.DataFrame(rows)

# Normalisation pour la couleur
vmin = df_plot["valeur"].min()
vmax = df_plot["valeur"].max()

def valeur_to_color(valeur):
    ratio = (valeur - vmin) / (vmax - vmin) if vmax != vmin else 0
    r = int(255 * ratio)
    g = int(255 * (1 - ratio))
    return f"rgb({r},{g},0)"

# Construction de la carte
fig = go.Figure()

for liaison in df_plot["liaison"].unique():
    subset = df_plot[df_plot["liaison"] == liaison]
    valeur = subset["valeur"].iloc[0]
    couleur = valeur_to_color(valeur)
    fig.add_trace(go.Scattermap(
        lat=subset["lat"].tolist(),
        lon=subset["lon"].tolist(),
        mode="lines+markers",
        line=dict(width=2, color=couleur),
        marker=dict(size=4, color=couleur),
        hovertext=f"{liaison}<br>{config[metrique]['label']} : {valeur:.1f}",
        hoverinfo="text",
        showlegend=False
    ))

fig.update_layout(
    map=dict(
        style="carto-darkmatter",
        center=dict(lat=46.5, lon=2.5),
        zoom=4
    ),
    height=700,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)"
)

st.plotly_chart(fig, width='stretch')
st.caption("ℹ️ Données basées sur la régularité mensuelle TGV SNCF.")