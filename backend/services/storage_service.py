"""
storage_service.py  —  WHERE garment images are stored.

Two options, chosen automatically:

    1. CLOUDINARY (if CLOUDINARY_URL is filled in backend/.env)
       The image is uploaded to your Cloudinary account and we keep its
       public https link, e.g.
           https://res.cloudinary.com/<cloud>/image/upload/v1730000000/ai-tryon/products/black-tshirt.jpg
       Advantages: works after deployment (servers often lose local files),
       fast worldwide delivery, and Genlook can download the garment
       straight from the link.

    2. LOCAL (if CLOUDINARY_URL is empty)
       The image is saved in backend/static/products/ on your computer.

Only GARMENT images are stored here. Customer photos are never stored in
the cloud (privacy) — they go straight to the try-on AI and are deleted.

How it connects:
    product_service.py calls save_garment_image() and delete_garment_image().
    Each product in products.json then has EITHER:
        "image": "black-tshirt.jpg"                          (local)
    OR:
        "image_url": "https://res.cloudinary.com/...",       (Cloudinary)
        "cloudinary_public_id": "ai-tryon/products/black-tshirt"

Cloudinary docs used:
    https://cloudinary.com/documentation/python_quickstart
    https://cloudinary.com/documentation/image_upload_api_reference_upload
"""

# The official Cloudinary library.
import cloudinary
import cloudinary.uploader

from config import CLOUDINARY_FOLDER, PRODUCT_IMAGES_DIR, is_cloudinary_configured
from services.file_service import EXTENSION_FOR_TYPE, delete_file


# The library reads CLOUDINARY_URL from the environment by itself
# (config.py already loaded .env). secure=True makes it return https links.
if is_cloudinary_configured():
    cloudinary.config(secure=True)


def using_cloudinary():
    """True if garment images go to Cloudinary, False if stored locally."""
    return is_cloudinary_configured()


# =====================================================================
# Saving
# =====================================================================
def save_garment_image(product_id, image_bytes, content_type):
    """
    Store a garment image and return a dictionary describing where it is.
    The dictionary is merged into the product in products.json.

    Cloudinary -> {"image_url": "...", "cloudinary_public_id": "..."}
    Local      -> {"image": "black-tshirt.jpg"}
    """
    if using_cloudinary():
        return upload_to_cloudinary(product_id, image_bytes)
    return save_to_local_folder(product_id, image_bytes, content_type)


def upload_to_cloudinary(product_id, image_bytes):
    """
    Upload the image to Cloudinary.

    public_id  -> the image's name in Cloudinary. We use the product id, so
                  uploading again for the same product REPLACES the old image
                  instead of creating a copy.
    overwrite  -> allow replacing an existing image with the same public_id.
    invalidate -> tell Cloudinary's servers to forget the old cached copy.
    asset_folder -> the folder shown in the Cloudinary Media Library.
    """
    public_id = f"{CLOUDINARY_FOLDER}/{product_id}"

    try:
        upload_result = cloudinary.uploader.upload(
            image_bytes,
            public_id=public_id,
            asset_folder=CLOUDINARY_FOLDER,
            overwrite=True,
            invalidate=True,
            resource_type="image",
        )
    except Exception as error:
        # Print the technical reason in the backend terminal for debugging,
        # and raise a simple message for the user.
        print(f"[storage_service] Cloudinary upload failed: {error}")
        raise StorageError(
            "Could not upload the image to Cloudinary. Check CLOUDINARY_URL in backend/.env."
        )

    # secure_url is the public https link. It contains a version number
    # (/v1730000000/), so browsers automatically show the NEW image after
    # a replacement.
    return {
        "image_url": upload_result["secure_url"],
        "cloudinary_public_id": upload_result["public_id"],
    }


def save_to_local_folder(product_id, image_bytes, content_type):
    """Save the image as backend/static/products/<product_id>.<ext>."""
    extension = EXTENSION_FOR_TYPE.get(content_type, ".jpg")
    file_name = product_id + extension
    with open(PRODUCT_IMAGES_DIR / file_name, "wb") as image_file:
        image_file.write(image_bytes)
    return {"image": file_name}


# =====================================================================
# Deleting
# =====================================================================
def delete_garment_image(product):
    """
    Delete a product's image from wherever it is stored.
    Never crashes: a failed delete only prints a warning.
    """
    public_id = product.get("cloudinary_public_id")
    if public_id:
        delete_from_cloudinary(public_id)

    local_file_name = product.get("image")
    if local_file_name:
        delete_file(PRODUCT_IMAGES_DIR / local_file_name)


def delete_from_cloudinary(public_id):
    """Delete one image from Cloudinary by its public_id."""
    if not using_cloudinary():
        print(f"[storage_service] Cloudinary not configured; could not delete {public_id}.")
        return
    try:
        cloudinary.uploader.destroy(public_id, invalidate=True)
    except Exception as error:
        print(f"[storage_service] Cloudinary delete failed for {public_id}: {error}")


class StorageError(Exception):
    """Raised when an image cannot be stored. The message is user-friendly."""
