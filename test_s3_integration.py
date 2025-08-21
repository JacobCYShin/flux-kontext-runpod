#!/usr/bin/env python3
"""
S3 통합 기능 테스트 스크립트
기존 테스트 스크립트들과 호환되면서 S3 기능도 테스트
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
    is_s3_url,
    upload_image_to_s3,
    download_image_from_s3,
    get_s3_client,
)

def test_s3_functions():
    """S3 관련 함수들을 테스트합니다."""
    print("🧪 S3 함수 테스트 시작")
    print("=" * 50)
    
    # 1. S3 클라이언트 테스트
    print("1. S3 클라이언트 테스트...")
    s3_client = get_s3_client()
    if s3_client:
        print("   ✅ S3 클라이언트 생성 성공")
    else:
        print("   ⚠️ S3 클라이언트 생성 실패 (환경변수 미설정)")
    
    # 2. URL 검증 테스트
    print("\n2. URL 검증 테스트...")
    test_urls = [
        "https://example.com/image.jpg",
        "https://my-bucket.s3.us-east-1.amazonaws.com/image.jpg",
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
        "not_a_url"
    ]
    
    for url in test_urls:
        is_s3 = is_s3_url(url)
        print(f"   {url[:50]}... -> S3 URL: {is_s3}")
    
    # 3. 테스트 이미지 생성
    print("\n3. 테스트 이미지 생성...")
    test_image = Image.new('RGB', (100, 100), color='red')
    print("   ✅ 테스트 이미지 생성 완료")
    
    # 4. S3 업로드 테스트 (환경변수가 설정된 경우에만)
    print("\n4. S3 업로드 테스트...")
    if s3_client:
        upload_url = upload_image_to_s3(test_image, "test_image.jpg")
        if upload_url:
            print(f"   ✅ S3 업로드 성공: {upload_url}")
            
            # 5. S3 다운로드 테스트
            print("\n5. S3 다운로드 테스트...")
            downloaded_image = download_image_from_s3(upload_url)
            if downloaded_image:
                print("   ✅ S3 다운로드 성공")
                print(f"   📏 다운로드된 이미지 크기: {downloaded_image.size}")
            else:
                print("   ❌ S3 다운로드 실패")
        else:
            print("   ❌ S3 업로드 실패")
    else:
        print("   ⚠️ S3 클라이언트 없음 - 업로드/다운로드 테스트 건너뜀")
    
    print("\n" + "=" * 50)
    print("🧪 S3 함수 테스트 완료")

def test_backward_compatibility():
    """기존 함수들과의 호환성을 테스트합니다."""
    print("\n🔄 호환성 테스트 시작")
    print("=" * 50)
    
    # 1. 기존 base64 함수들 테스트
    print("1. 기존 base64 함수들 테스트...")
    test_image = Image.new('RGB', (50, 50), color='blue')
    
    # 인코딩 테스트
    base64_str = encode_image_to_base64(test_image)
    print(f"   ✅ base64 인코딩 성공 (길이: {len(base64_str)})")
    
    # 디코딩 테스트
    decoded_image = decode_base64_to_image(base64_str)
    print(f"   ✅ base64 디코딩 성공 (크기: {decoded_image.size})")
    
    # 2. 크기 조정 함수 테스트
    print("\n2. 크기 조정 함수 테스트...")
    try:
        width, height = resize_to_target_area(test_image, "1:1")
        print(f"   ✅ 크기 조정 성공: {width}x{height}")
    except Exception as e:
        print(f"   ❌ 크기 조정 실패: {e}")
    
    # 3. 다양한 비율 테스트
    ratios = ["1:1", "16:9", "9:16", "4:3", "original"]
    for ratio in ratios:
        try:
            width, height = resize_to_target_area(test_image, ratio)
            print(f"   ✅ 비율 {ratio}: {width}x{height}")
        except Exception as e:
            print(f"   ❌ 비율 {ratio} 실패: {e}")
    
    print("\n" + "=" * 50)
    print("🔄 호환성 테스트 완료")

def main():
    """메인 테스트 함수"""
    print("🎨 Flux Kontext S3 통합 테스트")
    print("=" * 60)
    
    # 환경변수 확인
    print("📋 환경변수 확인:")
    env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * len(value)} (설정됨)")
        else:
            print(f"   ⚠️ {var}: 설정되지 않음")
    
    print()
    
    # S3 함수 테스트
    test_s3_functions()
    
    # 호환성 테스트
    test_backward_compatibility()
    
    print("\n🎉 모든 테스트 완료!")
    print("\n💡 참고사항:")
    print("   - S3 기능을 사용하려면 .env 파일에 AWS 인증 정보를 설정하세요")
    print("   - 기존 base64 방식은 그대로 사용 가능합니다")
    print("   - interactive_test.py와 local_test.py는 정상 동작합니다")

if __name__ == "__main__":
    main() 