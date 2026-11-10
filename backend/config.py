"""
All backend settings, read once from the .env file.
"""

from pathlib import Path
import os

from dotenv import load_dotenv


# ---------------------------------------------------------------------
# Folder paths
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
PRODUCT_IMAGES_DIR = STATIC_DIR / "products"
UPLOADS_DIR = BASE_DIR / "uploads"       # temporary user photos
OUTPUTS_DIR = BASE_DIR / "outputs"       # generated images and 3D models

PRODUCTS_FILE = DATA_DIR / "products.json"

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------
# Virtual try-on provider (Genlook)
# ---------------------------------------------------------------------
# Secret: must never be sent to the frontend.
TRYON_API_KEY = os.getenv("VIRTUAL_TRYON_API_KEY", "")
TRYON_API_URL = os.getenv("VIRTUAL_TRYON_API_URL", "https://api.genlook.app/tryon/v1")

# true = free test mode (photo returned unchanged, no credits used).
mock_mode_text = os.getenv("TRYON_MOCK_MODE", "true")
TRYON_MOCK_MODE = mock_mode_text.strip().lower() == "true"


# ---------------------------------------------------------------------
# Cloudinary (optional cloud storage for garment images)
# ---------------------------------------------------------------------
# Format: cloudinary://<api_key>:<api_secret>@<cloud_name>
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "ai-tryon/products")

# A malformed value would crash the Cloudinary library at startup,
# so we ignore it and fall back to local storage.
if CLOUDINARY_URL != "" and not CLOUDINARY_URL.startswith("cloudinary://"):
    print(
        "[config] WARNING: CLOUDINARY_URL in backend/.env must start with "
        "'cloudinary://' (check you didn't paste 'CLOUDINARY_URL=' twice). "
        "Using local image storage for now."
    )
    CLOUDINARY_URL = ""
    os.environ.pop("CLOUDINARY_URL", None)


def is_cloudinary_configured():
    """True if CLOUDINARY_URL is filled in (and its <placeholders> were replaced)."""
    if not CLOUDINARY_URL.startswith("cloudinary://"):
        return False
    if "<" in CLOUDINARY_URL:
        return False
    return True


# ---------------------------------------------------------------------
# 3D models
# ---------------------------------------------------------------------
# "triposr" (default, Hugging Face CPU Space), "flask" (our own TripoSR
# server) or "hunyuan" (Hunyuan3D-2.1, small daily GPU quota).
MODEL3D_ENGINE = os.getenv("MODEL3D_ENGINE", "triposr").strip().lower()

TRIPOSR_API_URL = os.getenv("TRIPOSR_API_URL", "http://127.0.0.1:5000").strip().rstrip("/")
TRIPOSR_SPACE = os.getenv("TRIPOSR_SPACE", "WeReCooking2/Dust3R-TripoSR").strip()
MODEL3D_SPACE = os.getenv("MODEL3D_SPACE", "tencent/Hunyuan3D-2.1").strip()   # Hunyuan3D

# Optional: gives you your own Hugging Face GPU quota instead of the anonymous one.
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()


# ---------------------------------------------------------------------
# Upload rules
# ---------------------------------------------------------------------
max_size_text = os.getenv("MAX_UPLOAD_SIZE_MB", "10")
MAX_UPLOAD_SIZE_MB = int(max_size_text)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Matches what Genlook supports.
# TODO: Remove a type here if you want to block it (e.g. HEIC from iPhones).
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"]


# ---------------------------------------------------------------------
# Product management and CORS
# ---------------------------------------------------------------------
# Set to false on the live site: Phase 1 has no admin login.
management_text = os.getenv("ALLOW_PRODUCT_MANAGEMENT", "true")
ALLOW_PRODUCT_MANAGEMENT = management_text.strip().lower() == "true"

# Comma-separated list of website addresses allowed to call the API.
frontend_urls_text = os.getenv("FRONTEND_URLS", "http://localhost:5173")
FRONTEND_URLS = []
for url in frontend_urls_text.split(","):
    cleaned_url = url.strip()
    if cleaned_url != "":
        FRONTEND_URLS.append(cleaned_url)


def is_api_key_configured():
    """True if a real Genlook API key is set."""
    if TRYON_API_KEY == "":
        return False
    if TRYON_API_KEY == "YOUR_API_KEY_HERE":
        return False
    return True
