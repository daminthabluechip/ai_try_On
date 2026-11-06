"""
config.py  —  ONE place for all backend settings.

Why this file exists:
    Settings such as the API key live in the .env file (so they are never
    written into the code). This file reads them ONCE when the backend
    starts, and every other file imports them from here, e.g.:

        from config import TRYON_API_KEY

    If a setting ever changes, you only edit .env — never the code.
"""

from pathlib import Path
import os

# python-dotenv reads the "NAME=value" lines from .env and makes them
# available through os.getenv(...), just like real environment variables.
from dotenv import load_dotenv


# ---------------------------------------------------------------------
# Folder paths
# ---------------------------------------------------------------------
# BASE_DIR is the "backend" folder (the folder that contains this file).
# Building every other path from it means the app works no matter which
# folder you start it from.
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"                         # products.json lives here
STATIC_DIR = BASE_DIR / "static"                     # files served to the browser
PRODUCT_IMAGES_DIR = STATIC_DIR / "products"         # garment images
UPLOADS_DIR = BASE_DIR / "uploads"                   # temporary user photos
OUTPUTS_DIR = BASE_DIR / "outputs"                   # generated try-on images

PRODUCTS_FILE = DATA_DIR / "products.json"

# Load the .env file that sits next to this config.py file.
load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------
# Virtual try-on provider settings (read from .env)
# ---------------------------------------------------------------------
# The secret key that proves to Genlook that the request comes from you.
# It must NEVER be sent to the frontend.
TRYON_API_KEY = os.getenv("VIRTUAL_TRYON_API_KEY", "")

# The base web address of the try-on API.
TRYON_API_URL = os.getenv("VIRTUAL_TRYON_API_URL", "https://api.genlook.app/tryon/v1")

# "true" -> free test mode (no AI, no credits used). Anything else -> real AI.
# .env values are always text, so we compare the text to "true".
mock_mode_text = os.getenv("TRYON_MOCK_MODE", "true")
TRYON_MOCK_MODE = mock_mode_text.strip().lower() == "true"


# ---------------------------------------------------------------------
# Cloudinary (cloud storage for garment images) — optional
# ---------------------------------------------------------------------
# Format: cloudinary://<api_key>:<api_secret>@<cloud_name>
# The Cloudinary library reads CLOUDINARY_URL by itself; we only read it
# here to check whether it has been filled in.
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "ai-tryon/products")

# A wrongly formatted value would make the Cloudinary library crash the
# whole backend at startup. Instead, we print a warning and ignore it
# (garment images are then saved locally until you fix .env).
if CLOUDINARY_URL != "" and not CLOUDINARY_URL.startswith("cloudinary://"):
    print(
        "[config] WARNING: CLOUDINARY_URL in backend/.env must start with "
        "'cloudinary://' (check you didn't paste 'CLOUDINARY_URL=' twice). "
        "Using local image storage for now."
    )
    CLOUDINARY_URL = ""
    os.environ.pop("CLOUDINARY_URL", None)


def is_cloudinary_configured():
    """
    Return True if a real CLOUDINARY_URL is in .env.
    (A value still containing "<" means the placeholders weren't replaced.)
    """
    if not CLOUDINARY_URL.startswith("cloudinary://"):
        return False
    if "<" in CLOUDINARY_URL:
        return False
    return True


# ---------------------------------------------------------------------
# Upload rules
# ---------------------------------------------------------------------
max_size_text = os.getenv("MAX_UPLOAD_SIZE_MB", "10")
MAX_UPLOAD_SIZE_MB = int(max_size_text)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Only these image types are accepted. They match what Genlook supports.
# TODO: Remove a type here if you want to block it (e.g. HEIC from iPhones).
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"]


# ---------------------------------------------------------------------
# Product management ("Manage Products" page)
# ---------------------------------------------------------------------
# "true"  -> the website may add/delete products and upload garment images.
# "false" -> those changes are refused (recommended once the site is online,
#            because Phase 1 has no admin login).
management_text = os.getenv("ALLOW_PRODUCT_MANAGEMENT", "true")
ALLOW_PRODUCT_MANAGEMENT = management_text.strip().lower() == "true"


# ---------------------------------------------------------------------
# CORS: which website addresses may call this backend from a browser
# ---------------------------------------------------------------------
# .env holds a comma-separated list, e.g. "http://localhost:5173,https://x.com".
# We split it into a Python list: ["http://localhost:5173", "https://x.com"].
frontend_urls_text = os.getenv("FRONTEND_URLS", "http://localhost:5173")
FRONTEND_URLS = []
for url in frontend_urls_text.split(","):
    cleaned_url = url.strip()
    if cleaned_url != "":
        FRONTEND_URLS.append(cleaned_url)


def is_api_key_configured():
    """Return True if a real API key has been put in .env."""
    if TRYON_API_KEY == "":
        return False
    if TRYON_API_KEY == "YOUR_API_KEY_HERE":
        return False
    return True
