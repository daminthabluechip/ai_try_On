"""
POST /tryon: put a catalog garment on the uploaded person photo.
"""

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config import OUTPUTS_DIR, UPLOADS_DIR, TRYON_MOCK_MODE
from services.file_service import (
    InvalidImageError,
    delete_file,
    delete_old_files,
    save_temporary_file,
    validate_image,
)
from services.product_service import find_product_by_id
from services.tryon_service import TryOnError, generate_tryon

router = APIRouter()

# TODO: Change this if users need more time to download their result.
KEEP_RESULTS_FOR_MINUTES = 60


@router.post("/tryon")
async def create_tryon(
    request: Request,
    person_image: UploadFile = File(None),
    product_id: str = Form(None),
):
    """
    Generate a virtual try-on image.
    Fields default to None so we can return our own friendly error messages.
    """
    if person_image is None:
        raise HTTPException(status_code=400, detail="Please upload a photo of yourself.")

    if product_id is None or product_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a clothing item.")

    product = find_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="The selected product does not exist.")

    file_bytes = await person_image.read()
    try:
        validate_image(person_image.content_type, file_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    delete_old_files(OUTPUTS_DIR, KEEP_RESULTS_FOR_MINUTES)

    person_image_path = None
    try:
        person_image_path = save_temporary_file(UPLOADS_DIR, file_bytes, person_image.content_type)
        # Runs in a thread so the server stays responsive while the AI works.
        output_path = await asyncio.to_thread(generate_tryon, person_image_path, product)
    except TryOnError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    finally:
        # Never keep the customer's photo (privacy).
        delete_file(person_image_path)

    result_url = str(request.base_url) + "outputs/" + output_path.name

    return {
        "result_url": result_url,
        "product_id": product["id"],
        "product_name": product["name"],
        "mock_mode": TRYON_MOCK_MODE,
    }
