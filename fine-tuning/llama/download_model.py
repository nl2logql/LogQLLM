# ---
# args: ["--force-download"]
# ---
import modal

MODELS_DIR = "/models"

DEFAULT_NAME = "nl-to-logql/llama-3.1-logql"
DEFAULT_REVISION = "a7c09948d9a632c2c840722f519672cd94af885d"


volume = modal.Volume.from_name("models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        [
            "huggingface_hub",  # download models from the Hugging Face Hub
            "hf-transfer",  # download models faster with Rust
        ]
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


MINUTES = 60
HOURS = 60 * MINUTES


app = modal.App(
    image=image, secrets=[modal.Secret.from_name("my-huggingface-secret")]
)


@app.function(volumes={MODELS_DIR: volume}, timeout=4 * HOURS)
def download_model(model_name, force_download=False):
    from huggingface_hub import snapshot_download

    volume.reload()

    snapshot_download(
        model_name,
        local_dir=MODELS_DIR + "/" + model_name,
        force_download=force_download,
    )

    volume.commit()


@app.local_entrypoint()
def main(
    model_name: str = DEFAULT_NAME,
    # model_revision: str = DEFAULT_REVISION,
    force_download: bool = False,
):
    download_model.remote(model_name, force_download)
