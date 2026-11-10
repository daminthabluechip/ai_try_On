"""
The only file that talks to the Genlook Try-On API
(https://genlook.app/docs/tryon-api/introduction).

Flow: POST /try-on -> poll GET /generations/{id} -> download the result.
"""

import json
import time
import uuid

import httpx

from config import (
    OUTPUTS_DIR,
    TRYON_API_KEY,
    TRYON_API_URL,
    TRYON_MOCK_MODE,
    is_api_key_configured,
)
from services.product_service import get_online_image_url, get_product_image_path


REQUEST_TIMEOUT_SECONDS = 30

# Genlook suggests ~1 s; 2 s is gentler on rate limits.
POLL_INTERVAL_SECONDS = 2

# TODO: Increase this if you often see "took too long" errors.
MAX_WAIT_SECONDS = 120

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
    """Raised whenever the try-on cannot be completed."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def generate_tryon(person_image_path, product):
    """Put `product` on the person in `person_image_path`."""
    if not is_api_key_configured():
        raise TryOnError(
            "The AI service is not configured. Add your API key to backend/.env "
            "(VIRTUAL_TRYON_API_KEY) and restart the backend.",
            status_code=500,
        )

    headers = {"x-api-key": TRYON_API_KEY}

    with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        generation_id = start_generation(client, person_image_path, product)
        result_image_url = wait_for_result(client, generation_id)
        output_path = download_result(client, result_image_url)

    return output_path


def build_request_data(product):
    """Build the request JSON (Genlook "Create Try-On"). Online garments are sent by URL, local ones as a file."""
    online_garment_url = get_online_image_url(product)
    if online_garment_url:
        garment_source = {"url": online_garment_url}
    else:
        garment_source = {"fileKey": "product"}

    request_data = {
        "products": [
            {
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
        "mock": TRYON_MOCK_MODE,
    }
    return request_data


def start_generation(client, person_image_path, product):
    """Send the person photo + garment image to Genlook."""
    request_data = build_request_data(product)
    form_fields = {"data": json.dumps(request_data)}

    if get_online_image_url(product):
        with open(person_image_path, "rb") as person_file:
            files = {"person": (person_image_path.name, person_file)}
            response = send_request(client, "POST", "/try-on", data=form_fields, files=files)
    else:
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


def wait_for_result(client, generation_id):
    """Ask Genlook every POLL_INTERVAL_SECONDS whether the try-on is ready."""
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

        seconds_waited = time.time() - started_at
        if seconds_waited > MAX_WAIT_SECONDS:
            raise TryOnError(
                "The AI took too long to respond. Please try again.",
                status_code=504,
            )

        time.sleep(POLL_INTERVAL_SECONDS)


def download_result(client, result_image_url):
    """Download the finished image and save it in outputs/ with a random name."""
    try:
        response = httpx.get(result_image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError:
        raise TryOnError("The generated image could not be downloaded. Please try again.")

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


def send_request(client, method, path, **request_options):
    """Send one request to the provider and handle network/API errors."""
    full_url = TRYON_API_URL + path

    try:
        response = client.request(method, full_url, **request_options)
    except httpx.TimeoutException:
        raise TryOnError("The AI service did not respond in time. Please try again.", status_code=504)
    except httpx.RequestError:
        raise TryOnError("Could not reach the AI service. Check your internet connection.")

    if response.is_success:
        return response

    error_code, provider_message = read_error_details(response)

    print(f"[tryon_service] Provider error {response.status_code} {error_code}: {response.text[:300]}")

    message = get_friendly_message(error_code)
    if provider_message:
        message = f"{message} (Details: {provider_message})"
    raise TryOnError(message, status_code=502)


def read_error_details(response):
    """Return (error_code, provider_message) from a provider error response."""
    try:
        error_body = response.json()
    except ValueError:
        return "UNKNOWN", ""
    return error_body.get("code", "UNKNOWN"), error_body.get("message", "")


def get_friendly_message(error_code):
    """Turn a provider error code into a sentence a user understands."""
    default_message = "The AI service returned an error. Please try again later."
    return FRIENDLY_ERROR_MESSAGES.get(error_code, default_message)
