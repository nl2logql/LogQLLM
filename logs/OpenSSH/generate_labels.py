# %%
import csv
import json
import re
from collections import defaultdict
from datetime import datetime

from models import Labels, LogEntry, StructuredMetadata


def parse_log(log_file, csv_file):
    results = []
    csv_content = defaultdict(str)
    with open(csv_file, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csv_content[int(row["LineId"])] = row["Content"]

        with open(log_file, "r") as file:
            for line_id, line in enumerate(file, 1):
                labels = Labels(hostname="LabSZ")
                process_match = re.search(r"sshd\[(\d+)\]", line)
                # rhost_match = re.search(r"rhost=(\S+)", line)
                # rhost = rhost_match.group(1) if rhost_match else None
                # user_match = re.search(r"user=(\S+)", line)
                # ruser = user_match.group(1) if user_match else None
                process_id = (
                    int(process_match.group(1)) if process_match else None
                )

                structured_metadata = StructuredMetadata(
                    process_id=process_id,
                    # rhost=rhost,
                    # ruser=ruser
                )
                timestamp_match = re.match(
                    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", line
                ).group(1)
                if timestamp_match:
                    datetime_str_with_year = f"2024 {timestamp_match}"
                    timestamp = datetime.strptime(
                        datetime_str_with_year, "%Y %b %d %H:%M:%S"
                    )
                else:
                    timestamp = None
                if timestamp is None:
                    continue
                log_entry = LogEntry(
                    labels=labels,
                    structured_metadata=structured_metadata,
                    timestamp=timestamp,
                    content=csv_content[line_id],
                )

                results.append(log_entry.model_dump())
    return results


output_file_path = "parsed_openssh_logs.json"
log_file_path = "OpenSSH_headers.log"
csv_file_path = "OpenSSH_full.log_structured.csv"

with open(output_file_path, "w") as output_file:
    parsed_data = parse_log(log_file_path, csv_file_path)
    json.dump(parsed_data, output_file, indent=2)
