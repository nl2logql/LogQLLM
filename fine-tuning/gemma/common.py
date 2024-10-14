import os
from pathlib import PurePosixPath
from typing import Union

import modal
from dotenv import load_dotenv

load_dotenv(".env")

APP_NAME = "axolotl-gemma-ft-00"

MINUTES = 60
HOURS = 60 * MINUTES

AXOLOTL_REGISTRY_SHA = (
    "7176949dd84a1e0449797da683b16a99a6aff66d34be33f447a3e2753d7a62c2"
)

ALLOW_WANDB = os.environ.get("ALLOW_WANDB", "false").lower() == "true"
print(ALLOW_WANDB)
axolotl_image = (
    modal.Image.from_registry(f"winglian/axolotl@sha256:{AXOLOTL_REGISTRY_SHA}")
    .pip_install(
        "huggingface_hub",
        "hf_transfer==0.1.5",
        "wandb==0.18.3",
        "fastapi==0.110.0",
        "pydantic==2.6.3",
    )
    .env(
        dict(
            HUGGINGFACE_HUB_CACHE="/pretrained",
            HF_HUB_ENABLE_HF_TRANSFER="1",
            TQDM_DISABLE="true",
            AXOLOTL_NCCL_TIMEOUT="60",
        )
    )
    .entrypoint([])
)

vllm_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("vllm==0.6.2", "torch==2.4.0")
    .entrypoint([])
)

app = modal.App(
    APP_NAME,
    secrets=[
        modal.Secret.from_name("my-huggingface-secret"),
        modal.Secret.from_dict(
            {"ALLOW_WANDB": os.environ.get("ALLOW_WANDB", "false")}
        ),
        *([modal.Secret.from_name("wandb")] if ALLOW_WANDB else []),
    ],
)

pretrained_volume = modal.Volume.from_name("gemma2", create_if_missing=True)
runs_volume = modal.Volume.from_name("runs-vol", create_if_missing=True)


VOLUME_CONFIG: dict[Union[str, PurePosixPath], modal.Volume] = {
    "/pretrained": pretrained_volume,
    "/runs": runs_volume,
}


class Colors:
    """ANSI color codes"""

    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    GRAY = "\033[0;90m"
    BOLD = "\033[1m"
    END = "\033[0m"
