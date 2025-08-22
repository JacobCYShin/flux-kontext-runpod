# Flux-Kontext RunPod 테스트 가이드

## 개요
이 문서는 RunPod에 배포된 Flux-Kontext 모델을 테스트하는 방법을 설명합니다.

## ✨ 주요 기능
- **동기/비동기 처리**: `/runsync` (동기) 또는 `/run` + `/status` (비동기) 지원
- **S3 URL 기반 처리**: 입력/출력 이미지를 S3 URL로 주고받기
- **Health Check**: 서버 상태 및 연결 확인
- **모델 목록 조회**: 사용 가능한 모델 정보 확인
- **진행 상황 모니터링**: 실시간 처리 진행률 확인
- **다양한 출력 형식**: base64 또는 S3 URL 선택 가능

## 사전 준비

### 1. 필수 라이브러리 설치
```bash
pip install requests python-dotenv boto3 pillow
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 내용을 설정하세요:

```ini
# RunPod API 설정
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_FLUX_KONTEXT_ENDPOINT=https://api.runpod.ai/v2/your-endpoint-id

# AWS S3 설정 (S3 기능 사용 시)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=likebutter-bucket
```

### 3. 테스트 이미지 준비
`asset/` 폴더에 테스트용 이미지를 넣어주세요:
- `asset/bts-jin.jpg` (기본 테스트용)
- 또는 원하는 이미지 파일

## 테스트 방법

### 1. 연결 테스트 (Health Check)
서버 연결 상태를 먼저 확인합니다:

```bash
# Health Check만 수행
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "test" --test-only

# 모델 목록 조회
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "test" --test-models
```

### 2. 기본 테스트 (Base64 방식)
로컬에서 base64로 이미지를 주고받는 기본 방식:

```bash
# 기본 사용법
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape"

# 메타데이터 저장 포함
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" --save-metadata
```

### 3. S3 URL 기반 테스트
S3를 통한 URL 기반 이미지 처리:

```bash
# 입력 이미지를 S3에 업로드하여 사용
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A cyberpunk city" --use-s3-upload

# 출력을 S3 URL로 받기
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A futuristic city" --output-format s3_url

# 완전한 S3 URL 기반 처리
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" \
    --use-s3-upload \
    --output-format s3_url
```

### 4. 비동기 처리 테스트
긴 처리 시간이 필요한 경우 비동기 처리:

```bash
# 비동기 처리 (기본값: 5초 폴링, 5분 대기)
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A detailed landscape" --use-async

# 비동기 처리 (커스텀 설정)
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A complex scene" \
    --use-async \
    --poll-interval 10 \
    --max-wait 600
```

## 📋 명령행 옵션

### 기본 설정
- `image_path`: 입력 이미지 파일 경로 (필수)
- `prompt`: 생성할 이미지에 대한 프롬프트 (필수)
- `--ratio`: 이미지 비율 (기본값: "16:9")
  - 지원 형식: "16:9", "1:1", "4:3", "9:16", "21:9"

### 처리 방식 설정
- `--use-runsync`: 동기 처리 사용 (기본값: True)
- `--use-async`: 비동기 처리 사용 (--use-runsync와 상호 배타적)
- `--poll-interval`: 비동기 폴링 간격 (초, 기본값: 5)
- `--max-wait`: 비동기 최대 대기시간 (초, 기본값: 300)

### 출력 형식 설정
- `--output-format`: 출력 형식 선택
  - `base64`: base64 인코딩된 이미지 (기본값)
  - `s3_url`: S3 URL (서버에서 S3에 저장 후 URL 반환)
- `--use-s3-upload`: 입력 이미지를 S3에 업로드하여 사용

### 파일 저장 설정
- `--output-dir`: 결과 저장 폴더 (기본값: "test_outputs")
- `--save-metadata`: 메타데이터 JSON 파일도 저장

### 테스트 모드
- `--test-only`: 연결 테스트만 수행하고 종료
- `--test-models`: 모델 목록 조회 테스트만 수행하고 종료

## 🎯 테스트 시나리오

### 시나리오 1: 기본 기능 테스트
```bash
# Health Check
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "test" --test-only

# 기본 이미지 생성
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A serene mountain landscape"
```

### 시나리오 2: S3 URL 기반 처리
```bash
# 입력 이미지 S3 업로드
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A cyberpunk city" --use-s3-upload

# 출력 S3 URL 받기
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A futuristic city" --output-format s3_url

# 완전한 S3 기반 처리
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape" \
    --use-s3-upload \
    --output-format s3_url
```

### 시나리오 3: 다양한 비율 테스트
```bash
# 정사각형
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A portrait of a cat" --ratio "1:1"

# 세로형
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A tall building" --ratio "9:16"

# 가로형
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A wide landscape" --ratio "21:9"
```

### 시나리오 4: 비동기 처리 테스트
```bash
# 기본 비동기 처리
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A detailed landscape" --use-async

# 긴 대기 시간 설정
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A complex scene" \
    --use-async \
    --poll-interval 10 \
    --max-wait 1800
```

### 시나리오 5: 배치 테스트
```bash
# 테스트 1
python3 test_runpod_flux_kontext.py image1.jpg "A peaceful garden" --output-dir batch_test

# 테스트 2
python3 test_runpod_flux_kontext.py image2.jpg "A stormy sea" --output-dir batch_test

