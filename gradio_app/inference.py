import asyncio
import aiohttp
from runpod import AsyncioEndpoint, AsyncioJob
from PIL import Image
import traceback

# Optional imports for local inference
try:
    import torch
    from diffusers import FluxKontextPipeline
    from diffusers.utils import load_image as diffusers_load_image
    from nunchaku import NunchakuFluxTransformer2dModel
    from nunchaku.utils import get_precision
    LOCAL_INFERENCE_ENABLED = torch.cuda.is_available()
    if not LOCAL_INFERENCE_ENABLED:
        print("Warning: No CUDA device found, local inference will be disabled.")
except ImportError:
    print("Warning: Some libraries for local inference are not installed. Local inference will be disabled.")
    LOCAL_INFERENCE_ENABLED = False

from config import RUNPOD_ENDPOINT_ID, LATENT_RGB_FACTORS
from utils import base64_to_pil, image_to_base64_uri, resize_to_target_area

# --- Local Inference ---
local_pipeline = None

def _initialize_local_pipeline():
    """Initializes and returns the local pipeline. Should not be called directly."""
    global local_pipeline
    if local_pipeline is None and LOCAL_INFERENCE_ENABLED:
        print("Initializing local pipeline for the first time...")
        try:
            transformer = NunchakuFluxTransformer2dModel.from_pretrained(
                f"mit-han-lab/nunchaku-flux.1-kontext-dev/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
            )
            pipeline = FluxKontextPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-Kontext-dev", transformer=transformer, torch_dtype=torch.bfloat16
            )
            pipeline.enable_sequential_cpu_offload()
            local_pipeline = pipeline
            print("Local pipeline initialized successfully.")
        except Exception as e:
            print(f"Error initializing local pipeline: {e}")
            local_pipeline = None  # Indicate failure
    return local_pipeline

def run_local_generation_sync(image_path: str, prompt: str, ratio: str, update_queue: asyncio.Queue, display_size: tuple[int, int]):
    """Synchronous function for local generation with progress updates."""
    pipeline = _initialize_local_pipeline()
    if pipeline is None:
        update_queue.put_nowait((None, "Status: Local pipeline initialization failed. Check server logs."))
        return

    try:
        input_image = diffusers_load_image(image_path).convert("RGB")
        width, height = resize_to_target_area(input_image, ratio)

        def on_step_end_callback(pipe, step: int, timestep: int, callback_kwargs: dict):
            total_steps = len(pipe.scheduler.timesteps)
            progress = int(((step + 1) / total_steps) * 100)
            
            if (step + 1) % 5 != 0 and (step + 1) < (total_steps - 1):
                return callback_kwargs

            latents = callback_kwargs["latents"]
            unpacked_latents = pipe._unpack_latents(latents, height, width, pipe.vae_scale_factor)
            
            with torch.no_grad():
                latent_rgb_factors = torch.tensor(LATENT_RGB_FACTORS, dtype=torch.float32, device='cpu')
                rgb = torch.einsum("...lhw,lr -> ...rhw", unpacked_latents.cpu().float(), latent_rgb_factors)
                rgb = (((rgb + 1) / 2).clamp(0, 1)).movedim(1, -1)
                image_np = (rgb[0] * 255).byte().numpy()
                pil_image = Image.fromarray(image_np)
                resized_intermediate = pil_image.resize(display_size, Image.Resampling.LANCZOS)
                update_queue.put_nowait((resized_intermediate, f"Status: In progress... ({progress}%)"))

            return callback_kwargs

        generated_image = pipeline(
            image=input_image, prompt=prompt, width=width, height=height, guidance_scale=2.5,
            callback_on_step_end=on_step_end_callback, callback_on_step_end_tensor_inputs=["latents"]
        ).images[0]
        
        update_queue.put_nowait((generated_image, "Status: Local generation complete!"))

    except Exception as e:
        traceback.print_exc()
        update_queue.put_nowait((None, f"Status: An error occurred during local generation: {e}"))


