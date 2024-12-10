import json
from datetime import datetime, timedelta
from typing import Dict, List

from tqdm import tqdm


def load_logs(filepath: str) -> List[Dict]:
    with open(filepath, "r") as f:
        return json.load(f)


def validate_timestamps(logs: List[Dict]) -> List[dict]:
    """Verify timestamps are non-decreasing and return list of errors"""
    errors = []
    for i in range(len(logs) - 1):
        current = datetime.fromisoformat(logs[i]["timestamp"])
        next_time = datetime.fromisoformat(logs[i + 1]["timestamp"])
        if next_time < current:
            error = {
                'index': i,
                'current_time': current,
                'next_time': next_time,
                'current_log': logs[i],
                'next_log': logs[i + 1]
            }
            errors.append(error)
    return errors


def write_validation_errors(errors: List[dict]):
    """Write validation errors to a file"""
    with open("validation_errors.txt", "w") as f:
        f.write(f"Found {len(errors)} timestamp validation errors:\n\n")
        for error in errors:
            f.write(f"Error at index: {error['index']}\n")
            f.write(f"Current time: {error['current_time']}\n")
            f.write(f"Next time: {error['next_time']}\n")
            f.write(f"Current log entry: {error['current_log']}\n")
            f.write(f"Next log entry: {error['next_log']}\n")
            f.write("-" * 80 + "\n\n")

def calculate_time_differences(logs: List[Dict]) -> List[timedelta]:
    """Calculate time differences between consecutive log entries"""
    differences = []
    total_span = timedelta()
    print("\nDebug: Checking time differences...")

    for i in tqdm(range(len(logs) - 1), desc="Calculating differences"):
        current = datetime.fromisoformat(logs[i]["timestamp"])
        next_time = datetime.fromisoformat(logs[i + 1]["timestamp"])

        # If going from December to January, keep them in the same year
        if current.month == 12 and next_time.month == 1:
            next_time = next_time.replace(year=current.year)
            print(f"\nDebug: Dec→Jan transition at index {i}")
            print(f"Debug: Current time: {current}")
            print(f"Debug: Next time before adjustment: {next_time}")
            print(f"Debug: Next time after adjustment: {next_time}")

        diff = next_time - current
        # If we get a negative difference, something's wrong
        if diff.total_seconds() < 0:
            print(f"\nWarning: Negative time difference at index {i}")
            print(f"Current: {current}")
            print(f"Next: {next_time}")
            print(f"Difference: {diff}")

        differences.append(diff)
        total_span += diff

        # Print significant time differences (more than 1 day)
        if diff > timedelta(days=1):
            print(f"\nDebug: Large time gap at index {i}:")
            print(f"Current: {current}")
            print(f"Next: {next_time}")
            print(f"Difference: {diff}")

    print(f"\nTotal time span: {total_span}")
    print(f"In days and hours: {total_span.days} days, {total_span.seconds//3600} hours")

    return differences


def generate_new_timestamps(differences: List[timedelta], num_logs: int) -> List[datetime]:
    """Generate new timestamps working backwards from current time"""
    current_time = datetime.now()
    # Ensure we're in 2024
    current_time = current_time.replace(year=2024)
    timestamps = [current_time]

    for diff in tqdm(reversed(differences), desc="Generating timestamps"):
        prev_time = timestamps[0] - diff
        # Ensure all timestamps stay in 2024
        if prev_time.year != 2024:
            prev_time = prev_time.replace(year=2024)
        timestamps.insert(0, prev_time)

    return timestamps


def update_log_timestamps(logs: List[Dict], new_timestamps: List[datetime]) -> List[Dict]:
    """Update logs with new timestamps while preserving format"""
    updated_logs = logs.copy()
    for log, new_time in tqdm(
        zip(updated_logs, new_timestamps),
        desc="Updating timestamps",
        total=len(logs),
    ):
        log["timestamp"] = new_time.isoformat(timespec="seconds")
    return updated_logs

def main():
    filepath = "parsed_hdfs_logs.json"
    MAX_LINES = 600_000

    print("Loading logs...")
    logs = load_logs(filepath)
    logs = logs[:MAX_LINES]  # Take only first 600k lines
    print(f"Processing first {MAX_LINES} log entries")

    print("\nChecking for timestamp validation errors...")
    validation_errors = validate_timestamps(logs)
    if validation_errors:
        print(f"Found {len(validation_errors)} timestamp validation errors")
        print("Writing errors to validation_errors.txt")
        write_validation_errors(validation_errors)
        print("Continuing with processing...")

    print("\nCalculating time differences...")
    differences = calculate_time_differences(logs)
    print(f"Found {len(differences)} time differences")

    print("\nGenerating new timestamps...")
    new_timestamps = generate_new_timestamps(differences, len(logs))

    print("\nUpdating logs with new timestamps...")
    updated_logs = update_log_timestamps(logs, new_timestamps)

    print("\nSample of updates:")
    for i in range(min(3, len(logs))):
        print(f"Original: {logs[i]['timestamp']}")
        print(f"New:      {updated_logs[i]['timestamp']}")
        print("-" * 50)

    print("\nSaving updated logs...")
    with open(filepath, "w") as f:
        json.dump(updated_logs, f, indent=2)
    print("Done!")


if __name__ == "__main__":
    main()
