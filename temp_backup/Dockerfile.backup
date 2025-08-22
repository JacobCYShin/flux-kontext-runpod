########################################
# Dockerfile (Python 3.11 + CUDA 12.4) #
########################################
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_PREFER_BINARY=1 \
    PYTHONUNBUFFERED=1 \
    CMAKE_BUILD_PARALLEL_LEVEL=8 \
    HF_TOKEN={Your Hugging Face Token}

# ───────────────────────────────────────
# 1) 시스템 패키지 & Python 3.11 설치
# ───────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        git wget git-lfs \
        libgl1 && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-distutils && \
    # python, python3 모두 3.11을 가리키도록 통일
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    git lfs install && \
    apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ───────────────────────────────────────
# 2) pip 부트스트랩 & 기본 패키지 설치
# ───────────────────────────────────────
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir --upgrade pip wheel setuptools

# ───────────────────────────────────────
# 3) 핵심 라이브러리 설치
# ───────────────────────────────────────
# BuildKit의 pip 캐시 활용
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir \
        huggingface_hub[hf_transfer] \
        torch==2.6 torchvision==0.21 torchaudio==2.6 && \
    # diffusers
    python -m pip install --no-cache-dir \
        git+https://github.com/huggingface/diffusers.git && \
    # nunchaku (cp311 wheel)
    python -m pip install --no-cache-dir \
        https://github.com/mit-han-lab/nunchaku/releases/download/v0.3.2dev20250701/nunchaku-0.3.2.dev20250701+torch2.6-cp311-cp311-linux_x86_64.whl && \
    python -m pip install --no-cache-dir \
        git+https://github.com/runpod/runpod-python.git

# ───────────────────────────────────────
# 4) 모델 체크포인트 미리 받아두기
# ───────────────────────────────────────
RUN huggingface-cli download \
        mit-han-lab/nunchaku-flux.1-kontext-dev \
        svdq-int4_r32-flux.1-kontext-dev.safetensors

RUN huggingface-cli download black-forest-labs/FLUX.1-Kontext-dev --exclude "flux1-kontext-dev.safetensors" "transformer/*" --token ${HF_TOKEN}


# ───────────────────────────────────────
# 5) 추가 의존성
# ───────────────────────────────────────
# COPY requirements.txt /tmp/requirements.txt
# RUN --mount=type=cache,target=/root/.cache/pip \
#     python -m pip install --no-cache-dir -r /tmp/requirements.txt

# ───────────────────────────────────────
# 6) 애플리케이션 코드
# ───────────────────────────────────────
WORKDIR /app
COPY main.py /app/main.py
COPY utils.py /app/utils.py

CMD ["python", "-u", "/app/main.py"]
