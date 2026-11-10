"""
Stores garment images on Cloudinary (if CLOUDINARY_URL is set) or in static/products/.
Customer photos are never stored here.
"""

import cloudinary
import cloudinary.uploader

from config import CLOUDINARY_FOLDER, PRODUCT_IMAGES_DIR, is_cloudinary_configured
from services.file_service import EXTENSION_FOR_TYPE, delete_file


# Reads CLOUDINARY_URL from the environment; secure=True returns https links.
if is_cloudinary_configured():
    cloudinary.config(secure=True)


def using_cloudinary():
    """True if garment images go to Cloudinary, False if stored locally."""
    return is_cloudinary_configured()


def save_garment_image(product_id, image_bytes, content_type):
    """Store a garment image and return a dictionary describing where it is."""
    if using_cloudinary():
        return upload_to_cloudinary(product_id, image_bytes)
    return save_to_local_folder(product_id, image_bytes, content_type)


def upload_to_cloudinary(product_id, image_bytes):
    """Upload the image to Cloudinary."""
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
        print(f"[storage_service] Cloudinary upload failed: {error}")
        raise StorageError(
            "Could not upload the image to Cloudinary. Check CLOUDINARY_URL in backend/.env."
        )

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


def delete_garment_image(product):
    """Delete a product's image from wherever it is stored."""
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
