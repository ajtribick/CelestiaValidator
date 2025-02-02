# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Definitions for timelines and reference frames"""

import re

from typing import Callable, Optional

from .orbits import (
    ORBIT_PROPERTIES, get_orbit_properties, validate_orbit_numbers, validate_orbit_strings
)
from .parser import DataType, PropertyDef, Token
from .rotations import (
    ROTATION_PROPERTIES, get_rotation_properties, validate_rotation_numbers,
    validate_rotation_strings,
)

_TIMELINE_PHASE_PROPERTIES: dict[str, PropertyDef] = {
    "OrbitFrame": (DataType.OBJECT, None),
    "BodyFrame": (DataType.OBJECT, None),
    "Beginning": (DataType.DATE, None),
    "Ending": (DataType.DATE, None),
} | ORBIT_PROPERTIES | ROTATION_PROPERTIES

TIMELINE_PROPERTIES: dict[str, PropertyDef] = {
    "Timeline": (DataType.OBJECT_LIST, None),
} | _TIMELINE_PHASE_PROPERTIES

_RELATIVE_POSITION_VELOCITY_PROPERTIES: dict[str, PropertyDef] = {
    "Observer": (DataType.STRING, None),
    "Target": (DataType.STRING, None),
}

_CONSTANT_VECTOR_PROPERTIES: dict[str, PropertyDef] = {
    "Vector": (DataType.VECTOR, None),
    "Frame": (DataType.OBJECT, None),
}

_FRAME_VECTOR_PROPERTIES: dict[str, PropertyDef] = {
    "Axis": (DataType.STRING, None),
    "RelativePosition": (DataType.OBJECT, None),
    "RelativeVelocity": (DataType.OBJECT, None),
    "ConstantVector": (DataType.OBJECT, None),
}

_BASE_FRAME_PROPERTIES: dict[str, PropertyDef] = {
    "Center": (DataType.STRING, None),
}

_MEAN_EQUATOR_PROPERTIES: dict[str, PropertyDef] = {
    "Object": (DataType.STRING, None),
    "Freeze": (DataType.DATE, None),
} | _BASE_FRAME_PROPERTIES

_TWO_VECTOR_PROPERTIES: dict[str, PropertyDef] = {
    "Primary": (DataType.OBJECT, None),
    "Secondary": (DataType.OBJECT, None),
} | _BASE_FRAME_PROPERTIES

_TOPOCENTRIC_PROPERTIES: dict[str, PropertyDef] = {
    "Target": (DataType.STRING, None),
    "Observer": (DataType.STRING, None),
} | _BASE_FRAME_PROPERTIES

_FRAME_TYPE_PROPERTIES = {
    "BodyFixed": _BASE_FRAME_PROPERTIES,
    "MeanEquator": _MEAN_EQUATOR_PROPERTIES,
    "TwoVector": _TWO_VECTOR_PROPERTIES,
    "Topocentric": _TOPOCENTRIC_PROPERTIES,
    "EclipticJ2000": _BASE_FRAME_PROPERTIES,
    "EquatorJ2000": _BASE_FRAME_PROPERTIES,
}

_FRAME_PROPERTIES = {
    k: (DataType.OBJECT, None) for k in _FRAME_TYPE_PROPERTIES
}

_AXIS_REGEX = re.compile(r"^[+\-]?[xyz]$")

def get_timeline_properties(object_name: str) -> Optional[dict[str, PropertyDef]]:
    """Gets the property list for timelines and reference frames"""
    if (properties := _FRAME_TYPE_PROPERTIES.get(object_name, None)) is not None:
        return properties
    if (properties := get_orbit_properties(object_name)) is not None:
        return properties
    if (properties := get_rotation_properties(object_name)) is not None:
        return properties

    match object_name:
        case "Frame" | "BodyFrame" | "OrbitFrame":
            return _FRAME_PROPERTIES
        case "Primary" | "Secondary":
            return _FRAME_VECTOR_PROPERTIES
        case "RelativePosition" | "RelativeVelocity":
            return _RELATIVE_POSITION_VELOCITY_PROPERTIES
        case "ConstantVector":
            return _CONSTANT_VECTOR_PROPERTIES
        case "Timeline":
            return _TIMELINE_PHASE_PROPERTIES
        case _:
            return None

def validate_timeline_numbers(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate timeline numeric parameters"""
    validate_orbit_numbers(object_type, property_name, token, warn)
    validate_rotation_numbers(object_type, property_name, token, warn)

def validate_timeline_strings(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate timeline string parameters"""
    if property_name == "Axis":
        if _AXIS_REGEX.match(token.value) is None:
            warn(token, f"Invalid axis specification {token.value!r}")
    validate_orbit_strings(object_type, property_name, token, warn)
    validate_rotation_strings(object_type, property_name, token, warn)
