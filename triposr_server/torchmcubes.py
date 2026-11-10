"""
torchmcubes.py  —  a small stand-in for the "torchmcubes" library.

Why does this file exist?
    TripoSR's code does `from torchmcubes import marching_cubes`.
    The real torchmcubes must be COMPILED with C++ build tools, which is
    difficult on Windows. PyMCubes ("mcubes") does the same job (turning a
    3D grid of numbers into a triangle surface) and installs with pip.

    app.py puts this folder first on Python's search path, so TripoSR
    imports THIS file instead of the real library. TripoSR's code is not
    changed at all.

What "marching cubes" does:
    The AI predicts, for every point in a 3D grid, "how solid is it here?".
    Marching cubes finds the boundary between solid and empty and turns
    it into triangles: that is the 3D model's surface.
"""

import mcubes
import numpy as np
import torch


def marching_cubes(volume, threshold):
    """
    Same inputs/outputs as torchmcubes.marching_cubes:
        volume    -> torch tensor of shape (N, N, N)
        threshold -> the surface level (TripoSR uses 0.0)
    Returns (vertices float32 tensor, faces int64 tensor).
    """
    grid = volume.detach().cpu().numpy().astype(np.float32)
    vertices, faces = mcubes.marching_cubes(grid, threshold)

    # torchmcubes lists each vertex as (x, y, z) = (last axis, middle, first);
    # PyMCubes lists (first, middle, last). TripoSR expects the torchmcubes
    # order (it swaps the axes back itself), so we reverse them here.
    vertices = vertices[:, [2, 1, 0]]

    # Reversing the axes mirrors the shape, which turns every triangle
    # "inside out". Swapping two corners of each triangle fixes that, so
    # the surface faces outwards (important for correct lighting).
    faces = faces[:, [0, 2, 1]]

    return (
        torch.from_numpy(np.ascontiguousarray(vertices, dtype=np.float32)),
        torch.from_numpy(np.ascontiguousarray(faces, dtype=np.int64)),
    )
