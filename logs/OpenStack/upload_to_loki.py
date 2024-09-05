import asyncio
import json
from datetime import datetime

import aiohttp
from models import LogEntry, LokiPayload
from tqdm import tqdm

# read from .env
LOKI_URL = ""
BATCH_SIZE = 1000  # Number of log lines to batch before sending to Loki
PARSED_LOG_FILE = "parsed_openstack_logs.json"

USER_ID = ""
API_KEY = ""


async def upload_to_loki(session, log_entry: LogEntry):
    headers = {"Content-type": "application/json", "X-Scope-OrgID": "tenant1"}
    try:
        # nanoseconds = int(log_entry.timestamp.timestamp() * 1e9)
        nanoseconds = int(datetime.now().timestamp() * 1e9)
        escaped_content = log_entry.content.replace('"', '"').replace(
            "\n", "\\n"
        )
        payload = LokiPayload(
            streams=[
                {
                    "stream": log_entry.labels.model_dump(exclude={"line_id"}),
                    "values": [
                        [
                            str(nanoseconds),
                            escaped_content,
                            log_entry.structured_metadata.model_dump(
                                exclude_none=True, mode="json"
                            ),
                        ]
                    ],
                }
            ]
        )
        # print(json.dumps(payload.model_dump(), indent=2))
        async with session.post(
            url=LOKI_URL, data=payload.model_dump_json(), headers=headers
        ) as response:
            if response.status != 204:
                print(f"Failed to upload to Loki: {await response.text()}")
            else:
                # print("Successfully uploaded to Loki")
                pass
    except Exception as e:
        print(f"Error during upload to Loki: {str(e)}")
        print(f"Problematic entry: {log_entry}")


async def process_log_files(session, filename, progress_bar):
    with open(filename, "r") as fd:
        entries = json.load(fd)
        for entry in entries:
            entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
            log_entry = LogEntry(**entry)
            await upload_to_loki(session, log_entry)
            progress_bar.update(1)


async def main():
    auth = aiohttp.BasicAuth(USER_ID, API_KEY)
    async with aiohttp.ClientSession(auth=auth) as session:
        with tqdm(total=207632, desc="Upload Progress") as progress_bar:
            upload_tasks = [
                process_log_files(session, PARSED_LOG_FILE, progress_bar)
            ]
            await asyncio.gather(*upload_tasks)


if __name__ == "__main__":
    asyncio.run(main())
