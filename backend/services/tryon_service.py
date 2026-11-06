"""
tryon_service.py  —  the ONLY file that talks to the virtual try-on provider.

Current provider: Genlook Try-On API
Official docs:    https://genlook.app/docs/tryon-api/introduction

Why keep this in one file?
    If you switch provider later (e.g. FASHN), you rewrite only this file.
    The rest of the app just calls:

        result_path = generate_tryon(person_image_path, product)

    and gets back the path of the generated image saved in outputs/.

How a Genlook try-on works (3 stages):
    1. START   POST /try-on            -> send person photo + garment image,
                                          Genlook answers with a "generationId".
    2. WAIT    GET /generations/{id}   -> ask "is it done?" every few seconds
                                          (called polling) until the status is
                                          COMPLETED or FAILED (usually ~10 s).
    3. SAVE    download resultImageUrl -> the URL is temporary, so we save the
                                          image into backend/outputs/ right away.
"""

import json
import time
import uuid

# httpx sends HTTP requests from Python (like a browser, but in code).
import httpx

from config import (
    OUTPUTS_DIR,
    TRYON_API_KEY,
    TRYON_API_URL,
    TRYON_MOCK_MODE,
    is_api_key_configured,
)
from services.product_service import get_online_image_url, get_product_image_path


# ---------------------------------------------------------------------
# Settings for talking to the provider
# ---------------------------------------------------------------------
# How long to wait for a single HTTP request before giving up (seconds).
REQUEST_TIMEOUT_SECONDS = 30

# How often to ask "is it done yet?" while polling (seconds).
# Genlook's docs suggest about once per second; 2 s is gentler on rate limits.
POLL_INTERVAL_SECONDS = 2

# The maximum total time we wait for the AI to finish (seconds).
# TODO: Increase this if you often see "took too long" errors.
MAX_WAIT_SECONDS = 120

# Friendly messages for the most common Genlook error codes.
# (Codes taken from https://genlook.app/docs/tryon-api/errors)
FRIENDLY_ERROR_MESSAGES = {
    "MISSING_API_KEY": "The AI service API key is missing. Check backend/.env.",
    "INVALID_API_KEY": "The AI service rejected the API key. Check backend/.env.",
    "INSUFFICIENT_CREDITS": "The AI service has no credits left. Top up your Genlook account or turn on mock mode.",
    "QUOTA_EXCEEDED": "The AI service quota is reached. Please try again later.",
    "RATE_LIMITED": "Too many requests to the AI service. Please wait a moment and try again.",
    "INVALID_IMAGE": "The AI service could not use one of the images (your photo or the garment image).",
    "UNSUPPORTED_IMAGE_TYPE": "This image format is not supported. Please use JPEG, PNG or WebP.",
    "FILE_TOO_LARGE": "The image is too large for the AI service (max 10 MB).",
    "CONTENT_POLICY_VIOLATION": "This product cannot be used for try-on.",
    "PRODUCT_IMAGE_FETCH_FAILED": "The AI service could not download the garment image. Check the product's image link.",
    "GENERATION_FAILED": "The AI could not generate a try-on for this photo. Try a clearer, front-facing photo.",
    "GENERATION_TIMEOUT": "The AI took too long. Please try again.",
}


class TryOnError(Exception):
    """
    Raised whenever the try-on cannot be completed.

    message     -> a friendly sentence that can be shown to the user
    status_code -> the HTTP status code our backend should send back
    """

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# =====================================================================
# MAIN FUNCTION — the rest of the app only calls this one
# =====================================================================
def generate_tryon(person_image_path, product):
    """
    Put `product` on the person in `person_image_path`.

    person_image_path -> path of the user's photo (saved in uploads/)
    product           -> one product dictionary from products.json

    Returns the path of the generated image saved in outputs/.
    Raises TryOnError if anything goes wrong.
    """
    if not is_api_key_configured():
        raise TryOnError(
            "The AI service is not configured. Add your API key to backend/.env "
            "(VIRTUAL_TRYON_API_KEY) and restart the backend.",
            status_code=500,
        )

    # One httpx "Client" re-uses the same connection for all our requests.
    # The x-api-key header is how Genlook knows the request comes from you.
    headers = {"x-api-key": TRYON_API_KEY}

    with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        generation_id = start_generation(client, person_image_path, product)
        result_image_url = wait_for_result(client, generation_id)
        output_path = download_result(client, result_image_url)

    return output_path


# =====================================================================
# Stage 1: START the try-on
# =====================================================================
def build_request_data(product):
    """
    Build the JSON description of the try-on request, following the
    Genlook "Create Try-On" docs.

    Two ways to give Genlook an image:
      {"url": "https://..."}  -> Genlook downloads it from that public link
                                 (used for Cloudinary garment images)
      {"fileKey": "product"}  -> the image is attached to this same request
                                 as a file (used for local garment images
                                 and always for the customer photo)
    """
    online_garment_url = get_online_image_url(product)
    if online_garment_url:
        garment_source = {"url": online_garment_url}
    else:
        garment_source = {"fileKey": "product"}

    request_data = {
        "products": [
            {
                # externalId lets Genlook remember this product, so the
                # next try-on of the same product is faster.
                "externalId": "catalog-" + product["id"],
                "title": product["name"],
                "description": product.get("description", ""),
                "images": [
                    {"source": garment_source},
                ],
            }
        ],
        "person": {
            "image": {"source": {"fileKey": "person"}},
        },
        # mock = True -> free test mode: Genlook returns the photo unchanged.
        "mock": TRYON_MOCK_MODE,
    }
    return request_data


