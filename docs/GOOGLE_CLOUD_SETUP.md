# Google Cloud & BigQuery Setup Guide

This guide walks you through setting up Google Cloud credentials to use the Data Analysis Agent with BigQuery.

## Prerequisites

- A Google account
- Python 3.10+ installed

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., `data-analysis-agent`)
4. Click "Create"
5. Note your **Project ID** (you'll need this later)

## Step 2: Enable BigQuery API

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for "BigQuery API"
3. Click on it and press **Enable**

## Step 3: Install Google Cloud CLI

### Windows

Download the installer from: https://cloud.google.com/sdk/docs/install

Or via PowerShell:
```powershell
# Download the installer
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")

# Run the installer
Start-Process "$env:Temp\GoogleCloudSDKInstaller.exe" -Wait
```

### macOS

```bash
# Using Homebrew
brew install --cask google-cloud-sdk
```

### Linux

```bash
# Debian/Ubuntu
sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

## Step 4: Authenticate with Google Cloud

### Option A: Application Default Credentials (Recommended for Development)

This is the simplest method for local development:

```bash
# Initialize gcloud (first time only)
gcloud init

# Login and set up application default credentials
gcloud auth application-default login
```

This will:
1. Open a browser for you to log in with your Google account
2. Create credentials at `~/.config/gcloud/application_default_credentials.json`
3. The BigQuery client will automatically use these credentials

### Option B: Service Account (Recommended for Production)

1. Go to **IAM & Admin** → **Service Accounts** in Cloud Console
2. Click **Create Service Account**
3. Name it (e.g., `bigquery-reader`)
4. Grant the role: **BigQuery Data Viewer** and **BigQuery Job User**
5. Click **Done**
6. Click on the service account → **Keys** → **Add Key** → **Create new key** → **JSON**
7. Save the downloaded JSON file securely

Then set the environment variable:

```bash
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"

# Windows CMD
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json

# Linux/macOS
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## Step 5: Verify Setup

Test that everything works:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

Test BigQuery connection by creating a file `test_bq.py`:

```python
from google.cloud import bigquery

# Replace with your project ID
client = bigquery.Client(project='YOUR_PROJECT_ID')

query = """
SELECT COUNT(*) as count 
FROM `bigquery-public-data.thelook_ecommerce.users` 
LIMIT 1
"""

result = list(client.query(query).result())
print(f"Users table has {result[0].count} rows")
print("BigQuery is working!")
```

Run it:
```bash
python test_bq.py
```

You should see output like:
```
Users table has 100000 rows
BigQuery is working!
```

## Step 6: Configure the Agent

Create your `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# LLM Provider
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Set your GCP project ID
# If not set, uses the default from gcloud config
GOOGLE_CLOUD_PROJECT=your-project-id
```

## Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the key and add it to your `.env` file as `GOOGLE_API_KEY`

## Troubleshooting

### "Could not automatically determine credentials"

Run:
```bash
gcloud auth application-default login
```

### "Permission denied" or "Access Denied"

1. Ensure BigQuery API is enabled in your project
2. Check that your account has BigQuery permissions
3. For service accounts, verify the roles are assigned

### "Quota exceeded"

The public dataset has usage limits. Wait a few minutes and try again.

### "Project not found"

Set your project explicitly:
```bash
gcloud config set project YOUR_PROJECT_ID
```

Or add to `.env`:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
```

## BigQuery Free Tier

Google Cloud provides:
- **1 TB** of free BigQuery queries per month
- **10 GB** of free storage per month

The `thelook_ecommerce` public dataset doesn't count against your storage quota, and typical queries for this agent use minimal compute.

## Quick Reference

| Command | Description |
|---------|-------------|
| `gcloud init` | Initialize gcloud CLI |
| `gcloud auth login` | Login to Google Cloud |
| `gcloud auth application-default login` | Set up application credentials |
| `gcloud config set project PROJECT_ID` | Set default project |
| `gcloud config list` | View current configuration |
| `gcloud auth list` | List authenticated accounts |
