# Chatting with Logs: An exploratory study on Finetuning LLMs for LogQL

This repository contains the scripts for creating the dataset and code for the paper "Chatting with Logs: An exploratory study on Finetuning LLMs for LogQL".

The dataset and the fine-tuned models are available on HuggingFace under the following links:
- [Dataset](https://huggingface.co/datasets/nl-to-logql/natural-logql)
- [nl-to-logql/llama-3.1-logql](https://huggingface.co/nl-to-logql/llama-3.1-logql)
- [nl-to-logql/gemma-2-logql](https://huggingface.co/nl-to-logql/gemma-2-logql)

The demo for the fine-tuned models is available at [this link](https://llm-response-simulator-alt-glitch.replit.app/)

## System Logs
[logs/](logs/): This directory containers the system logs and their respective transformation and ingestion scripts for each of the three systems: OpenSSH, OpenStack, and HDFS.

Respective logs are stored in the following directories:
- [logs/OpenSSH](logs/OpenSSH): Contains the OpenSSH logs and scripts.
- [logs/OpenStack](logs/OpenStack): Contains the OpenStack logs and scripts.
- [logs/HDFS](logs/HDFS): Contains the HDFS logs and scripts.


## Dataset Curation
[dataset-curation/](dataset-curation/): This directory contains the scripts for creating the natural language to LogQL dataset. The dataset is created by pairing the natural language queries with the LogQL queries.


## Fine-Tuning
[finetuning/](finetuning/): This directory contains the scripts for fine-tuning the LLMs on the dataset.
