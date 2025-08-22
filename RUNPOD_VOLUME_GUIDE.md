# RunPod Volume 체크포인트 배포 가이드

## 개요
이 가이드는 `/runpod-volume`을 사용하여 체크포인트를 사전에 다운로드하고 RunPod에 배포하는 방법을 설명합니다.

## 사전 준비

### 1. 체크포인트 다운로드
```bash
# HF_TOKEN 설정
export HF_TOKEN="your_huggingface_token_here"

# 체크포인트 다운로드
python download_checkpoints.py
```

### 2. 체크포인트 구조 확인
```
checkpoints/
├── nunchaku/
│   └── svdq-int4_r32-flux.1-kontext-dev.safetensors (~7GB)
└── flux-kontext/
    ├── scheduler/
    ├── text_encoder/
    ├── tokenizer/
    ├── unet/
    └── vae/
    └── ... (기타 파일들)
```

## 배포 방법

### 방법 1: 이미지에 체크포인트 포함 (권장)

#### A. Dockerfile 수정
```dockerfile
# 체크포인트를 이미지에 포함
COPY checkpoints/ /runpod-volume/checkpoints/
```

#### B. 이미지 빌드
```bash
# 체크포인트가 포함된 이미지 빌드
docker build -t flux-kontext-runpod:latest .
```

#### C. RunPod 배포
- RunPod에서 이미지 URL 입력
- 환경변수 설정 (HF_TOKEN은 선택사항)
- Pod 생성

### 방법 2: 볼륨 마운트 방식

#### A. RunPod 볼륨 생성
1. RunPod 대시보드에서 "Volumes" 클릭
2. "Create Volume" 클릭
3. 이름: `flux-kontext-checkpoints`
4. 크기: 10GB (체크포인트 크기에 맞게 조정)

#### B. 체크포인트 업로드
```bash
# 로컬에서 체크포인트를 압축
tar -czf checkpoints.tar.gz checkpoints/

# RunPod 볼륨에 업로드 (RunPod CLI 사용)
runpod volume upload flux-kontext-checkpoints checkpoints.tar.gz
```

#### C. Pod 생성 시 볼륨 마운트
- "Deploy from Container" 선택
- "Volumes" 섹션에서 `flux-kontext-checkpoints` 선택
- Mount Path: `/runpod-volume`

## 스토리지 요구사항

### 예상 크기
- **Nunchaku 모델**: ~7GB
- **FLUX.1-Kontext-dev 모델**: ~3-5GB
- **총 예상 크기**: ~10-12GB

### 권장 설정
- **볼륨 크기**: 15GB (여유 공간 포함)
- **이미지 크기**: 체크포인트 포함 시 ~15GB

## 장점

### 1. 빌드 타임 환경변수 문제 해결
- HF_TOKEN 없이도 이미지 빌드 가능
- RunPod Serverless 제약 우회

### 2. 빠른 시작
- 런타임에 모델 다운로드 불필요
- 첫 요청 응답 시간 단축

### 3. 안정성
- 네트워크 의존성 제거
- 일관된 성능 보장

### 4. 재사용성
- 동일한 체크포인트로 여러 Pod 생성 가능
- 버전 관리 용이

## 주의사항

### 1. 이미지 크기
- 체크포인트 포함 시 이미지가 커짐
- 배포 시간 증가

### 2. 업데이트
- 모델 업데이트 시 재빌드 필요
- 버전 관리 전략 필요

### 3. 비용
- RunPod 볼륨 사용 시 추가 비용
- 이미지 크기에 따른 저장 비용

## 문제 해결

### 1. 체크포인트 로드 실패
```
Warning: 로컬 체크포인트가 없습니다: /runpod-volume/checkpoints/nunchaku
```
**해결 방법:**
- 체크포인트가 올바른 경로에 있는지 확인
- 볼륨 마운트 설정 확인
- 파일 권한 확인

### 2. 메모리 부족
```
CUDA out of memory
```
**해결 방법:**
- GPU 메모리 증가 (24GB 이상 권장)
- 배치 크기 줄이기
- 이미지 해상도 줄이기

### 3. 시작 시간 오래 걸림
**해결 방법:**
- 체크포인트 사전 다운로드 확인
- 네트워크 연결 상태 확인
- GPU 사양 확인

## 성능 최적화

### 1. 이미지 최적화
- 멀티스테이지 빌드 사용
- 불필요한 파일 제거
- 압축 활용

### 2. 캐싱 전략
- RunPod 볼륨 캐싱 활용
- 모델 캐싱 최적화
- 메모리 캐싱 설정

### 3. 모니터링
- 시작 시간 측정
- 메모리 사용량 모니터링
- 성능 지표 추적
