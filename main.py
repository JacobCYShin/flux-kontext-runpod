import torch
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from nunchaku import NunchakuFluxTransformer2dModel
from nunchaku.utils import get_precision
import runpod
from runpod.serverless.utils.rp_validator import validate
from io import BytesIO
import base64

schema = {
    "image": {
        "type": str,
        "required": True,
    },
    "prompt": {
        "type": str,
        "required": True,
    },
}

def load_model():
    transformer = NunchakuFluxTransformer2dModel.from_pretrained(
    f"mit-han-lab/nunchaku-flux.1-kontext-dev/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
    )

    pipeline = FluxKontextPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-Kontext-dev", transformer=transformer, torch_dtype=torch.bfloat16
    ).to("cuda")

    return pipeline

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def handler(event):
    try:
        validated_input = validate(event["input"], schema)
        if "errors" in validated_input:
            return {"error": validated_input["errors"]}
        
        global model

        if "model" not in globals():
            model = load_model()

        image = validated_input["validated_input"]["image"]
        prompt = validated_input["validated_input"]["prompt"]

        image = load_image(image).convert("RGB")
        image = model(image=image, prompt=prompt, guidance_scale=2.5).images[0]
        
        # Convert the image to base64
        image_base64 = image_to_base64(image)


        job_result = {
            "image": image_base64,
        }

        return job_result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":   
    runpod.serverless.start({"handler": handler})