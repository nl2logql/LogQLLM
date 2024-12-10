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
            # Extract Labels
            log_level_match = re.search(r"\d+ \d+ \d+ (\w+)", line)
            component_match = re.search(r"\d+ \d+ \d+ \w+ ([\w.$]+):", line)

            labels = Labels(
                log_level=log_level_match.group(1) if log_level_match else None,
                component=component_match.group(1) if component_match else None
            )

            # Extract Structured Metadata
            block_id_match = re.search(r"blk_-?\d+", csv_content[line_id])
            source_match = re.search(r"src:\s*/(\S+)", csv_content[line_id])
            destination_match = re.search(r"dest:\s*/(\S+)", csv_content[line_id])

            structured_metadata = StructuredMetadata(
                block_id=block_id_match.group(0) if block_id_match else None,
                source=source_match.group(1) if source_match else None,
                destination=destination_match.group(1) if destination_match else None
            )

            # Extract Timestamp
            timestamp_match = re.match(r"^(\d{6}\s+\d{6}\s+\d{3})", line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.strptime(timestamp_str, "%m%d%y %H%M%S %f")
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


output_file_path = "parsed_hdfs_logs.json"
log_file_path = "HDFS_headers.log"
csv_file_path = "HDFS_full.log_structured.csv"

with open(output_file_path, "w") as output_file:
    json.dump(parse_log(log_file_path, csv_file_path), output_file, indent=2)