# 테스트 3
python3 test_runpod_flux_kontext.py image3.jpg "A cozy cafe interior" --output-dir batch_test
```

## 📊 결과 확인

### 1. base64 출력 형식
- 결과 이미지가 로컬 파일로 저장됩니다
- `test_outputs/` 폴더에 타임스탬프와 함께 저장
- 예: `flux_kontext_output_20250822_142528.png`

### 2. S3 URL 출력 형식
- 생성된 이미지의 S3 URL이 출력됩니다
- 브라우저에서 직접 확인 가능
- 예: `https://likebutter-bucket.s3.us-east-1.amazonaws.com/generated-images/...`

### 3. 메타데이터
`--save-metadata` 옵션 사용 시:
- 입력 파라미터
- API 응답
- 타임스탬프
- 기타 메타데이터가 JSON 파일로 저장

## 🔧 S3 버킷 구조

### 입력 이미지
- **경로**: `source-Images/{timestamp}_{filename}`
- **예시**: `source-Images/1755840110_bts-jin.jpg`

### 출력 이미지
- **경로**: `generated-images/{timestamp}_{filename}`
- **예시**: `generated-images/1755840110_flux_kontext_output.png`

## ⚠️ 문제 해결

### 1. 연결 실패
```
❌ RunPod 엔드포인트 연결 실패
```
**해결 방법:**
- 엔드포인트 URL 확인
- RunPod Pod가 실행 중인지 확인
- API 키가 올바른지 확인
- Health Check 실행: `--test-only`

### 2. Health Check 실패
```
⚠️ 연결은 성공했지만 Health Check 실패
```
**해결 방법:**
- RunPod Pod의 상태 확인
- 모델 로딩 완료 대기
- Pod 재시작 고려

### 3. 타임아웃
```
❌ API 호출 타임아웃 (5분)
```
**해결 방법:**
- 비동기 처리 사용: `--use-async`
- 더 큰 GPU 사양의 Pod 사용 (24GB 이상 권장)
- 네트워크 연결 상태 확인
- 이미지 크기 줄이기

### 4. 메모리 부족
```
❌ GPU 메모리 부족
```
**해결 방법:**
- 더 큰 GPU 사양의 Pod 사용
- 이미지 해상도 줄이기
- 배치 크기 줄이기

### 5. S3 관련 오류
```
❌ S3 업로드 실패
```
**해결 방법:**
- AWS 자격 증명 확인
- S3 버킷 존재 여부 확인
- S3 버킷 권한 확인
- `--use-s3-upload` 옵션 제거하고 base64 방식 사용

## 🚀 성능 최적화 팁

### 1. 하드웨어 권장사항
- **GPU 메모리**: 24GB 이상 권장
- **네트워크**: 안정적인 인터넷 연결 필요

### 2. 처리 방식 선택
- **빠른 응답**: 동기 처리 (`--use-runsync`, 기본값)
- **긴 처리 시간**: 비동기 처리 (`--use-async`)

### 3. 이미지 최적화
- **이미지 크기**: 너무 큰 이미지는 처리 시간이 오래 걸림
- **캐싱**: 첫 실행 후 모델이 캐시되어 후속 요청이 빨라짐

### 4. S3 사용 권장사항
- **대용량 이미지**: S3 URL 방식 권장
- **빠른 처리**: base64 방식 권장
- **배치 처리**: S3 URL 방식으로 중간 결과 저장

## 📝 로그 분석

### 성공적인 실행 로그
```
엔드포인트 BASE URL: https://api.runpod.ai/v2/90pjyy63qh64hn
🔍 서버 연결 테스트 중...
✅ RunPod 엔드포인트 연결 성공 (Health Check 통과)
📤 입력 이미지를 base64로 인코딩 중...
🚀 Flux-Kontext API 호출 중...
   프롬프트: A beautiful landscape with mountains
   비율: 16:9
   출력 형식: base64
   실행 방식: 동기(runsync)
✅ 이미지 생성 완료! (소요시간: 88.54초)
✅ 이미지 저장됨: test_outputs/flux_kontext_output_20250822_142528.png
🎉 테스트 완료!
```

### S3 URL 기반 처리 로그
```
📤 S3에 입력 이미지 업로드 중...
📤 S3 URL: https://likebutter-bucket.s3.us-east-1.amazonaws.com/source-Images/1755840110_bts-jin.jpg
🚀 Flux-Kontext API 호출 중...
   프롬프트: A cyberpunk city
   비율: 16:9
   출력 형식: s3_url
📤 생성된 이미지 S3 URL: https://likebutter-bucket.s3.us-east-1.amazonaws.com/generated-images/...
```

## 🔄 사용 예제

### 기본 사용
```bash
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A beautiful landscape"
```

### S3 기반 처리
```bash
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A cyberpunk city" \
    --use-s3-upload \
    --output-format s3_url
```

### 비동기 처리
```bash
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A detailed scene" \
    --use-async \
    --poll-interval 10 \
    --max-wait 1800
```

### 다양한 비율
```bash
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A portrait" --ratio "1:1"
python3 test_runpod_flux_kontext.py asset/bts-jin.jpg "A landscape" --ratio "21:9"
```

이 가이드를 통해 Flux-Kontext RunPod 모델의 모든 기능을 효과적으로 테스트할 수 있습니다! 🎉
