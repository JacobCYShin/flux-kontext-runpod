#!/usr/bin/env python3
"""
Flux-Kontext RunPod 배포 테스트 스크립트
RunPod에 배포된 Flux-Kontext 모델을 테스트하는 클라이언트입니다.
"""

import os
import sys
import json
import time
import argparse
import requests
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
from PIL import Image
import io

# 환경변수 설정을 위한 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv가 설치되지 않았습니다. 'pip install python-dotenv'로 설치해주세요.")
    sys.exit(1)


class FluxKontextTestError(Exception):
    """Flux-Kontext 테스트 중 발생하는 에러"""
    pass


class FluxKontextClient:
    """Flux-Kontext RunPod API 클라이언트"""
    
    def __init__(self, endpoint_url: str, api_key: str):
        self.endpoint_url = endpoint_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        # S3 설정
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_bucket_name = os.getenv('S3_BUCKET_NAME')
    
    def _get_s3_client(self):
        """S3 클라이언트를 반환합니다."""
        try:
            import boto3
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                raise FluxKontextTestError("AWS 인증 정보가 설정되지 않았습니다. 환경변수를 확인해주세요.")
                
            return boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
        except ImportError:
            raise FluxKontextTestError("boto3가 설치되지 않았습니다. 'pip install boto3'로 설치해주세요.")
        except Exception as e:
            raise FluxKontextTestError(f"S3 클라이언트 생성 실패: {str(e)}")
    
    def _upload_image_to_s3(self, image_path: str) -> str:
        """이미지를 S3에 업로드하고 공개 URL을 반환합니다."""
        try:
            s3_client = self._get_s3_client()
            
            # S3 키 생성 (타임스탬프 포함)
            timestamp = int(time.time())
            file_name = os.path.basename(image_path)
            s3_key = f"test-images/{timestamp}_{file_name}"
            
            # S3에 업로드
            s3_client.upload_file(image_path, self.s3_bucket_name, s3_key)
            
            # S3 공개 URL 생성
            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            return s3_url
            
        except Exception as e:
            raise FluxKontextTestError(f"S3 업로드 실패: {image_path} - {str(e)}")
    
    def _image_to_base64(self, image_path: str) -> str:
        """이미지를 base64로 인코딩합니다."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise FluxKontextTestError(f"이미지 base64 인코딩 실패: {image_path} - {str(e)}")
    
    def _save_base64_image(self, base64_data: str, output_path: str):
        """base64 이미지를 파일로 저장합니다."""
        try:
            image_data = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_data))
            image.save(output_path)
            print(f"이미지 저장됨: {output_path}")
        except Exception as e:
            raise FluxKontextTestError(f"이미지 저장 실패: {output_path} - {str(e)}")
    
    def test_health_check(self) -> bool:
        """RunPod 엔드포인트 헬스 체크"""
        try:
            response = requests.get(f"{self.endpoint_url}/health", headers=self.headers, timeout=10)
            if response.status_code == 200:
                print("✅ RunPod 엔드포인트 연결 성공")
                return True
            else:
                print(f"❌ RunPod 엔드포인트 연결 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ RunPod 엔드포인트 연결 실패: {str(e)}")
            return False
    
    def generate_image(self, 
                      image_path: str, 
                      prompt: str, 
                      ratio: str = "16:9",
                      output_format: str = "base64",
                      use_s3_upload: bool = False) -> Dict[str, Any]:
        """
        Flux-Kontext를 사용하여 이미지를 생성합니다.
        
        Args:
            image_path: 입력 이미지 파일 경로
            prompt: 생성할 이미지에 대한 프롬프트
            ratio: 이미지 비율 (예: "16:9", "1:1", "4:3")
            output_format: 출력 형식 ("base64" 또는 "s3_url")
            use_s3_upload: 입력 이미지를 S3에 업로드할지 여부
            
        Returns:
            생성 결과 딕셔너리
        """
        try:
            # 입력 이미지 처리
            if use_s3_upload and self.s3_bucket_name:
                print("📤 S3에 입력 이미지 업로드 중...")
                image_source = self._upload_image_to_s3(image_path)
                print(f"📤 S3 URL: {image_source}")
            else:
                print("📤 입력 이미지를 base64로 인코딩 중...")
                image_source = self._image_to_base64(image_path)
            
            # API 요청 데이터 준비
            payload = {
                "input": {
                    "image": image_source,
                    "prompt": prompt,
                    "ratio": ratio,
                    "output_format": output_format
                }
            }
            
            print(f"🚀 Flux-Kontext API 호출 중...")
            print(f"   프롬프트: {prompt}")
            print(f"   비율: {ratio}")
            print(f"   출력 형식: {output_format}")
            
            # API 호출
            start_time = time.time()
            response = requests.post(
                f"{self.endpoint_url}/run", 
                headers=self.headers, 
                json=payload,
                timeout=300  # 5분 타임아웃
            )
            end_time = time.time()
            
            if response.status_code != 200:
                raise FluxKontextTestError(f"API 호출 실패: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # 결과 처리
            if "error" in result:
                raise FluxKontextTestError(f"API 에러: {result['error']}")
            
            print(f"✅ 이미지 생성 완료! (소요시간: {end_time - start_time:.2f}초)")
            
            return result
            
        except Exception as e:
            raise FluxKontextTestError(f"이미지 생성 실패: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Flux-Kontext RunPod 배포 테스트")
    parser.add_argument("image_path", help="입력 이미지 파일 경로")
    parser.add_argument("prompt", help="생성할 이미지에 대한 프롬프트")
    parser.add_argument("--ratio", default="16:9", help="이미지 비율 (기본값: 16:9)")
    parser.add_argument("--output-format", choices=["base64", "s3_url"], default="base64", 
                       help="출력 형식 (기본값: base64)")
    parser.add_argument("--use-s3-upload", action="store_true", 
                       help="입력 이미지를 S3에 업로드하여 사용")
    parser.add_argument("--output-dir", default="test_outputs", 
                       help="결과 저장 폴더 (기본값: test_outputs)")
    parser.add_argument("--save-metadata", action="store_true", 
                       help="메타데이터 JSON 파일도 저장")
    
    args = parser.parse_args()
    
    # 환경변수 확인
    runpod_api_key = os.getenv('RUNPOD_API_KEY')
    runpod_endpoint = os.getenv('RUNPOD_FLUX_KONTEXT_ENDPOINT')
    
    if not runpod_api_key:
        print("❌ RUNPOD_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    if not runpod_endpoint:
        print("❌ RUNPOD_FLUX_KONTEXT_ENDPOINT 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 클라이언트 초기화
    client = FluxKontextClient(runpod_endpoint, runpod_api_key)
    
    try:
        # 헬스 체크
        if not client.test_health_check():
            print("❌ RunPod 엔드포인트 연결에 실패했습니다.")
            sys.exit(1)
        
        # 이미지 생성
        result = client.generate_image(
            image_path=args.image_path,
            prompt=args.prompt,
            ratio=args.ratio,
            output_format=args.output_format,
            use_s3_upload=args.use_s3_upload
        )
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.output_format == "base64" and "image" in result:
            # base64 이미지 저장
            output_path = os.path.join(args.output_dir, f"flux_kontext_output_{timestamp}.png")
            client._save_base64_image(result["image"], output_path)
        elif args.output_format == "s3_url" and "image_url" in result:
            # S3 URL 출력
            print(f"📤 생성된 이미지 S3 URL: {result['image_url']}")
        
        # 메타데이터 저장
        if args.save_metadata:
            metadata = {
                "timestamp": timestamp,
                "input_image": args.image_path,
                "prompt": args.prompt,
                "ratio": args.ratio,
                "output_format": args.output_format,
                "result": result
            }
            
            metadata_path = os.path.join(args.output_dir, f"metadata_{timestamp}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print(f"📄 메타데이터 저장됨: {metadata_path}")
        
        print("🎉 테스트 완료!")
        
    except FluxKontextTestError as e:
        print(f"❌ 테스트 실패: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