async def local_generation_flow(image_path: str, prompt: str, ratio: str):
    """Asynchronous wrapper for local image generation."""
    if not LOCAL_INFERENCE_ENABLED:
        yield None, "Status: Local inference is not available. Check server logs for details."
        return

    yield None, "Status: Starting local generation..."
    
    update_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    with Image.open(image_path) as img:
        display_size = resize_to_target_area(img, ratio)

    generation_task = loop.run_in_executor(
        None, run_local_generation_sync, image_path, prompt, ratio, update_queue, display_size
    )

    last_known_image = None
    while True:
        try:
            image, status = await asyncio.wait_for(update_queue.get(), timeout=1.0)
            last_known_image = image if image else last_known_image
            yield last_known_image, status
            update_queue.task_done()
        except asyncio.TimeoutError:
            if generation_task.done():
                break
    
    await generation_task


# --- RunPod Inference ---
async def runpod_generation_flow(image_path: str, prompt: str, ratio: str):
    """Handles the image generation flow using the RunPod endpoint."""
    with Image.open(image_path) as img:
        display_size = resize_to_target_area(img, ratio)
    
    last_known_image = None
    yield last_known_image, "Status: Starting..."

    image_uri = image_to_base64_uri(image_path)
    input_payload = {"image": image_uri, "prompt": prompt, "ratio": ratio.lower()}

    async with aiohttp.ClientSession() as session:
        try:
            endpoint = AsyncioEndpoint(RUNPOD_ENDPOINT_ID, session)
            job_request = endpoint.run(input_payload)
            yield last_known_image, "Status: Job submitted. Waiting for processing..."
            job: AsyncioJob = await job_request
            
            status_message = f"Status: Job {job.job_id} is in progress..."
            yield last_known_image, status_message

            last_progress = -1
            while True:
                status = await job.status()
                
                if status == "COMPLETED":
                    output = await job.output()
                    if output and "image" in output:
                        final_image = base64_to_pil(output["image"])
                        final_image.save("final_image.png")
                        yield final_image, "Status: Generation complete!"
                    else:
                        error_detail = f"Output: {str(output)[:100]}..." if output else "No output."
                        yield None, f"Status: Job completed but no image in output. {error_detail}"
                    break
                elif status in ["FAILED", "CANCELLED"]:
                    job_details = await job.error() or f"Job status was {status}"
                    yield last_known_image, f"Status: Job failed or was cancelled. Details: {job_details}"
                    break
                else:  # IN_QUEUE, IN_PROGRESS
                    data = await job._fetch_job()
                    if "output" in data and isinstance(data.get("output"), dict):
                        stream_output = data["output"]
                        progress = stream_output.get("progress")
                        if progress is not None and progress > last_progress:
                            last_progress = progress
                            status_message = f"Status: In progress... ({progress}%)"
                            
                            if stream_output.get("image"):
                                intermediate_pil = base64_to_pil(stream_output["image"])
                                resized_intermediate = intermediate_pil.resize(display_size, Image.Resampling.LANCZOS)
                                last_known_image = resized_intermediate
                            
                            yield last_known_image, status_message
                    
                    if status == "IN_PROGRESS":
                        await asyncio.sleep(0.2)
                    else:  # IN_QUEUE
                        await asyncio.sleep(1)

        except Exception as e:
            yield last_known_image, f"Status: An error occurred: {e}"


# --- Main Dispatcher ---
async def generate(execution_env: str, image_path: str, prompt: str, ratio: str):
    """
    Main dispatcher function to handle image generation.
    It calls the appropriate generation flow based on the selected environment.
    """
    if not image_path:
        yield None, "Status: Please upload an image to generate."
        return

    if execution_env == "local":
        async for result in local_generation_flow(image_path, prompt, ratio):
            yield result
    else: # runpod
        async for result in runpod_generation_flow(image_path, prompt, ratio):
            yield result 