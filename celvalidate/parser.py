# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Base class for parser"""

import re

from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import NoReturn, Optional, TextIO

from .filenames import is_mesh_file, is_texture_file
from .tokenizer import (
    MessageLevel,
    ParsingError,
    ParsingMessage,
    Token,
    Tokenizer,
    TokenKind,
)


class DataType(Enum):
    """Property map data types"""

    BOOLEAN = auto()
    NUMBER = auto()
    VECTOR = auto()
    QUATERNION = auto()
    STRING = auto()
    OBJECT = auto()
    DATE = auto()
    NUMBER_OR_STRING = auto()
    STRING_LIST = auto()
    OBJECT_LIST = auto()
    VECTOR_OR_OBJECT = auto()
    COLOR = auto()


class UnitsType(Enum):
    """Property map units types"""

    LENGTH = auto()
    TIME = auto()
    ANGLE = auto()
    MASS = auto()
    SPHERICAL = auto()


_UNIT_TYPES = {
    # length units
    "km": UnitsType.LENGTH,
    "m": UnitsType.LENGTH,
    "rE": UnitsType.LENGTH,
    "rS": UnitsType.LENGTH,
    "au": UnitsType.LENGTH,
    "AU": UnitsType.LENGTH,
    "ly": UnitsType.LENGTH,
    "pc": UnitsType.LENGTH,
    "kpc": UnitsType.LENGTH,
    "Mpc": UnitsType.LENGTH,
    # time units
    "s": UnitsType.TIME,
    "min": UnitsType.TIME,
    "h": UnitsType.TIME,
    "d": UnitsType.TIME,
    "y": UnitsType.TIME,
    # angle units
    "mas": UnitsType.ANGLE,
    "arcsec": UnitsType.ANGLE,
    "arcmin": UnitsType.ANGLE,
    "deg": UnitsType.ANGLE,
    "hRA": UnitsType.ANGLE,
    "rad": UnitsType.ANGLE,
    # mass units
    "kg": UnitsType.MASS,
    "mE": UnitsType.MASS,
    "mJ": UnitsType.MASS,
}

_X11_COLORS = {
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "white",
    "whitesmoke",
    "yellow",
    "yellowgreen",
}

_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{3,8}$")


class Disposition(Enum):
    """Disposition"""

    ADD = auto()
    MODIFY = auto()
    REPLACE = auto()


type PropertyDef = tuple[DataType, Optional[UnitsType]]

_ISO_DATE_REGEX = re.compile(
    r"""^(?P<year>[+\-]?[0-9]+)-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})
        T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2}(?:\.[0-9]+)?)$""",
    re.VERBOSE,
)

_NORMAL_REGEX = re.compile(
    r"""^\s*(?P<year>[+\-]?[0-9]+)\s+(?P<month>[0-9]{1,2})\s+(?P<day>[0-9]{1,2})
        (\s+(?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{1,2})(?::(?P<second>[0-9]{1,2}(?:\.[0-9]+)?))?)?
        \s*$""",
    re.VERBOSE,
)


def _check_date_string(date_str: str) -> bool:
    if (match := _ISO_DATE_REGEX.match(date_str)) is None and (
        match := _NORMAL_REGEX.match(date_str)
    ) is None:
        return False

    try:
        year = int(match["year"])
        month = int(match["month"])
        if month < 1 or month > 12:
            return False

        day = int(match["day"])
        if day < 1:
            return False

        if month == 2:
            if year % 4 == 0 and (year <= 1582 or (year % 100 != 0 or year % 400 == 0)):
                month_days = 29
            else:
                month_days = 28
        elif month in (4, 6, 9, 11):
            month_days = 30
        else:
            month_days = 31

        if day > month_days:
            return False

        if match["hour"] is not None:
            hour = int(match["hour"])
            if hour < 0 or hour >= 24:
                return False
            minute = int(match["minute"])
            if minute < 0 or minute >= 60:
                return False

            if match["second"] is not None:
                second = float(match["second"])
                if second < 0 or second >= 60:
                    return False
    except ValueError:
        return False
    else:
        return True


