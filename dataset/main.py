from typing import Optional

import pandas as pd
from datasets import Dataset
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

dataset_path = "nl-logql-dataset"
# Load existing dataset or create a new one
try:
    dataset = Dataset.load_from_disk(dataset_path)
    df = dataset.to_pandas()
    if "category" not in df.columns:
        df["category"] = ""  # Add category column if it doesn't exist
except Exception:
    df = pd.DataFrame(
        columns=[
            "application",
            "id",
            "category",
            "question",
            "logql_query",
            "query_explanation",
            "query_result",
        ]
    )


class Entry(BaseModel):
    application: str | None = "openssh"
    category: str
    question: str
    logql_query: str
    query_explanation: str
    query_result: str


@app.post("/add_entry")
async def add_entry(entry: Entry):
    global df
    new_id = df["id"].max() + 1 if len(df) > 0 else 1
    new_row = pd.DataFrame(
        {
            "application": [entry.application or "openssh"],
            "id": [new_id],
            "category": [entry.category],
            "question": [entry.question],
            "logql_query": [entry.logql_query],
            "query_explanation": [entry.query_explanation],
            "query_result": [entry.query_result],
        }
    )
    df = pd.concat([df, new_row], ignore_index=True)
    print(entry)
    save_dataset()
    return {"message": "Entry added successfully"}


@app.get("/entries")
async def get_entries(
    page: int = Query(1, ge=1),
    items_per_page: int = Query(25, ge=1, le=100),
    application_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
):
    global df

    # Sort entries in descending order of their IDs
    sorted_df = df.sort_values("id", ascending=False)

    # Filter by application if provided
    if application_filter and application_filter.lower() != "none":
        sorted_df = sorted_df[sorted_df["application"] == application_filter]

    # Filter by category if provided
    if category_filter and category_filter.lower() != "none":
        sorted_df = sorted_df[sorted_df["category"] == category_filter]

    # Calculate pagination
    total_items = len(sorted_df)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page

    # Get paginated entries
    paginated_df = sorted_df.iloc[start_index:end_index]

    # Prepare response
    entries = paginated_df.to_dict("records")
    response = {
        "entries": entries,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "items_per_page": items_per_page,
        "applications": sorted(df["application"].unique().tolist()),
        "categories": sorted(df["category"].unique().tolist()),
    }

    return response


@app.put("/edit_entry/{entry_id}")
async def edit_entry(entry_id: int, entry: Entry):
    global df
    if entry_id not in df["id"].values:
        raise HTTPException(status_code=404, detail="Entry not found")
    df.loc[
        df["id"] == entry_id,
        [
            "application",
            "category",
            "question",
            "logql_query",
            "query_explanation",
            "query_result",
        ],
    ] = [
        entry.application,
        entry.category,
        entry.question,
        entry.logql_query,
        entry.query_explanation,
        entry.query_result,
    ]
    save_dataset()
    return {"message": "Entry updated successfully"}


@app.delete("/delete_entry/{entry_id}")
async def delete_entry(entry_id: int):
    global df
    if entry_id not in df["id"].values:
        raise HTTPException(status_code=404, detail="Entry not found")
    df = df[df["id"] != entry_id].reset_index(drop=True)
    save_dataset()
    return {"message": "Entry deleted successfully"}


def save_dataset():
    dataset = Dataset.from_pandas(df)
    dataset.save_to_disk(dataset_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
