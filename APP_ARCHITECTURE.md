# SDOT Parking Dashboard — App Architecture Guide

> A plain-language explanation of how this application works, written for non-developers.

---

## What Does This App Do?

This app is an **interactive map dashboard** that shows Seattle's on-street parking infrastructure. It pulls **live data** from your Microsoft Fabric Lakehouse and displays it on a map with filters, charts, and storytelling cards.

Every time someone opens the dashboard, it connects to Fabric, grabs the latest data, and renders it in the browser. No manual exports. No stale spreadsheets.

---

## The Three Pieces

Think of this app as a **restaurant**:

| Piece | Restaurant Analogy | What It Actually Is |
|---|---|---|
| **Frontend** | The dining room (what customers see) | The HTML dashboard with the map, filters, and charts |
| **Backend API** | The kitchen (prepares the food) | A small Python program that queries Fabric and formats the data |
| **Data Source** | The pantry (where ingredients are stored) | Your Microsoft Fabric Lakehouse with the parking tables |

The customer (your browser) never goes into the pantry directly. They ask the kitchen, and the kitchen fetches what's needed.

---

## How Data Flows

Here is the step-by-step journey of data from Fabric to your screen:

```
  YOU (open browser)
   │
   ▼
┌──────────────────────────────────────────┐
│  1. FRONTEND (Azure Static Web App)      │
│     Your browser loads the HTML page     │
│     with the map, filters, and charts.   │
│                                          │
│     The page says:                       │
│     "I need data! Let me call the API."  │
│                                          │
│     It sends a request to /api/stations  │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  2. BACKEND API (Azure Function)         │
│     A small Python program wakes up.     │
│                                          │
│     It checks: "Do I have recent data    │
│     in my 5-minute cache?"               │
│                                          │
│     NO → It connects to Fabric and       │
│          runs a SQL query.               │
│     YES → It returns the cached data     │
│           instantly (saves time).         │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  3. DATA SOURCE (Microsoft Fabric)       │
│     The Fabric SQL Endpoint receives     │
│     the query and runs it against your   │
│     Lakehouse tables:                    │
│                                          │
│     • sdot_pay_stations (1,628 rows)     │
│     • Curb_Space_Categorieskmz (39,819)  │
│                                          │
│     It returns the results as a table.   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  4. RESPONSE (back to the browser)       │
│     The API converts the table into      │
│     JSON (a format browsers understand)  │
│     and sends it back to the frontend.   │
│                                          │
│     The frontend places markers on the   │
│     map, populates charts, and updates   │
│     the KPI numbers.                     │
│                                          │
│     Total time: 1-3 seconds.             │
└──────────────────────────────────────────┘
```

---

## What Lives Where

### Your Computer (Development Only)

During development, all the code lives on your Mac. Once deployed, you never need your computer to keep the app running.

```
sdot-parking-app/
│
├── src/                          ← FRONTEND (what users see)
│   └── index.html                   The entire dashboard in one file:
│                                    map, filters, charts, story cards.
│
├── api/                          ← BACKEND (the "kitchen")
│   ├── shared_db.py                 Connects to Fabric using your
│   │                                Azure credentials. Includes
│   │                                a 5-minute cache so it doesn't
│   │                                query Fabric on every single click.
│   │
│   ├── stations/                    API ENDPOINT #1
│   │   └── __init__.py              When the dashboard asks for
│   │                                station data, this code runs.
│   │                                It returns all 1,628 pay stations
│   │                                with their location, rate, model, etc.
│   │
│   ├── curb-stats/                  API ENDPOINT #2
│   │   └── __init__.py              When the dashboard asks for curb
│   │                                space stats, this code runs.
│   │                                It returns aggregated counts
│   │                                by neighborhood and category.
│   │
│   ├── requirements.txt             List of Python libraries needed
│   ├── host.json                    Azure Functions configuration
│   └── local.settings.json          Connection settings (server URL,
│                                    database name). You fill these in.
│
├── staticwebapp.config.json      ← SECURITY RULES
│                                    Controls who can access the app.
│                                    Configured for Azure AD (your org's
│                                    Microsoft login). Only your team
│                                    members can see the dashboard.
│
├── .github/workflows/deploy.yml  ← AUTO-DEPLOY PIPELINE
│                                    Every time you push code to GitHub,
│                                    this automatically deploys the new
│                                    version. No manual steps needed.
│
├── DEPLOYMENT_GUIDE.md           ← Step-by-step setup instructions
└── APP_ARCHITECTURE.md           ← This file
```

