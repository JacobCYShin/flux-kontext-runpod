import os
from huggingface_hub import snapshot_download

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise RuntimeError("HF_TOKEN environment variable is not set.")

snapshot_download(
    repo_id="black-forest-labs/FLUX.1-Kontext-dev",
    token=hf_token,
    local_dir="/app/models/flux",
    ignore_patterns=["flux1-kontext-dev.safetensors", "transformer/*"],
    local_dir_use_symlinks=False
)

snapshot_download(
    repo_id="mit-han-lab/nunchaku-flux.1-kontext-dev",
    token=hf_token,
    local_dir="/app/models/nunchaku",
    local_dir_use_symlinks=False
)