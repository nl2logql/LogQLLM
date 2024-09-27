import os

import instructor
from datasets import Dataset
from dotenv import load_dotenv
from models import LogClass, MetricClass
from openai import OpenAI
from prompts import METRIC_CATEGORY_PROMPT

load_dotenv(".env")

client = instructor.from_openai(OpenAI())
dataset_path = "dataset/nl-logql-dataset-classified"
output_path = "dataset/nl-logql-dataset-classified-metric"
dataset = Dataset.load_from_disk(dataset_path)


def classify_metric_query(example):
    try:
        res = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": METRIC_CATEGORY_PROMPT,
                },
                {
                    "role": "user",
                    "content": "Identify the metric aggregation types for the following log query:",
                },
                {
                    "role": "user",
                    "content": example["logql_query"],
                },
            ],
            response_model=MetricClass,
        )
        example["metric_category"] = res.model_dump()
        # print(res.model_dump())
    except Exception as e:
        print(f"Error processing query: {example['logql_query']}")
        print(f"Error: {str(e)}")
        example["metric_category"] = None
    return example


new_dataset = dataset.map(
    classify_metric_query,
    num_proc=os.cpu_count(),
    desc="Classifying metric queries",
    # disable=False,
)


# Save the updated dataset
dataset.save_to_disk(output_path)

print("Classification complete. Results saved to the dataset.")
