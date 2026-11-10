"""
Catalog endpoints: list, add, replace image, delete.

The change endpoints have no login in Phase 1, so set
ALLOW_PRODUCT_MANAGEMENT=false on the live site.
TODO (Phase 2): protect them with a proper admin login.
"""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config import ALLOW_PRODUCT_MANAGEMENT
from services.file_service import InvalidImageError, validate_image
from services.product_service import (
    add_product,
    delete_product,
    get_online_image_url,
    get_product_image_path,
    load_all_products,
    product_image_exists,
    replace_product_image,
)
from services.storage_service import StorageError

router = APIRouter()


def prepare_for_frontend(product, backend_address):
    """Add image_url (full address) and image_available for the frontend."""
    product_copy = dict(product)
    product_copy["image_available"] = product_image_exists(product)
    product_copy["image_url"] = None

    online_url = get_online_image_url(product)
    if online_url:
        product_copy["image_url"] = online_url
    elif product_copy["image_available"]:
        # "?v=" changes when the file changes, so browsers don't show a cached old image.
        file_version = int(get_product_image_path(product).stat().st_mtime)
        product_copy["image_url"] = (
            f"{backend_address}static/products/{product['image']}?v={file_version}"
        )

    return product_copy


def check_management_allowed():
    if not ALLOW_PRODUCT_MANAGEMENT:
        raise HTTPException(
            status_code=403,
            detail="Product management is disabled on this server.",
        )


async def read_and_validate_image(image):
    """Read an uploaded garment image, check it and return its bytes."""
    if image is None:
        raise HTTPException(status_code=400, detail="Please choose an image file.")

    image_bytes = await image.read()
    try:
        validate_image(image.content_type, image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return image_bytes


@router.get("/products")
def get_products(request: Request):
    backend_address = str(request.base_url)

    products_for_frontend = []
    for product in load_all_products():
        products_for_frontend.append(prepare_for_frontend(product, backend_address))
    return products_for_frontend


@router.post("/products")
async def create_product(
    request: Request,
    name: str = Form(""),
    category: str = Form(""),
    price: float = Form(0),
    description: str = Form(""),
    image: UploadFile = File(None),
):
    check_management_allowed()

    name = name.strip()
    category = category.strip()
    if name == "":
        raise HTTPException(status_code=400, detail="Please enter a product name.")
    if category == "":
        raise HTTPException(status_code=400, detail="Please enter a category.")
    if price < 0:
        raise HTTPException(status_code=400, detail="The price cannot be negative.")

    image_bytes = await read_and_validate_image(image)

    try:
        new_product = add_product(
            name=name,
            category=category,
            price=round(price, 2),
            description=description.strip(),
            image_bytes=image_bytes,
            content_type=image.content_type,
        )
    except StorageError as error:
        raise HTTPException(status_code=502, detail=str(error))

    return prepare_for_frontend(new_product, str(request.base_url))


@router.put("/products/{product_id}/image")
async def upload_product_image(product_id: str, request: Request, image: UploadFile = File(None)):
    check_management_allowed()

    image_bytes = await read_and_validate_image(image)
    try:
        updated_product = replace_product_image(product_id, image_bytes, image.content_type)
    except StorageError as error:
        raise HTTPException(status_code=502, detail=str(error))

    if updated_product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return prepare_for_frontend(updated_product, str(request.base_url))


@router.delete("/products/{product_id}")
def remove_product(product_id: str):
    check_management_allowed()

    was_deleted = delete_product(product_id)
    if not was_deleted:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"deleted": product_id}
