# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""STC file parsing"""

import re

from .orbits import (
    ORBIT_PROPERTIES,
    check_orbit_properties,
    get_orbit_properties,
    has_orbit,
    validate_orbit_numbers,
    validate_orbit_strings,
)
from .parser import DataType, Disposition, PropertyDef, TokenFileParser, UnitsType
from .rotations import (
    ROTATION_PROPERTIES,
    check_rotation_properties,
    get_rotation_properties,
    validate_rotation_numbers,
    validate_rotation_strings,
)
from .tokenizer import Token, TokenKind

_COMMON_PROPERTIES: dict[str, PropertyDef] = {
    "Position": (DataType.VECTOR, UnitsType.LENGTH),
    "RA": (DataType.NUMBER, UnitsType.ANGLE),
    "Dec": (DataType.NUMBER, UnitsType.ANGLE),
    "Distance": (DataType.NUMBER, UnitsType.LENGTH),
    "OrbitBarycenter": (DataType.NUMBER_OR_STRING, None),
    "Category": (DataType.STRING_LIST, None),
    "InfoURL": (DataType.STRING, None),
} | ORBIT_PROPERTIES

_STAR_PROPERTIES: dict[str, PropertyDef] = (
    {
        "SpectralType": (DataType.STRING, None),
        "AppMag": (DataType.NUMBER, None),
        "AbsMag": (DataType.NUMBER, None),
        "Extinction": (DataType.NUMBER, None),
        "Temperature": (DataType.NUMBER, None),
        "BoloCorrection": (DataType.NUMBER, None),
        "Mesh": (DataType.STRING, None),
        "Texture": (DataType.STRING, None),
        "SemiAxes": (DataType.VECTOR, UnitsType.LENGTH),
        "Radius": (DataType.NUMBER, UnitsType.LENGTH),
    }
    | _COMMON_PROPERTIES
    | ROTATION_PROPERTIES
)

_OBJ_PROPERTIES = {
    "Star": _STAR_PROPERTIES,
    "Barycenter": _COMMON_PROPERTIES,
}

_SPTYPE_REGEX = re.compile(
    r"""^(?:
        [QX?]
        | D(?P<wdtype>[ABCOQXZ][ABCOQXZVPHE]?)?[0-9]?
        | (?P<lumprefix>sd)?([OBAFGKMRSNLTYC]|W[CNO]?)
          ([0-9](\.[0-9])?)?
          (?P<lumtype>VI?|I(-?a0?|a-?0|-?b|V|I{0,2}))?
        )""",
    re.VERBOSE,
)


class STCParser(TokenFileParser):
    """Parse STC files"""

    def parse(self) -> None:
        """Parse STC file and check for errors"""
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

            object_type = "Star"
            if token.kind == TokenKind.NAME:
                if token.value in ("Star", "Barycenter"):
                    object_type = token.value
                    token = self._next_token()
                else:
                    self._error(
                        token.line, token.pos, f"Unknown stc object type {token.value}"
                    )

            has_id = False
            if token.kind == TokenKind.NUMBER:
                if not isinstance(token.value, int):
                    self._warn(token.line, token.pos, "Non-integer HIP number")
                has_id = True
                token = self._next_token()

            if token.kind == TokenKind.STRING:
                has_id = True
                token = self._next_token()

            if not has_id:
                self._error(token.line, token.pos, "Expected object identifier")

            if token.kind != TokenKind.START_OBJECT:
                self._error(token.line, token.pos, "Expected start of object")

            properties = _OBJ_PROPERTIES[object_type]
            self._check_object(object_type, token, properties, disposition)

    def _get_properties(self, object_name: str) -> dict[str, PropertyDef]:
        if (properties := get_rotation_properties(object_name)) is not None:
            return properties
        if (properties := get_orbit_properties(object_name)) is not None:
            return properties
        return super()._get_properties(object_name)

    def _validate_string(
        self, object_name: str, property_name: str, token: Token
    ) -> None:
        if property_name == "SpectralType":
            self._validate_sptype(token)
        else:
            validate_orbit_strings(
                object_name,
                property_name,
                token,
                lambda tok, msg: self._warn(tok.line, tok.pos, msg),
            )
            validate_rotation_strings(
                object_name,
                property_name,
                token,
                lambda tok, msg: self._warn(tok.line, tok.pos, msg),
            )
            super()._validate_string(object_name, property_name, token)

    def _validate_sptype(self, token: Token) -> None:
        if (match := _SPTYPE_REGEX.match(token.value)) is None:
            self._warn(token.line, token.pos, f"Invalid spectral type {token.value!r}")
            return

        if (
            (wdtype := match["wdtype"]) is not None
            and len(wdtype) == 2
            and wdtype[0] == wdtype[1]
        ):
            self._warn(
                token.line,
                token.pos,
                f"Spectral type {token.value!r} has duplicate extended type",
            )

        if (
            match["lumprefix"] is not None
            and match["lumtype"] is not None
            and match["lumtype"] != "VI"
        ):
            self._warn(
                token.line,
                token.pos,
                f"Spectral type {token.value!r} has mismatched luminosity types",
            )

        if match.end() != len(token.value):
            self._info(
                token.line,
                token.pos,
                f"Ignoring spectral type suffix on {token.value!r}: using {match[0]!r}",
            )

    def _validate_number(
        self, object_name: str, property_name: str, token: Token
    ) -> None:
        validate_orbit_numbers(
            object_name,
            property_name,
            token,
            lambda tok, msg: self._warn(tok.line, tok.pos, msg),
        )
        validate_rotation_numbers(
            object_name,
            property_name,
            token,
            lambda tok, msg: self._warn(tok.line, tok.pos, msg),
        )
        super()._validate_number(object_name, property_name, token)

    def _check_properties(
        self,
        object_name: str,
        open_token: Token,
        parsed_properties: set[str],
        disposition: Disposition,
    ) -> None:
        if object_name in ("Star", "Barycenter") and disposition != Disposition.MODIFY:
            if "OrbitBarycenter" in parsed_properties:
                if "Position" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Position ignored in favor of OrbitBarycenter",
                    )
                if "RA" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "RA ignored in favor of OrbitBarycenter",
                    )
                if "Dec" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Dec ignored in favor of OrbitBarycenter",
                    )
                if "Distance" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Distance ignored in favor of OrbitBarycenter",
                    )
                if not has_orbit(parsed_properties):
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "OrbitBarycenter specified without Orbit",
                    )
            elif has_orbit(parsed_properties):
                self._warn(
                    open_token.line,
                    open_token.pos,
                    "Orbit specified without OrbitBarycenter",
                )
            elif "Position" in parsed_properties:
                if "RA" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "RA ignored in favor of Position",
                    )
                if "Dec" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Dec ignored in favor of Position",
                    )
                if "Distance" in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Distance ignored in favor of Position",
                    )
            elif not {"RA", "Dec", "Distance"} <= parsed_properties:
                self._warn(
                    open_token.line,
                    open_token.pos,
                    "One of OrbitBarycenter, Position, or (RA, Dec, Distance) must be specified",
                )

            if object_name == "Star":
                if "AbsMag" in parsed_properties:
                    if "AppMag" in parsed_properties:
                        self._warn(
                            open_token.line,
                            open_token.pos,
                            "AppMag ignored in favor of AbsMag",
                        )
                elif "AppMag" not in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "One of AppMag or AbsMag must be specified",
                    )
                if "SpectralType" not in parsed_properties:
                    self._warn(
                        open_token.line,
                        open_token.pos,
                        "Spectral type must be specified",
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
