"""
POST /model3d: turn one image into a rotatable 3D model (.glb).
"""

import asyncio

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from config import OUTPUTS_DIR, UPLOADS_DIR
from services.file_service import (
    InvalidImageError,
    delete_file,
    delete_old_files,
    save_temporary_file,
    validate_image,
)
from services.model3d_service import Model3DError, generate_3d_model

router = APIRouter()


@router.post("/model3d")
async def create_3d_model(request: Request, image: UploadFile = File(None)):
    """Create a 3D model from one image. Returns {"model_url": ...}."""
    if image is None:
        raise HTTPException(status_code=400, detail="Please send an image.")

    image_bytes = await image.read()
    try:
        validate_image(image.content_type, image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    delete_old_files(OUTPUTS_DIR, max_age_minutes=60)

    image_path = save_temporary_file(UPLOADS_DIR, image_bytes, image.content_type)
    try:
        # Takes minutes: run in a thread so the server stays responsive.
        glb_path = await asyncio.to_thread(generate_3d_model, image_path)
    except Model3DError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    finally:
        delete_file(image_path)

    return {"model_url": f"{request.base_url}outputs/{glb_path.name}"}
