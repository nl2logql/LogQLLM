# %%
import csv
import json
import re
from collections import defaultdict
from datetime import datetime

from models import Labels, LogEntry, StructuredMetadata


def parse_log(log_file, csv_file):
    results = []

    # Read CSV file and store content by LineId
    csv_content = defaultdict(str)
    with open(csv_file, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csv_content[int(row["LineId"])] = row["Content"]

    with open(log_file, "r") as file:
        for line_id, line in enumerate(file, 1):
            # Extract Labels
            log_level_match = re.search(r"\s(INFO|WARN|ERROR|DEBUG)\s", line)
            labels = Labels(
                log_file_type=line.split(".")[0],
                log_level=log_level_match.group(1) if log_level_match else None,
                component=line.split()[5] if len(line.split()) > 5 else None,
                log_file_name=line.split()[0],
                # line_id=None,
            )

            # Extract Structured Metadata
            req_match = re.search(r"req-([a-f0-9-]+)", line)
            structured_metadata = StructuredMetadata(
                request_id=req_match.group(1) if req_match else None,
                tenant_id=line.split()[7] if len(line.split()) > 7 else None,
                user_id=line.split()[8] if len(line.split()) > 8 else None,
            )

            # Extract Timestamp
            timestamp_match = re.search(
                r"\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3}", line
            )
            if timestamp_match:
                timestamp_str = timestamp_match.group()
                timestamp = datetime.strptime(
                    timestamp_str, "%m-%d %H:%M:%S.%f"
                )
            else:
                timestamp = None

            if timestamp is None:
                continue  # Skip entries without a valid timestamp

            # Create LogEntry
            log_entry = LogEntry(
                labels=labels,
                structured_metadata=structured_metadata,
                timestamp=timestamp,
                content=csv_content[line_id],
            )

            results.append(log_entry.model_dump())
    return results


# %%
output_file_path = "parsed_openstack_logs.json"
log_file_path = "OpenStack_headers.log"
csv_file_path = "OpenStack_full.log_structured.csv"
parsed_data = parse_log(log_file_path, csv_file_path)
# %%
with open(output_file_path, "w") as outfile:
    json.dump(parsed_data, outfile, indent=2)

print(f"Parsed data has been written to {output_file_path}")

# %%
print(f"Total log entries processed: {len(parsed_data)}")
print("Sample entry:")
print(json.dumps(parsed_data[20731], indent=2))
