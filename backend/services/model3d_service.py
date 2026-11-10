"""
Turns one image into a 3D model (.glb). Engine chosen with MODEL3D_ENGINE:
  triposr (default) - TripoSR in a free Hugging Face CPU Space
  flask             - TripoSR on our own server (triposr_server/app.py)
  hunyuan           - Hunyuan3D-2.1 in a Hugging Face Space (daily GPU quota)
Both Spaces remove the image background themselves.
"""

import shutil
import uuid

import httpx
from gradio_client import handle_file

from config import MODEL3D_ENGINE, MODEL3D_SPACE, OUTPUTS_DIR, TRIPOSR_API_URL, TRIPOSR_SPACE
from services.hf_space_helpers import (
    SpaceError,
    connect_to_space,
    get_friendly_message,
    prepare_image,
    read_file_path,
)

Model3DError = SpaceError


TRIPOSR_RESOLUTION = 256
TRIPOSR_FOREGROUND_RATIO = 0.85

HUNYUAN_STEPS = 5
HUNYUAN_OCTREE_RESOLUTION = 256


def generate_3d_model(image_path):
    """Turn the image at `image_path` into a 3D model."""
    small_image_path = prepare_image(image_path)
    try:
        if MODEL3D_ENGINE == "flask":
            return generate_with_flask_server(small_image_path)
        if MODEL3D_ENGINE == "hunyuan":
            glb_temp_path = generate_with_hunyuan(small_image_path)
        else:
            glb_temp_path = generate_with_triposr(small_image_path)
    finally:
        small_image_path.unlink(missing_ok=True)

    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + ".glb")
    shutil.move(glb_temp_path, output_path)
    return output_path


def generate_with_triposr(image_path):
    """/preprocess (remove background) then /generate. Values are passed by position because Space copies name them differently."""
    client = connect_to_space(TRIPOSR_SPACE)

    try:
        cleaned_image = client.predict(
            handle_file(str(image_path)),
            True,
            TRIPOSR_FOREGROUND_RATIO,
            api_name="/preprocess",
        )
        cleaned_image_path = read_file_path(cleaned_image)

        # Some Space copies return (.obj, .glb), others only .glb: take the last item.
        result = client.predict(
            handle_file(cleaned_image_path),
            TRIPOSR_RESOLUTION,
            api_name="/generate",
        )
    except Exception as error:
        print(f"[model3d_service] TripoSR error: {type(error).__name__}: {error}")
        raise Model3DError(get_friendly_message(str(error)))

    if isinstance(result, (list, tuple)):
        result = result[-1]
    return check_glb(read_file_path(result), result)


FLASK_TIMEOUT_SECONDS = 600


def generate_with_flask_server(image_path):
    """POST the image to our Flask server and save the returned .glb in outputs/."""
    try:
        with open(image_path, "rb") as image_file:
            response = httpx.post(
                f"{TRIPOSR_API_URL}/generate",
                files={"image": (image_path.name, image_file, "image/jpeg")},
                timeout=FLASK_TIMEOUT_SECONDS,
            )
    except httpx.TimeoutException:
        raise Model3DError("The TripoSR server took too long. Please try again.", status_code=504)
    except httpx.RequestError:
        raise Model3DError(
            f"The TripoSR server is not running at {TRIPOSR_API_URL}. "
            "Start it with: python app.py (in the triposr_server folder).",
            status_code=503,
        )

    if not response.is_success:
        try:
            reason = response.json().get("detail", "")
        except ValueError:
            reason = response.text[:200]
        print(f"[model3d_service] TripoSR server error {response.status_code}: {reason}")
        status_code = 400 if response.status_code == 400 else 502
        raise Model3DError(f"The TripoSR server could not build the model. ({reason})", status_code=status_code)

    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + ".glb")
    with open(output_path, "wb") as output_file:
        output_file.write(response.content)
    return output_path


def generate_with_hunyuan(image_path):
    """Send the image to Hunyuan3D-2.1 and return the local .glb path."""
    client = connect_to_space(MODEL3D_SPACE)

    try:
        result = client.predict(
            image=handle_file(str(image_path)),
            mv_image_front=None,
            mv_image_back=None,
            mv_image_left=None,
            mv_image_right=None,
            steps=HUNYUAN_STEPS,
            guidance_scale=5.0,
            seed=1234,
            octree_resolution=HUNYUAN_OCTREE_RESOLUTION,
            check_box_rembg=True,   # remove the background (done by the Space)
            num_chunks=8000,
            randomize_seed=True,
            api_name="/generation_all",   # shape + colours (texture)
        )
    except Exception as error:
        print(f"[model3d_service] Hunyuan3D error: {type(error).__name__}: {error}")
        raise Model3DError(get_friendly_message(str(error)))

    return check_glb(read_file_path(result[1]), result)


def check_glb(glb_path, raw_result):
    """Make sure the Space really gave us a .glb file."""
    if not glb_path or not str(glb_path).endswith(".glb"):
        print(f"[model3d_service] Unexpected result: {str(raw_result)[:300]}")
        raise Model3DError("The 3D AI service returned an unexpected result. Please try again.")
    return glb_path
