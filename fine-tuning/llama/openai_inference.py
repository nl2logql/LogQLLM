import os
from pathlib import Path
from typing import Optional
import asyncio

import modal
import yaml
from common import HOURS, MINUTES, VOLUME_CONFIG, Colors, app, vllm_image
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

INFERENCE_GPU_CONFIG = os.environ.get("INFERENCE_GPU_CONFIG", "a10g:2")
if len(INFERENCE_GPU_CONFIG.split(":")) <= 1:
    N_INFERENCE_GPUS = int(os.environ.get("N_INFERENCE_GPUS", 2))
    INFERENCE_GPU_CONFIG = f"{INFERENCE_GPU_CONFIG}:{N_INFERENCE_GPUS}"
else:
    N_INFERENCE_GPUS = int(INFERENCE_GPU_CONFIG.split(":")[-1])


def get_model_path_from_run(path: Path) -> str:
    """Get the model path from a run directory's config"""
    with (path / "config.yml").open() as f:
        return str(
            (path / yaml.safe_load(f.read())["output_dir"] / "merged").resolve()
        )


@app.function(
    gpu=INFERENCE_GPU_CONFIG,
    image=vllm_image,
    volumes=dict(VOLUME_CONFIG),
    timeout=2*HOURS,
    allow_concurrent_inputs=1000,
)
@modal.asgi_app()
def serve(run_name: Optional[str] = None):
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

    # Load model path from runs directory
    run_dir = Path("/runs")
    VOLUME_CONFIG["/runs"].reload()

    if run_name:
        model_path = get_model_path_from_run(run_dir / run_name)
    else:
        run_paths = sorted(run_dir.iterdir(), reverse=True)
        for path in run_paths:
            try:
                model_path = get_model_path_from_run(path)
                if Path(model_path).exists():
                    break
            except (FileNotFoundError, KeyError):
                continue
        else:
            raise ValueError("No valid model found in runs directory")

    print(
        f"{Colors.GREEN}{Colors.BOLD}🧠: Loading model from {model_path}{Colors.END}"
    )

    # Create FastAPI app with security
    web_app = FastAPI(
        title="OpenAI-compatible Fine-tuned Model Server",
        description="Run an OpenAI-compatible LLM server with vLLM on modal.com 🚀",
        version="0.0.1",
        docs_url="/docs",
    )

    # Add CORS middleware for external requests
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup authentication
    http_bearer = HTTPBearer(
        scheme_name="Bearer Token",
        description="See code for authentication details.",
    )

    async def is_authenticated(
        auth: HTTPAuthorizationCredentials = Security(http_bearer),
    ):
        if auth.credentials != "your-secret-token":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )
        return True

    # Setup router with authentication
    router = fastapi.APIRouter(dependencies=[Depends(is_authenticated)])
    router.include_router(api_server.router)
    web_app.include_router(router)

    # Initialize vLLM engine
    engine_args = AsyncEngineArgs(
        model="models/nl-to-logql/llama-3.1-logql",
        # served_model_name="llama-3.1-logql",
        tensor_parallel_size=N_INFERENCE_GPUS,
        gpu_memory_utilization=0.90,
        max_model_len=4096,
        enforce_eager=False,
        disable_custom_all_reduce=True,
    )
    engine = AsyncLLMEngine.from_engine_args(
        engine_args, usage_context=UsageContext.OPENAI_API_SERVER
    )

    request_logger = RequestLogger(max_log_len=2048)

    try:
        event_loop = asyncio.get_running_loop()
    except RuntimeError:
        event_loop = None

    if event_loop is not None and event_loop.is_running():
        model_config = event_loop.run_until_complete(engine.get_model_config())
    else:
        model_config = asyncio.run(engine.get_model_config())

    base_model_paths = [
        BaseModelPath(name=Path(model_path).name, model_path=model_path)
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

# @app.local_entrypoint()
# def main(run_name: str = "", prompt: str = ""):
#     if not prompt:
#         prompt = input("Enter a prompt: ")

#     from openai import OpenAI

#     client = OpenAI(
#         base_url=f"https://{modal.NetworkFileSystem.current_workspace()}--{app.name}-serve.modal.run/v1",
#         api_key="your-secret-token",
#     )

#     response = client.chat.completions.create(
#         model="local-model",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.7,
#     )

#     print(f"{Colors.BLUE}👤: {prompt}{Colors.END}")
#     print(
#         f"{Colors.GREEN}{Colors.BOLD}🤖: {response.choices[0].message.content}{Colors.END}"
#     )
