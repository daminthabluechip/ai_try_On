"""
routes/tryon.py  —  the POST /tryon endpoint.

How the images travel:
    1. The React app sends a "multipart/form-data" request containing:
         - person_image : the user's photo (a file)
         - product_id   : which product was chosen, e.g. "black-tshirt" (text)
    2. This endpoint checks the photo and looks up the product.
       (We take a product_id, not a garment image, so users can only try
       on products from YOUR catalog.)
    3. tryon_service.py sends both images to the AI and saves the result
       in backend/outputs/.
    4. We reply with JSON containing "result_url": the web address of the
       generated image, which the React app shows with <img src=...>.
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

# Generated images are deleted after this many minutes (privacy).
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

    "File(None)" / "Form(None)" make the fields optional for FastAPI, so
    that WE can send a clear message when one is missing (instead of
    FastAPI's technical error).
    """
    # --- 1. Check the inputs ------------------------------------------
    if person_image is None:
        raise HTTPException(status_code=400, detail="Please upload a photo of yourself.")

    if product_id is None or product_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a clothing item.")

    product = find_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="The selected product does not exist.")

    # Read the uploaded file into memory and check it.
    file_bytes = await person_image.read()
    try:
        validate_image(person_image.content_type, file_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    # Remove generated images older than KEEP_RESULTS_FOR_MINUTES.
    delete_old_files(OUTPUTS_DIR, KEEP_RESULTS_FOR_MINUTES)

    # --- 2. Save the photo temporarily and call the AI ------------------
    person_image_path = None
    try:
        person_image_path = save_temporary_file(UPLOADS_DIR, file_bytes, person_image.content_type)

        # generate_tryon waits ~10 seconds for the AI. asyncio.to_thread runs
        # it in the background so the server can still answer other requests.
        output_path = await asyncio.to_thread(generate_tryon, person_image_path, product)

    except TryOnError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)

    finally:
        # "finally" ALWAYS runs — success or error — so the user's
        # uploaded photo is always deleted from our server.
        delete_file(person_image_path)

    # --- 3. Reply with the result's web address -------------------------
    # main.py serves the outputs folder at /outputs/...
    result_url = str(request.base_url) + "outputs/" + output_path.name

    return {
        "result_url": result_url,
        "product_id": product["id"],
        "product_name": product["name"],
        "mock_mode": TRYON_MOCK_MODE,
    }
