# %%
import csv
import json
import re
from collections import defaultdict

from models import Labels, LogEntry, StructuredMetadata

# %%

# Sample log lines
log_lines = [
    "081109 203519 147 INFO dfs.DataNode$PacketResponder: PacketResponder 0 for block blk_-1608999687919862906 terminating",
    "081109 203518 001 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.19.102:54106 dest: /10.250.19.102:50010",
]

# Regex patterns
block_id_pattern = r"blk_-?\d+"
source_pattern = r"src:\s*/(\S+)"
destination_pattern = r"dest:\s*/(\S+)"
thread_id_pattern = r"PacketResponder\s+(\d+)"


def extract_metadata(log_line):
    metadata = {}

    # Extract Block ID
    block_id_match = re.search(block_id_pattern, log_line)
    if block_id_match:
        metadata["block_id"] = block_id_match.group(0)

    # Extract Source
    source_match = re.search(source_pattern, log_line)
    if source_match:
        metadata["source"] = source_match.group(1)

    # Extract Destination
    destination_match = re.search(destination_pattern, log_line)
    if destination_match:
        metadata["destination"] = destination_match.group(1)

    # Extract Thread ID
    thread_id_match = re.search(thread_id_pattern, log_line)
    if thread_id_match:
        metadata["thread_id"] = thread_id_match.group(1)

    return metadata


# Process each log line
for log_line in log_lines:
    metadata = extract_metadata(log_line)
    print(f"Log: {log_line}")
    print(f"Extracted Metadata: {metadata}")
    print()


# %%


def parse_log(log_file, csv_file):
    results = []
    csv_content = defaultdict(str)
    with open(csv_file, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csv_content[int(row["LineId"])] = row["Content"]

        with open(log_file, "r") as file:
            for line_id, line in enumerate(file, 1):
                # timestamp_match = re.match(r"^(\d{6}\s+\d{6}\s+\d{3})", line)
                # timestamp_str = (
                #     timestamp_match.group(1) if timestamp_match else None
                # )
                # if timestamp_str is not None:
                #     full_timestamp_str = f"20{timestamp_str}"
                #     timestamp = datetime.strptime(
                #         full_timestamp_str, "%Y%m%d %H%M%S %f"
                #     )
                # else:
                #     timestamp = None
                #     print(line_id, line)
                # USE THE CSV CONTENT AND NOT STRIPPED HEADER LOG DUMBASS
                #
                log_level_match = re.search(r"\d+ \d+ \d+ (\w+)", line)
                log_level = (
                    log_level_match.group(1) if log_level_match else None
                )
                component_match = re.search(r"\d+ \d+ \d+ \w+ ([\w.$]+):", line)
                component = (
                    component_match.group(1) if component_match else None
                )

                block_id_match = re.search(r"blk_-?\d+", csv_content[line_id])
                block_id = block_id_match.group(0) if block_id_match else None

                source_match = re.search(r"src:\s*/(\S+)", csv_content[line_id])
                source = source_match.group(1) if source_match else None

                destination_match = re.search(
                    r"dest:\s*/(\S+)", csv_content[line_id]
                )
                destination = (
                    destination_match.group(1) if destination_match else None
                )

                labels = Labels(log_level=log_level, component=component)
                structured_metadata = StructuredMetadata(
                    block_id=block_id, source=source, destination=destination
                )
                log_entry = LogEntry(
                    labels=labels,
                    structured_metadata=structured_metadata,
                    # timestamp=timestamp,
                    content=csv_content[line_id],
                )
                results.append(log_entry.model_dump())
    return results


output_file_path = "parsed_hdfs_logs.json"
log_file_path = "HDFS_headers.log"
csv_file_path = "HDFS_full.log_structured.csv"

with open(output_file_path, "w") as output_file:
    json.dump(parse_log(log_file_path, csv_file_path), output_file, indent=2)
