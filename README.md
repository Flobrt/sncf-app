# SNCF Explorer

> Application de visualisation des données ferroviaires françaises et européennes    
> Données issues d'un pipeline Databricks (architecture Médaillon Bronze → Silver → Gold)  
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dxsut6nczidnmagqj6vcy2.streamlit.app/)
[![GitHub](https://img.shields.io/badge/GitHub-sncf--pipeline-black?logo=github)](https://github.com/Flobrt/sncf-pipeline) 

---

## Fonctionnalités

### Destinations depuis une gare
- Sélectionne une gare de départ
- Visualise toutes les destinations atteignables sur une carte interactive
- Détail des trains disponibles

### Trains de nuit en Europe
- Carte de toutes les lignes de nuit européennes
- Informations par ligne (opérateur, trajet, fréquence)

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Framework | Streamlit |
| Carte interactive | Folium |
| Traitement données | Pandas |
| Source de données | Databricks (tables Delta) |
| Hébergement | Streamlit Community Cloud |

---

## Aperçu

<img src="screenshots/destinations.png" width="700"/>
<img src="screenshots/trains_nuit.png" width="700"/>

---

## Contact

[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)](https://www.linkedin.com/in/florian-berthelot-ba2252173/)  
