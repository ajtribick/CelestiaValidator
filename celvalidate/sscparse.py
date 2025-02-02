# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""SSC file parsing"""

from .filenames import is_mesh_file, is_texture_file
from .orbits import check_orbit_properties, has_orbit
from .parser import (
    DataType,
    Disposition,
    PropertyDef,
    Token,
    TokenFileParser,
    TokenKind,
    UnitsType,
)
from .rotations import check_rotation_properties
from .timeline import (
    TIMELINE_PROPERTIES,
    get_timeline_properties,
    validate_timeline_numbers,
    validate_timeline_strings,
)

_SURFACE_PROPERTIES: dict[str, PropertyDef] = {
    "Color": (DataType.COLOR, None),
    "SpecularColor": (DataType.COLOR, None),
    "SpecularPower": (DataType.NUMBER, None),
    "LunarLambert": (DataType.NUMBER, None),
    "Texture": (DataType.STRING, None),
    "BumpMap": (DataType.STRING, None),
    "NightTexture": (DataType.STRING, None),
    "SpecularTexture": (DataType.STRING, None),
    "NormalMap": (DataType.STRING, None),
    "OverlayTexture": (DataType.STRING, None),
    "BumpHeight": (DataType.NUMBER, None),
    "BlendTexture": (DataType.BOOLEAN, None),
    "Emissive": (DataType.BOOLEAN, None),
    "CompressTexture": (DataType.BOOLEAN, None),
}

_ATMOSPHERE_PROPERTIES: dict[str, PropertyDef] = {
    "Height": (DataType.NUMBER, UnitsType.LENGTH),
    "Lower": (DataType.COLOR, None),
    "Upper": (DataType.COLOR, None),
    "Sky": (DataType.COLOR, None),
    "Sunset": (DataType.COLOR, None),
    "Mie": (DataType.NUMBER, None),
    "MieScaleHeight": (DataType.NUMBER, UnitsType.LENGTH),
    "MieAsymmetry": (DataType.NUMBER, None),
    "Rayleigh": (DataType.VECTOR, None),
    "Absorption": (DataType.VECTOR, None),
    "CloudHeight": (DataType.NUMBER, UnitsType.LENGTH),
    "CloudSpeed": (DataType.NUMBER, None),
    "CloudMap": (DataType.STRING, None),
    "CloudShadowDepth": (DataType.NUMBER, None),
}

_RINGS_PROPERTIES: dict[str, PropertyDef] = {
    "Inner": (DataType.NUMBER, UnitsType.LENGTH),
    "Outer": (DataType.NUMBER, UnitsType.LENGTH),
    "Color": (DataType.COLOR, None),
    "Texture": (DataType.STRING, None),
}

_BODY_PROPERTIES: dict[str, PropertyDef] = (
    {
        "Radius": (DataType.NUMBER, UnitsType.LENGTH),
        "SemiAxes": (DataType.VECTOR, UnitsType.LENGTH),
        "Oblateness": (DataType.NUMBER, None),
        "Class": (DataType.STRING, None),
        "Category": (DataType.STRING_LIST, None),
        "InfoURL": (DataType.STRING, None),
        "Albedo": (DataType.NUMBER, None),
        "GeomAlbedo": (DataType.NUMBER, None),
        "Reflectivity": (DataType.NUMBER, None),
        "BondAlbedo": (DataType.NUMBER, None),
        "Temperature": (DataType.NUMBER, None),
        "TempDiscrepancy": (DataType.NUMBER, None),
        "Mass": (DataType.NUMBER, UnitsType.MASS),
        "Density": (DataType.NUMBER, None),
        "Orientation": (DataType.QUATERNION, None),
        "Mesh": (DataType.STRING, None),
        "MeshCenter": (DataType.VECTOR, None),
        "NormalizeMesh": (DataType.BOOLEAN, None),
        "MeshScale": (DataType.NUMBER, UnitsType.LENGTH),
        "Atmosphere": (DataType.OBJECT, None),
        "Rings": (DataType.OBJECT, None),
        "TailColor": (DataType.COLOR, None),
        "Clickable": (DataType.BOOLEAN, None),
        "Visible": (DataType.BOOLEAN, None),
        "OrbitColor": (DataType.COLOR, None),
    }
    | _SURFACE_PROPERTIES
    | TIMELINE_PROPERTIES
)

