
#!/bin/bash

# Set your Loki endpoint URL
LOKI_URL="http://localhost:3100/loki/api/v1/push"

# Generate current timestamp in nanoseconds
CURRENT_TIME=$(date +%s%N)

# Create JSON payload with dummy log data
JSON_PAYLOAD=$(cat <<EOF
{
  "streams": [
    {
      "stream": {
        "job": "test_job",
        "environment": "production",
        "level": "info"
      },
      "values": [
        ["$CURRENT_TIME", "This is a test log message"],
        ["$((CURRENT_TIME + 1000000000))", "Another test log entry"],
        ["$((CURRENT_TIME + 2000000000))", "Third test log message"]
      ]
    }
  ]
}
EOF
)

# Send the request using HTTPie
http POST $LOKI_URL \
  Content-Type:application/json \
  X-Scope-OrgID:tenant1 \
  < <(echo "$JSON_PAYLOAD")

echo "Log data sent to Loki"
