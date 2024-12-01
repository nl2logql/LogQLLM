""""Script to delete and clean up logs from Grafana Loki."""

import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# LOKI_URL = os.getenv("LOKI_URL")
LOKI_URL = "https://logs-prod-006.grafana.net"
USER_ID = os.getenv("USER_ID", "")
API_KEY = os.getenv("API_KEY", "")

# Calculate yesterday's midnight timestamp
yesterday_midnight = datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
) - timedelta(days=1)
start_timestamp = int(yesterday_midnight.timestamp())
end_timestamp = int(datetime.now(timezone.utc).timestamp())

delete_url = f"{LOKI_URL}/loki/api/v1/delete"
params = {
    "query": {"application": "openstack"},
    "start": start_timestamp,
    "end": end_timestamp,
}

res = requests.post(
    delete_url,
    params=params,
    auth=(USER_ID, API_KEY),
    headers={"Content-type": "application/json"},
)

if res.status_code == 204:
    print("Successfully deleted logs")
else:
    print(f"Failed to delete logs: {res.status_code} - {res.text}")
