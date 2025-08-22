# RunPod 배포 가이드

## 개요
이 문서는 Flux-Kontext 모델을 RunPod에 배포하는 방법을 설명합니다.

## 환경변수 설정

RunPod Pod 설정에서 다음 환경변수를 설정해야 합니다:

### 필수 환경변수
- `HF_TOKEN`: Hugging Face 토큰 (gated 모델 접근용)
- `AWS_ACCESS_KEY_ID`: AWS S3 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS S3 시크릿 키
- `S3_BUCKET_NAME`: S3 버킷 이름

### 선택적 환경변수
- `AWS_REGION`: AWS 리전 (기본값: us-east-1)

## 배포 단계

### 1. Docker 이미지 빌드
```bash
# RunPod용 Dockerfile 사용
docker build -f Dockerfile.runpod -t flux-kontext-runpod .
```

### 2. RunPod에 이미지 푸시
```bash
# RunPod 레지스트리에 태그
docker tag flux-kontext-runpod:latest registry.runpod.io/[YOUR_USERNAME]/flux-kontext-runpod:latest

# 푸시
docker push registry.runpod.io/[YOUR_USERNAME]/flux-kontext-runpod:latest
```

### 3. RunPod Pod 생성
1. RunPod 대시보드에서 "Deploy" 클릭
2. "Deploy from Container" 선택
3. 이미지 URL 입력: `registry.runpod.io/[YOUR_USERNAME]/flux-kontext-runpod:latest`
4. 환경변수 설정 (위의 환경변수들)
5. GPU 설정 (최소 24GB VRAM 권장)
6. Pod 생성

## 사용법

### API 호출 예시
```python
import requests
import base64
from PIL import Image
import io

# 이미지를 base64로 인코딩
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# API 호출
url = "https://[YOUR_POD_ID]-[YOUR_ENDPOINT].runpod.net"
payload = {
    "input": {
        "image": image_to_base64("input_image.jpg"),
        "prompt": "A beautiful landscape with mountains",
        "ratio": "16:9",
        "output_format": "base64"  # 또는 "s3_url"
    }
}

response = requests.post(url, json=payload)
result = response.json()

if "image" in result:
    # base64 이미지 디코딩
    image_data = base64.b64decode(result["image"])
    image = Image.open(io.BytesIO(image_data))
    image.save("output_image.jpg")
elif "image_url" in result:
    print(f"이미지 URL: {result['image_url']}")
else:
    print(f"에러: {result.get('error', 'Unknown error')}")
```

## 문제 해결

### 1. HF_TOKEN 관련 문제
- HF_TOKEN이 설정되지 않은 경우 공개 모델만 사용됩니다
- gated 모델에 접근하려면 유효한 HF_TOKEN이 필요합니다

### 2. S3 관련 문제
- AWS 자격 증명이 올바르게 설정되었는지 확인
- S3 버킷이 존재하고 접근 권한이 있는지 확인

### 3. GPU 메모리 부족
- 24GB 이상의 VRAM을 가진 GPU 사용 권장
- 배치 크기나 이미지 해상도를 줄여보세요

## 로컬 테스트 vs RunPod 배포

| 항목 | 로컬 테스트 | RunPod 배포 |
|------|-------------|-------------|
| Dockerfile | `Dockerfile` | `Dockerfile.runpod` |
| 환경변수 | `.env` 파일 또는 직접 설정 | RunPod Pod 설정에서 설정 |
| 모델 다운로드 | 빌드 시점 | 런타임 |
| 보안 | 개발용 | 프로덕션용 |

## 성능 최적화

1. **GPU 메모리**: 24GB 이상 권장
2. **네트워크**: 고속 인터넷 연결로 모델 다운로드 속도 향상
3. **캐싱**: 첫 실행 후 모델이 캐시되어 후속 요청이 빨라집니다
