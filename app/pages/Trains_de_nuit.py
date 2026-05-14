import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from connection import run_query

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trains de nuit européens",
    layout="wide"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, .stApp { background-color: #0b0f1a; }
    .main { background-color: #0b0f1a; }

    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #e8c97a !important;
    }
    p, div, span, label {
        font-family: 'DM Sans', sans-serif;
    }

    .hero {
        padding: 24px 0 8px 0;
        border-bottom: 1px solid #1e2d45;
        margin-bottom: 20px;
    }
    .hero h1 { font-size: 2.2rem; margin-bottom: 4px; }
    .hero .subtitle {
        color: #6a85a0;
        font-size: 0.92rem;
        font-family: 'DM Sans', sans-serif;
        letter-spacing: 0.04em;
    }
    .block-container {
        padding-top: 1rem !important;
    }

    .badge {
        display: inline-block;
        background: #1e2d45;
        color: #7a9abf;
        border: 1px solid #2a3f5f;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.73rem;
        margin-right: 5px;
        font-family: 'DM Sans', sans-serif;
    }

    .info-box {
        color: #6a85a0;
        font-size: 0.86rem;
        line-height: 1.8;
        padding: 16px;
        background: #0f1825;
        border-radius: 10px;
        border: 1px solid #1e2d45;
        font-family: 'DM Sans', sans-serif;
    }

    .route-list-item {
        padding: 7px 12px;
        margin-bottom: 5px;
        background: #0f1825;
        border-radius: 6px;
        font-size: 0.81rem;
        color: #a8c0d6;
        font-family: 'DM Sans', sans-serif;
    }

    .section-title {
        color: #4a6580;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        margin: 16px 0 8px 0;
    }

    [data-testid="stSidebar"] { background-color: #080d16 !important; border-right: 1px solid #1e2d45; }
    [data-testid="stSidebar"] * { color: #a8c0d6 !important; font-family: 'DM Sans', sans-serif !important; }
    [data-testid="stSidebar"] h3 { color: #e8c97a !important; font-family: 'Playfair Display', serif !important; }

    div[data-testid="stSelectbox"] label { color: #6a85a0 !important; font-size: 0.82rem !important; }
    div[data-testid="stTextInput"] label { color: #6a85a0 !important; font-size: 0.82rem !important; }
    [data-testid="stIconMaterial"] {
        font-size: 0 !important;
    }
    [data-testid="stIconMaterial"]::after {
        content: "☰";
        font-size: 1.2rem;
        color: #e8c97a;
    }

    .stButton button {
        background: #1e2d45 !important;
        color: #e8c97a !important;
        border: 1px solid #2a3f5f !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.84rem !important;
    }
    .stButton button:hover {
        background: #2a3f5f !important;
        border-color: #e8c97a !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_night_trains():
    query = """
        SELECT 
            trip_id,
            route_long_name,
            route_short_name,
            stop_name,
            stop_lat,
            stop_lon,
            arrival_time,
            departure_time,
            stop_sequence
        FROM transport.gold.gtfs_gold_nuit
        WHERE jour_ou_nuit = '1'
        ORDER BY trip_id, stop_sequence
    """
    return run_query(query)

df = load_night_trains()

all_routes = sorted(df["route_long_name"].dropna().unique().tolist())
route_trips = {
    route: df[df["route_long_name"] == route]["trip_id"].unique().tolist()
    for route in all_routes
}

COLORS = [
    "#4a9eff","#ff6b6b","#51cf66","#ff922b","#cc5de8",
    "#20c997","#f06595","#74c0fc","#a9e34b","#fcc419",
    "#e599f7","#63e6be","#ff8787","#339af0","#8ce99a",
]
route_color = {r: COLORS[i % len(COLORS)] for i, r in enumerate(all_routes)}

# ── Session state ─────────────────────────────────────────────────────────────
if "selected_route" not in st.session_state:
    st.session_state.selected_route = None
if "selected_trip" not in st.session_state:
    st.session_state.selected_trip = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
#     st.markdown("### Filtres")
#     st.markdown("---")

    # search = st.text_input("Rechercher une ligne", placeholder="ex: Chopin, Nightjet…")
    # filtered_routes = (
    #     [r for r in all_routes if search.lower() in r.lower()]
    #     if search else all_routes
    # )

    # st.markdown(f'<div class="section-title">{len(filtered_routes)} ligne(s) disponible(s)</div>', unsafe_allow_html=True)
    # st.markdown("---")
    filtered_routes = all_routes

    show_all = st.toggle("Afficher toutes les lignes", value=True)
    st.markdown("---")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>Trains de nuit européens</h1>
    <p class="subtitle">Explorez les liaisons ferroviaires nocturnes à travers l'Europe</p>
</div>
""", unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
col_map, col_info = st.columns([3, 1.2])

selected_route = st.session_state.selected_route
selected_trip  = st.session_state.selected_trip

# ── Map ───────────────────────────────────────────────────────────────────────
with col_map:
    m = folium.Map(
        location=[48.5, 15.0],
        zoom_start=5,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    routes_to_draw = filtered_routes if show_all else ([selected_route] if selected_route else [])

    for route in routes_to_draw:
        is_selected = (route == selected_route)
        color   = "#e8c97a" if is_selected else route_color[route]
        weight  = 5 if is_selected else 2
        opacity = 1.0 if is_selected else 0.45
        z       = 20 if is_selected else 5

        for trip_id in route_trips[route]:
            trip_df = df[df["trip_id"] == trip_id].sort_values("stop_sequence")
            coords  = trip_df[["stop_lat", "stop_lon"]].dropna().values.tolist()
            if len(coords) < 2:
                continue

            folium.PolyLine(
                locations=coords,
                color=color,
                weight=weight,
                opacity=opacity,
                tooltip=f"{route} — {trip_id}",
                popup=folium.Popup(
                    f"<b style='color:#e8c97a'>{route}</b><br>"
                    f"<span style='color:#888'>{trip_id}</span><br>"
                    f"<span style='color:#666'>{len(trip_df)} arrêts</span>",
                    max_width=220,
                ),
                z_index_offset=z,
            ).add_to(m)

        if is_selected:
            for trip_id in route_trips[route]:
                trip_df = df[df["trip_id"] == trip_id].sort_values("stop_sequence")
                stops   = trip_df.dropna(subset=["stop_lat", "stop_lon"])

                for idx, (_, row) in enumerate(stops.iterrows()):
                    is_terminal = idx == 0 or idx == len(stops) - 1
                    folium.CircleMarker(
                        location=[row["stop_lat"], row["stop_lon"]],
                        radius=7 if is_terminal else 5,
                        color="#e8c97a" if is_terminal else "#ffffff",
                        fill=True,
                        fill_color="#e8c97a" if is_terminal else "#444444",
                        fill_opacity=1.0,
                        tooltip=f"{'🔴 ' if is_terminal else ''}{row['stop_name']} — {row.get('arrival_time', '?')}",
                        z_index_offset=30,
                    ).add_to(m)

    map_data = st_folium(m, width="100%", height=560, returned_objects=["last_object_clicked_tooltip"])

# ── Map click handler ─────────────────────────────────────────────────────────
tooltip_clicked = (map_data or {}).get("last_object_clicked_tooltip", "")
if tooltip_clicked:
    for route in all_routes:
        if route in tooltip_clicked:
            if st.session_state.selected_route != route:
                st.session_state.selected_route = route
                trips = route_trips[route]
                st.session_state.selected_trip = trips[0] if trips else None
                st.rerun()
            break

# ── Info panel ────────────────────────────────────────────────────────────────
with col_info:

    if selected_route:
        trips = route_trips[selected_route]

        if len(trips) > 1:
            selected_trip = st.selectbox(
                "Direction / Service",
                trips,
                index=trips.index(selected_trip) if selected_trip in trips else 0,
                key="trip_select",
            )
            st.session_state.selected_trip = selected_trip
        else:
            selected_trip = trips[0]
            st.session_state.selected_trip = selected_trip

        trip_df = (
            df[df["trip_id"] == selected_trip]
            .sort_values("stop_sequence")
            .dropna(subset=["stop_name"])
        )

        route_short = trip_df["route_short_name"].iloc[0] if not trip_df.empty else ""
        origine     = trip_df.iloc[0]["stop_name"]  if not trip_df.empty else "?"
        dest        = trip_df.iloc[-1]["stop_name"] if not trip_df.empty else "?"

        # ── Construction de la mini-timeline ─────────────────────────────────
        trip_df_clean = trip_df.drop_duplicates(subset=["stop_sequence"]).reset_index(drop=True)
        n_stops = len(trip_df_clean)

        timeline_parts = []
        timeline_parts.append(
            "<div style='"
            "max-height:210px;"
            "overflow-y:auto;"
            "padding-right:6px;"
            "scrollbar-width:thin;"
            "scrollbar-color:#1e2d45 transparent;"
            "'>"
        )

        for idx, (_, row) in enumerate(trip_df_clean.iterrows()):
            arr  = str(row.get("arrival_time",   "") or "")
            dep  = str(row.get("departure_time", "") or "")
            time = arr if arr and arr != "nan" else (dep if dep and dep != "nan" else "—")

            is_first = idx == 0
            is_last  = idx == n_stops - 1
            is_term  = is_first or is_last
            stop_name = str(row["stop_name"])

            if is_term:
                dot_bg     = "#e8c97a"
                dot_border = "#e8c97a"
                dot_size   = "10px"
                dot_margin = "0px"
                dot_shadow = "0 0 5px #e8c97a66"
                name_color = "#e8c97a"
                name_w     = "600"
                name_size  = "0.76rem"
                time_color = "#a8924a"
            else:
                dot_bg     = "#1e2d45"
                dot_border = "#3a5070"
                dot_size   = "7px"
                dot_margin = "1.5px"
                dot_shadow = "none"
                name_color = "#7a9abf"
                name_w     = "400"
                name_size  = "0.72rem"
                time_color = "#2e4560"

            if is_last:
                line = ""
            elif is_term:
                line = (
                    "<div style='width:1px; height:16px;"
                    "background:linear-gradient(#e8c97a55,#2a3f5f);"
                    "margin-left:4px; flex-shrink:0;'></div>"
                )
            else:
                line = (
                    "<div style='width:1px; height:16px;"
                    "background:#1e2d45;"
                    "margin-left:4px; flex-shrink:0;'></div>"
                )

            dot_style = (
                "width:" + dot_size + ";"
                "height:" + dot_size + ";"
                "border-radius:50%;"
                "background:" + dot_bg + ";"
                "border:1.5px solid " + dot_border + ";"
                "margin-top:" + dot_margin + ";"
                "flex-shrink:0;"
                "box-shadow:" + dot_shadow + ";"
            )

            timeline_parts.append(
                "<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:0px;'>"
                    "<div style='display:flex; flex-direction:column; align-items:center; min-width:10px;'>"
                        "<div style='" + dot_style + "'></div>"
                        + line +
                    "</div>"
                    "<div style='padding-bottom:0px; margin-top:-1px; min-width:0;'>"
                        "<div style='"
                            "color:" + name_color + ";"
                            "font-size:" + name_size + ";"
                            "font-family:DM Sans,sans-serif;"
                            "font-weight:" + name_w + ";"
                            "line-height:1.2;"
                            "white-space:nowrap;"
                            "overflow:hidden;"
                            "text-overflow:ellipsis;"
                            "max-width:120px;"
                        "'>" + stop_name + "</div>"
                        "<div style='"
                            "color:" + time_color + ";"
                            "font-size:0.68rem;"
                            "font-family:DM Sans,sans-serif;"
                            "margin-top:0px;"
                            "margin-bottom:2px;"
                        "'>" + time + "</div>"
                    "</div>"
                "</div>"
            )

        timeline_parts.append("</div>")
        timeline_html = "".join(timeline_parts)

        # ── Carte avec infos à gauche + timeline à droite ────────────────────
        card_html = (
            "<div style='"
            "background:linear-gradient(135deg,#131b2e 0%,#1a2640 100%);"
            "border:1px solid #2a3f5f;"
            "border-left:4px solid #e8c97a;"
            "border-radius:10px;"
            "padding:14px 16px;"
            "margin-bottom:12px;"
            "display:flex;"
            "gap:14px;"
            "align-items:flex-start;"
            "'>"

            # Colonne gauche — infos
            "<div style='flex:1; min-width:0;'>"
                "<div style='"
                "color:#e8c97a;"
                "font-size:1.0rem;"
                "font-weight:700;"
                "font-family:Playfair Display,serif;"
                "line-height:1.3;"
                "'>" + selected_route + "</div>"
                "<div style='"
                "color:#6a85a0;"
                "font-size:0.75rem;"
                "margin-top:3px;"
                "font-family:DM Sans,sans-serif;"
                "'>" + route_short + "</div>"
                "<div style='margin-top:8px;'>"
                    "<span class='badge'>🛤 " + str(n_stops) + " arrêts</span>"
                "</div>"
                "<div style='margin-top:2px;'>"
                    "<span class='badge'>🌙 Nuit</span>"
                "</div>"
                "<div style='"
                "margin-top:10px;"
                "color:#6a85a0;"
                "font-size:0.78rem;"
                "font-family:DM Sans,sans-serif;"
                "line-height:1.9;"
                "'>"
                    "<b style='color:#e8c97a'>De :</b> " + origine + "<br>"
                    "<b style='color:#e8c97a'>À :</b> " + dest +
                "</div>"
            "</div>"

            # Séparateur vertical
            "<div style='"
            "width:1px;"
            "background:#1e2d45;"
            "align-self:stretch;"
            "flex-shrink:0;"
            "'></div>"

            # Colonne droite — mini timeline
            "<div style='flex-shrink:0; max-width:140px;'>"
                + timeline_html +
            "</div>"

            "</div>"
        )

        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("")
        if st.button("↩ Réinitialiser la sélection", use_container_width=True):
            st.session_state.selected_route = None
            st.session_state.selected_trip  = None
            st.rerun()

    else:
        st.markdown("""
        <div class='info-box'>
            <b style='color:#e8c97a'>Cliquez sur une ligne</b> sur la carte pour voir le détail du trajet.<br><br>
            Utilisez le panneau latéral pour filtrer les lignes par nom.
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Toutes les lignes</div>', unsafe_allow_html=True)

        for route in filtered_routes[:30]:
            trips = route_trips[route]
            color = route_color[route]
            st.markdown(
                "<div class='route-list-item' style='border-left:3px solid " + color + ";'>"
                + route +
                "<span style='color:#2a3f5f; font-size:0.73rem;'> — " + str(len(trips)) + " service(s)</span>"
                "</div>",
                unsafe_allow_html=True
            )

        if len(filtered_routes) > 30:
            st.caption(f"… et {len(filtered_routes) - 30} autres lignes")
