# ---
# deploy: true
# cmd: ["modal", "serve", "06_gpu_and_ml/llm-serving/vllm_inference.py"]
# pytest: false
# tags: ["use-case-lm-inference", "featured"]
# ---

# # Run an OpenAI-Compatible vLLM Server

# LLMs do more than just model language: they chat, they produce JSON and XML, they run code, and more.
# This has complicated their interface far beyond "text-in, text-out".
# OpenAI's API has emerged as a standard for that interface,
# and it is supported by open source LLM serving frameworks like [vLLM](https://docs.vllm.ai/en/latest/).

# In this example, we show how to run a vLLM server in OpenAI-compatible mode on Modal.
# You can find a video walkthrough of this example on our YouTube channel [here](https://www.youtube.com/watch?v=QmY_7ePR1hM).

# Note that the vLLM server is a FastAPI app, which can be configured and extended just like any other.
# Here, we use it to add simple authentication middleware, following the
# [implementation in the vLLM repository](https://github.com/vllm-project/vllm/blob/v0.5.3post1/vllm/entrypoints/openai/api_server.py).

# Our examples repository also includes scripts for running clients and load-testing for OpenAI-compatible APIs
# [here](https://github.com/modal-labs/modal-examples/tree/main/06_gpu_and_ml/llm-serving/openai_compatible).

# You can find a video walkthrough of this example and the related scripts on the Modal YouTube channel
# [here](https://www.youtube.com/watch?v=QmY_7ePR1hM).

# ## Set up the container image

# Our first order of business is to define the environment our server will run in:
# the [container `Image`](https://modal.com/docs/guide/custom-container).
# vLLM can be installed with `pip`.

import modal
from common import app, VOLUME_CONFIG, MINUTES, HOURS, vllm_image
import os

# vllm_image = modal.Image.debian_slim(python_version="3.12").pip_install(
#     "vllm==0.6.3post1", "fastapi[standard]==0.115.4", "bitsandbytes>=0.44.0"
# )



INFERENCE_GPU_CONFIG = os.environ.get("INFERENCE_GPU_CONFIG", "a10g:2")
if len(INFERENCE_GPU_CONFIG.split(":")) <= 1:
    N_INFERENCE_GPUS = int(os.environ.get("N_INFERENCE_GPUS", 2))
    INFERENCE_GPU_CONFIG = f"{INFERENCE_GPU_CONFIG}:{N_INFERENCE_GPUS}"
else:
    N_INFERENCE_GPUS = int(INFERENCE_GPU_CONFIG.split(":")[-1])

MODELS_DIR = "/models"
MODEL_NAME = "nl-to-logql/gemma-2-logql"
# MODEL_NAME = "neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16"
# DEFAULT_REVISION = "a7c09948d9a632c2c840722f519672cd94af885d"

# MODEL_REVISION = "a7c09948d9a632c2c840722f519672cd94af885d"

# We need to make the weights of that model available to our Modal Functions.

# So to follow along with this example, you'll need to download those weights
# onto a Modal Volume by running another script from the
# [examples repository](https://github.com/modal-labs/modal-examples).

try:
    volume = modal.Volume.lookup("models", create_if_missing=False)
except modal.exception.NotFoundError:
    raise Exception("Download models first with modal run download_llama.py")


TOKEN = "your-secret-token"  # auth token. for production use, replace with a modal.Secret

@app.function(
    image=vllm_image,
    gpu=INFERENCE_GPU_CONFIG,
    container_idle_timeout=5 * MINUTES,
    timeout=24 * HOURS,
    allow_concurrent_inputs=1000,
    volumes={MODELS_DIR: volume},
)
@modal.asgi_app()
def serve():
    import fastapi
    import vllm.entrypoints.openai.api_server as api_server
    from vllm.engine.arg_utils import AsyncEngineArgs
    from vllm.engine.async_llm_engine import AsyncLLMEngine
    from vllm.entrypoints.logger import RequestLogger
    from vllm.entrypoints.openai.serving_chat import OpenAIServingChat
    from vllm.entrypoints.openai.serving_completion import (
        OpenAIServingCompletion,
    )
    from vllm.entrypoints.openai.serving_engine import BaseModelPath
    from vllm.usage.usage_lib import UsageContext

    volume.reload()  # ensure we have the latest version of the weights

    # create a fastAPI app that uses vLLM's OpenAI-compatible router
    web_app = fastapi.FastAPI(
        title=f"OpenAI-compatible {MODEL_NAME} server",
        description="Run an OpenAI-compatible LLM server with vLLM on modal.com 🚀",
        version="0.0.1",
        docs_url="/docs",
    )

    # security: CORS middleware for external requests
    http_bearer = fastapi.security.HTTPBearer(
        scheme_name="Bearer Token",
        description="See code for authentication details.",
    )
    web_app.add_middleware(
        fastapi.middleware.cors.CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # security: inject dependency on authed routes
    async def is_authenticated(api_key: str = fastapi.Security(http_bearer)):
        if api_key.credentials != TOKEN:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return {"username": "authenticated_user"}

    router = fastapi.APIRouter(dependencies=[fastapi.Depends(is_authenticated)])

    # wrap vllm's router in auth router
    router.include_router(api_server.router)
    # add authed vllm to our fastAPI app
    web_app.include_router(router)

    engine_args = AsyncEngineArgs(
        model=MODELS_DIR + "/" + MODEL_NAME + "/merged",
        tensor_parallel_size=N_INFERENCE_GPUS,
        gpu_memory_utilization=0.90,
        max_model_len=4096,
        enforce_eager=True,  # capture the graph for faster inference, but slower cold starts (30s > 20s)
    )

    engine = AsyncLLMEngine.from_engine_args(
        engine_args, usage_context=UsageContext.OPENAI_API_SERVER
    )

    model_config = get_model_config(engine)

    request_logger = RequestLogger(max_log_len=2048)

    base_model_paths = [
        BaseModelPath(name=MODEL_NAME.split("/")[1], model_path=MODEL_NAME)
    ]

    api_server.chat = lambda s: OpenAIServingChat(
        engine,
        model_config=model_config,
        base_model_paths=base_model_paths,
        chat_template=None,
        response_role="assistant",
        lora_modules=[],
        prompt_adapters=[],
        request_logger=request_logger,
    )
    api_server.completion = lambda s: OpenAIServingCompletion(
        engine,
        model_config=model_config,
        base_model_paths=base_model_paths,
        lora_modules=[],
        prompt_adapters=[],
        request_logger=request_logger,
    )

    return web_app


def get_model_config(engine):
    import asyncio

    try:  # adapted from vLLM source -- https://github.com/vllm-project/vllm/blob/507ef787d85dec24490069ffceacbd6b161f4f72/vllm/entrypoints/openai/api_server.py#L235C1-L247C1
        event_loop = asyncio.get_running_loop()
    except RuntimeError:
        event_loop = None

    if event_loop is not None and event_loop.is_running():
        # If the current is instanced by Ray Serve,
        # there is already a running event loop
        model_config = event_loop.run_until_complete(engine.get_model_config())
    else:
        # When using single vLLM without engine_use_ray
        model_config = asyncio.run(engine.get_model_config())

    return model_config
