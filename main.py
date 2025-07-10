from PIL import Image
import torch
import runpod
from runpod.serverless.utils.rp_validator import validate
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from nunchaku import NunchakuFluxTransformer2dModel
from nunchaku.utils import get_precision
from utils import (
    LATENT_RGB_FACTORS,
    resize_to_target_area,
    encode_image_to_base64,
    decode_base64_to_image,
)

schema = {
    "image": {
        "type": str,
        "required": True,
    },
    "prompt": {
        "type": str,
        "required": True,
    },
    "ratio": {
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

def handler(event):
    try:
        validated_input = validate(event["input"], schema)
        if "errors" in validated_input:
            return {"error": validated_input["errors"]}
        
        global model

        if "model" not in globals():
            model = load_model()

        validated_input = validated_input["validated_input"]

        image_source = validated_input["image"]
        prompt = validated_input["prompt"]
        ratio = validated_input["ratio"]

        if image_source.startswith(("http://", "https://")):
            input_image = load_image(image_source)
        else:
            input_image = decode_base64_to_image(image_source)

        input_image = input_image.convert("RGB")
        
        try:
            width, height = resize_to_target_area(input_image, ratio)
        except ValueError as e:
            return {"error": str(e)}
        
        def on_step_end_callback(pipeline, step: int, timestep: int, callback_kwargs: dict):
            # Send progress update every 5 steps
            if (step + 1) % 5 != 0:
                return {"latents": callback_kwargs["latents"]}

            latents = callback_kwargs["latents"]

            # Unpack latents, decode, and convert to PIL
            unpacked_latents = pipeline._unpack_latents(latents, height, width, pipeline.vae_scale_factor)  # (1, 16, 128, 128)
            with torch.no_grad():
                latent_rgb_factors = torch.tensor(LATENT_RGB_FACTORS, dtype=torch.float32, device='cpu')
                
                rgb = torch.einsum("...lhw,lr -> ...rhw", unpacked_latents.cpu().float(), latent_rgb_factors)
                rgb = (((rgb + 1) / 2).clamp(0, 1))  # Change scale from -1..1 to 0..1
                rgb = rgb.movedim(1,-1)

                image_np = (rgb[0] * 255).byte().numpy()
                pil_image = Image.fromarray(image_np)
                
                # Encode the preview image to a smaller JPEG format
                image_base64 = encode_image_to_base64(pil_image, use_jpeg=True)

                runpod.serverless.progress_update(event, {
                    "step": step + 1,
                    "image": image_base64
                })

            return {"latents": latents}

        output_image = model(image=input_image, prompt=prompt, width=width, height=height, guidance_scale=2.5, callback_on_step_end=on_step_end_callback,
    callback_on_step_end_tensor_inputs=["latents"]).images[0]
        
        # Convert the image to base64
        image_base64 = encode_image_to_base64(output_image)

        job_result = {
            "image": image_base64,
        }

        return job_result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":   
    runpod.serverless.start({"handler": handler})