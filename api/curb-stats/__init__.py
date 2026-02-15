"""
/api/curb-stats — Returns aggregated curb space statistics by neighborhood.

Queries the Curb_Space_Categorieskmz table and aggregates by PAIDAREA and CATEGORY.
Results are cached for 5 minutes.
"""

import json
import logging
import azure.functions as func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_db import query_fabric


CURB_SQL = """
SELECT
    PAIDAREA,
    SUM(CASE WHEN CATEGORY = 'PAID' THEN 1 ELSE 0 END) AS paid,
    SUM(CASE WHEN CATEGORY = 'NP' THEN 1 ELSE 0 END) AS np,
    SUM(CASE WHEN CATEGORY = 'NS' THEN 1 ELSE 0 END) AS ns,
    SUM(CASE WHEN CATEGORY = 'LOAD' THEN 1 ELSE 0 END) AS load_zones,
    SUM(CASE WHEN CATEGORY = 'RPZ' THEN 1 ELSE 0 END) AS rpz,
    SUM(CASE WHEN CATEGORY = 'BUS' THEN 1 ELSE 0 END) AS bus,
    SUM(CASE WHEN CATEGORY = 'DP' THEN 1 ELSE 0 END) AS dp,
    COUNT(*) AS total
FROM [dbo].[Curb_Space_Categorieskmz]
WHERE PAIDAREA IS NOT NULL AND PAIDAREA != ''
GROUP BY PAIDAREA
ORDER BY total DESC
"""


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("API /curb-stats called")

    try:
        rows = query_fabric(CURB_SQL, cache_key="curb_stats")

        # Build a dictionary keyed by neighborhood
        result = {}
        for r in rows:
            area = r.get("PAIDAREA", "Unknown")
            result[area] = {
                "paid": r.get("paid", 0),
                "np": r.get("np", 0),
                "ns": r.get("ns", 0),
                "load": r.get("load_zones", 0),
                "rpz": r.get("rpz", 0),
                "bus": r.get("bus", 0),
                "dp": r.get("dp", 0),
                "total": r.get("total", 0),
            }

        return func.HttpResponse(
            body=json.dumps(result),
            mimetype="application/json",
            status_code=200,
            headers={"Cache-Control": "public, max-age=300"}
        )

    except Exception as e:
        logging.error(f"Error querying Fabric: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Failed to fetch curb stats", "detail": str(e)}),
            mimetype="application/json",
            status_code=500
        )
