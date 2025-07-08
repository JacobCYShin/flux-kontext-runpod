import torch
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from nunchaku import NunchakuFluxTransformer2dModel
from nunchaku.utils import get_precision
import runpod


def load_model():
    transformer = NunchakuFluxTransformer2dModel.from_pretrained(
    f"mit-han-lab/nunchaku-flux.1-kontext-dev/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
    )

    pipeline = FluxKontextPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-Kontext-dev", transformer=transformer, torch_dtype=torch.bfloat16
    ).to("cuda")

    return pipeline

async def handler(job):
    job_input = job["input"]

    global model

    if "model" not in globals():
        model = load_model()

    image = load_image(job_input.get("image")).convert("RGB")
    result_image = model(image=image, prompt=job_input.get("prompt"), guidance_scale=2.5).images[0]
    
    job_result = {
        "image": result_image,
    }

    return job_result

if __name__ == "__main__":   
    runpod.serverless.start({"handler": handler})