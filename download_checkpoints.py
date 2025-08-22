#!/usr/bin/env python3
"""
체크포인트 다운로드 스크립트
로컬에서 체크포인트를 다운로드하여 /runpod-volume 구조로 준비합니다.
"""

import os
import sys
from huggingface_hub import snapshot_download
from nunchaku.utils import get_precision

def download_checkpoints():
    """체크포인트를 다운로드합니다."""
    
    # HF_TOKEN 확인
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN이 설정되지 않았습니다.")
        print("export HF_TOKEN='your_token_here'로 설정해주세요.")
        sys.exit(1)
    
    # 다운로드 디렉토리 설정
    base_dir = "./checkpoints"
    nunchaku_dir = os.path.join(base_dir, "nunchaku")
    flux_dir = os.path.join(base_dir, "flux-kontext")
    
    # 디렉토리 생성
    os.makedirs(nunchaku_dir, exist_ok=True)
    os.makedirs(flux_dir, exist_ok=True)
    
    print("🚀 체크포인트 다운로드 시작...")
    
    try:
        # 1. Nunchaku 모델 다운로드
        print("📥 Nunchaku 모델 다운로드 중...")
        precision = get_precision()
        filename = f"svdq-{precision}_r32-flux.1-kontext-dev.safetensors"
        
        snapshot_download(
            repo_id="mit-han-lab/nunchaku-flux.1-kontext-dev",
            filename=filename,
            local_dir=nunchaku_dir,
            token=hf_token
        )
        print(f"✅ Nunchaku 모델 다운로드 완료: {nunchaku_dir}")
        
        # 2. FLUX.1-Kontext-dev 모델 다운로드 (제외 파일 제외)
        print("📥 FLUX.1-Kontext-dev 모델 다운로드 중...")
        snapshot_download(
            repo_id="black-forest-labs/FLUX.1-Kontext-dev",
            exclude=["flux1-kontext-dev.safetensors", "transformer/*"],
            local_dir=flux_dir,
            token=hf_token
        )
        print(f"✅ FLUX 모델 다운로드 완료: {flux_dir}")
        
        print("🎉 모든 체크포인트 다운로드 완료!")
        print(f"📁 체크포인트 위치: {base_dir}")
        
        # 디렉토리 크기 확인
        total_size = get_directory_size(base_dir)
        print(f"📊 총 크기: {format_size(total_size)}")
        
    except Exception as e:
        print(f"❌ 다운로드 실패: {str(e)}")
        sys.exit(1)

def get_directory_size(path):
    """디렉토리 크기를 계산합니다."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def format_size(size_bytes):
    """바이트를 읽기 쉬운 형태로 변환합니다."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

if __name__ == "__main__":
    download_checkpoints()
