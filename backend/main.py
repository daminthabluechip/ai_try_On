"""
main.py  —  the starting point of the backend.

Run the backend (from inside the "backend" folder, with venv activated):
    uvicorn main:app --reload

    "main"     -> this file (main.py)
    "app"      -> the FastAPI object created below
    --reload   -> restart automatically every time you save a .py file

This file only does "wiring":
    1. creates the FastAPI app,
    2. allows the React app to talk to it (CORS),
    3. serves the static image folder,
    4. switches on the endpoints from the routes/ folder.
The real work happens in routes/ and services/.
"""

import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    FRONTEND_URLS,
    OUTPUTS_DIR,
    STATIC_DIR,
    TRYON_MOCK_MODE,
    is_api_key_configured,
    is_cloudinary_configured,
)
from routes import model3d, products, tryon, view_angle


# ---------------------------------------------------------------------
# 1. Create the app
# ---------------------------------------------------------------------
# TODO: Add your own project / university information here.
#       It appears on the automatic docs page: http://127.0.0.1:8000/docs
app = FastAPI(
    title="AI Virtual Try-On API",
    description="Backend for the AI Virtual Try-On System (Phase 1 MVP).",
    version="1.0.0",
)


# ---------------------------------------------------------------------
# 2. CORS (Cross-Origin Resource Sharing)
# ---------------------------------------------------------------------
# Browsers block a web page from calling a DIFFERENT address unless that
# address says "I allow it". The React app runs on localhost:5173 and the
# backend on 127.0.0.1:8000 — different addresses — so we must allow it.
# We allow ONLY the addresses listed in FRONTEND_URLS (from .env), not
# the whole internet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    # PUT and DELETE are used by the "Manage Products" page.
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# 3. Serve the "static" folder
# ---------------------------------------------------------------------
# Any file inside backend/static/ becomes available in the browser at
# http://127.0.0.1:8000/static/<file path>
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Generated try-on images are served the same way:
# backend/outputs/abc123.png -> http://127.0.0.1:8000/outputs/abc123.png
# The file names are long random codes, so nobody can guess someone
# else's result, and files are deleted after a while (see routes/tryon.py).
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# 3D models (.glb) are also saved in outputs/. Some computers (especially
# Windows) don't know the .glb file type, so we tell Python explicitly.
mimetypes.add_type("model/gltf-binary", ".glb")


# ---------------------------------------------------------------------
# 4. Switch on the endpoints from the routes/ folder
# ---------------------------------------------------------------------
app.include_router(products.router)   # GET/POST /products, PUT/DELETE /products/{id}
app.include_router(tryon.router)      # POST /tryon
app.include_router(model3d.router)    # POST /model3d  (image -> rotatable 3D model)
app.include_router(view_angle.router) # POST /view-angle  (same person, another camera angle)


# ---------------------------------------------------------------------
# Health check: GET /
# ---------------------------------------------------------------------
@app.get("/")
def health_check():
    """
    A quick "are you alive?" endpoint.
    Open http://127.0.0.1:8000/ in a browser to see if the backend runs.

    It also reports whether the API key is set up — but NEVER the key itself.
    "image_storage" says where garment images are stored: "cloudinary" or "local".
    """
    image_storage = "local"
    if is_cloudinary_configured():
        image_storage = "cloudinary"

    return {
        "status": "ok",
        "message": "AI Virtual Try-On backend is running.",
        "api_key_configured": is_api_key_configured(),
        "mock_mode": TRYON_MOCK_MODE,
        "image_storage": image_storage,
    }
