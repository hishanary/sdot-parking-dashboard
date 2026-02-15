"""
shared_db.py
Shared database connection helper for Azure Functions connecting to
Microsoft Fabric SQL Analytics Endpoint via Azure AD (Entra ID).

Uses DefaultAzureCredential for authentication, which works with:
  - Managed Identity (when deployed to Azure)
  - Azure CLI credentials (when developing locally)
  - Environment variables (for CI/CD)

Includes a simple in-memory cache to avoid hitting Fabric on every request.
"""

import os
import json
import time
import pyodbc
from azure.identity import DefaultAzureCredential

# ── Configuration ──
FABRIC_SQL_SERVER = os.environ.get("FABRIC_SQL_SERVER", "")
FABRIC_DATABASE = os.environ.get("FABRIC_DATABASE", "SDOT_Parking")

# Cache: store query results in memory for N seconds
# Azure Functions keep the process warm for ~10 minutes, so this works well
CACHE_TTL_SECONDS = 300  # 5-minute cache
_cache = {}


def get_connection():
    """
    Create a pyodbc connection to Microsoft Fabric SQL Endpoint
    using Azure AD token-based authentication.
    """
    # Get an Azure AD token for SQL Database scope
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default")

    # Build the connection string
    # Fabric SQL endpoints use TDS (Tabular Data Stream) protocol
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={FABRIC_SQL_SERVER};"
        f"DATABASE={FABRIC_DATABASE};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )

    # pyodbc needs the token as a bytes struct for Azure AD auth
    import struct
    token_bytes = token.token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
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
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

    # Update cache
    if cache_key:
        _cache[cache_key] = (time.time(), results)

    return results
