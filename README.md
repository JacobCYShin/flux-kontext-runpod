# Flux Kontext RunPod Serverless

FLUX.1-Kontext 모델을 RunPod Serverless에서 실행하기 위한 컨테이너입니다.

## 🚀 주요 기능

- **FLUX.1-Kontext 모델**: 고품질 이미지 생성 및 편집
- **다양한 입력 형식 지원**: 
  - Base64 인코딩된 이미지
  - HTTP/HTTPS URL
  - **S3 URL** (새로 추가!)
- **다양한 출력 형식 지원**:
  - Base64 인코딩 (기본값)
  - **S3 URL** (새로 추가!)
- **실시간 진행률 업데이트**: 생성 과정을 실시간으로 확인
- **GPU 가속**: CUDA 지원으로 빠른 처리

## 📋 요구사항

- NVIDIA GPU (CUDA 지원)
- RunPod Serverless 환경
- AWS S3 버킷 (S3 기능 사용 시)

## 🔧 설정

### 1. 환경변수 설정

`.env` 파일을 생성하고 다음 정보를 설정하세요:

```bash
# S3 설정 (S3 기능 사용 시)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name-here

# Hugging Face 설정
HF_TOKEN=your_huggingface_token_here
```

### 2. S3 버킷 설정

S3 기능을 사용하려면:
1. AWS S3 버킷 생성
2. 적절한 권한 설정
3. 환경변수에 버킷 정보 입력

## 🎯 사용법

### API 요청 예시

#### Base64 방식 (기존)
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
  "prompt": "make it a watercolor painting",
  "ratio": "1:1"
}
```

#### S3 URL 방식 (새로 추가!)
```json
{
  "image": "https://your-bucket.s3.us-east-1.amazonaws.com/input-image.jpg",
  "prompt": "make it a watercolor painting",
  "ratio": "1:1",
  "output_format": "s3_url"
}
```

### 응답 형식

#### Base64 응답 (기본값)
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
  "format": "base64"
}
```

#### S3 URL 응답
```json
{
  "image_url": "https://your-bucket.s3.us-east-1.amazonaws.com/flux-kontext/output-image.jpg",
  "format": "s3_url"
}
```

## 🧪 테스트

### 로컬 테스트
```bash
# 기존 base64 방식 테스트
python local_test.py input.jpg "make it a watercolor painting" "1:1"

# 대화형 테스트
python interactive_test.py

# S3 통합 기능 테스트
python test_s3_integration.py
```

### S3 기능 테스트
```bash
# 환경변수 설정 후
python test_s3_integration.py
```

## 📁 파일 구조

```
flux-kontext-runpod/
├── main.py                    # 메인 핸들러 (S3 지원 추가)
├── utils.py                   # 유틸리티 함수 (S3 함수 추가)
├── Dockerfile                 # 컨테이너 설정 (boto3 추가)
├── .env                       # 환경변수 설정
├── interactive_test.py        # 대화형 테스트 (기존)
├── local_test.py             # 로컬 테스트 (기존)
├── test_s3_integration.py    # S3 통합 테스트 (새로 추가)
├── main.py.backup            # 백업 파일
├── utils.py.backup           # 백업 파일
└── Dockerfile.backup         # 백업 파일
```

## 🔄 호환성

- ✅ **기존 base64 방식**: 완전 호환
- ✅ **기존 테스트 스크립트**: 정상 동작
- ✅ **S3 URL 방식**: 새로 추가
- ✅ **진행률 업데이트**: 기존과 동일

## 🚀 배포

### RunPod Serverless 배포

1. Docker 이미지 빌드
2. RunPod에 배포
3. 환경변수 설정
4. API 엔드포인트 테스트

### 환경변수 설정 (RunPod)

RunPod 대시보드에서 다음 환경변수를 설정하세요:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `HF_TOKEN`

## 📝 변경사항

### v2.0 (S3 지원 추가)
- ✅ S3 URL 입력 지원
- ✅ S3 URL 출력 지원
- ✅ 기존 base64 방식 완전 호환
- ✅ 기존 테스트 스크립트 정상 동작
- ✅ 새로운 S3 통합 테스트 추가

### v1.0 (기존)
- Base64 인코딩 방식
- HTTP URL 지원
- 실시간 진행률 업데이트

## 🤝 기여

버그 리포트나 기능 요청은 이슈로 등록해주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.