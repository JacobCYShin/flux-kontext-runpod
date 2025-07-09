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

def encode_image_to_base64(image):
    buffered = BytesIO()
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
                unpacked_latents = (
                    unpacked_latents / pipeline.vae.config.scaling_factor
                ) + pipeline.vae.config.shift_factor
                decoded_images = pipeline.vae.decode(unpacked_latents, return_dict=False)[0]
                
                # Use the pipeline's image processor to convert to PIL
                pil_images = pipeline.image_processor.postprocess(decoded_images, output_type="pil")
                
                # Encode the first image to base64
                image_base64 = encode_image_to_base64(pil_images[0])

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
        print("_callback_tensor_inputs", model._callback_tensor_inputs)

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