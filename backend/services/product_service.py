"""
product_service.py  —  reads and changes the clothing catalog (data/products.json).

Why this file exists:
    Several endpoints need product data:
      - GET /products              (show the catalog)
      - POST /tryon                (find the garment image the user picked)
      - the "Manage Products" endpoints (add / delete products, upload images)
    Keeping all catalog code here means the routes stay short and simple.

Where things are stored:
    - Product details  -> backend/data/products.json
    - Garment images   -> Cloudinary OR backend/static/products/
                          (decided by services/storage_service.py)

A product's image can be described in two ways in products.json:
    "image": "black-tshirt.jpg"              -> a file in static/products/
    "image_url": "https://res.cloudinary..." -> a public link (e.g. Cloudinary)
You can also paste an "image_url" by hand (see README / the guide).
"""

import json
import re

from config import PRODUCTS_FILE, PRODUCT_IMAGES_DIR
from services.storage_service import delete_garment_image, save_garment_image


# The keys that describe where a product's image is stored.
IMAGE_KEYS = ["image", "image_url", "cloudinary_public_id"]


# =====================================================================
# Reading
# =====================================================================
def load_all_products():
    """
    Read data/products.json and return it as a Python list of dictionaries.

    We read the file every time (instead of once at startup) so that changes
    appear immediately without restarting the server.
    """
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as products_file:
        products = json.load(products_file)
    return products


def find_product_by_id(product_id):
    """
    Return the one product whose "id" matches product_id.
    Return None if no product has that id.
    """
    all_products = load_all_products()
    for product in all_products:
        if product["id"] == product_id:
            return product
    return None


def get_online_image_url(product):
    """
    Return the product's public image link (e.g. Cloudinary), or None if
    the image is stored locally instead.
    """
    image_url = product.get("image_url", "")
    if image_url.startswith("https://") or image_url.startswith("http://"):
        return image_url
    return None


def get_product_image_path(product):
    """
    Return the full path on disk of a LOCAL product image,
    e.g.  E:/.../backend/static/products/black-tshirt.jpg
    """
    return PRODUCT_IMAGES_DIR / product["image"]


def product_image_exists(product):
    """Return True if the product has a usable image (online link or local file)."""
    if get_online_image_url(product):
        return True
    if not product.get("image"):
        return False
    return get_product_image_path(product).is_file()


# =====================================================================
# Changing the catalog (used by the "Manage Products" page)
# =====================================================================
def save_all_products(products):
    """
    Write the full product list back to data/products.json.
    indent=2 keeps the file nicely formatted, so you can still edit it by hand.
    """
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as products_file:
        json.dump(products, products_file, indent=2, ensure_ascii=False)


def make_product_id(name, existing_products):
    """
    Turn a product name into a unique, web-safe id.
        "Red Summer Dress!"  ->  "red-summer-dress"
    If that id is already used, a number is added: "red-summer-dress-2".
    """
    # Lower-case, then replace every group of non-letters/numbers with "-".
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
    """
    Replace the image keys of `product` with the new `image_info`
    (returned by storage_service.save_garment_image).
    """
    for key in IMAGE_KEYS:
        product.pop(key, None)
    product.update(image_info)


def add_product(name, category, price, description, image_bytes, content_type):
    """Create a new product with its image. Returns the new product."""
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
    """
    Upload a new image for an existing product.
    Returns the updated product, or None if the product doesn't exist.
    """
    products = load_all_products()

    for product in products:
        if product["id"] != product_id:
            continue

        # Remember where the OLD image was, before we change anything.
        old_image = {}
        for key in IMAGE_KEYS:
            if product.get(key):
                old_image[key] = product[key]

        new_image_info = save_garment_image(product_id, image_bytes, content_type)
        set_image_info(product, new_image_info)
        save_all_products(products)

        # Clean up the old image, unless the new one replaced it in place
        # (same local file name, or same Cloudinary public_id).
        if old_image.get("image") == new_image_info.get("image"):
            old_image.pop("image", None)
        if old_image.get("cloudinary_public_id") == new_image_info.get("cloudinary_public_id"):
            old_image.pop("cloudinary_public_id", None)
        delete_garment_image(old_image)

        return product

    return None


def delete_product(product_id):
    """
    Remove a product and its image.
    Returns True if it was deleted, False if it didn't exist.
    """
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