class TokenFileParser(ABC):
    """Common class for processing data files"""

    tokenizer: Tokenizer
    _messages: list[ParsingMessage]
    saved_token: Optional[Token]

    def __init__(self, f: TextIO) -> None:
        self.tokenizer = Tokenizer(f)
        self._messages = []
        self.saved_token = None

    @abstractmethod
    def parse(self) -> None:
        """Parse a data file"""

    @property
    def messages(self) -> list[ParsingMessage]:
        """Get the generated error messages"""
        messages = self.tokenizer.messages + self._messages
        messages.sort(key=lambda m: (m.line, m.pos))
        return messages

    def _error(self, line: int, pos: int, message: str) -> NoReturn:
        self._messages.append(ParsingMessage(line, pos, MessageLevel.ERROR, message))
        raise ParsingError(message)

    def _warn(self, line: int, pos: int, message: str) -> None:
        self._messages.append(ParsingMessage(line, pos, MessageLevel.WARN, message))

    def _info(self, line: int, pos: int, message: str) -> None:
        self._messages.append(ParsingMessage(line, pos, MessageLevel.INFO, message))

    def _next_token(
        self,
        kind: Optional[TokenKind] = None,
        message: Optional[str] = None,
        is_error: bool = False,
        allow_eof: bool = False,
    ) -> Optional[Token]:
        if self.saved_token is not None:
            token = self.saved_token
            self.saved_token = None
            return token

        token = next(self.tokenizer, None)
        if token is None:
            if not allow_eof:
                self._error(
                    self.tokenizer.line_number, self.tokenizer.pos, "Unexpected EOF"
                )
            return None

        if kind is not None and token.kind != kind:
            if is_error:
                self._error(token.line, token.pos, message)
            else:
                self._warn(token.line, token.pos, message)

        return token

    def _push_back(self, token: Token) -> None:
        self.saved_token = token

    def _skip_structure(self, open_token: TokenKind) -> None:
        struct_stack = [open_token]
        while struct_stack:
            token = self._next_token()
            match token.kind:
                case (
                    TokenKind.START_OBJECT
                    | TokenKind.START_ARRAY
                    | TokenKind.START_UNITS
                ):
                    struct_stack.append(token.kind)
                case TokenKind.END_OBJECT:
                    if struct_stack.pop() != TokenKind.START_OBJECT:
                        self._error(token.line, token.pos, "Mismatched nesting")
                case TokenKind.END_ARRAY:
                    if struct_stack.pop() != TokenKind.START_ARRAY:
                        self._error(token.line, token.pos, "Mismatched nesting")
                case TokenKind.END_UNITS:
                    if struct_stack.pop() != TokenKind.START_UNITS:
                        self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    pass

    def _skip_value(self) -> None:
        token = self._next_token()
        if token.kind == TokenKind.START_UNITS:
            self._skip_structure(TokenKind.START_UNITS)
            token = self._next_token()
        match token.kind:
            case TokenKind.START_OBJECT | TokenKind.START_ARRAY:
                self._skip_structure(token.kind)
            case TokenKind.START_UNITS:
                self._warn(token.line, token.pos, "Unexpected units definition")
                self._skip_structure(token.kind)
            case TokenKind.NAME | TokenKind.END_OBJECT:
                self._push_back(token)
            case TokenKind.END_ARRAY | TokenKind.END_UNITS:
                self._error(token.line, token.pos, "Mismatched nesting")
            case _:
                pass

    def _check_spherical_units(self) -> None:
        has_angle_unit = False
        has_length_unit = False
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.NAME:
                    unit_type = _UNIT_TYPES.get(token.value, None)
                    if unit_type is None:
                        self._warn(
                            token.line, token.pos, f"Unknown unit type {token.value}"
                        )
                    elif unit_type == UnitsType.ANGLE:
                        if has_angle_unit:
                            self._warn(token.line, token.pos, "Duplicate angle unit")
                        else:
                            has_angle_unit = True
                    elif unit_type == UnitsType.LENGTH:
                        if has_length_unit:
                            self._warn(token.line, token.pos, "Duplicate length unit")
                        else:
                            has_length_unit = True
                    else:
                        self._warn(
                            token.line,
                            token.pos,
                            f"Unexpected unit type {token.value} ignored",
                        )
                case TokenKind.END_UNITS:
                    break
                case TokenKind.START_ARRAY:
                    self._warn(token.line, token.pos, "Unexpected array in units block")
                    self._skip_structure(token.kind)
                case TokenKind.START_OBJECT:
                    self._warn(
                        token.line, token.pos, "Unexpected object in units block"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.START_UNITS:
                    self._warn(token.line, token.pos, "Unexpected nested units block")
                    self._skip_structure(token.kind)
                case TokenKind.END_ARRAY | TokenKind.END_OBJECT:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Unexpected token in units block")
        if not has_angle_unit:
            self._warn(token.line, token.pos, "Expected angle unit")
        if not has_length_unit:
            self._warn(token.line, token.pos, "Expected length unit")

    def _check_units(self, expected_units: UnitsType) -> None:
        if expected_units == UnitsType.SPHERICAL:
            self._check_spherical_units()
            return

        has_unit = False
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.NAME:
                    actual_units = _UNIT_TYPES.get(token.value, None)
                    if actual_units is None:
                        self._warn(
                            token.line, token.pos, f"Unknown unit type {token.value}"
                        )
                    elif actual_units != expected_units:
                        self._warn(
                            token.line,
                            token.pos,
                            f"Unexpected unit type {token.value} ignored",
                        )
                    elif has_unit:
                        self._warn(token.line, token.pos, "Multiple units found")

                    has_unit = True
                case TokenKind.END_UNITS:
                    break
                case TokenKind.START_ARRAY:
                    self._warn(token.line, token.pos, "Unexpected array in units block")
                    self._skip_structure(token.kind)
                case TokenKind.START_OBJECT:
                    self._warn(
                        token.line, token.pos, "Unexpected object in units block"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.START_UNITS:
                    self._warn(token.line, token.pos, "Unexpected nested units block")
                    self._skip_structure(token.kind)
                case TokenKind.END_ARRAY | TokenKind.END_OBJECT:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Unexpected token in units block")
        if not has_unit:
            self._warn(token.line, token.pos, "Empty unit block")

    def _check_vector(
        self, property_name: str, element_count: int | tuple[int, int]
    ) -> None:
        num_elements = 0
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.NUMBER:
                    num_elements += 1
                    self._validate_number(property_name, "[]", token)
                case TokenKind.END_ARRAY:
                    break
                case TokenKind.START_ARRAY:
                    self._warn(token.line, token.pos, "Unexpected sub-array in vector")
                    self._skip_structure(token.kind)
                case TokenKind.START_OBJECT:
                    self._warn(token.line, token.pos, "Unexpected sub-object in vector")
                    self._skip_structure(token.kind)
                case TokenKind.START_UNITS:
                    self._warn(
                        token.line, token.pos, "Unexpected units block in vector"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.END_OBJECT | TokenKind.END_UNITS:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Non-numeric token in vector")
        if (isinstance(element_count, int) and num_elements == element_count) or (
            element_count[0] <= num_elements <= element_count[1]
        ):
            return

        self._warn(
            token.line,
            token.pos,
            f"Expected {element_count} elements in vector, found {num_elements}",
        )

    def _check_string_list(self, property_name: str) -> None:
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.STRING:
                    self._validate_string(property_name, "[]", token)
                case TokenKind.END_ARRAY:
                    break
                case TokenKind.START_ARRAY:
                    self._warn(
                        token.line, token.pos, "Unexpected sub-array in string list"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.START_OBJECT:
                    self._warn(
                        token.line, token.pos, "Unexpected sub-object in string list"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.START_UNITS:
                    self._warn(
                        token.line, token.pos, "Unexpected units block in string list"
                    )
                    self._skip_structure(token.kind)
                case TokenKind.END_OBJECT | TokenKind.END_UNITS:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Non-string token in string list")

    def _validate_string(
        self,
        object_name: str,  # pylint: disable=unused-argument
        property_name: str,
        token: Token,
    ) -> None:
        match property_name:
            case "Mesh":
                if not is_mesh_file(token.value):
                    self._warn(
                        token.line, token.pos, f"Bad mesh filename {token.value!r}"
                    )
            case "Texture":
                if not is_texture_file(token.value):
                    self._warn(
                        token.line, token.pos, f"Bad texture filename {token.value!r}"
                    )
            case _:
                pass

    def _validate_number(
        self,
        object_name: str,
        property_name: str,
        token: Token,
    ) -> None:
        match property_name:
            case "Radius" | "Temperature" | "Mass":
                if token.value <= 0:
                    self._warn(
                        token.line,
                        token.pos,
                        f"{property_name} must be strictly positive",
                    )
            case "[]":
                if object_name == "__color":
                    if token.value < 0 or token.value > 1:
                        self._warn(
                            token.line,
                            token.pos,
                            "Color elements must be in range [0, 1]",
                        )
                if object_name == "SemiAxes":
                    if token.value <= 0:
                        self._warn(
                            token.line,
                            token.pos,
                            "SemiAxes element must be strictly positive",
                        )
            case _:
                pass

    def _check_value(
        self,
        object_name: str,
        property_name: str,
        data_type: DataType,
        units_type: Optional[UnitsType],
    ) -> None:
        token = self._next_token()
        if token.kind == TokenKind.START_UNITS:
            if units_type is None:
                self._warn(token.line, token.pos, f"Units ignored for {property_name}")
                self._skip_structure(token.kind)
            else:
                self._check_units(units_type)
            token = self._next_token()

        if token.kind in (TokenKind.END_ARRAY, TokenKind.END_UNITS):
            self._error(token.line, token.pos, "Mismatched nesting")
        if token.kind == TokenKind.END_OBJECT:
            self._warn(token.line, token.pos, "Expected value, got end of object")
            self._push_back(token)
            return

        is_match = True
        match data_type:
            case DataType.BOOLEAN:
                if token.kind != TokenKind.BOOLEAN:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected a boolean for {property_name}"
                    )
            case DataType.NUMBER:
                if token.kind == TokenKind.NUMBER:
                    self._validate_number(object_name, property_name, token)
                else:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected a number for {property_name}"
                    )
            case DataType.VECTOR:
                if token.kind == TokenKind.START_ARRAY:
                    self._check_vector(property_name, 3)
                else:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected a vector for {property_name}"
                    )
            case DataType.QUATERNION:
                if token.kind == TokenKind.START_ARRAY:
                    self._check_vector(property_name, 4)
                else:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected a quaternion for {property_name}",
                    )
            case DataType.STRING:
                if token.kind == TokenKind.STRING:
                    self._validate_string(object_name, property_name, token)
                else:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected a string for {property_name}"
                    )
            case DataType.OBJECT:
                if token.kind == TokenKind.START_OBJECT:
                    properties = self._get_properties(property_name)
                    self._check_object(property_name, token, properties)
                else:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected an object for {property_name}"
                    )
            case DataType.DATE:
                if token.kind == TokenKind.STRING:
                    if not _check_date_string(token.value):
                        self._warn(
                            token.line,
                            token.pos,
                            f"Invalid date string for {property_name}",
                        )
                elif token.kind != TokenKind.NUMBER:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected either number or date string for {property_name}",
                    )
            case DataType.NUMBER_OR_STRING:
                if token.kind == TokenKind.NUMBER:
                    self._validate_number(object_name, property_name, token)
                elif token.kind == TokenKind.STRING:
                    self._validate_string(object_name, property_name, token)
                else:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected either number or string for {property_name}",
                    )
            case DataType.STRING_LIST:
                if token.kind == TokenKind.START_ARRAY:
                    self._check_string_list(property_name)
                elif token.kind != TokenKind.STRING:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected either string or string list for {property_name}",
                    )
            case DataType.OBJECT_LIST:
                if token.kind == TokenKind.START_ARRAY:
                    properties = self._get_properties(property_name)
                    self._check_object_list(property_name, properties)
                else:
                    is_match = False
                    self._warn(
                        token.line, token.pos, f"Expected an array for {property_name}"
                    )
            case DataType.VECTOR_OR_OBJECT:
                if token.kind == TokenKind.START_ARRAY:
                    self._check_vector(property_name, 3)
                elif token.kind == TokenKind.START_OBJECT:
                    properties = self._get_properties(property_name)
                    self._check_object(property_name, token, properties)
                else:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected either vector or object for {property_name}",
                    )
            case DataType.COLOR:
                if token.kind == TokenKind.STRING:
                    if not (
                        token.value in _X11_COLORS
                        or (
                            len(token.value) in (4, 7, 9)
                            and _COLOR_REGEX.match(token.value) is not None
                        )
                    ):
                        self._warn(
                            token.line,
                            token.pos,
                            f"Could not parse {token.value!r} as a valid color",
                        )
                elif token.kind == TokenKind.START_ARRAY:
                    self._check_vector("__color", (3, 4))
                else:
                    is_match = False
                    self._warn(
                        token.line,
                        token.pos,
                        f"Expected either color vector or string for {property_name}",
                    )

        if not is_match:
            self._push_back(token)
            if token.kind != TokenKind.NAME:
                self._skip_value()

    def _get_properties(self, object_name: str) -> dict[str, PropertyDef]:
        raise RuntimeError(f"No object mapping defined for object type {object_name}")

    def _check_object(
        self,
        object_name: str,
        open_token: Token,
        properties: dict[str, PropertyDef],
        disposition: Disposition = Disposition.ADD,
    ) -> None:
        parsed_properties: set[str] = set()
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.NAME:
                    if token.value in parsed_properties:
                        self._warn(
                            token.line, token.pos, f"Duplicate property {token.value}"
                        )
                    else:
                        parsed_properties.add(token.value)
                    try:
                        data_type, unit_type = properties[token.value]
                    except KeyError:
                        self._warn(
                            token.line, token.pos, f"Unknown property {token.value}"
                        )
                        self._skip_value()
                    else:
                        self._check_value(
                            object_name, token.value, data_type, unit_type
                        )
                case TokenKind.END_OBJECT:
                    break
                case TokenKind.END_ARRAY | TokenKind.END_UNITS:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Expected property")
                    self._push_back(token)
                    self._skip_value()
        self._check_properties(object_name, open_token, parsed_properties, disposition)

    def _check_object_list(
        self, object_name: str, properties: dict[str, PropertyDef]
    ) -> None:
        while True:
            token = self._next_token()
            match token.kind:
                case TokenKind.START_OBJECT:
                    self._check_object(object_name, token, properties)
                case TokenKind.END_ARRAY:
                    break
                case TokenKind.END_OBJECT | TokenKind.END_UNITS:
                    self._error(token.line, token.pos, "Mismatched nesting")
                case _:
                    self._warn(token.line, token.pos, "Expected object")
                    self._push_back(token)
                    self._skip_value()

    def _check_properties(
        self,
        object_name: str,
        open_token: Token,
        parsed_properties: set[str],
        disposition: Disposition,
    ) -> None:
        pass
