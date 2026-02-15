# SDOT Parking Dashboard — Deployment Guide

## Architecture Overview

```
Browser → Azure Static Web App (Free) → Azure Function (Serverless)
                                              ↓
                                    Microsoft Fabric SQL Endpoint
                                       (SDOT_Parking Lakehouse)
```

**What each part does:**
- **Azure Static Web App**: Hosts your HTML/CSS/JS dashboard (free tier)
- **Azure Function**: Serverless Python API that queries Fabric and returns JSON
- **Fabric SQL Endpoint**: Your existing data source (no changes needed)

---

## Prerequisites

1. **Azure subscription** (you already have this)
2. **Azure CLI** installed on your Mac:
   ```bash
   brew install azure-cli
   ```
3. **GitHub account** (for deployment pipeline — free)
4. **Your Fabric SQL Endpoint URL** (looks like: `xxxxx.datawarehouse.fabric.microsoft.com`)

---

## Step-by-Step Deployment

### Step 1: Find Your Fabric SQL Endpoint URL

1. Go to **Microsoft Fabric** portal (app.fabric.microsoft.com)
2. Open your **SDOT_Parking** Lakehouse
3. Click **SQL analytics endpoint** in the top bar
4. Copy the **Server** URL from the connection string
   - It looks like: `abcdefg.datawarehouse.fabric.microsoft.com`

### Step 2: Create a GitHub Repository

1. Go to github.com and create a new repository called `sdot-parking-dashboard`
2. Push the project code:
   ```bash
   cd ~/Downloads/sdot-parking-app
   git init
   git add .
   git commit -m "Initial commit: SDOT Parking Dashboard"
   git remote add origin https://github.com/YOUR_USERNAME/sdot-parking-dashboard.git
   git push -u origin main
   ```

### Step 3: Create the Azure Static Web App

**Option A: Azure Portal (Recommended for beginners)**

1. Go to **portal.azure.com**
2. Click **Create a resource** → search **Static Web App**
3. Fill in:
   - **Name**: `sdot-parking-dashboard`
   - **Plan**: Free
   - **Region**: West US 2 (closest to Seattle)
   - **Source**: GitHub
   - **Organization**: Your GitHub account
   - **Repository**: `sdot-parking-dashboard`
   - **Branch**: `main`
   - **Build Presets**: Custom
   - **App location**: `/src`
   - **API location**: `/api`
   - **Output location**: (leave blank)
4. Click **Create**

This will automatically:
- Create the Static Web App resource
- Add a GitHub Actions workflow to your repo
- Deploy on every push to `main`

**Option B: Azure CLI**
```bash
az login
az staticwebapp create \
  --name sdot-parking-dashboard \
  --resource-group YOUR_RESOURCE_GROUP \
  --source https://github.com/YOUR_USERNAME/sdot-parking-dashboard \
  --location "westus2" \
  --branch main \
  --app-location "/src" \
  --api-location "/api" \
  --login-with-github
```

### Step 4: Configure Environment Variables

In the Azure Portal:
1. Go to your Static Web App → **Configuration**
2. Add these **Application settings**:
   - `FABRIC_SQL_SERVER` = `your-server.datawarehouse.fabric.microsoft.com`
   - `FABRIC_DATABASE` = `SDOT_Parking`
3. Click **Save**

### Step 5: Enable Managed Identity

This allows the Azure Function to authenticate to Fabric without passwords.

1. Go to your Static Web App → **Identity**
2. Under **System assigned**, toggle to **On** → Click **Save**
3. Copy the **Object ID** that appears
4. Go to **Microsoft Fabric** portal:
   - Open your Workspace settings
   - Under **Manage access**, add the Object ID as a **Member**
   - This gives the Azure Function permission to query your Lakehouse

### Step 6: Set Up Azure AD Authentication (Optional but Recommended)

To restrict access to your team only:

1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Click **New registration**:
   - Name: `SDOT Parking Dashboard`
   - Redirect URI: `https://YOUR-APP-NAME.azurestaticapps.net/.auth/login/aad/callback`
3. Copy the **Application (client) ID** and **Directory (tenant) ID**
4. Create a **Client secret** under Certificates & secrets
5. Go back to your Static Web App → **Configuration**, add:
   - `AAD_CLIENT_ID` = your client ID
   - `AAD_CLIENT_SECRET` = your client secret
6. Update `staticwebapp.config.json` — replace `<YOUR_TENANT_ID>` with your actual tenant ID
7. Commit and push the change

### Step 7: Verify Deployment

1. Go to your Static Web App in Azure Portal
2. Click the **URL** (e.g., `https://sdot-parking-dashboard.azurestaticapps.net`)
3. You should see:
   - The "Connecting to Microsoft Fabric..." loading spinner
   - Then the map populates with live station data
   - The "Live Data" badge pulses green in the header

---

## How It Works After Deployment

| Event | What Happens |
|---|---|
| **User opens dashboard** | Browser loads HTML from Azure Static Web App |
| **Page loads** | JavaScript calls `/api/stations` and `/api/curb-stats` |
| **Azure Function receives request** | Checks 5-minute cache. If stale, queries Fabric SQL Endpoint |
| **Fabric returns data** | Function transforms to JSON, sends to browser |
| **Dashboard renders** | Map markers, charts, and stats update with live data |
| **Every 5 minutes** | Dashboard auto-refreshes data in the background |
| **Data updates in Fabric** | Next dashboard refresh picks up new data automatically |

---

## Embedding in SharePoint / Teams

### SharePoint:
1. Edit your SharePoint page
2. Add a **Web Part** → choose **Embed**
3. Paste your Static Web App URL
4. Save

### Microsoft Teams:
1. In a Teams channel, click **+** (Add tab)
2. Choose **Website**
3. Paste your Static Web App URL
4. Name it "SDOT Parking Dashboard"

---

## Cost Estimate

| Component | Monthly Cost |
|---|---|
| Azure Static Web App (Free tier) | **$0** |
| Azure Functions (included with SWA) | **$0** (up to 1M executions) |
| Fabric SQL Endpoint | **Already paid** (part of your Fabric capacity) |
| Azure AD | **$0** (included with Azure) |
| **Total** | **$0/month** |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "Failed to fetch station data" | Check that Managed Identity has Fabric workspace access |
| 401 Unauthorized | Verify Azure AD app registration and redirect URI |
| ODBC driver not found | Azure Functions Linux host includes ODBC 18 by default |
| Data is stale | Cache TTL is 5 minutes — wait or restart the Function App |
| Map doesn't load | Check browser console for CORS errors; CSP headers may need updating |

---

## Updating the Dashboard

To make changes to the dashboard:

1. Edit files in `src/index.html` (frontend) or `api/` (backend)
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update dashboard"
   git push
   ```
3. GitHub Actions automatically redeploys in ~2 minutes

---

## Next Steps / Enhancements

- **Add occupancy data**: If you get real-time occupancy sensors, add a heatmap layer
- **Historical trends**: Add a time-series chart showing rate changes over time
- **Alert notifications**: Use Fabric Data Activator to trigger alerts when stations go offline
- **Mobile PWA**: Add a service worker manifest to make it installable on phones
- **Export to PDF**: Add a "Download Report" button that generates a PDF snapshot
