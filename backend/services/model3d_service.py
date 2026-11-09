"""
model3d_service.py  —  the ONLY file that talks to the 3D model AI.

Current provider: Hunyuan3D-2.1 by Tencent, running as a FREE demo
("Space") on Hugging Face:
    https://huggingface.co/spaces/tencent/Hunyuan3D-2.1

What it does:
    one 2D image  ->  a textured 3D model (.glb file) you can rotate 360°.

How we talk to it:
    Hugging Face Spaces are Gradio apps. The official "gradio_client"
    library calls them like a normal Python function:
        client.predict(image=..., api_name="/generation_all")
    We checked the exact inputs/outputs with client.view_api().

Background removal:
    The Space has a built-in option "check_box_rembg" that removes the
    background with the rembg tool ON THEIR GPU before building the model.
    We switch it on, so we don't need to install rembg ourselves (rembg +
    its AI model need ~1 GB of memory, more than a free Render server has).

Honest limits (tell your mentor!):
    - A 3D model from ONE photo is an AI guess: the back and sides are
      invented, faces/hands are often rough. It is a preview, not a scan.
    - Free Spaces have a daily GPU quota and can be busy or offline.
    - The image is sent to Hugging Face (a third party) for processing.

Why keep this in one file?
    To switch to a paid API later (e.g. Tripo3D or Meshy), you rewrite only
    this file. The rest of the app just calls:
        glb_path = generate_3d_model(image_path)
"""

import shutil
import uuid

from gradio_client import handle_file

from config import MODEL3D_SPACE, OUTPUTS_DIR
from services.hf_space_helpers import (
    SpaceError,
    connect_to_space,
    get_friendly_message,
    prepare_image,
    read_file_path,
)


# ---------------------------------------------------------------------
# AI settings sent to the Space (names come from client.view_api())
# ---------------------------------------------------------------------
# TODO: More steps = a bit better shape but slower. The Space's "Turbo"
#       mode uses 5; "Standard" uses 30.
INFERENCE_STEPS = 5
# How detailed the 3D shape is (16–512). 256 is the Space's default.
OCTREE_RESOLUTION = 256

# Other files catch this name, so keep it as another name for SpaceError.
Model3DError = SpaceError


# =====================================================================
# MAIN FUNCTION — the rest of the app only calls this one
# =====================================================================
def generate_3d_model(image_path):
    """
    Turn the image at `image_path` into a 3D model.
    Returns the path of the saved .glb file in outputs/.
    Raises Model3DError if anything goes wrong.

    This takes about 1–3 minutes, so routes call it with asyncio.to_thread
    (otherwise the whole backend would freeze while waiting).
    """
    small_image_path = prepare_image(image_path)
    try:
        glb_temp_path = call_space(small_image_path)
    finally:
        small_image_path.unlink(missing_ok=True)

    # gradio_client downloads the result into a temporary folder.
    # Move it into outputs/ with a random name, so it can be served at
    # http://<backend>/outputs/<name>.glb and is auto-deleted later.
    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + ".glb")
    shutil.move(glb_temp_path, output_path)
    return output_path


def call_space(image_path):
    """Send the image to the Space and return the local path of the .glb result."""
    client = connect_to_space(MODEL3D_SPACE)

    try:
        result = client.predict(
            image=handle_file(str(image_path)),
            # We send one front image only (no multi-view images).
            mv_image_front=None,
            mv_image_back=None,
            mv_image_left=None,
            mv_image_right=None,
            steps=INFERENCE_STEPS,
            guidance_scale=5.0,
            seed=1234,
            octree_resolution=OCTREE_RESOLUTION,
            check_box_rembg=True,   # remove the background (done by the Space)
            num_chunks=8000,
            randomize_seed=True,
            api_name="/generation_all",   # shape + colours (texture)
        )
    except Exception as error:
        print(f"[model3d_service] Space error: {type(error).__name__}: {error}")
        raise Model3DError(get_friendly_message(str(error)))

    # The Space returns 5 things:
    #   (white_mesh file, textured_mesh.glb, html preview, mesh stats, seed)
    # We want the second one: the textured .glb model.
    glb_path = read_file_path(result[1])
    if not glb_path or not glb_path.endswith(".glb"):
        print(f"[model3d_service] Unexpected result: {str(result)[:300]}")
        raise Model3DError("The 3D AI service returned an unexpected result. Please try again.")
    return glb_path