---

## Where It Runs in the Cloud

Once deployed, nothing runs on your computer. Everything lives in Azure:

```
┌─────────────────────────────────────────────────────────┐
│                     AZURE CLOUD                          │
│                                                          │
│  ┌────────────────────────────┐                          │
│  │  Azure Static Web App      │  Hosts your HTML page.   │
│  │  (Free Tier)               │  Serves it to browsers.  │
│  │                            │  Always on. No servers    │
│  │  Your dashboard lives here │  to manage.               │
│  └────────────┬───────────────┘                          │
│               │                                          │
│  ┌────────────▼───────────────┐                          │
│  │  Azure Function            │  Runs your Python code.  │
│  │  (Serverless)              │  Wakes up only when       │
│  │                            │  someone opens the page.  │
│  │  Your API lives here       │  Sleeps the rest of the  │
│  └────────────┬───────────────┘  time. Costs nothing.    │
│               │                                          │
│  ┌────────────▼───────────────┐                          │
│  │  Azure AD (Entra ID)       │  Handles login.          │
│  │                            │  Only people in your      │
│  │                            │  organization can access.  │
│  └────────────────────────────┘                          │
│                                                          │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────┐
    │  Microsoft Fabric            │
    │  Lakehouse SQL Endpoint      │  Your data. Already exists.
    │                              │  No changes needed.
    │  SDOT_Parking database       │
    └──────────────────────────────┘
```

---

## Key Concepts Explained

### What is "Serverless"?

Traditional apps need a computer (server) running 24/7, even when no one is using it. **Serverless** means Azure manages the computer for you. It only runs your code when someone actually opens the dashboard. The rest of the time, it costs nothing.

### What is an API?

An API is a **request-and-response system**. Your dashboard (the frontend) says: *"Give me all the parking stations."* The API (the backend) responds with the data in a format the dashboard understands (JSON). Think of it like ordering at a drive-through window.

### What is Caching?

When the API gets data from Fabric, it **remembers the answer for 5 minutes**. If another person opens the dashboard within that window, the API serves the remembered answer instantly instead of querying Fabric again. This makes the app faster and reduces load on your Lakehouse.

### What is Azure AD Authentication?

Azure AD (now called Entra ID) is your organization's login system — the same Microsoft account you use for Outlook, Teams, and SharePoint. The dashboard uses this to verify that only people in your organization can access it. No separate usernames or passwords needed.

### What is a GitHub Actions Pipeline?

A pipeline is an **automatic deployment process**. When you change the code and push it to GitHub, the pipeline:
1. Detects the change
2. Packages your code
3. Uploads it to Azure
4. The new version goes live in about 2 minutes

You never have to manually copy files or click "deploy" buttons.

---

## How Data Stays Fresh

```
Monday 8:00 AM    Your Fabric pipeline loads new parking data
Monday 8:01 AM    Data is now in the Lakehouse

Monday 9:00 AM    Alice opens the dashboard
                  → API queries Fabric → Gets Monday's data
                  → Caches it for 5 minutes

Monday 9:02 AM    Bob opens the dashboard
                  → API serves cached data (instant, no Fabric query)

Monday 9:06 AM    Carol opens the dashboard
                  → Cache expired → API queries Fabric again
                  → Gets the same Monday data (still fresh)

Tuesday 8:00 AM   Fabric pipeline loads Tuesday's data

Tuesday 9:00 AM   Dave opens the dashboard
                  → API queries Fabric → Gets Tuesday's data
                  → Dashboard automatically shows the new numbers
```

