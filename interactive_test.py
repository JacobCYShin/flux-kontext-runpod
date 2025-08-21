#!/usr/bin/env python3
"""
대화형 Flux Kontext 테스트 스크립트
사용자가 대화형으로 입력을 제공할 수 있는 간단한 인터페이스
"""

import os
import sys
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

def get_user_input():
    """사용자로부터 입력을 받습니다."""
    print("\n" + "="*60)
    print("🎨 Flux Kontext 대화형 테스트")
    print("="*60)
    
    # 이미지 경로 입력
    while True:
        image_path = input("📸 이미지 파일 경로를 입력하세요: ").strip()
        if os.path.exists(image_path):
            break
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
            print("다시 시도해주세요.")
    
    # 프롬프트 입력
    prompt = input("💬 변환 프롬프트를 입력하세요 (예: make it a watercolor painting): ").strip()
    if not prompt:
        prompt = "enhance this image"
    
    # 비율 선택
    print("\n📐 비율을 선택하세요:")
    print("1. 1:1 (정사각형)")
    print("2. 16:9 (가로형)")
    print("3. 9:16 (세로형)")
    print("4. 4:3 (전통적)")
    print("5. original (원본 비율)")
    
    ratio_choice = input("선택 (1-5): ").strip()
    ratio_map = {
        "1": "1:1",
        "2": "16:9", 
        "3": "9:16",
        "4": "4:3",
        "5": "original"
    }
    ratio = ratio_map.get(ratio_choice, "original")
    
    # 출력 파일명
    output_path = input("💾 출력 파일명을 입력하세요 (기본값: output.png): ").strip()
    if not output_path:
        output_path = "output.png"
    
    return image_path, prompt, ratio, output_path

def process_image(image_path, prompt, ratio, output_path):
    """이미지를 처리하고 결과를 저장합니다."""
    print(f"\n📸 입력 이미지: {image_path}")
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
        
        print("\n🚀 이미지 생성 시작...")
        
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
        print(f"\n✅ 생성 완료! 결과 이미지: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    # CUDA 사용 가능 여부 확인
    if not torch.cuda.is_available():
        print("❌ CUDA가 사용 불가능합니다. GPU가 필요합니다.")
        sys.exit(1)
    
    try:
        while True:
            # 사용자 입력 받기
            image_path, prompt, ratio, output_path = get_user_input()
            
            # 이미지 처리 실행
            success = process_image(image_path, prompt, ratio, output_path)
            
            if success:
                print("\n🎉 처리 완료!")
            else:
                print("\n💥 처리 실패!")
            
            # 계속할지 묻기
            continue_choice = input("\n다른 이미지로 테스트하시겠습니까? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', 'ㅇ']:
                print("👋 테스트를 종료합니다.")
                break
                
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    main() 