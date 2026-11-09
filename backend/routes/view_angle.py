"""
routes/view_angle.py  —  "show me from another angle" endpoint.

    POST /view-angle
        image           -> the image to redraw (the try-on result)
        rotate_degrees  -> -90 ... 90   (positive = left, negative = right)
        vertical_tilt   -> -1, 0 or 1   (from above / eye level / from below)

Returns:
    {"image_url": "http://127.0.0.1:8000/outputs/abc123.png"}
"""

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config import OUTPUTS_DIR, UPLOADS_DIR
from services.file_service import (
    InvalidImageError,
    delete_file,
    delete_old_files,
    save_temporary_file,
    validate_image,
)
from services.hf_space_helpers import SpaceError
from services.view_angle_service import ALLOWED_TILTS, MAX_ROTATE_DEGREES, generate_new_angle

router = APIRouter()


@router.post("/view-angle")
async def create_new_angle(
    request: Request,
    image: UploadFile = File(None),
    rotate_degrees: int = Form(0),
    vertical_tilt: int = Form(0),
):
    """Redraw the person from another camera angle."""
    if image is None:
        raise HTTPException(status_code=400, detail="Please send an image.")
    if abs(rotate_degrees) > MAX_ROTATE_DEGREES:
        raise HTTPException(status_code=400, detail="Rotation must be between -90 and 90 degrees.")
    if vertical_tilt not in ALLOWED_TILTS:
        raise HTTPException(status_code=400, detail="Camera height must be -1, 0 or 1.")

    image_bytes = await image.read()
    try:
        validate_image(image.content_type, image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    delete_old_files(OUTPUTS_DIR, max_age_minutes=60)

    image_path = save_temporary_file(UPLOADS_DIR, image_bytes, image.content_type)
    try:
        # The AI takes ~10–60 seconds: run it in a separate thread so the
        # backend keeps answering other requests meanwhile.
        new_image_path = await asyncio.to_thread(
            generate_new_angle, image_path, rotate_degrees, vertical_tilt
        )
    except SpaceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    finally:
        delete_file(image_path)   # privacy: never keep the upload

    return {"image_url": f"{request.base_url}outputs/{new_image_path.name}"}
