#!/bin/bash

# Check if USER_ID and API_KEY are set
if [ -z "$USER_ID" ] || [ -z "$API_KEY" ]; then
    echo "Error: USER_ID and API_KEY must be set as environment variables."
    exit 1
fi

# Set the Loki server address
LOKI_SERVER="https://logs-prod-006.grafana.net"

# Get current date in ISO 8601 format
START_DATE=$(date -u +"%Y-%m-%dT00:00:00Z")
END_DATE=$(date -u +"%Y-%m-%dT23:59:59Z")

# Execute the curl command
curl -u "$USER_ID:$API_KEY" -X POST \
    "${LOKI_SERVER}/loki/api/v1/delete" \
    --data-urlencode "query={application=\"openstack\"}" \
    --data-urlencode "start=${START_DATE}" \
    --data-urlencode "end=${END_DATE}"

# Check the curl exit status
if [ $? -eq 0 ]; then
    echo "Delete request sent successfully."
else
    echo "Error sending delete request."
    exit 1
fi
