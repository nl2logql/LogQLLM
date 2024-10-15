import os
from pathlib import Path, PurePosixPath
from typing import Union

import datasets
import evaluate
import modal
import numpy as np
import torch

# from dotenv import load_dotenv
from evaluate import logging
from torch.nn import CrossEntropyLoss
from transformers import AutoModelForCausalLM, AutoTokenizer

# load_dotenv(".env")


class Colors:
    """ANSI color codes"""

    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    GRAY = "\033[0;90m"
    BOLD = "\033[1m"
    END = "\033[0m"


APP_NAME = "lighteval-pplx-llama-3.1"

MINUTES = 60
HOURS = 60 * MINUTES


eval_image = (
    modal.Image.debian_slim()
    .pip_install("evaluate", "transformers[torch]")
    .env(
        dict(
            HUGGINGFACE_HUB_CACHE="/pretrained",
            HF_HUB_ENABLE_HF_TRANSFER="1",
            TQDM_DISABLE="true",
        )
    )
    .entrypoint([])
)


class Perplexity(evaluate.Metric):
    def _info(self):
        return evaluate.MetricInfo(
            module_type="metric",
            description="",
            citation="",
            features=datasets.Features(
                {"prediction": datasets.Value("string")}
            ),
        )

    def _compute(
        self,
        predictions,
        model_path,
        batch_size: int = 16,
        add_start_token: bool = True,
        device=None,
        max_length=None,
    ):
        if device is not None:
            assert device in [
                "cpu",
                "gpu",
                "cuda",
            ], "device should be either gpu or cpu"
            if device == "gpu":
                device = "cuda"
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(model_path)
        model = model.to(device)
        print(f"[*] Loaded {model}!")
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        if tokenizer.pad_token is None and batch_size > 1:
            existing_special_tokens = list(
                tokenizer.special_tokens_map_extended.values()
            )
            assert (
                len(existing_special_tokens) > 0
            ), "If batch_size > 1, model must have atleast one special token to use for padding. Please use a different model or set batch_size=1."
            tokenizer.add_special_tokens(
                {"pad_token": existing_special_tokens[0]}
            )

        if add_start_token and max_length:
            assert (
                tokenizer.bos_token is not None
            ), "Input model must already have a BOS token if using add_start_token=True. Please use a different model or set add_start_toke=False"
            max_tokenized_len = max_length - 1
        else:
            max_tokenized_len = max_length

        encodings = tokenizer(
            predictions,
            add_special_tokens=False,
            padding=True,
            truncation=True if max_tokenized_len else False,
            max_length=max_tokenized_len,
            return_tensors="pt",
            return_attention_mask=True,
        ).to(device)
        print("Tokenized the input!")
        encoded_texts = encodings["input_ids"]
        attn_masks = encodings["attention_mask"]

        if add_start_token:
            assert torch.all(
                torch.ge(attn_masks.sum(1), 1)
            ), "Each input text be atleast one token long"
        else:
            assert torch.all(
                torch.ge(attn_masks.sum(1), 2)
            ), "When add_start_token=False, each input text must be atleast two tokens longs"

        ppls = []
        loss_fct = CrossEntropyLoss(reduction="none")

        for start_index in logging.tqdm(
            range(0, len(encoded_texts), batch_size)
        ):
            end_index = min(start_index + batch_size, len(encoded_texts))
            encoded_batch = encoded_texts[start_index:end_index]
            attn_mask = attn_masks[start_index:end_index]

            if add_start_token:
                bos_tokens_tensor = torch.tensor(
                    [[tokenizer.bos_token_id]] * encoded_batch.size(dim=0)
                ).to(device)
                encoded_batch = torch.cat(
                    [bos_tokens_tensor, encoded_batch], dim=1
                )
                attn_mask = torch.cat(
                    [
                        torch.ones(
                            bos_tokens_tensor.size(), dtype=torch.int64
                        ).to(device),
                        attn_mask,
                    ],
                    dim=1,
                )

            labels = encoded_batch

            with torch.no_grad():
                out_logits = model(
                    encoded_batch, attention_mask=attn_mask
                ).logits
            shift_logits = out_logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            shift_attention_mask_batch = attn_mask[..., 1:].contiguous()

            perplexity_batch = torch.exp(
                (
                    loss_fct(shift_logits.transpose(1, 2), shift_labels)
                    * shift_attention_mask_batch
                ).sum(1)
                / shift_attention_mask_batch.sum(1)
            )

            ppls += perplexity_batch.tolist()

        return {"perplexities": ppls, "mean_perplexity": np.mean(ppls)}


app = modal.App(
    APP_NAME,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
)
pretrained_volume = modal.Volume.from_name("llama-3.1", create_if_missing=False)
runs_volume = modal.Volume.from_name("runs-vol", create_if_missing=False)

VOLUME_CONFIG: dict[Union[str, PurePosixPath], modal.Volume] = {
    "/pretrained": pretrained_volume,
    "/runs": runs_volume,
}

GPU_CONFIG = os.environ.get("GPU_CONFIG", "a100-40gb:1")
if len(GPU_CONFIG.split(":")) <= 1:
    N_GPUS = int(os.environ.get("N_GPUS", 2))
    GPU_CONFIG = f"{GPU_CONFIG}:{N_GPUS}"
SINGLE_GPU_CONFIG = os.environ.get("GPU_CONFIG", "a10g:1")


def run_cmd(cmd: str, run_folder: str):
    """Run a command inside a folder, with Modal Volume reloading before and commit on success"""
    import subprocess

    VOLUME_CONFIG["/pretrained"].reload()
    VOLUME_CONFIG["/runs"].reload()

    if exit_code := subprocess.call(cmd.split(), cwd=run_folder):
        exit(exit_code)

    VOLUME_CONFIG["/runs"].commit()


def get_model_path_from_run(path: Path) -> Path:
    return path / "lora-out" / "merged"


@app.function(
    image=eval_image,
    gpu=GPU_CONFIG,
    volumes=VOLUME_CONFIG,
    timeout=30 * MINUTES,
)
def launch(
    jsonl_file: str,
    run_dir: str = "/runs",
    run_name: str = "axo-2024-10-14-07-43-05-b0d9",
):
    import json

    run_path = Path(run_dir) / run_name
    model_path = get_model_path_from_run(path=run_path)
    perplexity = Perplexity()

    input_texts = []

    with open(jsonl_file, "r") as f:
        for line in f:
            data = json.loads(line)
            if "output" in data:
                input_texts.append(data["output"])

    if not input_texts:
        print("Warning: No 'output' fields found in the JSONL file.")
        return

    pplx = perplexity._compute(model_path=model_path, predictions=input_texts)
    print(pplx)


@app.local_entrypoint()
def main(
    jsonl_file: str,
    run_dir: str = "/runs",
    run_name: str = "axo-2024-10-14-07-43-05-b0d9",
):
    print("Local!")
    launch.remote(jsonl_file=jsonl_file, run_dir=run_dir, run_name=run_name)
