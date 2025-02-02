# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Filename validators"""

import os
import re

_INVALID_FILE_REGEX = re.compile(r"^(?:COM|LPT)[0-9\u00b2\u00b3\u00b9]$")

_MESH_EXTENSIONS = [".cmod", ".3ds", ".cms"]
_TEXTURE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".dds",
    ".dxt5nm",
    ".ctx",
    ".avif",
    ".*",
]
_TRAJECTORY_EXTENSIONS = [".xyz", ".xyzv", ".xyzvbin", ".*"]


def is_file(filename: str) -> bool:
    """Checks if a filename is valid and has no directory separators"""
    return (
        "/" not in filename
        and "\\" not in filename
        and filename not in ("CON", "PRN", "AUX", "NUL")
        and _INVALID_FILE_REGEX.match(filename) is None
    )


def is_mesh_file(filename: str) -> bool:
    """Checks if a filename is a mesh file"""
    return (
        is_file(filename)
        and os.path.splitext(filename)[1].casefold() in _MESH_EXTENSIONS
    )


def is_texture_file(filename: str) -> bool:
    """Checks if a filename is a texture file"""
    return (
        is_file(filename)
        and os.path.splitext(filename)[1].casefold() in _TEXTURE_EXTENSIONS
    )


def is_trajectory_file(filename: str) -> bool:
    """Checks if a filename is a trajectory file"""
    return (
        is_file(filename)
        and os.path.splitext(filename)[1].casefold() in _TRAJECTORY_EXTENSIONS
    )
