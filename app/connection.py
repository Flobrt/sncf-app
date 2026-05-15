import os
from databricks import sql
import pandas as pd
import streamlit as st


def get_connection():
    try:
        server_hostname = st.secrets["DATABRICKS_HOST"]
        http_path       = st.secrets["DATABRICKS_HTTP"]
        access_token    = st.secrets["DATABRICKS_TOKEN"]
        print("✅ Secrets Databricks chargés")
    except Exception as e:
        print(f"⚠️ Fallback .env : {e}")
        server_hostname = os.getenv("DATABRICKS_HOST")
        http_path       = os.getenv("DATABRICKS_HTTP")
        access_token    = os.getenv("DATABRICKS_TOKEN")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
        _socket_timeout=120
    )

def run_query(query: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)