No one had to re-export anything. No one had to rebuild the HTML. The data flows automatically.

---

## Monthly Cost

| Component | What It Does | Cost |
|---|---|---|
| Azure Static Web App | Hosts the HTML dashboard | **Free** |
| Azure Function | Runs the Python API | **Free** (up to 1 million requests/month) |
| Azure AD | Handles team login | **Free** (included with your Azure subscription) |
| Fabric SQL Endpoint | Stores and serves data | **Already paid** (part of your Fabric capacity) |
| GitHub | Stores code + auto-deploys | **Free** |
| **Total** | | **$0/month** |

---

---

## Adapting This App for a Different Fabric Warehouse

Want to build a similar live dashboard for a different dataset in Fabric? Follow this guide to reuse the same architecture with your own tables.

### What You Need Before Starting

- A **Fabric Lakehouse or Warehouse** with tables you want to visualize
- The **SQL Endpoint URL** for that Lakehouse
- The **database name** and **table names** you want to query
- An idea of what your dashboard should show (map? charts? table?)

### Step 1: Copy the Project

Duplicate the entire `sdot-parking-app` folder and rename it:

```bash
cp -r sdot-parking-app  my-new-dashboard-app
```

### Step 2: Update the Connection Settings

Open `api/local.settings.json` and change:

```json
{
  "Values": {
    "FABRIC_SQL_SERVER": "YOUR_NEW_SERVER.datawarehouse.fabric.microsoft.com",
    "FABRIC_DATABASE": "YOUR_DATABASE_NAME"
  }
}
```

**How to find these values:**
1. Go to app.fabric.microsoft.com
2. Open your Lakehouse
3. Click the SQL analytics endpoint
4. The server URL and database name are shown in the connection properties

### Step 3: Update the SQL Queries

This is the most important step. You need to tell the API **what data to fetch** from your tables.

Open `api/stations/__init__.py` (or rename this folder to match your data). Find the SQL query at the top:

```python
# BEFORE (SDOT parking)
STATIONS_SQL = """
SELECT UNITID, PAIDAREA, MODEL, SHAPE_LNG, SHAPE_LAT
FROM [dbo].[sdot_pay_stations]
WHERE SHAPE_LAT IS NOT NULL
"""
```

Replace it with a query for YOUR tables:

```python
# EXAMPLE: Traffic signals
SIGNALS_SQL = """
SELECT SignalID, IntersectionName, Latitude, Longitude, SignalType, Status
FROM [dbo].[traffic_signals]
WHERE Latitude IS NOT NULL
"""
```

```python
# EXAMPLE: Transit stops
STOPS_SQL = """
SELECT StopID, StopName, RouteName, Ridership, Lat, Lng
FROM [dbo].[transit_stops]
ORDER BY Ridership DESC
"""
```

```python
# EXAMPLE: Crash data
CRASHES_SQL = """
SELECT IncidentID, Location, Severity, CrashDate, Latitude, Longitude
FROM [dbo].[crash_reports]
WHERE YEAR(CrashDate) = 2025
"""
```

Then update the Python code that **transforms the rows into JSON**. Match the field names to your columns:

```python
# BEFORE (parking stations)
stations.append({
    "id": r.get("UNITID"),
    "area": r.get("PAIDAREA"),
    "lat": float(r.get("SHAPE_LAT")),
    "lng": float(r.get("SHAPE_LNG")),
})

# AFTER (your data — example: traffic signals)
signals.append({
    "id": r.get("SignalID"),
    "name": r.get("IntersectionName"),
    "type": r.get("SignalType"),
    "lat": float(r.get("Latitude")),
    "lng": float(r.get("Longitude")),
})
```

### Step 4: Update the Frontend Dashboard

