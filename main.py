from io import BytesIO
import base64
from PIL import Image
import torch
import runpod
from runpod.serverless.utils.rp_validator import validate
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from nunchaku import NunchakuFluxTransformer2dModel
from nunchaku.utils import get_precision


LATENT_RGB_FACTORS = [
    [-0.0346,  0.0244,  0.0681],
    [ 0.0034,  0.0210,  0.0687],
    [ 0.0275, -0.0668, -0.0433],
    [-0.0174,  0.0160,  0.0617],
    [ 0.0859,  0.0721,  0.0329],
    [ 0.0004,  0.0383,  0.0115],
    [ 0.0405,  0.0861,  0.0915],
    [-0.0236, -0.0185, -0.0259],
    [-0.0245,  0.0250,  0.1180],
    [ 0.1008,  0.0755, -0.0421],
    [-0.0515,  0.0201,  0.0011],
    [ 0.0428, -0.0012, -0.0036],
    [ 0.0817,  0.0765,  0.0749],
    [-0.1264, -0.0522, -0.1103],
    [-0.0280, -0.0881, -0.0499],
    [-0.1262, -0.0982, -0.0778]
]

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

def encode_image_to_base64(image, use_jpeg=False):
    buffered = BytesIO()
    if use_jpeg:
        # Convert to RGB if it's RGBA, as JPEG doesn't support alpha channel
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        # Save as JPEG with a specific quality for smaller size
        image.save(buffered, format="JPEG", quality=85)
    else:
        image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def decode_base64_to_image(base64_str):
    """
    Decodes a base64 string to an image.
    """
    if "," in base64_str:
        base64_str = base64_str.split(',')[1]

    try:
        image_data = base64.b64decode(base64_str)
        return Image.open(BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"Invalid base64 string: {e}")


def handler(event):
    try:
        validated_input = validate(event["input"], schema)
        if "errors" in validated_input:
            return {"error": validated_input["errors"]}
        
        global model

        if "model" not in globals():
            model = load_model()

        
        def on_step_end_callback(pipeline, step: int, timestep: int, callback_kwargs: dict):
            # Send progress update every 5 steps
            if (step + 1) % 5 != 0:
                return {"latents": callback_kwargs["latents"]}

            latents = callback_kwargs["latents"]

            # Unpack latents, decode, and convert to PIL
            height = 1024
            width = 1024
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

        image_source = validated_input["validated_input"]["image"]
        prompt = validated_input["validated_input"]["prompt"]

        if image_source.startswith(("http://", "https://")):
            input_image = load_image(image_source)
        else:
            input_image = decode_base64_to_image(image_source)

        input_image = input_image.convert("RGB")

        output_image = model(image=input_image, prompt=prompt, guidance_scale=2.5, callback_on_step_end=on_step_end_callback,
    callback_on_step_end_tensor_inputs=["latents"]).images[0]
        
        print("output_image", output_image)
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