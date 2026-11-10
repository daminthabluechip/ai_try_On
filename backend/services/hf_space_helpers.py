"""
hf_space_helpers.py  —  small helpers shared by the features that use
free Hugging Face "Spaces" (AI demos):

    - services/model3d_service.py     (image -> 3D model)

Keeping them in their own file keeps model3d_service.py short, and any
future Hugging Face feature can reuse them.
"""

import uuid

from gradio_client import Client
from PIL import Image, ImageOps

from config import HF_TOKEN, UPLOADS_DIR

# Big images upload slowly and these AIs work at ~1024 px anyway, so we
# shrink the longest side to this size first.
MAX_IMAGE_SIDE_PX = 1024


class SpaceError(Exception):
    """Raised when a Hugging Face Space fails. The message is user-friendly."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def connect_to_space(space_name):
    """
    Open a connection to a Hugging Face Space.
    HF_TOKEN (optional) makes Hugging Face count usage against YOUR free
    account instead of the small anonymous quota.
    """
    try:
        return Client(space_name, token=HF_TOKEN or None, verbose=False)
    except Exception as error:
        print(f"[hf_space] Could not connect to {space_name}: {error}")
        raise SpaceError(
            "The free AI service is offline or starting up. Please try again in a few minutes.",
            status_code=503,
        )


def prepare_image(image_path):
    """
    Make a smaller JPEG copy of the image (faster upload, fewer timeouts).
    Also applies the phone's rotation info (EXIF), so the image is upright.
    Returns the path of the copy (in uploads/). The caller must delete it.
    """
    try:
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)       # fix phone rotation
            image = image.convert("RGB")                 # JPEG has no transparency
            image.thumbnail((MAX_IMAGE_SIDE_PX, MAX_IMAGE_SIDE_PX))  # keeps the shape
            small_image_path = UPLOADS_DIR / (uuid.uuid4().hex + ".jpg")
            image.save(small_image_path, "JPEG", quality=90)
    except Exception as error:
        print(f"[hf_space] Could not read image: {error}")
        raise SpaceError("This image could not be read. Please try another image.", status_code=400)
    return small_image_path


def read_file_path(file_value):
    """Gradio returns a file as a path text, {"value": path} or {"path": path}."""
    if isinstance(file_value, dict):
        return file_value.get("value") or file_value.get("path")
    return file_value


def get_friendly_message(error_text):
    """Turn a technical Space error into a sentence a user understands."""
    lowered = error_text.lower()
    if "quota" in lowered:
        # Keep Hugging Face's own sentence: it says how long to wait,
        # e.g. "(270s requested vs. 179s left). Try again in 23:42:36."
        hf_sentence = error_text.strip().strip("'\"").split(" Subscribe")[0]
        return (
            "The free AI quota is used up for now. Try again later, or check the "
            f"Hugging Face token (HF_TOKEN) in backend/.env. (Details: {hf_sentence})"
        )
    if "timed out" in lowered or "timeout" in lowered:
        return "The free AI service took too long. Please try again."
    if "queue" in lowered or "too many" in lowered:
        return "The free AI service is busy. Please try again in a minute."
    # Unknown error: add the service's own reason (shortened) to help debugging.
    short_reason = error_text.strip()[:200]
    return f"The free AI service could not finish. Please try again later. (Details: {short_reason})"
