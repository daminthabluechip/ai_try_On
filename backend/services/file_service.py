"""
Validation, saving and clean-up of uploaded and generated image files.
"""

import time
import uuid

from config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB


EXTENSION_FOR_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


class InvalidImageError(Exception):
    """Uploaded file is not acceptable. The message is shown to the user."""


def validate_image(content_type, file_bytes):
    """Raise InvalidImageError if the upload is missing, the wrong type or too large."""
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
    Save bytes under a random name and return the path.
    Random names avoid collisions, can't be guessed, and ignore unsafe user file names.
    """
    extension = EXTENSION_FOR_TYPE.get(content_type, ".jpg")
    random_name = uuid.uuid4().hex + extension
    file_path = folder / random_name

    with open(file_path, "wb") as new_file:
        new_file.write(file_bytes)

    return file_path


def delete_file(file_path):
    """Delete a file if it exists; never raises."""
    if file_path is None:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # May be briefly locked on Windows; delete_old_files removes it later.
        pass


def delete_old_files(folder, max_age_minutes):
    """Delete files older than max_age_minutes (keeps .gitkeep)."""
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
