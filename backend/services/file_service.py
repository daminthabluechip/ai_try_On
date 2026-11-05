"""
file_service.py  —  safe handling of uploaded and generated image files.

Why this file exists:
    Users can upload ANY file, so before we send anything to the AI we check:
      - Is there a file at all?
      - Is it an allowed image type (JPEG, PNG, WebP, HEIC)?
      - Is it small enough?
    This file also saves photos with random names and deletes them
    afterwards, because customer photos are personal data.

How it connects:
    routes/tryon.py calls these functions before and after the AI call.
"""

import time
import uuid

from config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB


# Maps each allowed image type to a file extension, used when saving.
EXTENSION_FOR_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


class InvalidImageError(Exception):
    """
    Raised when the uploaded file is not acceptable.
    The message is written for the end user, so the route can show it directly.
    """


def validate_image(content_type, file_bytes):
    """
    Check an uploaded image. Raise InvalidImageError with a friendly
    message if something is wrong; do nothing if everything is fine.

    content_type -> the type the browser reported, e.g. "image/jpeg"
    file_bytes   -> the raw content of the uploaded file
    """
    if file_bytes is None or len(file_bytes) == 0:
        raise InvalidImageError("No image was uploaded. Please choose an image file.")

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImageError(
            "Unsupported file type. Please upload a JPEG, PNG, WebP or HEIC image."
        )

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise InvalidImageError(
            f"The image is too large. The maximum size is {MAX_UPLOAD_SIZE_MB} MB."
        )


def save_temporary_file(folder, file_bytes, content_type):
    """
    Save bytes into `folder` with a RANDOM file name and return the path.

    Why a random name (uuid)?
      - Two users uploading "photo.jpg" at the same time won't overwrite each other.
      - Nobody can guess the file name of someone else's photo.
      - We never trust the user's own file name (it could contain tricks like "../").
    """
    extension = EXTENSION_FOR_TYPE.get(content_type, ".jpg")
    random_name = uuid.uuid4().hex + extension
    file_path = folder / random_name

    with open(file_path, "wb") as new_file:
        new_file.write(file_bytes)

    return file_path


def delete_file(file_path):
    """Delete a file if it exists. Never crashes if it is already gone."""
    if file_path is None:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # The file might be in use for a moment (Windows). It will be
        # removed later by delete_old_files, so we simply move on.
        pass


def delete_old_files(folder, max_age_minutes):
    """
    Delete files in `folder` older than `max_age_minutes`.

    Generated try-on images are kept for a short time so the user can view
    and download them, then cleaned up automatically (privacy!).
    The ".gitkeep" file is never deleted.
    """
    now = time.time()
    max_age_seconds = max_age_minutes * 60

    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue
        if file_path.name == ".gitkeep":
            continue

        file_age_seconds = now - file_path.stat().st_mtime
        if file_age_seconds > max_age_seconds:
            delete_file(file_path)