def start_generation(client, person_image_path, product):
    """
    Send the person photo + garment image to Genlook.
    Returns the generationId that Genlook gives back.
    """
    request_data = build_request_data(product)
    form_fields = {"data": json.dumps(request_data)}

    # We send a "multipart/form-data" request: one text field called "data"
    # (our JSON) plus the image file(s).
    if get_online_image_url(product):
        # Garment is online (Cloudinary): only the person photo is attached.
        with open(person_image_path, "rb") as person_file:
            files = {"person": (person_image_path.name, person_file)}
            response = send_request(client, "POST", "/try-on", data=form_fields, files=files)
    else:
        # Garment is a local file: attach it too.
        garment_image_path = get_local_garment_path(product)
        with open(person_image_path, "rb") as person_file, open(garment_image_path, "rb") as garment_file:
            files = {
                "person": (person_image_path.name, person_file),
                "product": (garment_image_path.name, garment_file),
            }
            response = send_request(client, "POST", "/try-on", data=form_fields, files=files)

    response_json = response.json()
    return response_json["generationId"]


def get_local_garment_path(product):
    """Return the local garment image path, or raise a clear error if it's missing."""
    if not product.get("image"):
        raise TryOnError(f"'{product['name']}' has no garment image yet.", status_code=500)

    garment_image_path = get_product_image_path(product)
    if not garment_image_path.is_file():
        raise TryOnError(
            f"The garment image for '{product['name']}' is missing on the server "
            f"(expected backend/static/products/{product['image']}).",
            status_code=500,
        )
    return garment_image_path


# =====================================================================
# Stage 2: WAIT for the result (polling)
# =====================================================================
def wait_for_result(client, generation_id):
    """
    Ask Genlook every POLL_INTERVAL_SECONDS whether the try-on is ready.
    Returns the temporary URL of the finished image.
    """
    started_at = time.time()

    while True:
        response = send_request(client, "GET", f"/generations/{generation_id}")
        generation = response.json()
        status = generation.get("status")

        if status == "COMPLETED":
            return generation["resultImageUrl"]

        if status == "FAILED":
            error_code = generation.get("errorCode", "GENERATION_FAILED")
            message = get_friendly_message(error_code)
            if generation.get("errorMessage"):
                message = f"{message} (Details: {generation['errorMessage']})"
            print(f"[tryon_service] Generation failed: {error_code} {generation.get('errorMessage', '')}")
            raise TryOnError(message, status_code=502)

        # Still PENDING or PROCESSING. Have we waited too long?
        seconds_waited = time.time() - started_at
        if seconds_waited > MAX_WAIT_SECONDS:
            raise TryOnError(
                "The AI took too long to respond. Please try again.",
                status_code=504,
            )

        time.sleep(POLL_INTERVAL_SECONDS)


# =====================================================================
# Stage 3: SAVE the result
# =====================================================================
def download_result(client, result_image_url):
    """
    Download the finished image and save it in outputs/ with a random name.
    Returns the saved file's path.
    """
    try:
        # The result URL is a public, temporary link — the API key is not
        # needed, so we use a plain httpx.get instead of our client.
        response = httpx.get(result_image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError:
        raise TryOnError("The generated image could not be downloaded. Please try again.")

    # Pick the file extension from the type the server reports.
    content_type = response.headers.get("content-type", "")
    if "png" in content_type:
        extension = ".png"
    elif "webp" in content_type:
        extension = ".webp"
    else:
        extension = ".jpg"

    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + extension)
    with open(output_path, "wb") as output_file:
        output_file.write(response.content)

    return output_path


# =====================================================================
# Helpers
# =====================================================================
def send_request(client, method, path, **request_options):
    """
    Send one request to the provider and handle network/API errors.

    method          -> "GET" or "POST"
    path            -> the part after the base URL, e.g. "/try-on"
    request_options -> extra things to send (form fields, files, ...)

    Returns the response if it succeeded; raises TryOnError otherwise.
    """
    full_url = TRYON_API_URL + path

    try:
        response = client.request(method, full_url, **request_options)
    except httpx.TimeoutException:
        raise TryOnError("The AI service did not respond in time. Please try again.", status_code=504)
    except httpx.RequestError:
        raise TryOnError("Could not reach the AI service. Check your internet connection.")

    # Status codes 200-299 mean success.
    if response.is_success:
        return response

    # Genlook errors look like: {"code": "...", "message": "...", "status": 400}
    error_code, provider_message = read_error_details(response)

    # Print the details in the backend terminal to help you debug.
    # (We never print the API key.)
    print(f"[tryon_service] Provider error {response.status_code} {error_code}: {response.text[:300]}")

    # Show our friendly sentence PLUS the provider's own reason, because the
    # reason is often the most useful part (e.g. "Image resolution is too low").
    message = get_friendly_message(error_code)
    if provider_message:
        message = f"{message} (Details: {provider_message})"
    raise TryOnError(message, status_code=502)


def read_error_details(response):
    """
    Return (error_code, provider_message) from a provider error response.
    If the body isn't JSON, returns ("UNKNOWN", "").
    """
    try:
        error_body = response.json()
    except ValueError:
        return "UNKNOWN", ""
    return error_body.get("code", "UNKNOWN"), error_body.get("message", "")


def get_friendly_message(error_code):
    """Turn a provider error code into a sentence a user understands."""
    default_message = "The AI service returned an error. Please try again later."
    return FRIENDLY_ERROR_MESSAGES.get(error_code, default_message)
