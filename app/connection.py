import os
from databricks import sql
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def get_connection():
    try:
        import databricks.sdk.runtime as sdk
        dbutils = sdk.dbutils
        server_hostname = dbutils.secrets.get(scope="my_app_scope", key="DATABRICKS_HOST")
        http_path       = dbutils.secrets.get(scope="my_app_scope", key="DATABRICKS_HTTP")
        access_token    = dbutils.secrets.get(scope="my_app_scope", key="DATABRICKS_TOKEN")
    except Exception:
        server_hostname = os.getenv("DATABRICKS_HOST")
        http_path       = os.getenv("DATABRICKS_HTTP")
        access_token    = os.getenv("DATABRICKS_TOKEN")
    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token
    )

def run_query(query: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)