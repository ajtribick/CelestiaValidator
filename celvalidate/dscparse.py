# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""DSC file parsing utilities"""

from .parser import DataType, Disposition, PropertyDef, TokenFileParser, UnitsType
from .tokenizer import Token, TokenKind

_COMMON_PROPERTIES: dict[str, PropertyDef] = {
    "Position": (DataType.VECTOR, UnitsType.LENGTH),
    "RA": (DataType.NUMBER, UnitsType.ANGLE),
    "Dec": (DataType.NUMBER, UnitsType.ANGLE),
    "Distance": (DataType.NUMBER, UnitsType.LENGTH),
    "Axis": (DataType.VECTOR, None),
    "Angle": (DataType.NUMBER, UnitsType.ANGLE),
    "Radius": (DataType.NUMBER, UnitsType.LENGTH),
    "AbsMag": (DataType.NUMBER, None),
    "InfoURL": (DataType.STRING, None),
    "Visible": (DataType.BOOLEAN, None),
    "Clickable": (DataType.BOOLEAN, None),
}

_GALAXY_PROPERTIES: dict[str, PropertyDef] = _COMMON_PROPERTIES | {
    "Detail": (DataType.NUMBER, None),
    "Type": (DataType.STRING, None),
    "CustomTemplate": (DataType.STRING, None),
}

_GLOBULAR_PROPERTIES: dict[str, PropertyDef] = _COMMON_PROPERTIES | {
    "Detail": (DataType.NUMBER, None),
    "CoreRadius": (DataType.NUMBER, UnitsType.ANGLE),
    "KingConcentration": (DataType.NUMBER, None),
}

_NEBULA_PROPERTIES: dict[str, PropertyDef] = _COMMON_PROPERTIES | {
    "Mesh": (DataType.STRING, None),
}

_OPEN_CLUSTER_PROPERTIES: dict[str, PropertyDef] = _COMMON_PROPERTIES

_DSO_PROPERTIES = {
    "Galaxy": _GALAXY_PROPERTIES,
    "Globular": _GLOBULAR_PROPERTIES,
    "OpenCluster": _OPEN_CLUSTER_PROPERTIES,
    "Nebula": _NEBULA_PROPERTIES,
}

_GALAXY_TYPES = {
    "Irr",
    "S0",
    "Sa",
    "Sb",
    "Sc",
    "SBa",
    "SBb",
    "SBc",
    "E0",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
}


class DSCParser(TokenFileParser):
    """Parse DSC files"""

    def parse(self) -> None:
        """Parse dsc file and check for errors"""
        while True:
            token = self._next_token(allow_eof=True)
            if token is None:
                break

            if token.kind != TokenKind.NAME:
                self._error(token.line, token.pos, "Expected DSO type")

            object_type = token.value
            dso_properties = _DSO_PROPERTIES.get(object_type, None)
            if dso_properties is None:
                self._warn(token.line, token.pos, f"Unknown DSO type {object_type}")

            token = self._next_token(TokenKind.STRING, "Expected DSO name")
            if token.kind != TokenKind.STRING:
                self._error(token.line, token.pos, "Expected DSO name")

            token = self._next_token(TokenKind.START_OBJECT, is_error=True)

            if dso_properties is None:
                self._skip_structure(token.kind)
            else:
                self._check_object(object_type, token, dso_properties)

    def _validate_string(
        self, object_name: str, property_name: str, token: Token
    ) -> None:
        if object_name == "Galaxy" and property_name == "Type":
            if token.value not in _GALAXY_TYPES:
                self._warn(
                    token.line, token.pos, f"Invalid galaxy type {token.value!r}"
                )
        else:
            super()._validate_string(object_name, property_name, token)

    def _check_properties(
        self,
        object_name: str,
        open_token: Token,
        parsed_properties: set[str],
        disposition: Disposition,
    ) -> None:
        if "Position" in parsed_properties:
            if "RA" in parsed_properties:
                self._warn(
                    open_token.line, open_token.pos, "Position specified: RA ignored"
                )
            if "Dec" in parsed_properties:
                self._warn(
                    open_token.line, open_token.pos, "Position specified, Dec ignored"
                )
            if "Distance" in parsed_properties:
                self._warn(
                    open_token.line,
                    open_token.pos,
                    "Position specified, Distance ignored",
                )
        elif not ({"RA", "Dec", "Distance"} <= parsed_properties):
            self._warn(
                open_token.line,
                open_token.pos,
                "No position information specified, specify either RA/Dec/Distance or Position",
            )
        if "Radius" not in parsed_properties:
            self._warn(open_token.line, open_token.pos, "Missing Radius property")

        if object_name != "OpenCluster" and "AbsMag" not in parsed_properties:
            self._warn(open_token.line, open_token.pos, "Missing AbsMag property")

        if object_name == "Galaxy" and "Type" not in parsed_properties:
            self._warn(open_token.line, open_token.pos, "Missing Type property")
