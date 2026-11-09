"""
routes/model3d.py  —  the "turn my result into a 3D model" endpoint.

    POST /model3d   (form field "image": the image to turn into 3D)

The frontend sends the try-on RESULT image (rotated, if the user rotated
it). We save it for a moment, ask services/model3d_service.py to build a
3D model, and return the address of the .glb file.

Returns:
    {"model_url": "http://127.0.0.1:8000/outputs/abc123.glb"}
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
    """Create a rotatable 3D model (.glb) from one image."""
    if image is None:
        raise HTTPException(status_code=400, detail="Please send an image.")

    image_bytes = await image.read()
    try:
        validate_image(image.content_type, image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    # Remove generated files older than 60 minutes (images AND .glb models).
    delete_old_files(OUTPUTS_DIR, max_age_minutes=60)

    image_path = save_temporary_file(UPLOADS_DIR, image_bytes, image.content_type)
    try:
        # 3D generation takes minutes: run it in a separate thread so the
        # backend can keep answering other requests meanwhile.
        glb_path = await asyncio.to_thread(generate_3d_model, image_path)
    except Model3DError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    finally:
        # Never keep the uploaded image longer than needed (privacy).
        delete_file(image_path)

    return {"model_url": f"{request.base_url}outputs/{glb_path.name}"}
