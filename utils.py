from io import BytesIO
import base64
from PIL import Image
import os
import tempfile
import logging
import uuid
import time

# S3 관련 import (선택적)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

# 로깅 설정
logger = logging.getLogger(__name__)

LATENT_RGB_FACTORS = [
    [-0.0346,  0.0244,  0.0681],
    [ 0.0034,  0.0210,  0.0687],
    [ 0.0275, -0.0668, -0.0433],
    [-0.0174,  0.0160,  0.0617],
    [ 0.0859,  0.0721,  0.0329],
    [ 0.0004,  0.0383,  0.0115],
    [ 0.0405,  0.0861,  0.0915],
    [-0.0236, -0.0185, -0.0259],
    [-0.0245,  0.0250,  0.1180],
    [ 0.1008,  0.0755, -0.0421],
    [-0.0515,  0.0201,  0.0011],
    [ 0.0428, -0.0012, -0.0036],
    [ 0.0817,  0.0765,  0.0749],
    [-0.1264, -0.0522, -0.1103],
    [-0.0280, -0.0881, -0.0499],
    [-0.1262, -0.0982, -0.0778]
]

PREFERED_KONTEXT_RESOLUTIONS = [
    (672, 1568),
    (688, 1504),
    (720, 1456),
    (752, 1392),
    (800, 1328),
    (832, 1248),
    (880, 1184),
    (944, 1104),
    (1024, 1024),
    (1104, 944),
    (1184, 880),
    (1248, 832),
    (1328, 800),
    (1392, 752),
    (1456, 720),
    (1504, 688),
    (1568, 672),
]

def resize_to_target_area(image, ratio):
    if ratio == "original":
        original_width, original_height = image.size
        if original_height == 0:
            raise ValueError("Original image height cannot be zero.")
        target_aspect_ratio = original_width / original_height
    else:
        try:
            w, h = map(int, ratio.split(':'))
            if h == 0:
                raise ValueError("Ratio height cannot be zero.")
            target_aspect_ratio = w / h
        except ValueError:
            raise ValueError(f"Invalid ratio format: {ratio}. Expected 'W:H' or 'original'.")

    best_resolution = None
    min_aspect_ratio_diff = float('inf')

    for width, height in PREFERED_KONTEXT_RESOLUTIONS:
        aspect_ratio = width / height
        diff = abs(target_aspect_ratio - aspect_ratio)
        if diff < min_aspect_ratio_diff:
            min_aspect_ratio_diff = diff
            best_resolution = (width, height)

    return best_resolution

def encode_image_to_base64(image, use_jpeg=False):
    buffered = BytesIO()
    if use_jpeg:
        # Convert to RGB if it's RGBA, as JPEG doesn't support alpha channel
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        # Save as JPEG with a specific quality for smaller size
        image.save(buffered, format="JPEG", quality=85)
    else:
        image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def decode_base64_to_image(base64_str):
    """
    Decodes a base64 string to an image.
    """
    if "," in base64_str:
        base64_str = base64_str.split(',')[1]

    try:
        image_data = base64.b64decode(base64_str)
        return Image.open(BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"Invalid base64 string: {e}")

# ───────────────────────────────────────
# S3 관련 새로운 함수들 (기존 함수들과 분리)
# ───────────────────────────────────────

def get_s3_client():
    """S3 클라이언트를 반환합니다."""
    if not S3_AVAILABLE:
        logger.warning("boto3가 설치되지 않음 - S3 기능 비활성화")
        return None
        
    try:
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not aws_access_key_id or not aws_secret_access_key:
            logger.warning("AWS 인증 정보가 설정되지 않음")
            return None
            
        return boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
    except Exception as e:
        logger.error(f"S3 클라이언트 생성 실패: {e}")
        return None

def is_s3_url(url):
    """URL이 S3 URL인지 확인합니다."""
    return url.startswith(('http://', 'https://')) and 's3.' in url

def upload_image_to_s3(image, file_name=None, use_jpeg=True):
    """이미지를 S3에 업로드하고 URL을 반환합니다."""
    if not S3_AVAILABLE:
        logger.warning("S3 기능이 비활성화됨")
        return None
        
    try:
        s3_client = get_s3_client()
        if not s3_client:
            return None
            
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if not bucket_name:
            logger.warning("S3_BUCKET_NAME 환경변수가 설정되지 않음")
            return None
            
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg' if use_jpeg else '.png') as tmp_file:
            if use_jpeg:
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                image.save(tmp_file.name, format="JPEG", quality=85)
            else:
                image.save(tmp_file.name, format="PNG")
            
            # S3 키 생성
            if not file_name:
                file_name = f"flux_kontext_{int(time.time())}_{str(uuid.uuid4())[:8]}"
                file_name += '.jpg' if use_jpeg else '.png'
            
            s3_key = f"generated-images/{file_name}"
            
            # S3에 업로드
            s3_client.upload_file(tmp_file.name, bucket_name, s3_key)
            
            # 임시 파일 삭제
            os.unlink(tmp_file.name)
            
            # S3 URL 생성
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
            
            logger.info(f"이미지 S3 업로드 완료: {s3_url}")
            return s3_url
            
    except Exception as e:
        logger.error(f"S3 업로드 실패: {e}")
        return None

def download_image_from_s3(s3_url):
    """S3 URL에서 이미지를 다운로드합니다."""
    if not S3_AVAILABLE:
        logger.warning("S3 기능이 비활성화됨")
        return None
        
    try:
        s3_client = get_s3_client()
        if not s3_client:
            return None
            
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if not bucket_name:
            logger.warning("S3_BUCKET_NAME 환경변수가 설정되지 않음")
            return None
            
        # S3 URL에서 키 추출
        if bucket_name not in s3_url:
            logger.error(f"S3 URL이 올바른 버킷을 가리키지 않음: {s3_url}")
            return None
            
        s3_key = s3_url.split(f"{bucket_name}.s3.")[1].split(".amazonaws.com/")[1]
        
        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            s3_client.download_file(bucket_name, s3_key, tmp_file.name)
            
            # 이미지 로드
            image = Image.open(tmp_file.name)
            
            # 임시 파일 삭제
            os.unlink(tmp_file.name)
            
            logger.info(f"이미지 S3 다운로드 완료: {s3_url}")
            return image
            
    except Exception as e:
        logger.error(f"S3 다운로드 실패: {e}")
        return None 