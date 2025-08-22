from PIL import Image
import torch
import runpod
import time
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
    is_s3_url,
    download_image_from_s3,
    upload_image_to_s3,
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
    "output_format": {
        "type": str,
        "required": False,
        "default": "base64",  # "base64" 또는 "s3_url"
    },
}

def load_model():
    import os
    from huggingface_hub import snapshot_download
    
    # 로컬 체크포인트 경로 설정
    nunchaku_path = "/runpod-volume/checkpoints/nunchaku"
    flux_path = "/runpod-volume/checkpoints/flux-kontext"
    
    # 체크포인트 존재 여부 확인
    if not os.path.exists(nunchaku_path):
        print(f"Warning: 로컬 체크포인트가 없습니다: {nunchaku_path}")
        print("원격에서 다운로드합니다...")
        
        # 원격에서 다운로드 (기존 방식)
        transformer = NunchakuFluxTransformer2dModel.from_pretrained(
            f"mit-han-lab/nunchaku-flux.1-kontext-dev/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
        )
        
        # HF_TOKEN 확인
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            print("Warning: HF_TOKEN이 설정되지 않았습니다. 공개 모델만 사용 가능합니다.")
        
        pipeline = FluxKontextPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-Kontext-dev", transformer=transformer, torch_dtype=torch.bfloat16
        ).to("cuda")
    else:
        print(f"로컬 체크포인트 사용: {nunchaku_path}")
        
        # 로컬 체크포인트에서 로드 (전체 모델 경로 사용)
        transformer = NunchakuFluxTransformer2dModel.from_pretrained(
            f"{nunchaku_path}/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
        )
        
        if not os.path.exists(flux_path):
            print(f"Warning: FLUX 체크포인트가 없습니다: {flux_path}")
            print("원격에서 다운로드합니다...")
            
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                print("Warning: HF_TOKEN이 설정되지 않았습니다. 공개 모델만 사용 가능합니다.")
            
            pipeline = FluxKontextPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-Kontext-dev", transformer=transformer, torch_dtype=torch.bfloat16
            ).to("cuda")
        else:
            print(f"로컬 FLUX 체크포인트 사용: {flux_path}")
            pipeline = FluxKontextPipeline.from_pretrained(
                flux_path, transformer=transformer, torch_dtype=torch.bfloat16
            ).to("cuda")

    return pipeline

def handler(event):
    try:
        job_input = event.get("input", {})
        
        # Health check 요청 처리
        if job_input.get("type") == "health_check":
            return {
                "status": "healthy",
                "message": "Flux-Kontext service is running",
                "timestamp": time.time()
            }
        
        # 모델 목록 조회 요청 처리
        if job_input.get("type") == "list_models":
            return {
                "status": "success",
                "models": {
                    "transformer": "mit-han-lab/nunchaku-flux.1-kontext-dev",
                    "pipeline": "black-forest-labs/FLUX.1-Kontext-dev"
                },
                "message": "Available models retrieved successfully"
            }
        
        # 기본 이미지 생성 요청 처리
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
        output_format = validated_input.get("output_format", "base64")

        # 이미지 소스 처리 (S3 URL, HTTP URL, 또는 base64)
        if is_s3_url(image_source):
            # S3 URL에서 이미지 다운로드
            input_image = download_image_from_s3(image_source)
            if input_image is None:
                return {"error": "S3에서 이미지 다운로드 실패"}
        elif image_source.startswith(("http://", "https://")):
            # 일반 HTTP URL에서 이미지 로드
            input_image = load_image(image_source)
        else:
            # base64 디코딩
            input_image = decode_base64_to_image(image_source)

        input_image = input_image.convert("RGB")
        
        try:
            width, height = resize_to_target_area(input_image, ratio)
        except ValueError as e:
            return {"error": str(e)}
        
        def on_step_end_callback(pipeline, step: int, timestep: int, callback_kwargs: dict):
            """진행 상황을 업데이트하는 콜백 함수"""
            total_steps = len(pipeline.scheduler.timesteps)
            progress = int(((step + 1) / total_steps) * 100)
            
            # 진행 상황 로깅
            print(f"진행률: {progress}% ({step + 1}/{total_steps})")

            # 5단계마다 또는 마지막 단계에서 진행 상황 업데이트
            if (step + 1) % 5 == 0 or (step + 1) >= (total_steps - 1):
                try:
                    latents = callback_kwargs["latents"]

                    # Unpack latents, decode, and convert to PIL
                    unpacked_latents = pipeline._unpack_latents(latents, height, width, pipeline.vae_scale_factor)
                    with torch.no_grad():
                        latent_rgb_factors = torch.tensor(LATENT_RGB_FACTORS, dtype=torch.float32, device='cpu')
                        
                        rgb = torch.einsum("...lhw,lr -> ...rhw", unpacked_latents.cpu().float(), latent_rgb_factors)
                        rgb = (((rgb + 1) / 2).clamp(0, 1))  # Change scale from -1..1 to 0..1
                        rgb = rgb.movedim(1,-1)

                        image_np = (rgb[0] * 255).byte().numpy()
                        pil_image = Image.fromarray(image_np)
                        
                        # Encode the preview image to a smaller JPEG format
                        image_base64 = encode_image_to_base64(pil_image, use_jpeg=True)

                        # RunPod progress update
                        runpod.serverless.progress_update(event, {
                            "progress": progress,
                            "step": step + 1,
                            "total_steps": total_steps,
                            "preview_image": image_base64,
                            "status": "processing"
                        })
                        
                        print(f"진행 상황 업데이트 완료: {progress}%")
                except Exception as e:
                    print(f"진행 상황 업데이트 실패: {e}")
                    # 진행 상황 업데이트 실패해도 계속 진행
                    runpod.serverless.progress_update(event, {
                        "progress": progress,
                        "step": step + 1,
                        "total_steps": total_steps,
                        "status": "processing"
                    })

            return {"latents": callback_kwargs["latents"]}

        output_image = model(image=input_image, prompt=prompt, width=width, height=height, guidance_scale=2.5, callback_on_step_end=on_step_end_callback,
    callback_on_step_end_tensor_inputs=["latents"]).images[0]
        
        # 출력 형식에 따라 처리
        if output_format == "s3_url":
            # S3에 업로드하고 URL 반환
            image_url = upload_image_to_s3(output_image)
            if image_url is None:
                return {"error": "S3 업로드 실패"}
            
            job_result = {
                "image_url": image_url,
                "format": "s3_url",
                "status": "completed",
                "progress": 100
            }
        else:
            # base64 인코딩 (기본값)
            image_base64 = encode_image_to_base64(output_image)
            
            job_result = {
                "image": image_base64,
                "format": "base64",
                "status": "completed",
                "progress": 100
            }

        # 최종 완료 상태 업데이트
        runpod.serverless.progress_update(event, {
            "progress": 100,
            "status": "completed",
            "message": "Image generation completed successfully"
        })

        return job_result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":   
    runpod.serverless.start({"handler": handler})