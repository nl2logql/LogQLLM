import os
from pathlib import Path

from common import VOLUME_CONFIG, app, axolotl_image, HOURS, MINUTES
from huggingface_hub import HfApi


@app.function(
    image=axolotl_image,
    volumes=VOLUME_CONFIG,
    timeout=2*HOURS,
    container_idle_timeout=15*MINUTES,
)
def upload_model_to_hf(axolotl_run_path: str, hf_repo_id: str):
    """
    Upload trained LORA model to HuggingFace.

    Args:
        axolotl_run_path: Path like 'axo-2024-11-12-19-22-09-b0e1'
        hf_repo_id: HuggingFace repository ID (e.g., 'username/model-name')
    """
    # Construct full path to the LORA output
    base_path = Path("/runs")
    lora_path = base_path / axolotl_run_path / "lora-out"

    if not lora_path.exists():
        raise ValueError(f"LORA output directory not found at {lora_path}")

    # Initialize HF API with token from secrets
    hf_api = HfApi()

    print(f"Starting upload to {hf_repo_id}")

    # Upload all files in the lora-out directory
    for file_path in lora_path.rglob("*"):
        if file_path.is_file():
            # Get relative path from lora-out directory
            relative_path = file_path.relative_to(lora_path)

            print(f"Uploading {relative_path}")

            # Upload file to HF
            hf_api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=str(relative_path),
                repo_id=hf_repo_id,
                repo_type="model",
            )

    print(f"Upload completed to {hf_repo_id}")
    return True
