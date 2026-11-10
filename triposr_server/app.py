"""
Flask API around the TripoSR 3D model.

    POST /generate   image -> 3D model (.glb)
    GET  /health

Run with: python app.py   (first start downloads ~1.7 GB of weights)
TripoSR: https://github.com/VAST-AI-Research/TripoSR (MIT licence)
"""

import io
import logging
import os
import sys
import threading
import time
from pathlib import Path

# Our torchmcubes.py stand-in must come before TripoSR's code on the path.
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "TripoSR"))   # the official TripoSR code (tsr package)
sys.path.insert(0, str(BASE_DIR))               # our torchmcubes.py comes first

import numpy as np  # noqa: E402
import rembg  # noqa: E402
import torch  # noqa: E402
from flask import Flask, jsonify, request, send_file  # noqa: E402
from PIL import Image, ImageOps, UnidentifiedImageError  # noqa: E402

from tsr.system import TSR  # noqa: E402
from tsr.utils import remove_background, resize_foreground, to_gradio_3d_orientation  # noqa: E402


PORT = int(os.getenv("PORT", "5000"))

# "cuda" needs an NVIDIA GPU with ~6 GB of memory.
DEVICE = os.getenv("TRIPOSR_DEVICE", "cpu")

DEFAULT_RESOLUTION = 256
MIN_RESOLUTION, MAX_RESOLUTION = 32, 320

FOREGROUND_RATIO = 0.85

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("triposr")


log.info("Loading TripoSR on %s (first run downloads ~1.7 GB)...", DEVICE)
model = TSR.from_pretrained(
    "stabilityai/TripoSR",
    config_name="config.yaml",
    weight_name="model.ckpt",
)
model.renderer.set_chunk_size(8192)   # smaller = less memory, a bit slower
model.to(DEVICE)

log.info("Loading the background removal model (rembg)...")
rembg_session = rembg.new_session()
log.info("Ready.")

# One image at a time: the model isn't safe to use from several threads.
model_lock = threading.Lock()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def prepare_image(uploaded_file, remove_bg):
    """Remove the background, centre the subject and put it on grey (as in TripoSR's run.py)."""
    image = Image.open(uploaded_file.stream)
    image = ImageOps.exif_transpose(image)

    if not remove_bg:
        return image.convert("RGB")

    image = remove_background(image.convert("RGB"), rembg_session)
    image = resize_foreground(image, FOREGROUND_RATIO)

    pixels = np.array(image).astype(np.float32) / 255.0
    rgb, alpha = pixels[:, :, :3], pixels[:, :, 3:4]
    pixels = rgb * alpha + (1 - alpha) * 0.5
    return Image.fromarray((pixels * 255.0).astype(np.uint8))


def read_resolution():
    """Read the optional "resolution" form field and keep it in the allowed range."""
    try:
        resolution = int(request.form.get("resolution", DEFAULT_RESOLUTION))
    except ValueError:
        resolution = DEFAULT_RESOLUTION
    return max(MIN_RESOLUTION, min(MAX_RESOLUTION, resolution))


def error(message, status_code):
    """Send an error in the same shape as the FastAPI backend: {"detail": ...}."""
    return jsonify({"detail": message}), status_code


@app.get("/health")
def health():
    """Quick check: open http://127.0.0.1:5000/health in a browser."""
    return jsonify({"status": "ok", "model": "stabilityai/TripoSR", "device": DEVICE})


@app.post("/generate")
def generate():
    """Form fields: image (required), resolution (32-320), remove_background. Returns a .glb."""
    uploaded_file = request.files.get("image")
    if uploaded_file is None or uploaded_file.filename == "":
        return error("Please send an image in the form field 'image'.", 400)

    remove_bg = request.form.get("remove_background", "true").lower() != "false"
    resolution = read_resolution()

    try:
        image = prepare_image(uploaded_file, remove_bg)
    except UnidentifiedImageError:
        return error("This file is not an image the server can read.", 400)
    except ValueError:
        return error("No person or object was found in the image.", 400)

    started = time.time()
    try:
        with model_lock, torch.no_grad():
            scene_codes = model([image], device=DEVICE)
            mesh = model.extract_mesh(scene_codes, True, resolution=resolution)[0]
    except Exception as exception:
        log.exception("TripoSR failed")
        return error(f"TripoSR could not build the model: {exception}", 500)

    # Stand the model upright for web 3D viewers (glTF: Y is up).
    mesh = to_gradio_3d_orientation(mesh)
    glb_bytes = mesh.export(file_type="glb")
    log.info(
        "Built model: %d vertices, %.1f MB, %.0f s",
        len(mesh.vertices), len(glb_bytes) / 1e6, time.time() - started,
    )

    return send_file(
        io.BytesIO(glb_bytes),
        mimetype="model/gltf-binary",
        as_attachment=False,
        download_name="model.glb",
    )


@app.errorhandler(413)
def file_too_large(_error):
    return error("The image is too large (max 10 MB).", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, threaded=True)