_REFERENCE_POINT_PROPERTIES: dict[str, PropertyDef] = {
    "Visible": (DataType.BOOLEAN, None),
    "Clickable": (DataType.BOOLEAN, None),
    "OrbitColor": (DataType.COLOR, None),
} | TIMELINE_PROPERTIES

_LOCATION_PROPERTIES: dict[str, PropertyDef] = {
    "LongLat": (DataType.VECTOR, UnitsType.SPHERICAL),
    "Size": (DataType.NUMBER, UnitsType.LENGTH),
    "Importance": (DataType.NUMBER, None),
    "Type": (DataType.STRING, None),
    "LabelColor": (DataType.COLOR, None),
    "Category": (DataType.STRING_LIST, None),
}

_OBJ_PROPERTIES = {
    "Body": _BODY_PROPERTIES,
    "SurfaceObject": _BODY_PROPERTIES,
    "ReferencePoint": _REFERENCE_POINT_PROPERTIES,
    "AltSurface": _SURFACE_PROPERTIES,
    "Location": _LOCATION_PROPERTIES,
}

_TEXTURE_PROPERTIES = {
    "Texture",
    "BumpMap",
    "NightTexture",
    "SpecularTexture",
    "NormalMap",
    "OverlayTexture",
    "CloudMap",
}

# properties that must be positive, and whether zero is allowed
_POSITIVE_PROPERTIES = {
    "Height": False,
    "MieScaleHeight": False,
    "CloudHeight": False,
    "Inner": True,
    "Outer": True,
    "Albedo": True,
    "GeomAlbedo": True,
    "Reflectivity": True,
    "BondAlbedo": True,
    "Density": False,
    "MeshScale": False,
    "Size": False,
    "Importance": False,
}

_CATEGORIES = {
    "planet",
    "dwarfplanet",
    "moon",
    "minormoon",
    "comet",
    "asteroid",
    "spacecraft",
    "invisible",
    "surfacefeature",
    "component",
    "diffuse",
}


