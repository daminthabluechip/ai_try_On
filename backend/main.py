"""
Entry point of the backend. Run with: uvicorn main:app --reload
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
from routes import model3d, products, tryon

# TODO: Add your own project / university information (shown on /docs).
app = FastAPI(
    title="AI Virtual Try-On API",
    description="Backend for the AI Virtual Try-On System (Phase 1 MVP).",
    version="1.0.0",
)

# Only the website addresses in FRONTEND_URLS may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Generated images and 3D models. Random file names; old files are deleted automatically.
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Windows doesn't know the .glb file type by default.
mimetypes.add_type("model/gltf-binary", ".glb")

app.include_router(products.router)
app.include_router(tryon.router)
app.include_router(model3d.router)


@app.get("/")
def health_check():
    """Report backend status (never the API key itself)."""
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
