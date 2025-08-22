#!/usr/bin/env python3
"""
Flux-Kontext RunPod 간단 테스트 스크립트
빠른 테스트를 위한 간단한 버전입니다.
"""

import os
import sys
import requests
import base64
from PIL import Image
import io

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv가 설치되지 않았습니다.")
    sys.exit(1)

def test_flux_kontext():
    """Flux-Kontext API 간단 테스트"""
    
    # 환경변수 확인
    api_key = os.getenv('RUNPOD_API_KEY')
    endpoint = os.getenv('RUNPOD_FLUX_KONTEXT_ENDPOINT')
    
    if not api_key or not endpoint:
        print("❌ 환경변수가 설정되지 않았습니다.")
        print("env_example.txt를 .env로 복사하고 설정해주세요.")
        return False
    
    # 테스트 이미지 경로 (asset 폴더의 이미지 사용)
    test_image_path = "asset/test_image.jpg"
    
    if not os.path.exists(test_image_path):
        print(f"❌ 테스트 이미지가 없습니다: {test_image_path}")
        print("asset 폴더에 test_image.jpg 파일을 넣어주세요.")
        return False
    
    # 이미지를 base64로 인코딩
    try:
        with open(test_image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ 이미지 인코딩 실패: {e}")
        return False
    
    # API 요청 데이터
    payload = {
        "input": {
            "image": image_base64,
            "prompt": "A beautiful landscape with mountains and sunset",
            "ratio": "16:9",
            "output_format": "base64"
        }
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("🚀 Flux-Kontext API 테스트 시작...")
    print(f"📤 엔드포인트: {endpoint}")
    print(f"📤 프롬프트: {payload['input']['prompt']}")
    
    try:
        # API 호출
        response = requests.post(
            f"{endpoint}/run",
            headers=headers,
            json=payload,
            timeout=300
        )
        
        if response.status_code != 200:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
        
        result = response.json()
        
        if "error" in result:
            print(f"❌ API 에러: {result['error']}")
            return False
        
        # 결과 처리
        if "image" in result:
            # base64 이미지 저장
            try:
                image_data = base64.b64decode(result["image"])
                image = Image.open(io.BytesIO(image_data))
                
                output_path = "test_output.png"
                image.save(output_path)
                print(f"✅ 테스트 성공! 결과 이미지: {output_path}")
                return True
            except Exception as e:
                print(f"❌ 이미지 저장 실패: {e}")
                return False
        else:
            print("❌ 응답에 이미지가 없습니다.")
            print(f"응답: {result}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ API 호출 타임아웃 (5분)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 연결 실패 - 엔드포인트 URL을 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_flux_kontext()
    sys.exit(0 if success else 1)
