"""
model3d_service.py  —  the ONLY file that talks to the 3D model AI.

What it does:
    one 2D image  ->  a coloured 3D model (.glb file) you can rotate 360°.

Two free AI engines are supported (choose with MODEL3D_ENGINE in .env):

    "triposr"  (DEFAULT)  TripoSR by Stability AI & Tripo.
               Runs in a free Hugging Face Space on CPU, so it does NOT use
               the daily Hugging Face GPU quota. ~1–2 minutes per model.
               Space: TRIPOSR_SPACE (default WeReCooking2/Dust3R-TripoSR).
               Colours are stored per point ("vertex colours").

    "hunyuan"  Hunyuan3D-2.1 by Tencent. Better shape and a real texture,
               but uses the free GPU quota (~1 model per day per account).
               Space: MODEL3D_SPACE (default tencent/Hunyuan3D-2.1).

How we talk to them:
    Hugging Face Spaces are Gradio apps. The official "gradio_client"
    library calls them like a normal Python function. We checked the exact
    inputs/outputs of each Space with client.view_api() and tested them.

Background removal:
    Both Spaces remove the background themselves (with the rembg tool) on
    their servers, so we don't install rembg (it needs ~1 GB of memory,
    more than a free Render server has).
      TripoSR  -> step "/preprocess" with remove_background = True
      Hunyuan  -> option "check_box_rembg" = True

Honest limits (tell your mentor!):
    - A 3D model from ONE photo is an AI guess: the back and sides are
      invented, faces/hands are often rough. It is a preview, not a scan.
    - Free Spaces are run by volunteers/companies and can be busy, slow
      or switched off at any time. If one stops working, change the Space
      name in .env.
    - The image is sent to Hugging Face (a third party) for processing.

Why keep this in one file?
    To switch to a paid API later (e.g. Tripo3D or Meshy), you rewrite only
    this file. The rest of the app just calls:
        glb_path = generate_3d_model(image_path)
"""

import shutil
import uuid

from gradio_client import handle_file

from config import MODEL3D_ENGINE, MODEL3D_SPACE, OUTPUTS_DIR, TRIPOSR_SPACE
from services.hf_space_helpers import (
    SpaceError,
    connect_to_space,
    get_friendly_message,
    prepare_image,
    read_file_path,
)

# Other files catch this name, so keep it as another name for SpaceError.
Model3DError = SpaceError


# ---------------------------------------------------------------------
# AI settings
# ---------------------------------------------------------------------
# TripoSR: how detailed the 3D surface is (32–512). Higher = finer but
# slower and a bigger file. 256 is the Space's default.
TRIPOSR_RESOLUTION = 256
# TripoSR: how much of the picture the person fills after cropping (0.5–1.0).
TRIPOSR_FOREGROUND_RATIO = 0.85

# Hunyuan3D: steps (5 = "Turbo", 30 = "Standard") and surface detail.
HUNYUAN_STEPS = 5
HUNYUAN_OCTREE_RESOLUTION = 256


# =====================================================================
# MAIN FUNCTION — the rest of the app only calls this one
# =====================================================================
def generate_3d_model(image_path):
    """
    Turn the image at `image_path` into a 3D model.
    Returns the path of the saved .glb file in outputs/.
    Raises Model3DError if anything goes wrong.

    This takes 1–3 minutes, so routes call it with asyncio.to_thread
    (otherwise the whole backend would freeze while waiting).
    """
    small_image_path = prepare_image(image_path)
    try:
        if MODEL3D_ENGINE == "hunyuan":
            glb_temp_path = generate_with_hunyuan(small_image_path)
        else:
            glb_temp_path = generate_with_triposr(small_image_path)
    finally:
        small_image_path.unlink(missing_ok=True)

    # gradio_client downloads the result into a temporary folder.
    # Move it into outputs/ with a random name, so it can be served at
    # http://<backend>/outputs/<name>.glb and is auto-deleted later.
    output_path = OUTPUTS_DIR / (uuid.uuid4().hex + ".glb")
    shutil.move(glb_temp_path, output_path)
    return output_path


# =====================================================================
# Engine 1: TripoSR (default)
# =====================================================================
def generate_with_triposr(image_path):
    """
    Two steps, exactly like the TripoSR website:
      1. /preprocess -> remove the background and centre the person
      2. /generate   -> build the 3D model from the cleaned image

    We pass the values in ORDER (not by name): copies of the TripoSR demo
    use slightly different input names, but always the same order.
    """
    client = connect_to_space(TRIPOSR_SPACE)

    try:
        # Step 1: (image, remove background?, foreground ratio) -> clean image
        cleaned_image = client.predict(
            handle_file(str(image_path)),
            True,
            TRIPOSR_FOREGROUND_RATIO,
            api_name="/preprocess",
        )
        cleaned_image_path = read_file_path(cleaned_image)

        # Step 2: (clean image, resolution) -> 3D model.
        # Some copies return only the .glb, others (.obj, .glb):
        # in both cases the .glb is the LAST item.
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


# =====================================================================
# Engine 2: Hunyuan3D-2.1 (optional)
# =====================================================================
def generate_with_hunyuan(image_path):
    """Send the image to Hunyuan3D-2.1 and return the local .glb path."""
    client = connect_to_space(MODEL3D_SPACE)

    try:
        result = client.predict(
            image=handle_file(str(image_path)),
            # We send one front image only (no multi-view images).
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

    # Returns (white_mesh, textured_mesh.glb, html, stats, seed): we want #2.
    return check_glb(read_file_path(result[1]), result)


def check_glb(glb_path, raw_result):
    """Make sure the Space really gave us a .glb file."""
    if not glb_path or not str(glb_path).endswith(".glb"):
        print(f"[model3d_service] Unexpected result: {str(raw_result)[:300]}")
        raise Model3DError("The 3D AI service returned an unexpected result. Please try again.")
    return glb_path
