import os
from databricks import sql
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
import pandas as pd

import base64

def get_secret(w, scope, key):
    secret = w.secrets.get_secret(scope=scope, key=key)
    value = secret.value
    # Décoder si base64
    try:
        decoded = base64.b64decode(value).decode("utf-8")
        return decoded
    except Exception:
        return value

load_dotenv()

def get_connection():
    try:
        w = WorkspaceClient()
        server_hostname = get_secret(w, "my_app_scope", "DATABRICKS_HOST")
        http_path       = get_secret(w, "my_app_scope", "DATABRICKS_HTTP")
        access_token    = get_secret(w, "my_app_scope", "DATABRICKS_TOKEN")
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