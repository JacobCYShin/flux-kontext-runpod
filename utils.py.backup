from io import BytesIO
import base64
from PIL import Image

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