class SSCParser(TokenFileParser):
    """Parse SSC files"""

    def parse(self) -> None:
        """Parse SSC file and check for errors"""
        while True:
            token = self._next_token(allow_eof=True)
            if token is None:
                break

            disposition = Disposition.ADD
            if token.kind == TokenKind.NAME:
                match token.value:
                    case "Add":
                        token = self._next_token()
                    case "Modify":
                        disposition = Disposition.MODIFY
                        token = self._next_token()
                    case "Replace":
                        disposition = Disposition.REPLACE
                        token = self._next_token()
                    case _:
                        pass

            object_type = "Body"
            properties = _BODY_PROPERTIES
            if token.kind == TokenKind.NAME:
                try:
                    properties = _OBJ_PROPERTIES[token.value]
                except KeyError:
                    self._error(
                        token.line, token.pos, f"Unknown body type {token.value}"
                    )
                else:
                    object_type = token.value
                    token = self._next_token()

            if token.kind == TokenKind.STRING:
                token = self._next_token()
            else:
                self._error(token.line, token.pos, "Expected object name")

            if token.kind == TokenKind.STRING:
                token = self._next_token()
            else:
                self._error(token.line, token.pos, "Expected parent object name")

            if token.kind != TokenKind.START_OBJECT:
                self._error(token.line, token.pos, "Expected start of object")

            self._check_object(object_type, token, properties, disposition)

    def _get_properties(self, object_name: str) -> dict[str, PropertyDef]:
        if object_name == "Atmosphere":
            return _ATMOSPHERE_PROPERTIES
        if object_name == "Rings":
            return _RINGS_PROPERTIES
        if (properties := get_timeline_properties(object_name)) is not None:
            return properties
        return super()._get_properties(object_name)

    def _validate_number(
        self, object_name: str, property_name: str, token: Token
    ) -> None:
        validate_timeline_numbers(
            object_name,
            property_name,
            token,
            lambda tok, msg: self._warn(tok.line, tok.pos, msg),
        )
        super()._validate_number(object_name, property_name, token)

    def _validate_string(
        self, object_name: str, property_name: str, token: Token
    ) -> None:
        if property_name == "Class":
            if token.value not in _CATEGORIES:
                self._warn(token.line, token.pos, f"Unknown class type {token.value!r}")
        elif property_name in _TEXTURE_PROPERTIES:
            if not is_texture_file(token.value):
                self._warn(
                    token.line, token.pos, f"Bad texture filename {token.value!r}"
                )
        elif property_name == "Mesh":
            # override the check here as some add-ons use Mesh "" to switch off geometry
            if token.value != "" and not is_mesh_file(token.value):
                self._warn(token.line, token.pos, f"Bad mesh filename {token.value!r}")
        elif (allow_zero := _POSITIVE_PROPERTIES.get(property_name, None)) is not None:
            if token.value < 0 or (token.value == 0 and not allow_zero):
                status = "positive or zero" if allow_zero else "strictly positive"
                self._warn(token.line, token.pos, f"{property_name} must be {status}")
        else:
            validate_timeline_strings(
                object_name,
                property_name,
                token,
                lambda tok, msg: self._warn(tok.line, tok.pos, msg),
            )
            super()._validate_string(object_name, property_name, token)

    def _check_properties(
        self,
        object_name: str,
        open_token: Token,
        parsed_properties: set[str],
        disposition: Disposition,
    ) -> None:
        if disposition != Disposition.MODIFY:
            match object_name:
                case "Body" | "SurfaceObject" | "ReferencePoint":
                    if not (
                        "Timeline" in parsed_properties or has_orbit(parsed_properties)
                    ):
                        self._warn(
                            open_token.line,
                            open_token.pos,
                            f"No valid orbit specified for {object_name}",
                        )
                    if (
                        object_name != "ReferencePoint"
                        and "Radius" not in parsed_properties
                        and "SemiAxes" not in parsed_properties
                    ):
                        self._warn(
                            open_token.line,
                            open_token.pos,
                            "At least one of Radius and SemiAxes must be specified",
                        )
                case "Rings":
                    if "Inner" not in parsed_properties:
                        self._warn(
                            open_token.line, open_token.pos, "Inner must be specified"
                        )
                    if "Outer" not in parsed_properties:
                        self._warn(
                            open_token.line, open_token.pos, "Outer must be specified"
                        )
                case "Atmosphere":
                    if "Height" not in parsed_properties:
                        self._warn(
                            open_token.line, open_token.pos, "Height must be specified"
                        )
                    if "Mie" in parsed_properties:
                        if "Mie" in parsed_properties:
                            if "MieScaleHeight" not in parsed_properties:
                                self._warn(
                                    open_token.line,
                                    open_token.pos,
                                    "Mie specified without MieScaleHeight",
                                )
                        elif "MieScaleHeight" in parsed_properties:
                            self._warn(
                                open_token.line,
                                open_token.pos,
                                "MieScaleHeight specified without Mie",
                            )
                    if "CloudMap" in parsed_properties:
                        if "CloudHeight" not in parsed_properties:
                            self._warn(
                                open_token.line,
                                open_token.pos,
                                "CloudMap specified without CloudHeight",
                            )
                    elif "CloudHeight" in parsed_properties:
                        self._warn(
                            open_token.line,
                            open_token.pos,
                            "CloudHeight specified without CloudMap",
                        )
                    elif "CloudSpeed" in parsed_properties:
                        self._warn(
                            open_token.line,
                            open_token.pos,
                            "CloudSpeed specified without CloudMap or CloudHeight",
                        )

        if object_name == "Timeline":
            if not has_orbit(parsed_properties):
                self._warn(
                    open_token.line,
                    open_token.pos,
                    "No valid orbit specifed for timeline phase",
                )
        check_rotation_properties(
            object_name,
            parsed_properties,
            lambda msg: self._warn(open_token.line, open_token.pos, msg),
        )
        check_orbit_properties(
            object_name,
            parsed_properties,
            lambda msg: self._warn(open_token.line, open_token.pos, msg),
        )
