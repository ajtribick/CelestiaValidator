# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Celestia file tokenizer"""

import re

from enum import auto, Enum, IntEnum
from io import StringIO
from typing import Iterator, NamedTuple, NoReturn, TextIO

_NAME_REGEX = re.compile(r"[A-Za-z_][0-9A-Za-z_]*")
_NUMBER_REGEX = re.compile(r"[+\-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?")

class ParsingError(Exception):
    """Represents an error generated from the tokenizer/parser"""

class MessageLevel(IntEnum):
    """Represents the message level"""
    INFO = auto()
    WARN = auto()
    ERROR = auto()

class ParsingMessage(NamedTuple):
    """Represents a parsing message"""
    line: int
    pos: int
    level: MessageLevel
    message: str

    def __str__(self) -> str:
        match self.level:
            case MessageLevel.INFO:
                mtype = 'INF'
            case MessageLevel.WARN:
                mtype = 'WRN'
            case _:
                mtype = 'ERR'
        return f"{mtype} ({self.line}:{self.pos}) {self.message}"

class TokenKind(Enum):
    """Token types"""
    NAME = auto()
    BOOLEAN = auto()
    STRING = auto()
    NUMBER = auto()
    START_OBJECT = auto()
    END_OBJECT = auto()
    START_ARRAY = auto()
    END_ARRAY = auto()
    START_UNITS = auto()
    END_UNITS = auto()
    EQUALS = auto()
    BAR = auto()

    def __str__(self):
        return super().__str__().removeprefix('TokenKind.')

    def __repr__(self):
        type_str = super().__str__()
        if type_str.startswith('TokenKind.'):
            return type_str
        return f"TokenKind.{type_str}"

type TokenValue = str | bool | int | float | None

class Token:
    """Celestia catalog file token"""
    kind: TokenKind
    line: int
    pos: int
    value: TokenValue

    def __init__(
        self,
        kind: TokenKind,
        line: int,
        pos: int,
        value: TokenValue = None
    ) -> None:
        self.kind = kind
        self.line = line
        self.pos = pos
        self.value = value

    def __str__(self) -> str:
        if self.value is None:
            return str(self.kind)
        return f'{self.kind}({self.value!r})'

    def __repr__(self) -> str:
        if self.value is None:
            return f"Token({self.kind!r})"
        return f"Token({self.kind!r}, {self.value!r})"


class Tokenizer:
    """Processes a Celestia catalog file into a series of tokens"""
    f: TextIO
    line: str
    pos: int
    line_number: int
    messages: list[ParsingMessage]

    def __init__(self, f: TextIO) -> None:
        self.f = f
        self.line = b""
        self.pos = 0
        self.line_number = 0
        self.messages = []

    def __next__(self) -> Token:
        try:
            while True:
                while self.pos == len(self.line):
                    self._read_line()

                match self.line[self.pos]:
                    case '\t' | ' ':
                        self.pos += 1
                    case '#':
                        self.pos = len(self.line)
                    case '"':
                        return self._read_string()
                    case '{':
                        token = Token(TokenKind.START_OBJECT, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '}':
                        token = Token(TokenKind.END_OBJECT, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '[':
                        token = Token(TokenKind.START_ARRAY, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case ']':
                        token = Token(TokenKind.END_ARRAY, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '<':
                        token = Token(TokenKind.START_UNITS, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '>':
                        token = Token(TokenKind.END_UNITS, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '=':
                        token = Token(TokenKind.EQUALS, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case '|':
                        token = Token(TokenKind.BAR, self.line_number, self.pos)
                        self.pos += 1
                        return token
                    case c:
                        line_number = self.line_number
                        pos = self.pos
                        m = _NAME_REGEX.match(self.line, self.pos)
                        if m:
                            self.pos = m.end()
                            match m.group():
                                case "false":
                                    return Token(TokenKind.BOOLEAN, line_number, pos, False)
                                case "true":
                                    return Token(TokenKind.BOOLEAN, line_number, pos, True)
                                case name:
                                    return Token(TokenKind.NAME, line_number, pos, name)
                        m = _NUMBER_REGEX.match(self.line, self.pos)
                        if m:
                            self.pos = m.end()
                            try:
                                value = int(m.group())
                            except ValueError:
                                value = float(m.group())
                            return Token(TokenKind.NUMBER, line_number, pos, value)

                        self._warn(f"Unexpected character {c!r} in file")
                        self.pos += 1
        except ParsingError as ex:
            raise StopIteration from ex

    def _warn(self, message: str) -> None:
        self.messages.append(ParsingMessage(self.line_number, self.pos, MessageLevel.WARN, message))

    def _error(self, message: str) -> NoReturn:
        self.messages.append(
            ParsingMessage(self.line_number, self.pos, MessageLevel.ERROR, message)
        )
        raise ParsingError(message)

    def _read_line(self) -> None:
        self.line = self.f.readline()
        if not self.line:
            raise StopIteration
        self.line = self.line.rstrip()
        self.pos = 0
        self.line_number += 1

    def _read_string(self) -> Token:
        line_number = self.line_number
        pos = self.pos
        with StringIO() as output:
            self.pos += 1
            while True:
                while self.pos == len(self.line):
                    try:
                        self._read_line()
                    except StopIteration:
                        self._error("Unterminated string")
                c = self.line[self.pos]
                self.pos += 1
                if c == '"':
                    return Token(TokenKind.STRING, line_number, pos, output.getvalue())
                if c == '\\':
                    c = self._parse_escape()
                if c == '\ufffd':
                    self._warn("Invalid UTF-8 in string literal")
                output.write(c)

    def _parse_escape(self) -> str:
        if self.pos == len(self.line):
            self._error("Unterminated escape sequence")
        c = self.line[self.pos]
        self.pos += 1
        match c:
            case '"' | '\\':
                return c
            case 'n':
                return '\n'
            case 'u':
                start_pos = self.pos
                self.pos += 4
                if self.pos >= len(self.line):
                    self._error("Unterminated Unicode escape")
                c = chr(int(self.line[start_pos:self.pos], 16)).encode('utf-8')
            case _:
                return None

    def __iter__(self) -> Iterator[Token]:
        return self
