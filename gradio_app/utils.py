import base64
from PIL import Image
import io
from config import PREFERED_KONTEXT_RESOLUTIONS

def image_to_base64_uri(image_path: str) -> str:
    """Converts an image file to a base64 data URI."""
    with open(image_path, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
    # Basic mime type detection, can be improved
    mime_type = f"image/{image_path.split('.')[-1] or 'png'}"
    return f"data:{mime_type};base64,{encoded_string}"

def base64_to_pil(base64_string: str) -> Image.Image:
    """Converts a base64 string to a PIL Image."""
    # Strip data URI prefix if present
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

def resize_to_target_area(image: Image.Image, ratio_str: str) -> tuple[int, int]:
    """
    Finds the best resolution from a predefined list that matches the target aspect ratio.
    """
    if ratio_str.lower() == "original":
        original_width, original_height = image.size
        if original_height == 0:
            raise ValueError("Original image height cannot be zero.")
        target_aspect_ratio = original_width / original_height
    else:
        try:
            w, h = map(int, ratio_str.split(':'))
            if h == 0:
                raise ValueError("Ratio height cannot be zero.")
            target_aspect_ratio = w / h
        except ValueError:
            raise ValueError(f"Invalid ratio format: {ratio_str}. Expected 'W:H' or 'original'.")

    best_resolution = None
    min_aspect_ratio_diff = float('inf')

    for width, height in PREFERED_KONTEXT_RESOLUTIONS:
        aspect_ratio = width / height
        diff = abs(target_aspect_ratio - aspect_ratio)
        if diff < min_aspect_ratio_diff:
            min_aspect_ratio_diff = diff
            best_resolution = (width, height)

    return best_resolution 