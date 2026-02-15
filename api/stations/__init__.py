"""
/api/stations — Returns all pay station data for the map dashboard.

This Azure Function queries the Fabric SQL Endpoint for pay station records
and returns a compact JSON array optimized for the Leaflet map.

Supports optional query parameters:
  - area: Filter by neighborhood (e.g., ?area=Belltown)

Results are cached for 5 minutes to reduce Fabric load.
"""

import json
import logging
import azure.functions as func

# Import shared database helper (one level up)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_db import query_fabric


# The SQL query selects only the columns needed for the map
STATIONS_SQL = """
SELECT
    UNITID,
    PAIDAREA,
    SUBAREA,
    MODEL,
    CATEGORY,
    WKD_RATE1,
    SAT_RATE1,
    START_TIME_WKD,
    END_TIME_WKD,
    SHAPE_LNG,
    SHAPE_LAT,
    SIDE
FROM [dbo].[sdot_pay_stations]
WHERE SHAPE_LAT IS NOT NULL
  AND SHAPE_LNG IS NOT NULL
ORDER BY PAIDAREA, UNITID
"""


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("API /stations called")

    try:
        # Query Fabric with caching
        rows = query_fabric(STATIONS_SQL, cache_key="all_stations")

        # Optional: filter by area if query param provided
        area_filter = req.params.get("area")
        if area_filter:
            rows = [r for r in rows if r.get("PAIDAREA") == area_filter]

        # Transform to compact format for the frontend
        stations = []
        for r in rows:
            stations.append({
                "id": r.get("UNITID", ""),
                "area": r.get("PAIDAREA", "") or "Unknown",
                "sub": r.get("SUBAREA", "") or "",
                "model": r.get("MODEL", "") or "Unknown",
                "cat": r.get("CATEGORY", "") or "Other",
                "wkd": float(r.get("WKD_RATE1") or 0),
                "sat": float(r.get("SAT_RATE1") or 0),
                "shr": r.get("START_TIME_WKD", "") or "",
                "ehr": r.get("END_TIME_WKD", "") or "",
                "lng": float(r.get("SHAPE_LNG") or 0),
                "lat": float(r.get("SHAPE_LAT") or 0),
            })

        return func.HttpResponse(
            body=json.dumps(stations),
            mimetype="application/json",
            status_code=200,
            headers={"Cache-Control": "public, max-age=300"}  # Browser cache 5 min
        )

    except Exception as e:
        logging.error(f"Error querying Fabric: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Failed to fetch station data", "detail": str(e)}),
            mimetype="application/json",
            status_code=500
        )
