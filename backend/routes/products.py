"""
routes/products.py  —  catalog endpoints.

    GET    /products                 -> list all products (used by the shop pages)
    POST   /products                 -> add a new product with an image
    PUT    /products/{id}/image      -> upload / replace a product's image
    DELETE /products/{id}            -> delete a product and its image

The last three are used by the "Manage Products" page in the frontend.

SECURITY NOTE (important before deploying!):
    Phase 1 has no login system, so ANYONE who can open the website could
    use the three "change" endpoints. That is fine on your own computer.
    Before putting the site online, set ALLOW_PRODUCT_MANAGEMENT=false in
    backend/.env (the endpoints then refuse all changes).
    TODO (Phase 2): protect these endpoints with a proper admin login.

How it connects:
    main.py "includes" this router. All reading/writing of products.json
    happens in services/product_service.py.
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

# An APIRouter is a small group of endpoints. main.py plugs it into the app.
router = APIRouter()


# =====================================================================
# Helpers
# =====================================================================
def prepare_for_frontend(product, backend_address):
    """
    Add two extra fields the frontend needs:
      image_url       -> full web address of the picture
      image_available -> False if the image file is missing (show a placeholder)
    """
    product_copy = dict(product)
    product_copy["image_available"] = product_image_exists(product)
    product_copy["image_url"] = None

    # Case 1: the image is online (e.g. Cloudinary) -> use that link directly.
    online_url = get_online_image_url(product)
    if online_url:
        product_copy["image_url"] = online_url

    # Case 2: the image is a local file in backend/static/products/.
    elif product_copy["image_available"]:
        # FastAPI serves the "static" folder (see main.py), so
        # static/products/black-tshirt.jpg is reachable at
        # http://127.0.0.1:8000/static/products/black-tshirt.jpg
        #
        # "?v=<number>" changes whenever the file changes. Without it the
        # browser might keep showing an OLD cached picture after you
        # upload a new one with the same file name.
        file_version = int(get_product_image_path(product).stat().st_mtime)
        product_copy["image_url"] = (
            f"{backend_address}static/products/{product['image']}?v={file_version}"
        )

    return product_copy


def check_management_allowed():
    """Stop the request if product management is switched off in .env."""
    if not ALLOW_PRODUCT_MANAGEMENT:
        raise HTTPException(
            status_code=403,
            detail="Product management is disabled on this server.",
        )


async def read_and_validate_image(image):
    """Read an uploaded garment image and check type/size. Returns the bytes."""
    if image is None:
        raise HTTPException(status_code=400, detail="Please choose an image file.")

    image_bytes = await image.read()
    try:
        validate_image(image.content_type, image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return image_bytes


# =====================================================================
# Endpoints
# =====================================================================
@router.get("/products")
def get_products(request: Request):
    """Return the full clothing catalog."""
    # request.base_url is the backend's own address, e.g. "http://127.0.0.1:8000/"
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
    """Add a new product. The form must include a name, category, price and image."""
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
    """Upload (or replace) the garment image of an existing product."""
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
    """Delete a product and its image file."""
    check_management_allowed()

    was_deleted = delete_product(product_id)
    if not was_deleted:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"deleted": product_id}