Open `src/index.html` and modify the JavaScript to match your new data format.

**Change the API endpoint call:**
```javascript
// BEFORE
const res = await fetch('/api/stations');

// AFTER
const res = await fetch('/api/signals');  // match your API folder name
```

**Change the map marker popups:**
```javascript
// BEFORE
marker.bindPopup(`
  <div class="popup-title">${s.id}</div>
  <div class="popup-area">${s.area}</div>
`);

// AFTER (example: traffic signals)
marker.bindPopup(`
  <div class="popup-title">${s.name}</div>
  <div class="popup-area">Type: ${s.type}</div>
`);
```

**Change the marker colors** to match your data categories:
```javascript
// BEFORE (colored by parking rate)
function rateColor(rate) {
  if (rate <= 1.0) return '#10B981';  // green
  if (rate <= 1.5) return '#F59E0B';  // amber
  return '#EF4444';                    // red
}

// AFTER (example: colored by signal type)
function signalColor(type) {
  if (type === 'Actuated') return '#10B981';
  if (type === 'Fixed-Time') return '#F59E0B';
  if (type === 'Adaptive') return '#0EA5E9';
  return '#6B7280';
}
```

**Update the map center** to your area of interest:
```javascript
// BEFORE (Seattle)
map.setView([47.615, -122.34], 13);

// AFTER (example: Olympia, WA)
map.setView([47.037, -122.900], 13);

// AFTER (example: Tacoma, WA)
map.setView([47.253, -122.444], 13);
```

**Update filters, charts, KPIs, and story cards** to reflect your data. The patterns are the same — just change the labels, field names, and values.

### Step 5: Add or Remove API Endpoints

If your dashboard needs **different data queries**, you can add new API endpoints:

```
api/
├── shared_db.py            ← Keep this (handles Fabric connection)
├── my-endpoint-1/          ← Rename or create new folders
│   ├── __init__.py         ← Your Python query logic
│   └── function.json       ← Route configuration
├── my-endpoint-2/
│   ├── __init__.py
│   └── function.json
```

Each folder becomes a URL: `/api/my-endpoint-1`, `/api/my-endpoint-2`, etc.

The `function.json` file for each endpoint looks the same — just change the route name:

```json
{
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get"],
      "route": "my-endpoint-1"
    },
    { "type": "http", "direction": "out", "name": "$return" }
  ]
}
```

### Step 6: Deploy

Follow the same deployment steps from `DEPLOYMENT_GUIDE.md`, but with your new project name and Fabric connection settings.

### Quick Reference: What to Change for Each New Project

| File | What to Change |
|---|---|
| `api/local.settings.json` | Fabric server URL and database name |
| `api/stations/__init__.py` | SQL query and JSON field mapping |
| `api/curb-stats/__init__.py` | Second SQL query (or delete if not needed) |
| `src/index.html` | Map center, filters, popups, charts, KPIs, story text |
| `staticwebapp.config.json` | Tenant ID (only if using a different Azure AD tenant) |
| `.github/workflows/deploy.yml` | Usually no changes needed |
| `api/shared_db.py` | Usually no changes needed |

### Example: What a Transit Dashboard Adaptation Looks Like

```
SDOT Parking Dashboard              Your Transit Dashboard
─────────────────────               ──────────────────────
Table: sdot_pay_stations     →      Table: transit_stops
Map markers: pay stations    →      Map markers: bus stops
Color by: rate/hr            →      Color by: daily ridership
Filters: neighborhood, rate  →      Filters: route, ridership range
KPIs: stations, avg rate     →      KPIs: stops, avg ridership
Story: "The $1 Question"     →      Story: "The Busiest Stop"
```

The **architecture is identical**. Only the data and labels change.

---

## Questions?

If anything in this guide is unclear, ask Claude Code to explain it further. You can also reference the `DEPLOYMENT_GUIDE.md` for the step-by-step deployment instructions.
