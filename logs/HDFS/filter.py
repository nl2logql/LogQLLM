import csv

# File paths
original_log_file = "HDFS_full.log"
parsed_log_file = "HDFS_full.log_structured.csv"
output_log_file = "HDFS_headers.log"

# Read the parsed loglines into a dictionary
parsed_logs = {}
with open(parsed_log_file, "r") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        line_id = int(row["LineId"])
        content = row["Content"]
        parsed_logs[line_id] = content

# Process the original loglines
with open(original_log_file, "r") as infile, open(
    output_log_file, "w"
) as outfile:
    for line_number, original_logline in enumerate(infile, start=1):
        if line_number in parsed_logs:
            content_field = parsed_logs[line_number]
            modified_logline = original_logline.replace(
                content_field, ""
            ).strip()
            outfile.write(modified_logline + "\n")
        else:
            outfile.write(original_logline)

print(f"Processed loglines have been written to {output_log_file}")
