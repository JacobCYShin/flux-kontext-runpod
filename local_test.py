#!/usr/bin/env python3
"""
로컬 테스트용 Flux Kontext 스크립트
기존 main.py의 핵심 로직을 재사용하되 RunPod 의존성을 제거한 버전
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import torch
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from nunchaku import NunchakuFluxTransformer2dModel
from nunchaku.utils import get_precision

# utils.py에서 필요한 함수들 import
from utils import (
    LATENT_RGB_FACTORS,
    resize_to_target_area,
    encode_image_to_base64,
    decode_base64_to_image,
)

def load_model():
    """모델을 로드하고 초기화합니다."""
    print("🔄 모델 로딩 중...")
    
    try:
        transformer = NunchakuFluxTransformer2dModel.from_pretrained(
            f"mit-han-lab/nunchaku-flux.1-kontext-dev/svdq-{get_precision()}_r32-flux.1-kontext-dev.safetensors"
        )

        pipeline = FluxKontextPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-Kontext-dev", 
            transformer=transformer, 
            torch_dtype=torch.bfloat16
        ).to("cuda")
        
        print("✅ 모델 로딩 완료!")
        return pipeline
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return None

def create_progress_callback(total_steps):
    """진행 상황을 콘솔에 출력하는 콜백 함수를 생성합니다."""
    def on_step_end_callback(pipeline, step: int, timestep: int, callback_kwargs: dict):
        progress = int(((step + 1) / total_steps) * 100)
        
        # 5단계마다 또는 마지막 단계에서 진행 상황 출력
        if (step + 1) % 5 == 0 or (step + 1) == total_steps:
            print(f"🔄 생성 진행률: {progress}% ({step + 1}/{total_steps})")
        
        return {"latents": callback_kwargs["latents"]}
    
    return on_step_end_callback

def process_image(image_path, prompt, ratio, output_path="output.png"):
    """이미지를 처리하고 결과를 저장합니다."""
    print(f"📸 입력 이미지: {image_path}")
    print(f"💬 프롬프트: {prompt}")
    print(f"📐 비율: {ratio}")
    
    # 모델 로드
    model = load_model()
    if model is None:
        return False
    
    try:
        # 입력 이미지 처리
        if image_path.startswith(("http://", "https://")):
            input_image = load_image(image_path)
        else:
            input_image = Image.open(image_path)
        
        input_image = input_image.convert("RGB")
        
        # 이미지 크기 조정
        try:
            width, height = resize_to_target_area(input_image, ratio)
            print(f"📏 조정된 크기: {width}x{height}")
        except ValueError as e:
            print(f"❌ 크기 조정 오류: {e}")
            return False
        
        # 진행 상황 콜백 설정
        total_steps = len(model.scheduler.timesteps)
        progress_callback = create_progress_callback(total_steps)
        
        print("🚀 이미지 생성 시작...")
        
        # 이미지 생성
        output_image = model(
            image=input_image, 
            prompt=prompt, 
            width=width, 
            height=height, 
            guidance_scale=2.5, 
            callback_on_step_end=progress_callback,
            callback_on_step_end_tensor_inputs=["latents"]
        ).images[0]
        
        # 결과 저장
        output_image.save(output_path)
        print(f"✅ 생성 완료! 결과 이미지: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수 - CLI 인터페이스 제공"""
    parser = argparse.ArgumentParser(
        description="Flux Kontext 로컬 테스트 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python local_test.py image.jpg "make it a watercolor painting" "1:1"
  python local_test.py image.png "add snow" "16:9" --output result.png
        """
    )
    
    parser.add_argument("image", help="입력 이미지 파일 경로")
    parser.add_argument("prompt", help="이미지 변환을 위한 프롬프트")
    parser.add_argument("ratio", help="출력 이미지 비율 (예: 1:1, 16:9, original)")
    parser.add_argument("--output", "-o", default="output.png", help="출력 파일 경로 (기본값: output.png)")
    
    args = parser.parse_args()
    
    # 입력 파일 존재 확인
    if not os.path.exists(args.image):
        print(f"❌ 입력 이미지 파일을 찾을 수 없습니다: {args.image}")
        sys.exit(1)
    
    # CUDA 사용 가능 여부 확인
    if not torch.cuda.is_available():
        print("❌ CUDA가 사용 불가능합니다. GPU가 필요합니다.")
        sys.exit(1)
    
    print("🎨 Flux Kontext 로컬 테스트 시작")
    print("=" * 50)
    
    # 이미지 처리 실행
    success = process_image(args.image, args.prompt, args.ratio, args.output)
    
    if success:
        print("=" * 50)
        print("🎉 테스트 완료!")
    else:
        print("=" * 50)
        print("💥 테스트 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main() 