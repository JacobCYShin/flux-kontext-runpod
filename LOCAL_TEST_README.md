# Flux Kontext 로컬 테스트 가이드

이 가이드는 도커 빌드 후 로컬 PC에서 Flux Kontext를 테스트하는 방법을 설명합니다.

## 📋 사전 요구사항

- **GPU**: CUDA 지원 GPU (최소 8GB VRAM 권장)
- **Python**: 3.8 이상
- **PyTorch**: CUDA 지원 버전
- **필요한 라이브러리들**: diffusers, nunchaku, PIL 등

## 🚀 테스트 방법

### 1. CLI 방식 (local_test.py)

명령줄에서 직접 파라미터를 지정하여 테스트할 수 있습니다.

```bash
# 기본 사용법
python local_test.py <이미지파일> "<프롬프트>" <비율>

# 예시
python local_test.py my_image.jpg "make it a watercolor painting" "1:1"
python local_test.py photo.png "add snow" "16:9" --output result.png
```

**파라미터 설명:**
- `이미지파일`: 처리할 이미지 파일 경로
- `프롬프트`: 이미지 변환을 위한 텍스트 설명
- `비율`: 출력 이미지 비율 (예: "1:1", "16:9", "original")
- `--output`: 출력 파일 경로 (선택사항, 기본값: output.png)

### 2. 대화형 방식 (interactive_test.py)

대화형으로 입력을 받아 테스트할 수 있습니다.

```bash
python interactive_test.py
```

실행하면 다음 순서로 입력을 받습니다:
1. 이미지 파일 경로
2. 변환 프롬프트
3. 비율 선택 (1-5번 메뉴)
4. 출력 파일명

## 📐 지원하는 비율

- `1:1`: 정사각형
- `16:9`: 가로형 (와이드스크린)
- `9:16`: 세로형 (모바일)
- `4:3`: 전통적 비율
- `original`: 원본 이미지 비율 유지

## 🔧 문제 해결

### CUDA 오류
```
❌ CUDA가 사용 불가능합니다. GPU가 필요합니다.
```
- NVIDIA GPU가 설치되어 있는지 확인
- CUDA 드라이버가 설치되어 있는지 확인
- PyTorch CUDA 버전이 설치되어 있는지 확인

### 모델 로딩 오류
```
❌ 모델 로딩 실패: ...
```
- 인터넷 연결 확인
- 충분한 디스크 공간 확인 (모델 다운로드 필요)
- GPU 메모리 부족 시 다른 프로그램 종료

### 메모리 부족 오류
- GPU 메모리가 부족한 경우 더 작은 이미지 사용
- 다른 GPU 프로그램 종료
- 시스템 재부팅 후 재시도

## 📁 파일 구조

```
flux-kontext-runpod/
├── main.py              # RunPod 서버리스용 (수정하지 않음)
├── local_test.py        # CLI 테스트용 (새로 생성)
├── interactive_test.py  # 대화형 테스트용 (새로 생성)
├── utils.py             # 공통 유틸리티 함수들
└── gradio_app/          # 웹 인터페이스 (기존)
    ├── app.py
    ├── inference.py
    └── ...
```

## 💡 사용 팁

1. **첫 실행 시**: 모델 다운로드로 인해 시간이 오래 걸릴 수 있습니다
2. **프롬프트 작성**: 구체적이고 명확한 설명이 좋은 결과를 만듭니다
3. **이미지 크기**: 너무 큰 이미지는 처리 시간이 오래 걸립니다
4. **진행 상황**: 5단계마다 진행률이 출력됩니다

## 🎯 예시 프롬프트

- "make it a watercolor painting"
- "add snow and winter atmosphere"
- "convert to anime style"
- "make it look like a vintage photograph"
- "add magical sparkles and glow effects"

## ⚠️ 주의사항

- 기존 `main.py`는 수정하지 마세요 (RunPod용)
- GPU 메모리 사용량을 모니터링하세요
- 생성된 이미지는 로컬에 저장됩니다
- 인터넷 연결이 필요합니다 (모델 다운로드용) 