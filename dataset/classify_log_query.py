import os

import instructor
from datasets import Dataset
from dotenv import load_dotenv
from models import LogClass
from openai import OpenAI
from prompts import LOG_CATEGORY_PROMPT

load_dotenv(".env")

client = instructor.from_openai(OpenAI())
dataset_path = "dataset/nl-logql-dataset"
output_path = "dataset/nl-logql-dataset-classified"
dataset = Dataset.load_from_disk(dataset_path)


def classify_log_query(example):
    try:
        res = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": LOG_CATEGORY_PROMPT,
                },
                {
                    "role": "user",
                    "content": "Identify the label and line filter types for the following log query:",
                },
                {
                    "role": "user",
                    "content": example["logql_query"],
                },
            ],
            response_model=LogClass,
        )
        example["log_category"] = res.model_dump()
    except Exception as e:
        print(f"Error processing query: {example['logql_query']}")
        print(f"Error: {str(e)}")
        example["log_category"] = None
    return example


# Use map to apply the function to all examples with a progress bar
dataset = dataset.map(
    classify_log_query,
    num_proc=os.cpu_count(),
    desc="Classifying log queries",
    # disable=False,
)

# Save the updated dataset
dataset.save_to_disk(output_path)

print("Classification complete. Results saved to the dataset.")
