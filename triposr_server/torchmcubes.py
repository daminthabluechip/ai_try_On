"""
Stand-in for the torchmcubes library, using PyMCubes.
The real torchmcubes needs a C++ build, which is hard on Windows.
app.py puts this file first on the import path, so TripoSR uses it unchanged.
"""

import mcubes
import numpy as np
import torch


def marching_cubes(volume, threshold):
    """Same inputs/outputs as torchmcubes.marching_cubes(volume, threshold)."""
    grid = volume.detach().cpu().numpy().astype(np.float32)
    vertices, faces = mcubes.marching_cubes(grid, threshold)

    # torchmcubes orders vertex axes in reverse; TripoSR expects that order.
    vertices = vertices[:, [2, 1, 0]]

    # Reversing the axes flips the triangles inside out; swap two corners to fix.
    faces = faces[:, [0, 2, 1]]

    return (
        torch.from_numpy(np.ascontiguousarray(vertices, dtype=np.float32)),
        torch.from_numpy(np.ascontiguousarray(faces, dtype=np.int64)),
    )
