import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv
from models import LogEntry, LokiPayload
from tqdm import tqdm

load_dotenv()

LOKI_URL = os.getenv("LOKI_URL")
PARSED_LOG_FILE = "parsed_openssh_logs.json"
USER_ID = os.getenv("USER_ID", "")
API_KEY = os.getenv("API_KEY", "")

NUM_WORKERS = 100  # Number of worker tasks


async def upload_to_loki(session, log_entry: LogEntry):
    headers = {"Content-type": "application/json", "X-Scope-OrgID": "tenant1"}
    try:
        nanoseconds = int(datetime.now().timestamp() * 1e9)
        payload = LokiPayload(
            streams=[
                {
                    "stream": log_entry.labels.model_dump(exclude_none=True),
                    "values": [
                        [
                            str(nanoseconds),
                            log_entry.content,
                            log_entry.structured_metadata.model_dump(
                                exclude_none=True, mode="json"
                            ),
                        ]
                    ],
                }
            ]
        )
        async with session.post(
            url=LOKI_URL, data=payload.model_dump_json(), headers=headers
        ) as response:
            if response.status != 204:
                print(f"Failed to upload to Loki: {await response.text()}")
    except Exception as e:
        print(f"Error during upload to Loki: {str(e)}")
        print(f"Problematic entry: {log_entry}")


async def worker(name, queue, session, progress_bar):
    while True:
        log_entry = await queue.get()
        if log_entry is None:
            queue.task_done()
            break
        await upload_to_loki(session, log_entry)
        progress_bar.update(1)
        queue.task_done()


async def producer(queue, filename):
    with open(filename, "r") as fd:
        entries = json.load(fd)
        for entry in entries:
            entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
            log_entry = LogEntry(**entry)
            await queue.put(log_entry)


async def main():
    auth = aiohttp.BasicAuth(USER_ID, API_KEY)
    queue = asyncio.Queue(
        maxsize=1000
    )  # Limit queue size to control memory usage

    async with aiohttp.ClientSession(auth=auth) as session:
        with tqdm(total=638947, desc="Upload Progress") as progress_bar:
            # Start the producer
            producer_task = asyncio.create_task(
                producer(queue, PARSED_LOG_FILE)
            )

            # Start the workers
            workers = [
                asyncio.create_task(
                    worker(f"worker-{i}", queue, session, progress_bar)
                )
                for i in range(NUM_WORKERS)
            ]

            # Wait for the producer to finish
            await producer_task

            # Send termination signals to workers
            for _ in range(NUM_WORKERS):
                await queue.put(None)

            # Wait for all workers to finish
            await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
