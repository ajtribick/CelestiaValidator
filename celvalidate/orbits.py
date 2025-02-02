# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Definitions for orbits"""

from typing import Callable, Optional

from .filenames import is_file, is_trajectory_file
from .parser import DataType, PropertyDef, UnitsType
from .tokenizer import Token

ORBIT_PROPERTIES: dict[str, PropertyDef] = {
    "CustomOrbit": (DataType.STRING, None),
    "SpiceOrbit": (DataType.OBJECT, None),
    "ScriptedOrbit": (DataType.OBJECT, None),
    "SampledTrajectory": (DataType.OBJECT, None),
    "SampledOrbit": (DataType.STRING, None),
    "EllipticalOrbit": (DataType.OBJECT, None),
    "FixedPosition": (DataType.VECTOR_OR_OBJECT, None),
    "LongLat": (DataType.VECTOR, UnitsType.SPHERICAL),
}

_SPICE_ORBIT_PROPERTIES: dict[str, PropertyDef] = {
    "Kernel": (DataType.STRING, None),
    "Target": (DataType.STRING, None),
    "Origin": (DataType.STRING, None),
    "BoundingRadius": (DataType.NUMBER, UnitsType.LENGTH),
    "Period": (DataType.NUMBER, UnitsType.TIME),
    "Beginning": (DataType.DATE, UnitsType.TIME),
    "Ending": (DataType.DATE, UnitsType.TIME),
}

_SCRIPTED_ORBIT_PROPERTIES: dict[str, PropertyDef] = {
    "Function": (DataType.STRING, None),
    "Module": (DataType.STRING, None),
}

_SAMPLED_TRAJECTORY_PROPERTIES: dict[str, PropertyDef] = {
    "Source": (DataType.STRING, None),
    "Interpolation": (DataType.STRING, None),
    "DoublePrecision": (DataType.BOOLEAN, None),
}

_ELLIPTICAL_ORBIT_PROPERTIES: dict[str, PropertyDef] = {
    "Eccentricity": (DataType.NUMBER, None),
    "SemiMajorAxis": (DataType.NUMBER, UnitsType.LENGTH),
    "PericenterDistance": (DataType.NUMBER, UnitsType.LENGTH),
    "Period": (DataType.NUMBER, UnitsType.TIME),
    "Inclination": (DataType.NUMBER, UnitsType.ANGLE),
    "AscendingNode": (DataType.NUMBER, UnitsType.ANGLE),
    "ArgOfPericenter": (DataType.NUMBER, UnitsType.ANGLE),
    "LongOfPericenter": (DataType.NUMBER, UnitsType.ANGLE),
    "Epoch": (DataType.DATE, None),
    "MeanAnomaly": (DataType.NUMBER, UnitsType.ANGLE),
    "MeanLongitude": (DataType.NUMBER, UnitsType.ANGLE),
}

_FIXED_POSITION_PROPERTIES: dict[str, PropertyDef] = {
    "Rectangular": (DataType.VECTOR, UnitsType.LENGTH),
    "Planetographic": (DataType.VECTOR, UnitsType.SPHERICAL),
    "Planetocentric": (DataType.VECTOR, UnitsType.SPHERICAL),
}

_ORBIT_SPECIFIC_PROPERTIES = {
    "SpiceOrbit": _SPICE_ORBIT_PROPERTIES,
    "ScriptedOrbit": _SCRIPTED_ORBIT_PROPERTIES,
    "SampledTrajectory": _SAMPLED_TRAJECTORY_PROPERTIES,
    "EllipticalOrbit": _ELLIPTICAL_ORBIT_PROPERTIES,
    "FixedPosition": _FIXED_POSITION_PROPERTIES,
}


def get_orbit_properties(object_type: str) -> Optional[dict[str, PropertyDef]]:
    """Gets the property list for orbits"""
    return _ORBIT_SPECIFIC_PROPERTIES.get(object_type, None)


def has_orbit(parsed_properties: set[str]):
    """Checks if an orbit definition exists"""
    for prop in parsed_properties:
        if prop in ORBIT_PROPERTIES:
            return True
    return False


def validate_orbit_strings(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate orbit string parameters"""
    match object_type:
        case "SpiceOrbit":
            if property_name == "Kernel" and not is_file(token.value):
                warn(token, f"Bad filename {token.value!r}")
        case "Kernel":
            if not is_file(token.value):
                warn(token, f"Bad filename {token.value!r}")
        case "SampledTrajectory":
            match property_name:
                case "Source":
                    if not is_trajectory_file(token.value):
                        warn(token, f"Bad trajectory filename {token.value!r}")
                case "Interpolation":
                    if token.value not in ("linear", "cubic"):
                        warn(token, f"Unknown Interpolation type {token.value!r}")


def validate_orbit_numbers(
    object_type: str,
    property_name: str,
    token: Token,
    warn: Callable[[Token, str], None],
) -> None:
    """Validate orbit numeric parameters"""
    match object_type:
        case "EllipticalOrbit":
            if property_name == "Period" and token.value == 0:
                warn(token, f"{property_name} must be non-zero")
        case "SpiceOrbit":
            match property_name:
                case "BoundingRadius":
                    if token.value <= 0:
                        warn(token, "BoundingRadius must be strictly positive")
                case "Period":
                    if token.value < 0:
                        warn(token, "Period must be zero or positive")
        case _:
            pass


def check_orbit_properties(
    object_type: str, parsed_properties: set[str], warn: Callable[[str], None]
) -> None:
    """Checks required parameters for rotations"""
    match object_type:
        case "SpiceOrbit":
            if "Frame" not in parsed_properties:
                warn("Missing Frame property")
            if "Target" not in parsed_properties:
                warn("Missing Target property")
            if "Origin" not in parsed_properties:
                warn("Missing Origin property")
            if "BoundingRadius" not in parsed_properties:
                warn("Missing BoundingRadius property")
            if ("Beginning" in parsed_properties) != ("Ending" in parsed_properties):
                warn("Either both Beginning and Ending must be supplied, or neither")
        case "ScriptedOrbit":
            if "Function" not in parsed_properties:
                warn("Missing Function property")
        case "SampledTrajectory":
            if "Source" not in parsed_properties:
                warn("Missing Source property")
        case "EllipticalOrbit":
            if "SemiMajorAxis" in parsed_properties:
                if "PericenterDistance" in parsed_properties:
                    warn("PericenterDistance ignored in favor of SemiMajorAxis")
            elif "PericenterDistance" not in parsed_properties:
                warn("Either SemiMajorAxis or PericenterDistance must be specified")
            if "Period" not in parsed_properties:
                warn("Missing Period property")
            if {"MeanAnomaly", "MeanLongitude"} <= parsed_properties:
                warn("MeanLongitude ignored in favor of MeanAnomaly")
        case "FixedPosition":
            if "Rectangular" in parsed_properties:
                if "Planetographic" in parsed_properties:
                    warn("Planetographic ignored in favor of Rectangular")
                if "Planetocentric" in parsed_properties:
                    warn("Planetocentric ignored in favor of Rectangular")
            elif "Planetographic" in parsed_properties:
                if "Planetocentric" in parsed_properties:
                    warn("Planetocentric ignored in favor of Planetographic")
            elif "Planetocentric" not in parsed_properties:
                warn(
                    "One of Rectangular, Planetographic, or Planetocentric must be specified"
                )
        case _:
            pass
