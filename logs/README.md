# LogQLLM

## Prepping the logs

To process the logs from LogHub into an ingestable format for Grafana Loki:

1. Remove message content to keep only log headers:
```
cd logs/OpenSSH   # or OpenStack, HDFS
python filter.py  # Creates *_headers.log containing only log headers
```

2. Generate labels for the processed logs:
```
cd logs/OpenSSH   # or OpenStack, HDFS
python generate_labels.py
```

## Ingesting

To ingest the logs to Grafana Loki

```
cd logs/OpenSSH   # or OpenStack or HDFS
python upload_to_loki.py
```
