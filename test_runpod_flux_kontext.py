#!/usr/bin/env python3
"""
Flux-Kontext RunPod Serverless API 테스트 스크립트
RunPod에 배포된 Flux-Kontext 모델을 테스트하는 클라이언트입니다.
- 동기(runsync)와 비동기(run/status) 모두 지원
- Health check 및 status 체크 기능
- S3 URL 및 base64 출력 형식 지원
"""

import os
import sys
import json
import time
import argparse
import requests
import base64
from datetime import datetime
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
    """Flux-Kontext RunPod Serverless API 클라이언트"""
    
    def __init__(self, endpoint_url: str, api_key: str):
        """
        클라이언트 초기화
        
        Args:
            endpoint_url: RunPod Endpoint 기준 URL. 예시:
              - https://api.runpod.ai/v2/<ENDPOINT_ID>
              - 또는 기존 형식: https://api.runpod.ai/v2/<ENDPOINT_ID>/run, /runsync 중 하나
            api_key: RunPod API 키
        """
        # 엔드포인트 URL 정규화
        base = endpoint_url.rstrip("/")
        if base.endswith("/run") or base.endswith("/runsync") or base.endswith("/status"):
            # 기존 형식에서 엔드포인트 베이스로 환원
            base = base.rsplit("/", 1)[0]
        
        self.base_url = base
        self.url_run = f"{self.base_url}/run"
        self.url_runsync = f"{self.base_url}/runsync"
        self.url_status_base = f"{self.base_url}/status"
        
        print(f"엔드포인트 BASE URL: {self.base_url}")
        print(f"RUN URL: {self.url_run}")
        print(f"RUNSYNC URL: {self.url_runsync}")
        
        self.api_key = api_key
        
        # requests 세션 설정
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 5분 타임아웃 기본값
        self.session.timeout = 300
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers.update(headers)
    
    def _unwrap_output(self, response_json: dict) -> dict:
        """RunPod runsync/run 응답에서 output 래핑을 해제합니다."""
        print(f"원본 응답: {response_json}")
        
        # status가 COMPLETED인 경우 output 필드 확인
        if response_json.get("status") == "COMPLETED":
            if "output" in response_json and isinstance(response_json["output"], dict):
                print(f"output 필드 발견: {response_json['output']}")
                return response_json["output"]
            else:
                print("output 필드가 없거나 올바르지 않습니다.")
                return response_json
        
        # 일반적인 경우
        if isinstance(response_json, dict) and "output" in response_json and isinstance(response_json["output"], dict):
            return response_json["output"]
        return response_json
    
    def _status_url(self, job_id: str) -> str:
        return f"{self.url_status_base}/{job_id}"
    
    def _upload_image_to_s3(self, image_path: str) -> str:
        """이미지를 S3에 업로드하고 공개 URL을 반환합니다."""
        try:
            import boto3
            import time
            
            # AWS 설정
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            s3_bucket_name = os.getenv('S3_BUCKET_NAME', 'likebutter-bucket')
            
            if not aws_access_key_id or not aws_secret_access_key:
                raise FluxKontextTestError("AWS 인증 정보가 설정되지 않았습니다. 환경변수를 확인해주세요.")
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            
            # S3 키 생성 (타임스탬프 포함)
            timestamp = int(time.time())
            file_name = os.path.basename(image_path)
            s3_key = f"source-Images/{timestamp}_{file_name}"
            
            # S3에 업로드
            s3_client.upload_file(image_path, s3_bucket_name, s3_key)
            
            # S3 공개 URL 생성
            s3_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
            
            return s3_url
            
        except ImportError:
            raise FluxKontextTestError("boto3가 설치되지 않았습니다. 'pip install boto3'로 설치해주세요.")
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
            print(f"✅ 이미지 저장됨: {output_path}")
        except Exception as e:
            raise FluxKontextTestError(f"이미지 저장 실패: {output_path} - {str(e)}")
    
    def _download_image_from_s3(self, s3_url: str, output_path: str):
        """S3 URL에서 이미지를 다운로드하여 로컬에 저장합니다."""
        try:
            import requests
            
            print(f"📥 S3에서 이미지 다운로드 중: {s3_url}")
            response = requests.get(s3_url, timeout=60)
            response.raise_for_status()
            
            # 이미지 데이터를 파일로 저장
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ 이미지 다운로드 완료: {output_path}")
            
        except Exception as e:
            raise FluxKontextTestError(f"S3 이미지 다운로드 실패: {s3_url} - {str(e)}")

    def test_connection(self) -> dict:
        """서버 연결을 테스트합니다."""
        try:
            # Health check 요청 (동기 처리)
            payload = {"input": {"type": "health_check"}}
            r = self.session.post(self.url_runsync, json=payload, timeout=30)
            try:
                j = r.json()
            except Exception:
                j = {"text": r.text}
            return {"status_code": r.status_code, "response": j}
        except Exception as e:
            return {"error": str(e)}
    
    def list_models(self) -> dict:
        """사용 가능한 모델 목록을 조회합니다."""
        try:
            payload = {"input": {"type": "list_models"}}
            r = self.session.post(self.url_runsync, json=payload, timeout=30)
            try:
                j = r.json()
            except Exception:
                j = {"text": r.text}
            return {"status_code": r.status_code, "response": j}
        except Exception as e:
            return {"error": str(e)}
    
    def test_health_check(self) -> bool:
        """RunPod 엔드포인트 헬스 체크"""
        try:
            # 연결 테스트
            connection_test = self.test_connection()
            if connection_test.get("status_code") == 200:
                response = connection_test.get("response", {})
                
                # RunPod 래핑 해제
                output = self._unwrap_output(response)
                
                if output.get("status") == "healthy":
                    print("✅ RunPod 엔드포인트 연결 성공 (Health Check 통과)")
                    print(f"   메시지: {output.get('message', 'N/A')}")
                    return True
                else:
                    print(f"⚠️ 연결은 성공했지만 Health Check 실패: {response}")
                    return False
            else:
                print(f"❌ RunPod 엔드포인트 연결 실패: {connection_test}")
                return False
        except Exception as e:
            print(f"❌ RunPod 엔드포인트 연결 실패: {str(e)}")
            return False
    
    def test_models_list(self) -> bool:
        """모델 목록 조회 테스트"""
        try:
            models_test = self.list_models()
            if models_test.get("status_code") == 200:
                response = models_test.get("response", {})
                
                # RunPod 래핑 해제
                output = self._unwrap_output(response)
                
                if output.get("status") == "success":
                    models = output.get("models", {})
                    print("✅ 모델 목록 조회 성공:")
                    for model_type, model_path in models.items():
                        print(f"   {model_type}: {model_path}")
                    return True
                else:
                    print(f"⚠️ 모델 목록 조회 실패: {response}")
                    return False
            else:
                print(f"❌ 모델 목록 조회 실패: {models_test}")
                return False
        except Exception as e:
            print(f"❌ 모델 목록 조회 실패: {str(e)}")
            return False
    
    def generate_image(self, 
                      image_path: str, 
                      prompt: str, 
                      ratio: str = "16:9",
                      output_format: str = "s3_url",
                      use_runsync: bool = True,
                      poll_interval_sec: int = 5,
                      max_wait_sec: int = 300,
                      use_s3_upload: bool = True,
                      seed: int = None) -> dict:
        """
        Flux-Kontext를 사용하여 이미지를 생성합니다.
        
        Args:
            image_path: 입력 이미지 파일 경로
            prompt: 생성할 이미지에 대한 프롬프트
            ratio: 이미지 비율 (예: "16:9", "1:1", "4:3")
            output_format: 출력 형식 ("base64" 또는 "s3_url")
            use_runsync: True면 runsync 동기 처리, False면 run+status 폴링
            poll_interval_sec: 비동기 폴링 간격
            max_wait_sec: 비동기 최대 대기시간
            use_s3_upload: True면 입력 이미지를 S3에 업로드하여 사용
            
        Returns:
            생성 결과 딕셔너리
        """
        try:
            # 입력 이미지 처리
            if use_s3_upload:
                print("📤 S3에 입력 이미지 업로드 중...")
                # S3 업로드 기능 추가 필요
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
                     "output_format": output_format,
                     "seed": seed
                 }
             }
            
            print(f"🚀 Flux-Kontext API 호출 중...")
            print(f"   프롬프트: {prompt}")
            print(f"   비율: {ratio}")
            print(f"   출력 형식: {output_format}")
            print(f"   실행 방식: {'동기(runsync)' if use_runsync else '비동기(run+status)'}")
            
            if use_runsync:
                # 동기 실행
                start_time = time.time()
                response = self.session.post(
                    self.url_runsync, 
                    json=payload,
                    timeout=self.session.timeout
                )
                end_time = time.time()
                
                print(f"runsync 상태: {response.status_code}")
                
                if response.status_code != 200:
                    raise FluxKontextTestError(f"API 호출 실패: {response.status_code} - {response.text}")
                
                try:
                    result = response.json()
                except Exception:
                    raise FluxKontextTestError(f"응답 JSON 파싱 실패: {response.text}")
                
                # RunPod 래핑 해제
                unwrapped_result = self._unwrap_output(result)
                
                # 결과 처리
                if "error" in unwrapped_result:
                    raise FluxKontextTestError(f"API 에러: {unwrapped_result['error']}")
                
                print(f"✅ 이미지 생성 완료! (소요시간: {end_time - start_time:.2f}초)")
                
                return unwrapped_result
                
            else:
                # 비동기 실행
                print("run 비동기 제출...")
                start_time = time.time()
                
                submit = self.session.post(self.url_run, json=payload, timeout=self.session.timeout)
                print(f"run 상태: {submit.status_code}")
                submit.raise_for_status()
                
                try:
                    submit_json = submit.json()
                except Exception:
                    raise FluxKontextTestError(f"제출 응답 JSON 파싱 실패: {submit.text}")
                
                job_id = submit_json.get("id")
                if not job_id:
                    raise FluxKontextTestError(f"작업 ID를 받지 못했습니다. 응답: {submit_json}")
                
                print(f"작업 ID: {job_id}")
                
                # /status 폴링
                waited = 0
                while waited < max_wait_sec:
                    status_resp = self.session.get(self._status_url(job_id), timeout=self.session.timeout)
                    if status_resp.status_code != 200:
                        print(f"status HTTP {status_resp.status_code}")
                    
                    try:
                        status_json = status_resp.json()
                    except Exception:
                        raise FluxKontextTestError(f"상태 응답 JSON 파싱 실패: {status_resp.text}")
                    
                    status = status_json.get("status") or status_json.get("state")
                    print(f"상태: {status}")
                    
                    if status == "COMPLETED":
                        end_time = time.time()
                        unwrapped_result = self._unwrap_output(status_json)
                        
                        # 결과 처리
                        if "error" in unwrapped_result:
                            raise FluxKontextTestError(f"API 에러: {unwrapped_result['error']}")
                        
                        print(f"✅ 이미지 생성 완료! (소요시간: {end_time - start_time:.2f}초)")
                        return unwrapped_result
                        
                    if status == "FAILED":
                        raise FluxKontextTestError(f"작업 실패: {status_json}")
                    
                    time.sleep(poll_interval_sec)
                    waited += poll_interval_sec
                
                raise FluxKontextTestError(f"작업 완료 대기 시간 초과 ({max_wait_sec}초)")
            
        except Exception as e:
            if isinstance(e, FluxKontextTestError):
                raise
            raise FluxKontextTestError(f"이미지 생성 실패: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Flux-Kontext RunPod Serverless API 테스트")
    parser.add_argument("image_path", help="입력 이미지 파일 경로")
    parser.add_argument("prompt", help="생성할 이미지에 대한 프롬프트")
    parser.add_argument("--ratio", default="16:9", help="이미지 비율 (기본값: 16:9)")
    parser.add_argument("--output-format", choices=["base64", "s3_url"], default="s3_url", 
                       help="출력 형식 (기본값: s3_url)")
    parser.add_argument("--use-runsync", action="store_true", default=True,
                       help="동기 실행 사용 (기본값: True)")
    parser.add_argument("--use-async", action="store_true",
                       help="비동기 실행 사용 (--use-runsync와 상호 배타적)")
    parser.add_argument("--poll-interval", type=int, default=5,
                       help="비동기 폴링 간격 (초, 기본값: 5)")
    parser.add_argument("--max-wait", type=int, default=300,
                       help="비동기 최대 대기시간 (초, 기본값: 300)")
    parser.add_argument("--output-dir", default="test_outputs", 
                       help="결과 저장 폴더 (기본값: test_outputs)")
    parser.add_argument("--save-metadata", action="store_true", 
                       help="메타데이터 JSON 파일도 저장")
    parser.add_argument("--test-only", action="store_true",
                       help="연결 테스트만 수행하고 종료")
    parser.add_argument("--test-models", action="store_true",
                       help="모델 목록 조회 테스트만 수행하고 종료")
    parser.add_argument("--use-s3-upload", action="store_true",
                       help="입력 이미지를 S3에 업로드하여 사용")
    parser.add_argument("--use-base64", action="store_true",
                       help="base64 방식으로 이미지를 주고받기 (기본값: S3 URL 방식)")
    parser.add_argument("--seed", type=int, default=None,
                       help="랜덤 시드 값 (지정하지 않으면 랜덤)")
    
    args = parser.parse_args()
    
    # 실행 방식 확인
    if args.use_async:
        args.use_runsync = False
    
    # base64 옵션 처리
    if args.use_base64:
        args.output_format = "base64"
        args.use_s3_upload = False
    
    # 환경변수 확인
    runpod_api_key = os.getenv('RUNPOD_API_KEY')
    runpod_endpoint = os.getenv('RUNPOD_FLUX_KONTEXT_ENDPOINT')
    
    if not runpod_api_key:
        print("❌ RUNPOD_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 RUNPOD_API_KEY=your_api_key를 추가해주세요.")
        sys.exit(1)
    
    if not runpod_endpoint:
        print("❌ RUNPOD_FLUX_KONTEXT_ENDPOINT 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 RUNPOD_FLUX_KONTEXT_ENDPOINT=https://your-pod-id-your-endpoint.runpod.net를 추가해주세요.")
        sys.exit(1)
    
    # 입력 이미지 파일 확인 (테스트 모드가 아닌 경우)
    if not args.test_only and not os.path.exists(args.image_path):
        print(f"❌ 입력 이미지 파일이 없습니다: {args.image_path}")
        sys.exit(1)
    
    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 클라이언트 초기화
    client = FluxKontextClient(runpod_endpoint, runpod_api_key)
    
    try:
        # 헬스 체크
        print("🔍 서버 연결 테스트 중...")
        if not client.test_health_check():
            print("❌ RunPod 엔드포인트 연결에 실패했습니다.")
            sys.exit(1)
        
        # 테스트 모드인 경우 여기서 종료
        if args.test_only:
            print("✅ 연결 테스트 완료!")
            sys.exit(0)
        
        if args.test_models:
            print("🔍 모델 목록 조회 테스트 중...")
            if client.test_models_list():
                print("✅ 모델 목록 조회 테스트 완료!")
                sys.exit(0)
            else:
                print("❌ 모델 목록 조회 테스트 실패!")
                sys.exit(1)
        
        # 이미지 생성
        result = client.generate_image(
            image_path=args.image_path,
            prompt=args.prompt,
            ratio=args.ratio,
            output_format=args.output_format,
            use_runsync=args.use_runsync,
            poll_interval_sec=args.poll_interval,
            max_wait_sec=args.max_wait,
            use_s3_upload=args.use_s3_upload,
            seed=args.seed
        )
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.output_format == "base64" and "image" in result:
            # base64 이미지 저장
            output_path = os.path.join(args.output_dir, f"flux_kontext_output_{timestamp}.png")
            client._save_base64_image(result["image"], output_path)
        elif args.output_format == "s3_url" and "image_url" in result:
            # S3 URL 출력 및 로컬 다운로드
            print(f"📤 생성된 이미지 S3 URL: {result['image_url']}")
            
            # S3 URL에서 로컬로 다운로드
            output_path = os.path.join(args.output_dir, f"flux_kontext_output_{timestamp}.png")
            client._download_image_from_s3(result["image_url"], output_path)
        
        # 메타데이터 저장
        if args.save_metadata:
            metadata = {
                "timestamp": timestamp,
                "input_image": args.image_path,
                "prompt": args.prompt,
                "ratio": args.ratio,
                "output_format": args.output_format,
                "execution_mode": "synchronous" if args.use_runsync else "asynchronous",
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

# 사용 예제:
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "Maintain the face identity and the man in A beautiful landscape"
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --use-async --poll-interval 10
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --test-only
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --test-models
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --use-base64
# python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --seed 12345  # 특정 시드 사용
