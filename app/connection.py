import os
from databricks import sql
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def get_connection():
    try:
        w = WorkspaceClient()
        server_hostname = w.secrets.get_secret(scope="my_app_scope", key="DATABRICKS_HOST").value
        http_path       = w.secrets.get_secret(scope="my_app_scope", key="DATABRICKS_HTTP").value
        access_token    = w.secrets.get_secret(scope="my_app_scope", key="DATABRICKS_TOKEN").value
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