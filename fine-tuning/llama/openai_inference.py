import os
import time
from pathlib import Path

import modal
from common import MINUTES, VOLUME_CONFIG, Colors, app, vllm_image
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

INFERENCE_GPU_CONFIG = os.environ.get("INFERENCE_GPU_CONFIG", "a10g:2")
if len(INFERENCE_GPU_CONFIG.split(":")) <= 1:
    N_INFERENCE_GPUS = int(os.environ.get("N_INFERENCE_GPUS", 2))
    INFERENCE_GPU_CONFIG = f"{INFERENCE_GPU_CONFIG}:{N_INFERENCE_GPUS}"
else:
    N_INFERENCE_GPUS = int(INFERENCE_GPU_CONFIG.split(":")[-1])

with vllm_image.imports():
    import yaml
    from vllm.engine.arg_utils import AsyncEngineArgs
    from vllm.engine.async_llm_engine import AsyncLLMEngine
    from vllm.sampling_params import SamplingParams
    from vllm.utils import random_uuid
    from vllm.entrypoints.openai.serving_chat import OpenAIServingChat
    from vllm.entrypoints.openai.serving_completion import OpenAIServingCompletion
    import vllm.entrypoints.openai.api_server as api_server

def get_model_path_from_run(path: Path) -> Path:
    with (path / "config.yml").open() as f:
        return path / yaml.safe_load(f.read())["output_dir"] / "merged"

@app.cls(
    gpu=INFERENCE_GPU_CONFIG,
    image=vllm_image,
    volumes=VOLUME_CONFIG,
    allow_concurrent_inputs=30,
    container_idle_timeout=15 * MINUTES,
)
class Inference:
    def __init__(self, run_name: str = "", run_dir: str = "/runs") -> None:
        self.run_name = run_name
        self.run_dir = run_dir
        self.web_app = FastAPI()

    @modal.enter()
    def init(self):
        if self.run_name:
            path = Path(self.run_dir) / self.run_name
            VOLUME_CONFIG[self.run_dir].reload()
            model_path = get_model_path_from_run(path)
        else:
            run_paths = list(Path(self.run_dir).iterdir())
            for path in sorted(run_paths, reverse=True):
                model_path = get_model_path_from_run(path)
                if model_path.exists():
                    break

        print(
            Colors.GREEN,
            Colors.BOLD,
            f"🧠: Initializing vLLM engine for model at {model_path}",
            Colors.END,
            sep="",
        )

        engine_args = AsyncEngineArgs(
            model=model_path,
            gpu_memory_utilization=0.95,
            tensor_parallel_size=N_INFERENCE_GPUS,
            disable_custom_all_reduce=True,
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.setup_openai_compatible_server()

    def setup_openai_compatible_server(self):
        self.web_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        http_bearer = HTTPBearer()

        async def authenticate(token: str = Security(http_bearer)):
            if token.credentials != "your-secret-token":
                raise HTTPException(status_code=401, detail="Invalid token")
            return token.credentials

        router = api_server.router
        self.web_app.include_router(router, dependencies=[Depends(authenticate)])

        model_config = self.get_model_config()
        api_server.engine = self.engine
        api_server.chat = lambda: OpenAIServingChat(self.engine, model_config)
        api_server.completion = lambda: OpenAIServingCompletion(self.engine, model_config)

    def get_model_config(self):
        import asyncio
        return asyncio.run(self.engine.get_model_config())

    async def _stream(self, input: str):
        if not input:
            return

        sampling_params = SamplingParams(
            repetition_penalty=1.1,
            temperature=0.2,
            top_p=0.95,
            top_k=50,
            max_tokens=1024,
        )
        request_id = random_uuid()
        results_generator = self.engine.generate(
            input, sampling_params, request_id
        )

        t0 = time.time()
        index, tokens = 0, 0
        async for request_output in results_generator:
            if (
                request_output.outputs[0].text
                and "\ufffd" == request_output.outputs[0].text[-1]
            ):
                continue
            yield request_output.outputs[0].text[index:]
            index = len(request_output.outputs[0].text)

            new_tokens = len(request_output.outputs[0].token_ids)
            tokens = new_tokens

        throughput = tokens / (time.time() - t0)
        print(
            Colors.GREEN,
            Colors.BOLD,
            f"🧠: Effective throughput of {throughput:.2f} tok/s",
            Colors.END,
            sep="",
        )

    @modal.method()
    async def completion(self, input: str):
        async for text in self._stream(input):
            yield text

    @modal.method()
    async def non_streaming(self, input: str):
        output = [text async for text in self._stream(input)]
        return "".join(output)

    @modal.asgi_app()
    def api(self):
        return self.web_app

    @modal.web_endpoint()
    async def web(self, input: str):
        return StreamingResponse(
            self._stream(input), media_type="text/event-stream"
        )

    @modal.exit()
    def stop_engine(self):
        if N_INFERENCE_GPUS > 1:
            import ray
            ray.shutdown()
        self.engine._background_loop_unshielded.cancel()

@app.local_entrypoint()
def inference_main(run_name: str = "", prompt: str = ""):
    if not prompt:
        prompt = input(
            "Enter a prompt (including the prompt template, e.g. [INST] ... [/INST]):\n"
        )
    print(
        Colors.GRAY,
        Colors.BOLD,
        f"🧠: Querying model {run_name}",
        Colors.END,
        sep="",
    )
    response = ""
    for chunk in Inference(run_name).completion.remote_gen(prompt):
        response += chunk
    print(Colors.BLUE, f"👤: {prompt}", Colors.END, sep="")
    print(Colors.GREEN, Colors.BOLD, f"🤖: {response}", Colors.END, sep="")
