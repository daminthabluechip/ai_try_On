"""
Reads and changes the catalog in data/products.json.

A product's image is either "image": "<file in static/products/>"
or "image_url": "<public link, e.g. Cloudinary>".
"""

import json
import re

from config import PRODUCTS_FILE, PRODUCT_IMAGES_DIR
from services.storage_service import delete_garment_image, save_garment_image


IMAGE_KEYS = ["image", "image_url", "cloudinary_public_id"]


# Read on every call, so manual edits to products.json apply without a restart.
def load_all_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as products_file:
        products = json.load(products_file)
    return products


def find_product_by_id(product_id):
    """Return the product with this id, or None."""
    all_products = load_all_products()
    for product in all_products:
        if product["id"] == product_id:
            return product
    return None


def get_online_image_url(product):
    """Return the product's public image link, or None if the image is local."""
    image_url = product.get("image_url", "")
    if image_url.startswith("https://") or image_url.startswith("http://"):
        return image_url
    return None


def get_product_image_path(product):
    return PRODUCT_IMAGES_DIR / product["image"]


def product_image_exists(product):
    """True if the product has an online link or an existing local file."""
    if get_online_image_url(product):
        return True
    if not product.get("image"):
        return False
    return get_product_image_path(product).is_file()


def save_all_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as products_file:
        json.dump(products, products_file, indent=2, ensure_ascii=False)


def make_product_id(name, existing_products):
    """"Red Summer Dress!" -> "red-summer-dress" (adds -2, -3... if taken)."""
    base_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if base_id == "":
        base_id = "product"

    used_ids = []
    for product in existing_products:
        used_ids.append(product["id"])

    new_id = base_id
    counter = 2
    while new_id in used_ids:
        new_id = f"{base_id}-{counter}"
        counter = counter + 1
    return new_id


def set_image_info(product, image_info):
    """Replace the product's image keys with image_info from storage_service."""
    for key in IMAGE_KEYS:
        product.pop(key, None)
    product.update(image_info)


def add_product(name, category, price, description, image_bytes, content_type):
    products = load_all_products()
    product_id = make_product_id(name, products)

    # Store the image first: if that fails, nothing is added to the catalog.
    image_info = save_garment_image(product_id, image_bytes, content_type)

    new_product = {
        "id": product_id,
        "name": name,
        "category": category,
        "price": price,
        "description": description,
    }
    set_image_info(new_product, image_info)

    products.append(new_product)
    save_all_products(products)
    return new_product


def replace_product_image(product_id, image_bytes, content_type):
    """Returns the updated product, or None if it doesn't exist."""
    products = load_all_products()

    for product in products:
        if product["id"] != product_id:
            continue

        old_image = {}
        for key in IMAGE_KEYS:
            if product.get(key):
                old_image[key] = product[key]

        new_image_info = save_garment_image(product_id, image_bytes, content_type)
        set_image_info(product, new_image_info)
        save_all_products(products)

        # Delete the old image, unless the new one overwrote it in place.
        if old_image.get("image") == new_image_info.get("image"):
            old_image.pop("image", None)
        if old_image.get("cloudinary_public_id") == new_image_info.get("cloudinary_public_id"):
            old_image.pop("cloudinary_public_id", None)
        delete_garment_image(old_image)

        return product

    return None


def delete_product(product_id):
    """Returns True if deleted, False if it didn't exist."""
    products = load_all_products()
    remaining_products = []
    deleted_product = None

    for product in products:
        if product["id"] == product_id:
            deleted_product = product
        else:
            remaining_products.append(product)

    if deleted_product is None:
        return False

    save_all_products(remaining_products)
    delete_garment_image(deleted_product)
    return True
