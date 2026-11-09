"""
view_angle_service.py  —  show the try-on result from ANOTHER ANGLE.

Example: the result shows the person from the front. The user asks for
"45° to the left", and the AI redraws the same person + outfit as if the
camera had moved 45° to the left around them.

Current provider: Qwen-Image-Edit-2509 + "Multiple-Angles" LoRA, running
as a FREE demo ("Space") on Hugging Face:
    https://huggingface.co/spaces/linoyts/Qwen-Image-Edit-Angles

How we call it (checked in the Space's own app.py and with view_api()):
    client.predict(image=..., rotate_deg=45, vertical_tilt=0, ...,
                   api_name="/infer_edit_camera_angles")
    -> (new image, seed, prompt text)

    rotate_deg     -90 ... 90   positive = camera turns LEFT,
                                negative = camera turns RIGHT
    vertical_tilt  -1, 0, 1     -1 = from above (bird's-eye),
                                 1 = from below (worm's-eye)

Honest limits (tell your mentor!):
    - The AI IMAGINES the new view; parts that were hidden (the back,
      the side of the garment) are invented and may differ from reality.
    - Maximum turn is 90°: a full back view is not supported.
    - Free Space = shared daily GPU quota (same quota as the 3D feature).
    - The image is sent to Hugging Face (a third party).
"""

import shutil
import uuid
from pathlib import Path

from gradio_client import handle_file
from PIL import Image

from config import OUTPUTS_DIR, VIEW_ANGLE_SPACE
from services.hf_space_helpers import (
    SpaceError,
    connect_to_space,
    get_friendly_message,
    prepare_image,
    read_file_path,
)

# The allowed range of the Space's controls.
MAX_ROTATE_DEGREES = 90
ALLOWED_TILTS = [-1, 0, 1]

# AI settings (the Space's defaults: a fast 4-step "Lightning" model).
INFERENCE_STEPS = 4
GUIDANCE_SCALE = 1.0


def generate_new_angle(image_path, rotate_degrees, vertical_tilt):
    """
    Redraw the image from another camera angle.

    rotate_degrees -> -90 ... 90 (positive = left, negative = right)
    vertical_tilt  -> -1 (from above), 0 (eye level), 1 (from below)

    Returns the path of the new image saved in outputs/.
    Raises SpaceError if anything goes wrong.
    """
    if rotate_degrees == 0 and vertical_tilt == 0:
        raise SpaceError("Choose a rotation or a camera height first.", status_code=400)

    small_image_path = prepare_image(image_path)
    try:
        new_image_temp_path = call_space(small_image_path, rotate_degrees, vertical_tilt)
    finally:
        small_image_path.unlink(missing_ok=True)

    # Move the result into outputs/ (served at /outputs/..., auto-deleted later).
    extension = Path(new_image_temp_path).suffix or ".png"
    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + extension)
    shutil.move(new_image_temp_path, output_path)
    return output_path


def get_output_size(image_path):
    """
    Same size rule as the Space's own website: the longest side becomes
    1024 px, the shape stays the same, and both sides are multiples of 8.
    """
    with Image.open(image_path) as image:
        width, height = image.size
    if width > height:
        new_width = 1024
        new_height = int(1024 * height / width)
    else:
        new_height = 1024
        new_width = int(1024 * width / height)
    return (new_width // 8) * 8, (new_height // 8) * 8


def call_space(image_path, rotate_degrees, vertical_tilt):
    """Send the image + camera settings to the Space; return the new image's local path."""
    client = connect_to_space(VIEW_ANGLE_SPACE)
    width, height = get_output_size(image_path)

    try:
        result = client.predict(
            image=handle_file(str(image_path)),
            rotate_deg=rotate_degrees,
            move_forward=0,          # 0 = same distance (no zoom)
            vertical_tilt=vertical_tilt,
            wideangle=False,
            seed=0,
            randomize_seed=True,
            true_guidance_scale=GUIDANCE_SCALE,
            num_inference_steps=INFERENCE_STEPS,
            height=height,
            width=width,
            prev_output=None,
            api_name="/infer_edit_camera_angles",
        )
    except Exception as error:
        print(f"[view_angle_service] Space error: {type(error).__name__}: {error}")
        raise SpaceError(get_friendly_message(str(error)))

    # result = (new image, seed, prompt). The prompt shows what the AI was
    # asked, e.g. "Rotate the camera 45 degrees to the left."
    print(f"[view_angle_service] Prompt used: {result[2]}")
    new_image_path = read_file_path(result[0])
    if not new_image_path or not Path(new_image_path).is_file():
        print(f"[view_angle_service] Unexpected result: {str(result)[:300]}")
        raise SpaceError("The AI service returned an unexpected result. Please try again.")
    return new_image_path
