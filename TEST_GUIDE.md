# Flux-Kontext RunPod 테스트 가이드

## 개요
이 문서는 RunPod에 배포된 Flux-Kontext 모델을 테스트하는 방법을 설명합니다.

## 사전 준비

### 1. 필수 라이브러리 설치
```bash
pip install requests python-dotenv boto3 pillow
```

### 2. 환경변수 설정
`env_example.txt` 파일을 `.env`로 복사하고 실제 값으로 수정하세요:

```bash
cp env_example.txt .env
```

`.env` 파일에 다음 내용을 설정:
```ini
# RunPod API 설정
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_FLUX_KONTEXT_ENDPOINT=https://your-pod-id-your-endpoint.runpod.net

# AWS S3 설정 (선택사항)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name
```

### 3. 테스트 이미지 준비
`asset/` 폴더에 테스트용 이미지를 넣어주세요:
- `asset/test_image.jpg` (간단 테스트용)
- 또는 원하는 이미지 파일

## 테스트 방법

### 1. 간단 테스트 (Quick Test)
가장 빠른 방법으로 기본 기능을 테스트합니다:

```bash
python quick_test.py
```

**특징:**
- 기본 프롬프트 사용
- 16:9 비율로 고정
- base64 출력 형식
- 결과를 `test_output.png`로 저장

### 2. 상세 테스트 (Full Test)
모든 옵션을 사용하여 상세한 테스트를 수행합니다:

```bash
# 기본 사용법
python test_runpod_flux_kontext.py input_image.jpg "A beautiful landscape"

# 다양한 옵션 사용
python test_runpod_flux_kontext.py input_image.jpg "A futuristic city" \
    --ratio "1:1" \
    --output-format s3_url \
    --use-s3-upload \
    --output-dir my_results \
    --save-metadata
```

**옵션 설명:**
- `--ratio`: 이미지 비율 (16:9, 1:1, 4:3 등)
- `--output-format`: 출력 형식 (base64 또는 s3_url)
- `--use-s3-upload`: 입력 이미지를 S3에 업로드하여 사용
- `--output-dir`: 결과 저장 폴더
- `--save-metadata`: 메타데이터 JSON 파일도 저장

## 테스트 시나리오

### 시나리오 1: 기본 기능 테스트
```bash
python test_runpod_flux_kontext.py asset/test_image.jpg "A serene mountain landscape"
```

### 시나리오 2: S3 업로드 테스트
```bash
python test_runpod_flux_kontext.py asset/test_image.jpg "A cyberpunk city" \
    --use-s3-upload \
    --output-format s3_url
```

### 시나리오 3: 다양한 비율 테스트
```bash
# 정사각형
python test_runpod_flux_kontext.py asset/test_image.jpg "A portrait of a cat" --ratio "1:1"

# 세로형
python test_runpod_flux_kontext.py asset/test_image.jpg "A tall building" --ratio "9:16"

# 가로형
python test_runpod_flux_kontext.py asset/test_image.jpg "A wide landscape" --ratio "21:9"
```

### 시나리오 4: 배치 테스트
여러 이미지와 프롬프트로 테스트:

```bash
# 테스트 1
python test_runpod_flux_kontext.py image1.jpg "A peaceful garden" --output-dir batch_test

# 테스트 2
python test_runpod_flux_kontext.py image2.jpg "A stormy sea" --output-dir batch_test

# 테스트 3
python test_runpod_flux_kontext.py image3.jpg "A cozy cafe interior" --output-dir batch_test
```

## 결과 확인

### 1. base64 출력 형식
- 결과 이미지가 로컬 파일로 저장됩니다
- `test_outputs/` 폴더에 타임스탬프와 함께 저장

### 2. S3 URL 출력 형식
- 생성된 이미지의 S3 URL이 출력됩니다
- 브라우저에서 직접 확인 가능

### 3. 메타데이터
`--save-metadata` 옵션 사용 시:
- 입력 파라미터
- API 응답
- 타임스탬프
- 기타 메타데이터가 JSON 파일로 저장

## 문제 해결

### 1. 연결 실패
```
❌ RunPod 엔드포인트 연결 실패
```
**해결 방법:**
- 엔드포인트 URL 확인
- RunPod Pod가 실행 중인지 확인
- API 키가 올바른지 확인

### 2. 타임아웃
```
❌ API 호출 타임아웃 (5분)
```
**해결 방법:**
- RunPod Pod의 GPU 사양 확인 (24GB 이상 권장)
- 네트워크 연결 상태 확인
- 이미지 크기 줄이기

### 3. 메모리 부족
```
❌ GPU 메모리 부족
```
**해결 방법:**
- 더 큰 GPU 사양의 Pod 사용
- 이미지 해상도 줄이기
- 배치 크기 줄이기

### 4. S3 관련 오류
```
❌ S3 업로드 실패
```
**해결 방법:**
- AWS 자격 증명 확인
- S3 버킷 존재 여부 확인
- S3 버킷 권한 확인

## 성능 최적화 팁

1. **GPU 메모리**: 24GB 이상 권장
2. **이미지 크기**: 너무 큰 이미지는 처리 시간이 오래 걸림
3. **네트워크**: 안정적인 인터넷 연결 필요
4. **캐싱**: 첫 실행 후 모델이 캐시되어 후속 요청이 빨라짐

## 로그 분석

테스트 실행 시 다음과 같은 로그를 확인할 수 있습니다:

```
🚀 Flux-Kontext API 호출 중...
   프롬프트: A beautiful landscape with mountains
   비율: 16:9
   출력 형식: base64
✅ 이미지 생성 완료! (소요시간: 45.23초)
✅ 테스트 완료!
```

이 로그를 통해 API 호출 상태와 성능을 모니터링할 수 있습니다.
