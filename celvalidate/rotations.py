# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Definitions for rotation models"""

from typing import Callable, Optional

from .filenames import is_file
from .parser import DataType, PropertyDef, UnitsType
from .tokenizer import Token

ROTATION_PROPERTIES: dict[str, PropertyDef] = {
    "CustomRotation": (DataType.STRING, None),
    "SpiceRotation": (DataType.OBJECT, None),
    "ScriptedRotation": (DataType.OBJECT, None),
    "SampledOrientation": (DataType.STRING, None),
    "PrecessingRotation": (DataType.OBJECT, None),
    "UniformRotation": (DataType.OBJECT, None),
    "FixedRotation": (DataType.OBJECT, None),
    "FixedAttitude": (DataType.OBJECT, None),
    # Backward compatibility properties - note no units support
    "RotationPeriod": (DataType.NUMBER, None),
    "RotationOffset": (DataType.NUMBER, None),
    "RotationEpoch": (DataType.DATE, None),
    "Obliquity": (DataType.NUMBER, None),
    "EquatorAscendingNode": (DataType.NUMBER, None),
    "PrecessionRate": (DataType.NUMBER, None),
}

_SPICE_ROTATION_PROPERTIES: dict[str, PropertyDef] = {
    "Kernel": (DataType.STRING, None),
    "Target": (DataType.STRING, None),
    "Origin": (DataType.STRING, None),
    "BoundingRadius": (DataType.NUMBER, UnitsType.LENGTH),
    "Period": (DataType.NUMBER, UnitsType.TIME),
    "Beginning": (DataType.DATE, UnitsType.TIME),
    "Ending": (DataType.DATE, UnitsType.TIME),
}

_SCRIPTED_ROTATION_PROPERTIES: dict[str, PropertyDef] = {
    "Function": (DataType.STRING, None),
    "Module": (DataType.STRING, None),
}

_UNIFORM_ROTATION_PROPERTIES: dict[str, PropertyDef] = {
    "Period": (DataType.NUMBER, UnitsType.TIME),
    "Epoch": (DataType.DATE, None),
    "MeridianAngle": (DataType.NUMBER, UnitsType.ANGLE),
    "Inclination": (DataType.NUMBER, UnitsType.ANGLE),
    "AscendingNode": (DataType.NUMBER, UnitsType.ANGLE),
}

_PRECESSING_ROTATION_PROPERTIES: dict[str, PropertyDef] = _UNIFORM_ROTATION_PROPERTIES | {
    "PrecessionPeriod": (DataType.NUMBER, UnitsType.TIME),
}

_FIXED_ROTATION_PROPERTIES: dict[str, PropertyDef] = {
    "MeridianAngle": (DataType.NUMBER, UnitsType.ANGLE),
    "Inclination": (DataType.NUMBER, UnitsType.ANGLE),
    "AscendingNode": (DataType.NUMBER, UnitsType.ANGLE),
}

_FIXED_ATTITUDE_PROPERTIES: dict[str, PropertyDef] = {
    "Heading": (DataType.NUMBER, UnitsType.ANGLE),
    "Tilt": (DataType.NUMBER, UnitsType.ANGLE),
    "Roll": (DataType.NUMBER, UnitsType.ANGLE),
}

_ROTATION_SPECIFIC_PROPERTIES = {
    "SpiceRotation": _SPICE_ROTATION_PROPERTIES,
    "ScriptedRotation": _SCRIPTED_ROTATION_PROPERTIES,
    "PrecessingRotation": _PRECESSING_ROTATION_PROPERTIES,
    "UniformRotation": _UNIFORM_ROTATION_PROPERTIES,
    "FixedRotation": _FIXED_ROTATION_PROPERTIES,
    "FixedAttitude": _FIXED_ATTITUDE_PROPERTIES,
}

def get_rotation_properties(object_type: str) -> Optional[dict[str, PropertyDef]]:
    """Gets the property list for rotations"""
    return _ROTATION_SPECIFIC_PROPERTIES.get(object_type, None)

def validate_rotation_strings(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate rotation string parameters"""
    if property_name == "SampledOrientation":
        if not is_file(token.value):
            warn(token, f"Bad filename {token.value!r}")
        return

    match object_type:
        case "SpiceRotation":
            if property_name == "Kernel" and not is_file(token.value):
                warn(token, f"Bad filename {token.value!r}")
        case "Kernel":
            if not is_file(token.value):
                warn(token, f"Bad filename {token.value!r}")

def validate_rotation_numbers(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate rotation numeric parameters"""
    if object_type == "SpiceOrbit":
        match property_name:
            case "BoundingRadius":
                if token.value <= 0:
                    warn(token, "BoundingRadius must be strictly positive")
            case "Period":
                if token.value < 0:
                    warn(token, "Period must be zero or positive")

def check_rotation_properties(
    object_type: str,
    parsed_properties: set[str],
    warn: Callable[[str], None]
) -> None:
    """Checks required parameters for rotations"""
    match object_type:
        case "SpiceRotation":
            if "Frame" not in parsed_properties:
                warn("Missing Frame property")
            if ("Beginning" in parsed_properties) != ("Ending" in parsed_properties):
                warn("Either both Beginning and Ending must be supplied, or neither")
        case "ScriptedRotation":
            if "Function" not in parsed_properties:
                warn("Missing Function property")
        case "PrecessingRotation":
            pass
        case "UniformRotation":
            pass
        case "FixedRotation":
            pass
        case "FixedAttitude":
            pass
        case _:
            pass
