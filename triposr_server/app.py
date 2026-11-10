"""
app.py  —  a small Flask API around the TripoSR 3D model.

    POST /generate   send one image  ->  receive a 3D model (.glb file)
    GET  /health     "is the server running and is the model loaded?"

How it fits into the project:

    React website ──► FastAPI backend (/model3d) ──► THIS Flask server ──► TripoSR
                                                   (port 5000, your PC)

    The website keeps calling the FastAPI backend, and the backend forwards
    the image here (set MODEL3D_ENGINE=flask in backend/.env). That way the
    browser only ever talks to one backend.

Run it (from the triposr_server folder, with its venv active):
    python app.py
The first start downloads the TripoSR weights (~1.7 GB) and the background
removal model (~170 MB) once; after that they are loaded from the cache.

TripoSR:  https://github.com/VAST-AI-Research/TripoSR  (MIT licence)
Weights:  https://huggingface.co/stabilityai/TripoSR
"""

import io
import logging
import os
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------
# Make Python find (1) our torchmcubes.py stand-in and (2) TripoSR's code.
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# Settings (can be changed with environment variables)
# ---------------------------------------------------------------------
PORT = int(os.getenv("PORT", "5000"))

# "cuda" needs an NVIDIA GPU with ~6 GB memory. Smaller GPUs (like 2 GB)
# are not enough, so we use the processor ("cpu") unless told otherwise.
DEVICE = os.getenv("TRIPOSR_DEVICE", "cpu")

# Surface detail (marching cubes grid). 256 = TripoSR's default.
# Lower (e.g. 128) is faster with a rougher surface.
DEFAULT_RESOLUTION = 256
MIN_RESOLUTION, MAX_RESOLUTION = 32, 320

# How much of the picture the object fills after cropping (TripoSR default).
FOREGROUND_RATIO = 0.85

# Largest accepted upload (10 MB), same limit as the main backend.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("triposr")


# ---------------------------------------------------------------------
# Load the AI models ONCE when the server starts (takes ~10–60 seconds).
# Loading them for every request would be far too slow.
# ---------------------------------------------------------------------
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

# The model can only work on one image at a time safely, so requests
# wait in line for this lock.
model_lock = threading.Lock()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


# =====================================================================
# Helpers
# =====================================================================
def prepare_image(uploaded_file, remove_bg):
    """
    Turn the uploaded file into the image TripoSR expects:
      1. open it and apply the phone's rotation info (EXIF),
      2. remove the background (rembg),
      3. crop around the person and centre them (resize_foreground),
      4. put them on a plain grey background.
    Steps 2–4 are copied from TripoSR's own run.py.
    """
    image = Image.open(uploaded_file.stream)
    image = ImageOps.exif_transpose(image)

    if not remove_bg:
        return image.convert("RGB")

    image = remove_background(image.convert("RGB"), rembg_session)
    image = resize_foreground(image, FOREGROUND_RATIO)

    # Blend the transparent background into grey (0.5), as TripoSR was trained.
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


# =====================================================================
# Endpoints
# =====================================================================
@app.get("/health")
def health():
    """Quick check: open http://127.0.0.1:5000/health in a browser."""
    return jsonify({"status": "ok", "model": "stabilityai/TripoSR", "device": DEVICE})


@app.post("/generate")
def generate():
    """
    Form fields:
        image              (required) JPEG / PNG / WebP file
        resolution         (optional) 32–320, default 256
        remove_background  (optional) "true" (default) or "false"
    Returns the 3D model as a .glb file (with vertex colours).
    """
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
        # resize_foreground fails when rembg removed EVERYTHING.
        return error("No person or object was found in the image.", 400)

    started = time.time()
    try:
        with model_lock, torch.no_grad():
            scene_codes = model([image], device=DEVICE)
            # True = also predict a colour for every vertex.
            mesh = model.extract_mesh(scene_codes, True, resolution=resolution)[0]
    except Exception as exception:
        log.exception("TripoSR failed")
        return error(f"TripoSR could not build the model: {exception}", 500)

    # Turn the model so it stands upright in web 3D viewers (glTF: Y is up),
    # the same as TripoSR's own demo website does.
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
    # threaded=True: /health still answers while a model is being built.
    # 127.0.0.1 = only this computer can reach it (the FastAPI backend).
    app.run(host="127.0.0.1", port=PORT, threaded=True)
