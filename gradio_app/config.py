import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- RunPod Configuration ---
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID") 

# --- UI and Model Configuration ---
# List of aspect ratios for the UI, matching the API's expected format
ratios = ["Original", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "4:5", "5:4", "21:9", "9:21", "2:1", "1:2"]

# --- Constants for Resolution and Latent Preview ---
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
    (672, 1568), (688, 1504), (720, 1456), (752, 1392), (800, 1328),
    (832, 1248), (880, 1184), (944, 1104), (1024, 1024), (1104, 944),
    (1184, 880), (1248, 832), (1328, 800), (1392, 752), (1456, 720),
    (1504, 688), (1568, 672),
] 