"""
shared_db.py
Shared database connection helper for Azure Functions connecting to
Microsoft Fabric SQL Analytics Endpoint via Azure AD (Entra ID).

Uses a Service Principal (App Registration) for authentication:
  - AZURE_TENANT_ID: Your Azure AD tenant ID
  - AZURE_CLIENT_ID: The App Registration's Application (client) ID
  - AZURE_CLIENT_SECRET: The App Registration's client secret

Includes a simple in-memory cache to avoid hitting Fabric on every request.
"""

import os
import time
import pymssql
from azure.identity import ClientSecretCredential

# ── Configuration ──
FABRIC_SQL_SERVER = os.environ.get("FABRIC_SQL_SERVER", "")
FABRIC_DATABASE = os.environ.get("FABRIC_DATABASE", "SDOT_Parking")

# Service Principal credentials
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")

# Cache: store query results in memory for N seconds
# Azure Functions keep the process warm for ~10 minutes, so this works well
CACHE_TTL_SECONDS = 300  # 5-minute cache
_cache = {}


def get_connection():
    """
    Create a pymssql connection to Microsoft Fabric SQL Endpoint
    using a Service Principal (App Registration) for authentication.
    """
    # Get an Azure AD token using the Service Principal
    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET
    )
    token = credential.get_token("https://database.windows.net/.default")

    # pymssql can connect using the access token directly
    conn = pymssql.connect(
        server=FABRIC_SQL_SERVER,
        database=FABRIC_DATABASE,
        tds_version="7.4",
        port=1433,
        user="token",
        password=token.token
    )
    return conn


def query_fabric(sql, cache_key=None):
    """
    Execute a SQL query against Fabric and return results as a list of dicts.

    Args:
        sql: The SQL query string to execute
        cache_key: Optional cache key. If provided, results are cached for CACHE_TTL_SECONDS.

    Returns:
        List of dictionaries, one per row
    """
    # Check cache first
    if cache_key and cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    # Execute query
    conn = get_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(sql)
        results = cursor.fetchall()
    finally:
        conn.close()

    # Update cache
    if cache_key:
        _cache[cache_key] = (time.time(), results)

    return results
